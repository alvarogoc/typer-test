#!/usr/bin/env python3
"""
typer-test - a terminal typing trainer for practicing English.

It generates a fresh practice quote every round with `claude -p`, then has you
type it MonkeyType-style (gray text that turns white as you type, red on a
mistake). The quotes are deliberately built around the kinds of mistakes the
author is working on:

  * punctuation   -> where to put  .   ,   and  ;
  * contractions  -> you're, you've, I'd, I've, it's, don't, that's ...
  * the always-capital "I" and correct  a / an  usage

If `claude` is not installed or a request fails, it falls back to a built-in
set of quotes so the trainer always works offline.

Usage:
  typer-test                      start a test (60s, mixed mode, AI quotes)
  typer-test --time 120           longer test
  typer-test --mode punctuation   drill commas, periods, semicolons
  typer-test --mode contractions  drill you're / you've / I'd ...
  typer-test --mode plain         no contractions, only commas and periods
  typer-test --offline            skip claude, use built-in quotes
  typer-test --help

Controls:
  start screen : Enter=start  t=change time  m=change mode  a=AI on/off  q=quit
  while typing : type the gray text; Backspace fixes a slip; Esc cancels
  results      : Enter=again  s=settings  q=quit
"""

import argparse
import curses
import random
import shutil
import subprocess
import threading
import time

# ---------------------------------------------------------------------------
# Content
# ---------------------------------------------------------------------------

# Built-in fallback quotes (used when claude is unavailable). They are written
# to exercise the same skills the AI prompt targets.
QUOTES = {
    "contractions": [
        "I'm certain you're going to make it; I've watched you try, you've never quit, and that's exactly why I'd bet on you.",
        "You're not behind, you're just early; don't rush it, because what's worth building isn't finished in a single day.",
        "I'd rather fail at something I've chosen than win at something I'd never wanted; that's a lesson you've earned, not borrowed.",
        "It's strange how we're sure we'll remember, yet we don't; so write it down, because tomorrow's mind isn't today's.",
        "Don't wait until you're ready; you'll never feel ready, and the ones who've grown are simply the ones who've started scared.",
    ],
    "punctuation": [
        "Read it once, then read it again; the first time you meet the words, the second time you understand them.",
        "Plans change, people grow, and seasons turn; nothing stays, so hold it gently while it lasts.",
        "She packed three things: a map, a coat, and a reason. The map was old, the coat was thin; the reason was enough.",
        "Work hard, rest well, and choose kindly; a good life is not one decision, but a thousand small, quiet ones.",
        "First, you learn the rules; then, you practice them; finally, you forget them, and you simply write.",
    ],
    "mixed": [
        "An idea is a fragile thing; it's easy to crush, hard to grow, and you're its only gardener, so don't look away.",
        "I've learned a simple truth: an honest no is kinder than a soft maybe, and you'll sleep better once you've said it.",
        "There's an art to waiting. You're not wasting time; you're letting it ripen, and what's rushed is rarely what's right.",
        "A goal without a date is a wish; so pick a day, mark it down, and tell yourself, I'll start, and I won't stop.",
        "It's not a lack of time; it's a lack of focus. Choose one thing, finish it, and then you've earned the next.",
    ],
    "plain": [
        "Success is not an accident. It is the result of preparation, effort, and learning from every mistake you make.",
        "Great things take time. Focus on one step, finish it well, and the next step will feel much easier.",
        "A calm mind sees clearly. When you slow down, breathe, and think before you act, you make better choices.",
        "Small habits build big results. Read a little every day, practice a little every day, and watch yourself grow.",
        "Kindness costs nothing but means everything. A simple smile, a patient word, or a helping hand can brighten a whole room.",
    ],
}

TIPS = [
    "Comma = a short pause or a list. Period = a full stop. Semicolon = links two complete sentences.",
    "A semicolon joins two full thoughts: 'I tried; I failed; I learned.' Each side could stand alone.",
    "'you're' = you are. 'your' = belongs to you. Swap in 'you are' to check which one fits.",
    "'I've' = I have. 'I'd' = I would (or I had). The apostrophe stands in for the dropped letters.",
    "The word 'I' is always a capital letter, even when it stands alone.",
    "Use 'an' before a vowel SOUND (an idea, an hour); use 'a' before a consonant sound (a goal, a user).",
    "A colon introduces a list or an explanation: exactly like this one does.",
]

