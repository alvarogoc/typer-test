# typer-test

> **Beta** — `0.1.0-beta`. Works end to end, but behaviour and the on-disk
> database format may still change between releases. Check your version with
> `typer-test --version`.

**Read a whole book by typing it.** A terminal reading-and-typing trainer:
point it at your own `.txt`, `.epub` or `.pdf`, and it becomes the text you
practice on — one page at a time, remembering exactly where you left off, for
as many sessions as the book takes.

It works like [MonkeyType](https://monkeytype.com), but in your terminal, and
built around reading something you actually want to read instead of disposable
drill sentences. Text appears in gray, turns white as you type it correctly and
red when you slip.

```
 progress  10%    wpm  74    acc 98%                        Romeo and Juliet

 Where I may read who pass'd that passing fair? Farewell, thou canst not
 teach me to forget. BENVOLIO. I'll pay that doctrine, or else die in debt.
 Exeunt. SCENE II. A Street. Enter Capulet, Paris and Servant. CAPULET.

 page 41/394                                                  names skipped
 [left]/[right] page  [^G] jump  [^P] more words  [^C] settings  [^L] list
```

What it does:

- **Reads your books.** EPUB, plain text and PDF, with the title and author
  pulled from EPUB metadata. Text is sanitised to characters you can actually
  type on a keyboard.
- **Never loses your place.** Page *and* line are saved every round, so you
  resume mid-page rather than re-typing what you already did.
- **No clock while reading.** A page stays up as long as it takes, then flips
  to the next one automatically. Move around with the arrows, jump to any page,
  or combine several pages into one screen.
- **Tracks a real WPM.** A cumulative per-book average that carries across
  sessions and freezes when you stop typing instead of decaying while you think.
- **Learns what you're bad at.** Records every word you fumble, with fail count
  and average time, and asks `claude` to work your slowest words into generated
  practice quotes.
- **Adapts to the text.** Optionally show pictures as placeholders, include or
  skip code blocks, or grey out character names so the cursor jumps past them —
  handy for plays and dialogue-heavy books.
- **Fits your terminal.** Never asks you to type text that isn't on screen,
  whatever size the window is.

It also still does the original thing — short generated quotes for drilling
English punctuation and contractions, the mistakes that are easy to make as a
non-native writer (`.` `,` `;`, `you're` / `your`, `I'd`, `I've`, the
always-capital `I`, `a` vs `an`). Those modes are a keypress away, and work
offline from a built-in quote set when `claude` isn't installed.

## Requirements

- **Python 3.8+** — `curses` and `sqlite3` are built in on Linux and macOS.
  `.txt` and `.epub` reading mode need nothing beyond the standard library.
- **`claude` CLI** *(optional)* — for live, AI-generated quotes. Without it the
  app uses its built-in quotes.
- **`pdfminer.six`** *(optional)* — only needed if you want to read `.pdf`
  books in reading mode: `pip install pdfminer.six`.

## Install

```bash
git clone https://github.com/alvarogoc/typer-test.git
cd typer-test
./install.sh
```

This copies the script to `~/.local/bin/typer-test`. Make sure `~/.local/bin`
is on your `PATH` (the installer warns you if it isn't):

```bash
export PATH="$HOME/.local/bin:$PATH"   # add to ~/.bashrc if needed
```

### Manual install (no script)

```bash
install -Dm755 typer_test.py ~/.local/bin/typer-test
```

### Run without installing

```bash
python3 typer_test.py
```

## Usage

```bash
typer-test                      # starts in read/books mode (the default)
typer-test --time 120           # longer test
typer-test --mode mixed         # AI quotes: contractions + punctuation
typer-test --mode punctuation   # drill commas, periods, semicolons
typer-test --mode contractions  # drill you're / you've / I'd ...
typer-test --mode plain         # no contractions, only commas and periods
typer-test --offline            # skip claude, use built-in quotes
typer-test --add-book novel.epub   # import/resume a book, print status, exit
typer-test --help
```

### Controls

| Screen      | Keys                                                         |
|-------------|-------------------------------------------------------------|
| Start menu  | `Enter` start · `t` change time · `m` change mode · `a` AI on/off · `Ctrl+F` struggle words · `q` quit |
| Start menu (mode `read`) | `Enter` start (resumes where you left off) · `m` change mode · `b` book library · `l` list books · `Ctrl+F` struggle words · `q` quit |
| Library     | `up`/`down` navigate · `Enter` select · `n` add new · `d` delete · `Esc` back |
| Book list (`l`) | `up`/`down` navigate · `Enter` select · `Esc` back |
| Struggle words (`Ctrl+F`) | `up`/`down` scroll · `Esc` back |
| While reading | `left`/`right` prev/next page(s) · `Ctrl+G` jump to page · `Ctrl+P` add more words · `Ctrl+C` settings · `Ctrl+L` list/switch books · `Ctrl+Q` quit app |
| Settings (`Ctrl+C` / `c`) | `up`/`down` move · `space`/`Enter` toggle · `Esc` done |
| While typing| type the gray text · `Backspace` fix a slip · `Esc` cancel  |
| Results     | `Enter` again · `s` settings · `q` quit                     |

### Modes

- **read** *(default)* — practice typing your own book instead of AI/built-in quotes (see below)
- **mixed** — AI quotes: contractions + punctuation together
- **punctuation** — heavy on commas, periods, semicolons, colons
- **contractions** — heavy on `you're`, `you've`, `I'd`, `it's`, `don't` …
- **plain** — no contractions or abbreviations at all, only `,` and `.`

### Time options

Default is **60s** (one minute). Press `t` on the start screen to cycle through
30 / 60 / 90 / 120 / 180 seconds, or pass `--time <seconds>`.

## Reading settings

Press `Ctrl+C` while reading (or `c` on the start screen) to toggle:

| Setting | What it does |
|---------|--------------|
| **show images** | Turns `<img>` into a typeable `(image: caption)` placeholder instead of dropping the picture silently. |
| **include code** | Keeps the contents of `<pre>` code blocks as text to type. Inline `<code>` inside a sentence is always kept — it's part of the prose. |
| **skip names** | The cursor jumps over speaker cues and proper nouns. The name stays on the page in its own colour but is never typed. |

Settings persist in the database.

**Images and code affect extraction**, which happens when a book is imported —
so a book added under different settings is rebuilt automatically the next time
you open it. Its page number is kept (clamped), since page boundaries can shift.
Only EPUB marks images and code up explicitly; plain text and PDF carry no
reliable signal for either.

**Skipping names** greys the name out rather than deleting it, and the cursor
jumps straight past. Given `forget. BENVOLIO. I'll`, you type
`forget. I'll` — one space between the words that remain. A name is detected as
either an all-caps speaker cue (`BENVOLIO`, `CAPULET`) or a Title-case word
appearing mid-sentence (`Montague`, `Verona`). A capitalized word that *opens* a
sentence is ordinary prose, and contractions like `I'll` are never mistaken for
names. Skipped characters count towards neither WPM nor accuracy, and you can't
backspace into them.

`Ctrl+C` is available here because the reading loop switches the terminal to raw
mode; everywhere else `Ctrl+C` still interrupts the program as usual.

## Words you struggle with

Every typing session — any mode, AI quotes or your own book — silently tracks
each word's stats: how many times you failed to type it cleanly on the first
pass (fixing it with `Backspace` afterward still counts as a fail) and how
long it took on average. Punctuation is stripped and case is ignored, so
`"Hello"`, `"hello,"`, and `"HELLO"` all count as the same word.

Numbers, times, dates, and words that look like proper nouns (capitalized
mid-sentence — names of people or places) are never tracked, since they're
one-off tokens rather than useful practice targets.

Press `Ctrl+F` on the start screen (any mode) to see the list — sorted by
**highest average time first** (your slowest words, not just your
most-failed ones); only words with at least one fail show up. Stats
accumulate in the same SQLite database as your book library and persist
across every session.

Whenever a fresh quote is generated with `claude -p`, the prompt always asks
it to naturally work in a few of these words, so AI-quote rounds keep giving
you extra practice on exactly what trips you up.

## Reading mode (practice with your own book)

This is the default mode — the start screen opens straight into it. (Press
`m` to cycle to a different mode, e.g. AI quotes.) Press `b` to open the book
library; `n` there lets you paste a path
to a `.txt`, `.epub`, or `.pdf` file; the app extracts its text, splits it
into sentences, and groups those into fixed-size "pages" (~12 sentences each,
independent of your terminal size). Each practice round shows one page of the
book instead of an AI/built-in quote.

There is no timer while reading: a page stays up for as long as it takes to
type, and finishing it automatically flips to the next page — no results
screen in between, just continuous reading. Pressing `Esc` stops the session
and returns to the menu. Your position (page + line) is saved every time a
round ends, whether that's by finishing a page or pressing `Esc`, so the next
session resumes from exactly where you stopped — and the book you had open is
remembered too, so relaunching drops you straight back into it rather than an
empty library. Books and progress live in a small SQLite database at
`~/.local/share/typer-test/library.db`; deleting a book from the library (`d`)
only removes that tracking row, never the original file.

While actively reading, you can jump around without stopping first:
`right` always marks the current page(s) complete (no matter how much you'd
actually typed) and moves on; `left` goes back the same number of pages.
`Ctrl+G` prompts for a specific page number. `Ctrl+P` adds one more page to
the current view (see below). `Ctrl+L` opens the detailed book list so you
can switch to a different book mid-session (adding/deleting a book is
menu-only, via `b` after `Esc`), and `Ctrl+Q` quits the app outright. `Enter`
does nothing while reading.

These use `Ctrl` because plain letters can't be reading-time shortcuts —
book text constantly contains `g`, `l`, `p`, and `q`, so a bare keypress has
to be typed input, not a command. Two control keys have no reading-time
equivalent: `Ctrl+M` and `Ctrl+J` are physically the same bytes as
`Enter`/`Return` in most terminals, so neither can be bound to anything —
cycle mode from the start screen (`m`) instead.

### Fitting the window

A round never shows more text than the terminal can display — anything that
would fall below the bottom edge is held back for the next round instead, so
you are never asked to type text you cannot see. Resize the window and the
next page adapts. If the window is so small that not even one sentence fits,
the app says so rather than showing a truncated page.

### Adding more words (`Ctrl+P`)

By default one page fills the screen per round. Pressing `Ctrl+P` combines
one more page into the same view (e.g. pages 3 and 4 shown and typed as a
single round), and can be pressed repeatedly to add further pages. If the
combined text would not fit the terminal's current size, nothing changes —
you get **"error: text does not fit in the window"** instead. `right`/`left`
then move by however many pages are currently combined, and progress still
resumes at the exact line you reached, even mid-span.

### Reading screen layout

- **Top-left**: your overall book progress (%) plus WPM/accuracy — same
  format and position `wpm`/`acc` already use. This is the same percentage
  the `l` list shows, not how much of the current page you've typed. WPM
  here is a running average for the whole book (see below), not per-page.
- **Top-right**: the book's title.
- **Bottom-left**: the current page count, e.g. `page 3/12` (or `page 3-4/12`
  when Ctrl+P has combined pages).
- **Bottom**: key hints.

### WPM never resets

Reading-mode WPM is a running average for the entire book, backed by
cumulative character/time totals in the database — not a per-page snapshot.
It shows your saved average the instant a page loads (never 0 on a fresh
page or after flipping pages), updates live as you type, and **freezes**
rather than decaying the moment you stop typing — pausing mid-page never
hurts it. It's written to the database at the end of every round.

Press `l` to see the full list of books you've added — title, author (parsed
from EPUB metadata when available), % read, page count (e.g. `p.120/500`),
last date read, WPM from your last round, and a short form of the folder it
lives in (e.g. `~/Downloads`). Selecting a book there (`Enter`) makes it the
active one, same as picking it from the library.

Pressing `m` again cycles away from `read` back to the AI/built-in-quote modes
(and hides the book library key until you cycle back).

## How the AI quotes work

On each round the app runs `claude -p` with a prompt asking for one original
one-sentence quote that deliberately uses the punctuation and contractions you
are practising. The output is sanitised to plain keyboard characters (smart
quotes, em dashes and ellipses are converted) so everything is typeable.

If `claude` is missing, errors, or takes longer than 45s, the app quietly falls
back to a built-in quote. You can press `Esc` during generation to skip the
wait, or run with `--offline` to never call it.

## Uninstall

```bash
rm ~/.local/bin/typer-test
rm -rf ~/.local/share/typer-test   # optional: also forget imported books/progress
```

## License

MIT — see [LICENSE](LICENSE).
