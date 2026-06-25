# typer-test

A small terminal typing trainer for practicing **English**, focused on the
mistakes that are easy to make as a non-native writer:

- **punctuation** — where to put `.` `,` and `;`
- **contractions** — `you're`, `you've`, `I'd`, `I've`, `it's`, `don't`, `that's` …
- the always-capital **`I`**, and correct **`a` / `an`** usage

It works like [MonkeyType](https://monkeytype.com), but in your terminal: a
quote appears in **gray**, each character turns **white** as you type it
correctly and **red** when you slip. At the end you get your WPM, accuracy, and
a breakdown of the punctuation and contractions you missed.

Every round, a **fresh quote is written for you by `claude -p`**, tuned to the
skill you are practising. No `claude`? It falls back to a built-in set of
quotes, so it always works offline.

```
TYPER-TEST
 time 60s   wpm 72   acc 98%                              Esc cancel

 You're stronger than you've ever guessed; don't let yesterday's doubts
 define you, because it's clear that what you're becoming is brighter.

 progress 100%    quote: claude
```

## Requirements

- **Python 3.8+** (uses only the standard library — `curses` is built in on
  Linux and macOS)
- **`claude` CLI** *(optional)* — for live, AI-generated quotes. Without it the
  app uses its built-in quotes.

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
typer-test                      # 60s test, mixed mode, AI quotes
typer-test --time 120           # longer test
typer-test --mode punctuation   # drill commas, periods, semicolons
typer-test --mode contractions  # drill you're / you've / I'd ...
typer-test --offline            # skip claude, use built-in quotes
typer-test --help
```

### Controls

| Screen      | Keys                                                         |
|-------------|-------------------------------------------------------------|
| Start menu  | `Enter` start · `t` change time · `m` change mode · `a` AI on/off · `q` quit |
| While typing| type the gray text · `Backspace` fix a slip · `Esc` cancel  |
| Results     | `Enter` again · `s` settings · `q` quit                     |

### Modes

- **mixed** *(default)* — contractions + punctuation together
- **punctuation** — heavy on commas, periods, semicolons, colons
- **contractions** — heavy on `you're`, `you've`, `I'd`, `it's`, `don't` …

### Time options

Default is **60s** (one minute). Press `t` on the start screen to cycle through
30 / 60 / 90 / 120 / 180 seconds, or pass `--time <seconds>`.

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
```

## License

MIT — see [LICENSE](LICENSE).