PUNCT = set(".,;:!?'\"-")
MODES = ["mixed", "punctuation", "contractions", "plain"]
TIMES = [30, 60, 90, 120, 180]
CLAUDE_TIMEOUT = 45  # seconds to wait for `claude -p`


def pool(mode):
    if mode == "mixed":
        return QUOTES["contractions"] + QUOTES["punctuation"] + QUOTES["mixed"]
    return QUOTES[mode]


# ---------------------------------------------------------------------------
# Quote generation via `claude -p`
# ---------------------------------------------------------------------------

# Normalise the "smart" characters an LLM may emit into plain keyboard ASCII,
# so every character can actually be typed on a normal keyboard.
_TRANS = {
    "’": "'", "‘": "'", "“": '"', "”": '"',
    "—": "-", "–": "-", "…": "...", " ": " ",
    "«": '"', "»": '"',
}


def clean_quote(text):
    """Turn raw model output into a single typeable line."""
    for a, b in _TRANS.items():
        text = text.replace(a, b)
    text = "".join(ch for ch in text if (32 <= ord(ch) < 127) or ch in "\n\t")
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    if not lines:
        return ""
    q = " ".join(max(lines, key=len).split())
    if len(q) >= 2 and q[0] == '"' and q[-1] == '"':
        q = q[1:-1].strip()
    if len(q) >= 2 and q[0] == "`" and q[-1] == "`":
        q = q[1:-1].strip()
    return q


def build_prompt(mode):
    base = ("Write one original, uplifting one-sentence quote of about 18 to 28 words "
            "(no author, no title, no explanation). ")
    if mode == "contractions":
        focus = ("It MUST naturally use at least four contractions such as you're, you've, "
                 "I'd, I've, it's, don't, that's, we're. Include some commas and at least one semicolon. ")
    elif mode == "punctuation":
        focus = ("It MUST use several commas, at least one semicolon, and a colon if it fits, "
                 "so it is good practice for where punctuation goes. ")
    elif mode == "plain":
        focus = ("It MUST NOT use any contractions or apostrophes at all (write 'do not' instead of "
                 "'don't', 'it is' instead of 'it's'). It MUST NOT use semicolons or colons. "
                 "Use ONLY commas and a final period as punctuation. ")
    else:
        focus = ("It MUST use at least three contractions (you're, you've, I'd, it's, don't), "
                 "several commas, and at least one semicolon. ")
    tail = "Output ONLY the quote text on a single line: no quotation marks, no preamble, no markdown."
    return base + focus + tail


def claude_available():
    return shutil.which("claude") is not None


def generate_quote(mode, holder=None):
    """Return (quote, source). source is 'claude' or 'offline'."""
    proc = None
    try:
        proc = subprocess.Popen(
            ["claude", "-p", build_prompt(mode)],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        )
        if holder is not None:
            holder["proc"] = proc
        out, _ = proc.communicate(timeout=CLAUDE_TIMEOUT)
        if proc.returncode == 0:
            q = clean_quote(out or "")
            if len(q) >= 20:
                return q, "claude"
    except Exception:
        if proc is not None:
            try:
                proc.kill()
            except Exception:
                pass
    return random.choice(pool(mode)), "offline"


# ---------------------------------------------------------------------------
# Curses helpers
# ---------------------------------------------------------------------------

P_DIM, P_GOOD, P_BAD, P_ACCENT, P_WARN, P_OK = 1, 2, 3, 4, 5, 6


def init_colors():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(P_DIM, curses.COLOR_WHITE, -1)
    curses.init_pair(P_GOOD, curses.COLOR_WHITE, -1)
    curses.init_pair(P_BAD, curses.COLOR_RED, -1)
    curses.init_pair(P_ACCENT, curses.COLOR_CYAN, -1)
    curses.init_pair(P_WARN, curses.COLOR_YELLOW, -1)
    curses.init_pair(P_OK, curses.COLOR_GREEN, -1)


