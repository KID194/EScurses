# EScurses

A Python library that lets you make terminal games — one single file, no third-party dependencies.

[Go to homepage](./README.md) | [中文 README](./README-zh.md)

## Why should you choose EScurses?

- **Cross-platform support**
  It works on Windows and on Linux.
  So you don't need to worry about this library being incompatible with your system, unless you're using macOS.
- **Easy to use**
  You just need to download it and drop it into your code directory, and then you can use it!
- **Maintained**
  You probably don't know about pycurses — that's a very, very old library that hasn't been maintained for a long time.
  EScurses is much newer than it, which means you can rest assured it won't suddenly stop being updated.
  But the author also has to go to school QAQ (I'm just a fifth grader).

> I don't have a MacBook because it's not a common thing — it's too expensive, at least for me.
> So... if you have a MacBook, please help me test whether this library works on macOS.
> I need help :)

## Installation

EScurses doesn't need `pip install`. Just copy the single file `escurses.py` into your code directory:

```
your_project/
├── escurses.py      ← copy this one file here
└── mygame.py        ← your own game
```

Then `import escurses` in your code and you're ready to go.

Requirement: Python 3.7 or newer.

> **Windows users**: EScurses automatically enables the console's "virtual terminal"
> support, which is what makes colors and cursor positioning work. If you're on a very
> old Windows version or some third-party terminal, the output may look wrong —
> try Windows Terminal or a recent `cmd`.

## Quick start

Save this as `mygame.py`, then run `python mygame.py`:

```python
import escurses

escurses.initGame()
try:
    escurses.clear()
    escurses.drawText(1, 1, "Hello, EScurses!", escurses.COLORBRIGHTCYAN)
    escurses.drawChar(1, 3, "@", escurses.COLORRED)
    escurses.refresh()

    # Wait until the player presses q
    while True:
        key = escurses.getch(False)
        if key == "q":
            break
finally:
    escurses.endGame()
```

The `try ... finally` part matters: even if your game crashes, `endGame()` will put the
terminal back the way it was, so it won't be left stuck on the game screen.

## How a game loop looks

Almost every terminal game uses the same pattern:

```python
import escurses

escurses.initGame()
try:
    while True:
        escurses.frameStart()        # 1. remember when this frame started

        key = escurses.getch(True)   # 2. read a key (non-blocking, None if none)
        if key == "q":
            break

        escurses.clear()             # 3. erase the previous frame
        escurses.drawChar(5, 5, "@") # 4. draw this frame
        escurses.refresh()           # 5. push it to the terminal in one go

        escurses.sleepForFrame(30)   # 6. hold the frame rate at 30 FPS
finally:
    escurses.endGame()
```

More ready-to-run examples live in the [`examples/`](./examples) directory:

| Example | What it shows |
| --- | --- |
| [`examples/hello.py`](./examples/hello.py) | Writes a line in the middle of the screen; press q to quit |
| [`examples/bounce.py`](./examples/bounce.py) | Moves a ball with WASD, with frame-rate control |

## Coordinates

The top-left corner of the screen is **(1, 1)**, not (0, 0)!

```
(1,1) ──────────► x grows
  │
  │
  ▼
 y grows
```

In `drawChar(x, y, ...)` the first argument is x (across) and the second is y (down).

## Documentation

### Color constants

Pass one of these constants as the `color` argument of `drawChar()` or `drawText()`:

| Constant | Meaning |
| --- | --- |
| `COLORDEFAULT` | The terminal's default color (the default value) |
| `COLORBLACK` | Black |
| `COLORRED` | Red |
| `COLORGREEN` | Green |
| `COLORYELLOW` | Yellow |
| `COLORBLUE` | Blue |
| `COLORMAGENTA` | Magenta |
| `COLORCYAN` | Cyan |
| `COLORWHITE` | White |
| `COLORBRIGHTRED` | Bright red |
| `COLORBRIGHTGREEN` | Bright green |
| `COLORBRIGHTYELLOW` | Bright yellow |
| `COLORBRIGHTBLUE` | Bright blue |
| `COLORBRIGHTMAGENTA` | Bright magenta |
| `COLORBRIGHTCYAN` | Bright cyan |
| `COLORBRIGHTWHITE` | Bright white |

### Setup and shutdown

- **`initGame()`**
  Sets up the game: reads the terminal size, creates the internal screen buffer, and
  switches to the "alternate screen" (so the game doesn't mess up what was in your
  terminal before). Call it once at the start of every game; only after it can you call
  `clear()`, `drawChar()`, `refresh()` and friends. If you draw something before calling
  it, you get a `RuntimeError` with a friendly message.
- **`endGame()`**
  Ends the game and restores the terminal (shows the cursor again, leaves the alternate
  screen) — but does **not** exit the Python program. Great for putting in a `finally` block.
- **`exitGame()`**
  Restores the terminal and exits the program (it calls `endGame()` for you).
- **`resize()`**
  Re-reads the terminal size and rebuilds the screen buffer. Useful when the player
  resizes the window; note that whatever was drawn is cleared.

### Size and environment