def safe_add(stdscr, y, x, text, attr=0):
    h, w = stdscr.getmaxyx()
    if y < 0 or y >= h or x < 0 or x >= w:
        return
    try:
        stdscr.addstr(y, x, text[: max(0, w - x - 1)], attr)
    except curses.error:
        pass


def layout(target, width):
    """Map each char index of target to (row, col) using word wrapping."""
    positions = {}
    words = []
    idx = 0
    for w in target.split(" "):
        words.append((idx, w))
        idx += len(w) + 1
    row = col = 0
    for start, w in words:
        wlen = len(w)
        if col > 0:  # the space before this word lives at index start-1
            if col + 1 + wlen > width:
                positions[start - 1] = (row, min(col, width - 1))
                row += 1
                col = 0
            else:
                positions[start - 1] = (row, col)
                col += 1
        for j in range(wlen):
            positions[start + j] = (row, col)
            col += 1
    return positions


# ---------------------------------------------------------------------------
# Screens
# ---------------------------------------------------------------------------

def menu_screen(stdscr, settings):
    stdscr.nodelay(False)
    while True:
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        m = 4
        y = 2
        safe_add(stdscr, y, m, "TYPER-TEST", curses.color_pair(P_ACCENT) | curses.A_BOLD | curses.A_UNDERLINE)
        y += 2
        safe_add(stdscr, y, m, "Practice English: punctuation ( . , ; ) and contractions ( you're, I'd, you've ).", curses.A_DIM)
        y += 1
        safe_add(stdscr, y, m, "A fresh quote is written for you each round by claude.", curses.A_DIM)
        y += 2
        safe_add(stdscr, y, m, "time   {}s".format(settings["time"]), curses.color_pair(P_OK) | curses.A_BOLD)
        y += 1
        safe_add(stdscr, y, m, "mode   {}".format(settings["mode"]), curses.color_pair(P_OK) | curses.A_BOLD)
        y += 1
        ai_on = settings["ai"] and claude_available()
        ai_txt = "claude" if ai_on else ("off" if not settings["ai"] else "unavailable -> built-in")
        safe_add(stdscr, y, m, "quotes {}".format(ai_txt), curses.color_pair(P_OK) | curses.A_BOLD)
        y += 2
        safe_add(stdscr, y, m, "[Enter] start", curses.A_BOLD)
        y += 1
        safe_add(stdscr, y, m, "[t] time   [m] mode   [a] AI on/off   [q] quit", curses.A_DIM)
        stdscr.refresh()
        ch = stdscr.getch()
        if ch in (10, 13, curses.KEY_ENTER):
            return "start"
        if ch in (ord("t"), ord("T")):
            times = sorted(set(TIMES + [settings["time"]]))
            settings["time"] = times[(times.index(settings["time"]) + 1) % len(times)]
        elif ch in (ord("m"), ord("M")):
            settings["mode"] = MODES[(MODES.index(settings["mode"]) + 1) % len(MODES)]
        elif ch in (ord("a"), ord("A")):
            settings["ai"] = not settings["ai"]
        elif ch in (ord("q"), ord("Q"), 27):
            return "quit"