- **`getTerminalSize()`**
  Returns a tuple `(width, height)` in characters, e.g. `(80, 24)`. Note the order is
  **width first, height second**. If the size can't be read (for example when output is
  redirected to a file), it falls back to `(80, 24)`.
- **`linuxTerminalCheck()`**
  Checks whether standard input is a real terminal (tty). Returns `True` if keys can be
  read normally, `False` if input is redirected (e.g. reading from a file), in which case
  blocking `getch()` may misbehave. It also works on Windows, where it tells you whether
  you're in a real console.

### Drawing

- **`clear()`**
  Clears the internal screen buffer, ready for a new frame. It only empties the buffer of
  what is about to be drawn — the old content on the actual terminal is overwritten row
  by row on the next `refresh()`. That's why the standard pattern is
  `clear()` → draw again → `refresh()`.
- **`drawChar(x, y, char, color=COLORDEFAULT)`**
  Draws one character at `(x, y)`. Out-of-range coordinates never raise an error —
  the call is simply ignored and returns `False` — so a character walking off-screen
  won't crash your game. Full-width characters such as Chinese characters automatically
  take two cells. Returns `True` when it was actually drawn.
- **`drawText(x, y, text, color=COLORDEFAULT)`**
  Draws every character of `text` starting at `(x, y)`. Returns the width actually drawn
  (in cells), so you can continue drawing right after it.
- **`refresh()`**
  Pushes the internal buffer to the terminal. It writes row by row and skips repeating
  the color code when the color hasn't changed, so it's much faster than drawing cell by
  cell. Normally you call `refresh()` once per frame.
- **`cursorEcho(echo=False)`**
  Pass `False` (the default) to hide the cursor, `True` to show it again.

### Input

- **`getch(nodelay=True)`**
  Reads one key press. This is the hardest one to implement, because it covers both
  Windows input and Linux input, and each of those has a blocking and a non-blocking
  version — controlled by the `nodelay` parameter, which defaults to `True`.
  - `nodelay=True`: returns `None` immediately when no key is pressed, so the game never freezes.
  - `nodelay=False`: waits until you press a key.
  - It returns a single character. On Windows, special keys such as the arrow keys
    return special characters that you have to interpret yourself.
  - On Linux both modes return as soon as a key is pressed — you don't need to press Enter.

### Frame rate

- **`frameStart()`**
  Records when this frame started. Call it at the very, very beginning of each main
  loop iteration — nothing may run before it — and combine it with `sleepForFrame()`
  to control the frame rate.
- **`sleepForFrame(fps)`**
  Holds the frame rate at `fps` frames per second (e.g. `sleepForFrame(60)` for 60 FPS).
  It sleeps for most of the remaining time and then busy-waits the last fraction of a
  millisecond, so the rate stays accurate. `fps` must be greater than 0.

## FAQ

**Q: The screen is blank, or I see garbage like `←[31m`?**
A: The terminal doesn't understand ANSI escape sequences. On Windows use Windows
Terminal or a recent `cmd`. If you're running inside an IDE output pane (PyCharm, the
VS Code console, ...), run `python mygame.py` in a real terminal instead.

**Q: Key presses don't register, or the arrow keys do nothing?**
A: `getch()` returns a single character. On Windows special keys return special
characters that you have to interpret yourself. Also double-check whether you called
`getch(True)` or `getch(False)` — the former doesn't wait for a key, the latter does.

**Q: After a crash the terminal went blank / the cursor disappeared?**
A: That means `endGame()` wasn't called. Wrap your main loop in `try ... finally` and
call `escurses.endGame()` in `finally`. If you're already stuck, type `reset` and press
Enter in the terminal.

**Q: Does it work on macOS?**
A: The author has no MacBook and can't test it. In theory macOS is a posix system so it
should work, but nobody has verified it yet. Feedback is welcome.

**Q: How do I change the terminal size?**
A: Drag the window edge with your mouse. In your program, call `resize()` to re-read the
size and rebuild the buffer.

**Q: Why is the origin (1,1) instead of (0,0)?**
A: It matches the convention of ANSI escape sequences (terminal rows and columns also
start at 1). `drawChar()` takes care of mapping x and y for you, so you don't have to
worry about it.

## Development and testing

```bash
# run the unit tests
python -m unittest discover -s tests -v

# run the examples
python examples/hello.py
python examples/bounce.py
```

The tests don't require any third-party packages.

To see what problems the library used to have and how they were fixed, read the
[code review report](./REVIEW.md).

## Other versions (from forks)

- **EScurses-fix** (by Natsuki3462): https://github.com/Natsuki3462/EScurses-fix
  Fixed many bugs in EScurses and added new features such as `drawRect()`, `drawText()`,
  `fillRect()`, `resize()`.
- **Escurses** (by 9178nekomc): https://github.com/9178nekomc/EScurses
  Overrode some APIs; you can use the original style (called the 1.0 API) or the new
  style (called the 2.0 API).
- **EScurses-h** (by Jej1111064): https://github.com/Jej1111064/EScurses-h
  If it has a new feature or a bug fix, it will be written here.

That's basically all the content. I wish you all can make good games! (Although this
library is basically useless)