def loading_screen(stdscr, settings):
    """Fetch a quote from claude while showing a spinner. Returns (quote, source)."""
    holder = {}
    result = {}

    def work():
        result["q"], result["src"] = generate_quote(settings["mode"], holder=holder)

    t = threading.Thread(target=work, daemon=True)
    t.start()
    stdscr.nodelay(True)
    frames = "|/-\\"
    i = 0
    while t.is_alive():
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        safe_add(stdscr, h // 2 - 1, 4, "writing a fresh quote with claude  {}".format(frames[i % 4]),
                 curses.color_pair(P_ACCENT) | curses.A_BOLD)
        safe_add(stdscr, h // 2 + 1, 4, "[Esc] skip and use a built-in quote", curses.A_DIM)
        stdscr.refresh()
        ch = stdscr.getch()
        if ch == 27:
            proc = holder.get("proc")
            if proc is not None:
                try:
                    proc.terminate()
                except Exception:
                    pass
            return random.choice(pool(settings["mode"])), "offline"
        time.sleep(0.08)
        i += 1
    return result.get("q") or random.choice(pool(settings["mode"])), result.get("src", "offline")


def draw_test(stdscr, target, typed, time_left, wpm, acc, source):
    stdscr.erase()
    h, w = stdscr.getmaxyx()
    margin = 4
    text_w = max(20, w - margin * 2)
    status = " time {:>3}s    wpm {:>3}    acc {:>3}% ".format(int(round(time_left)), int(wpm), int(acc))
    safe_add(stdscr, 1, margin, status, curses.color_pair(P_ACCENT) | curses.A_BOLD)
    safe_add(stdscr, 1, w - margin - 12, "Esc cancel", curses.A_DIM)
    positions = layout(target, text_w)
    top = 4
    n = len(target)
    tlen = len(typed)
    for i in range(n):
        pos = positions.get(i)
        if pos is None:
            continue
        ch = target[i]
        r, c = pos
        y, x = top + r, margin + c
        if y >= h - 2:
            break
        if i < tlen:
            if typed[i] == ch:
                disp, attr = ch, curses.color_pair(P_GOOD) | curses.A_BOLD
            elif ch == " ":
                disp, attr = "_", curses.color_pair(P_BAD)
            else:
                disp, attr = ch, curses.color_pair(P_BAD) | curses.A_UNDERLINE
        elif i == tlen:
            disp, attr = ch, curses.A_REVERSE
        else:
            disp, attr = ch, curses.color_pair(P_DIM) | curses.A_DIM
        safe_add(stdscr, y, x, disp, attr)
    pct = int(tlen * 100 / n) if n else 0
    safe_add(stdscr, h - 2, margin, "progress {}%    quote: {}".format(pct, source), curses.A_DIM)
    stdscr.refresh()


def run_test(stdscr, target, source, settings):
    """Returns a result dict, or None if the user pressed Esc."""
    typed = []
    start = None
    total_keys = 0
    error_keys = 0
    stdscr.nodelay(True)
    try:
        while True:
            now = time.time()
            if start is not None:
                elapsed = now - start
                time_left = settings["time"] - elapsed
                if time_left <= 0:
                    break
            else:
                elapsed = 0.0
                time_left = settings["time"]
            correct = sum(1 for i, c in enumerate(typed) if c == target[i])
            wpm = (correct / 5) / (elapsed / 60) if elapsed > 0 else 0
            acc = (total_keys - error_keys) / total_keys * 100 if total_keys else 100
            draw_test(stdscr, target, typed, time_left, wpm, acc, source)
            ch = stdscr.getch()
            if ch == -1:
                time.sleep(0.03)
                continue
            if ch == 27:
                return None
            if ch in (curses.KEY_BACKSPACE, 127, 8):
                if typed:
                    typed.pop()
                continue
            if ch == curses.KEY_RESIZE:
                continue
            if 32 <= ch <= 126:
                if start is None:
                    start = time.time()
                i = len(typed)
                if i < len(target):
                    c = chr(ch)
                    typed.append(c)
                    total_keys += 1
                    if c != target[i]:
                        error_keys += 1
                    if len(typed) >= len(target):
                        break
    finally:
        stdscr.nodelay(False)
    elapsed = (time.time() - start) if start else 0.0
    return analyze(target, typed, elapsed, total_keys, error_keys, source, settings)


def analyze(target, typed, elapsed, total_keys, error_keys, source, settings):
    tlen = len(typed)
    correct = sum(1 for i, c in enumerate(typed) if c == target[i])
    wpm = (correct / 5) / (elapsed / 60) if elapsed > 0 else 0
    raw = (tlen / 5) / (elapsed / 60) if elapsed > 0 else 0
    acc = (total_keys - error_keys) / total_keys * 100 if total_keys else 0

    punct_total = punct_ok = 0
    for i, ch in enumerate(target):
        if ch in PUNCT and i < tlen:
            punct_total += 1
            if typed[i] == ch:
                punct_ok += 1

    review = []
    contractions_total = contractions_ok = 0
    idx = 0
    for w in target.split(" "):
        wstart, wend = idx, idx + len(w)
        idx = wend + 1
        if wstart >= tlen:
            continue
        wrong = any(j < tlen and typed[j] != target[j] for j in range(wstart, wend))
        if "'" in w:
            contractions_total += 1
            if not wrong and wend <= tlen:
                contractions_ok += 1
        if wrong:
            clean = w.strip(".,;:!?\"")
            if clean and clean not in review:
                review.append(clean)

    return {
        "elapsed": elapsed, "wpm": wpm, "raw": raw, "acc": acc,
        "punct_total": punct_total, "punct_ok": punct_ok,
        "contractions_total": contractions_total, "contractions_ok": contractions_ok,
        "review": review, "source": source, "settings": dict(settings),
    }


def results_screen(stdscr, r):
    stdscr.nodelay(False)
    tip = random.choice(TIPS)
    while True:
        stdscr.erase()
        m = 4
        y = 2
        safe_add(stdscr, y, m, "RESULTS", curses.color_pair(P_ACCENT) | curses.A_BOLD | curses.A_UNDERLINE)
        y += 2
        safe_add(stdscr, y, m, "WPM        {}".format(int(round(r["wpm"]))), curses.color_pair(P_OK) | curses.A_BOLD)
        y += 1
        safe_add(stdscr, y, m, "accuracy   {}%".format(int(round(r["acc"]))))
        y += 1
        safe_add(stdscr, y, m, "raw wpm    {}".format(int(round(r["raw"]))))
        y += 1
        safe_add(stdscr, y, m, "time       {}s    mode {}    quote {}".format(
            int(round(r["elapsed"])), r["settings"]["mode"], r["source"]))
        y += 2

        if r["punct_total"]:
            col = curses.color_pair(P_OK) if r["punct_ok"] == r["punct_total"] else curses.color_pair(P_WARN)
            safe_add(stdscr, y, m, "punctuation ( . , ; )   {}/{} correct".format(r["punct_ok"], r["punct_total"]), col)
            y += 1
        if r["contractions_total"]:
            col = curses.color_pair(P_OK) if r["contractions_ok"] == r["contractions_total"] else curses.color_pair(P_WARN)
            safe_add(stdscr, y, m, "contractions            {}/{} clean".format(r["contractions_ok"], r["contractions_total"]), col)
            y += 1
        y += 1

        if r["review"]:
            safe_add(stdscr, y, m, "words to review:", curses.A_BOLD)
            y += 1
            safe_add(stdscr, y, m, "  " + "   ".join(r["review"][:8]), curses.color_pair(P_BAD))
            y += 2
        else:
            safe_add(stdscr, y, m, "clean run - no mistyped words!", curses.color_pair(P_OK))
            y += 2

        safe_add(stdscr, y, m, "tip: " + tip, curses.color_pair(P_ACCENT))
        y += 2
        safe_add(stdscr, y, m, "[Enter] again    [s] settings    [q] quit", curses.A_DIM)
        stdscr.refresh()
        ch = stdscr.getch()
        if ch in (10, 13, curses.KEY_ENTER):
            return "again"
        if ch in (ord("s"), ord("S")):
            return "menu"
        if ch in (ord("q"), ord("Q"), 27):
            return "quit"


def _run(stdscr, settings):
    curses.curs_set(0)
    init_colors()
    while True:
        if menu_screen(stdscr, settings) == "quit":
            return
        while True:
            if settings["ai"] and claude_available():
                target, source = loading_screen(stdscr, settings)
            else:
                target, source = random.choice(pool(settings["mode"])), "offline"
            result = run_test(stdscr, target, source, settings)
            if result is None:
                break
            action = results_screen(stdscr, result)
            if action == "quit":
                return
            if action == "menu":
                break


def main():
    p = argparse.ArgumentParser(
        prog="typer-test",
        description="Terminal typing trainer for English punctuation and contractions. Quotes by claude -p.",
    )
    p.add_argument("-t", "--time", type=int, default=60, help="seconds per test (default 60)")
    p.add_argument("-m", "--mode", choices=MODES, default="mixed", help="quote focus (default mixed)")
    p.add_argument("--offline", action="store_true", help="use built-in quotes instead of claude")
    args = p.parse_args()
    settings = {"time": max(10, args.time), "mode": args.mode, "ai": not args.offline}
    try:
        curses.wrapper(_run, settings)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
