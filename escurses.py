import sys
import os
import time
import atexit
import ctypes
import unicodedata

if os.name == 'posix':
    import termios, tty, select
if os.name == 'nt':
    import msvcrt

KEY_UP    = 'KEY_UP'
KEY_DOWN  = 'KEY_DOWN'
KEY_LEFT  = 'KEY_LEFT'
KEY_RIGHT = 'KEY_RIGHT'
KEY_HOME  = 'KEY_HOME'
KEY_END   = 'KEY_END'
KEY_PGUP  = 'KEY_PGUP'
KEY_PGDN  = 'KEY_PGDN'
KEY_DEL   = 'KEY_DEL'
KEY_ESC   = 'KEY_ESC'

COLOR_DEFAULT = None
COLOR_BLACK   = 30
COLOR_RED     = 31
COLOR_GREEN   = 32
COLOR_YELLOW  = 33
COLOR_BLUE    = 34
COLOR_MAGENTA = 35
COLOR_CYAN    = 36
COLOR_WHITE   = 37
COLOR_BRIGHT_RED     = 91
COLOR_BRIGHT_GREEN   = 92
COLOR_BRIGHT_YELLOW  = 93
COLOR_BRIGHT_BLUE    = 94
COLOR_BRIGHT_MAGENTA = 95
COLOR_BRIGHT_CYAN    = 96
COLOR_BRIGHT_WHITE   = 97

_screen = []
_colors = []
_screenWidth = None
_screenHeight = None
_dirtyRows = set()

_frameStartTime = None

_fd = None
_oldSettings = None
_terminalInited = False

def _char_width(ch):
    """字符在终端占用的列数:中文等全角字符为 2,组合字符为 0,其余为 1。"""
    if not ch:
        return 0
    if unicodedata.combining(ch):
        return 0
    return 2 if unicodedata.east_asian_width(ch) in ('W', 'F') else 1

def _enableWindowsVT():
    if os.name != 'nt':
        return
    try:
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        pass

def _initTerminalPosix():
    global _fd, _oldSettings, _terminalInited
    if _terminalInited:
        return
    _fd = sys.stdin.fileno()
    _oldSettings = termios.tcgetattr(_fd)
    tty.setcbreak(_fd)
    _terminalInited = True

def _restoreTerminalPosix():
    global _terminalInited
    if _terminalInited and _fd is not None and _oldSettings is not None:
        try:
            termios.tcsetattr(_fd, termios.TCSADRAIN, _oldSettings)
        except Exception:
            pass
        _terminalInited = False

def _restoreAll():
    try:
        sys.stdout.write('\033[?25h')
        sys.stdout.flush()
    except Exception:
        pass
    if os.name == 'posix':
        _restoreTerminalPosix()

atexit.register(_restoreAll)

def linuxTerminalCheck():
    try:
        return os.isatty(sys.stdin.fileno())
    except Exception:
        return False

def isTTY():
    return linuxTerminalCheck()

def getTerminalSize():
    scrSize = os.get_terminal_size()
    return (scrSize.columns, scrSize.lines)

def initGame():
    global _screenWidth, _screenHeight, _screen, _colors, _dirtyRows
    _enableWindowsVT()
    scrSize = getTerminalSize()
    _screenWidth, _screenHeight = scrSize
    _screen = [[' '] * (_screenWidth - 1) for _ in range(_screenHeight)]
    _colors = [[None] * (_screenWidth - 1) for _ in range(_screenHeight)]
    _dirtyRows = set(range(1, _screenHeight + 1))

    if os.name == 'posix':
        _initTerminalPosix()

    sys.stdout.write('\033[?25l\033[2J\033[H')
    sys.stdout.flush()

def clear():
    global _screen, _colors, _dirtyRows
    sys.stdout.write('\033[2J\033[H')
    _screen = [[' '] * (_screenWidth - 1) for _ in range(_screenHeight)]
    _colors = [[None] * (_screenWidth - 1) for _ in range(_screenHeight)]
    _dirtyRows = set(range(1, _screenHeight + 1))

def resize():
    initGame()

def drawChar(x, y, char, color=None):
    if not char:
        return
    ch = char[0]
    w = _char_width(ch)
    if w == 0:
        return
    if not (1 <= x <= _screenWidth - 1 and 1 <= y <= _screenHeight):
        return
    if w == 2 and x + 1 > _screenWidth - 1:
        return  # 右侧放不下全角字符
    row = _screen[y - 1]
    crow = _colors[y - 1]
    # 目标格若为全角字符的占位格,先清掉左侧那个全角字符
    if row[x - 1] == '' and x - 2 >= 0:
        row[x - 2] = ' '
        crow[x - 2] = None
    # 目标格若原本是全角字符,清掉它的占位格
    if row[x - 1] != '' and _char_width(row[x - 1]) == 2 and x < len(row):
        row[x] = ' '
        crow[x] = None
    row[x - 1] = ch
    crow[x - 1] = color
    if w == 2:
        row[x] = ''      # 占位格,refresh 时跳过
        crow[x] = color
    _dirtyRows.add(y)

def drawText(x, y, text, color=None):
    cx = x
    for ch in text:
        w = _char_width(ch)
        if w == 0:
            continue
        drawChar(cx, y, ch, color)
        cx += w

def drawRect(x, y, w, h, char='#', fill=False, color=None):
    if w <= 0 or h <= 0:
        return
    for j in range(h):
        for i in range(w):
            if fill or j in (0, h - 1) or i in (0, w - 1):
                drawChar(x + i, y + j, char, color)

def fillRect(x, y, w, h, char=' ', color=None):
    drawRect(x, y, w, h, char, fill=True, color=color)

def refresh():
    global _dirtyRows
    if not _dirtyRows:
        return
    out = []
    for y in sorted(_dirtyRows):
        if y < 1 or y > _screenHeight:
            continue
        out.append(f'\033[{y};1H')
        current_color = 'NONE'
        row_chars = _screen[y - 1]
        row_colors = _colors[y - 1]
        for i, ch in enumerate(row_chars):
            if ch == '':     # 全角字符占位格,跳过(前一个全角字符已占两列)
                continue
            c = row_colors[i]
            if c != current_color:
                if c is None:
                    out.append('\033[0m')
                else:
                    out.append(f'\033[0;{c}m')
                current_color = c
            out.append(ch)
        out.append('\033[0m')
    sys.stdout.write(''.join(out))
    sys.stdout.flush()
    _dirtyRows = set()

def cursorEcho(echo=False):
    sys.stdout.write('\033[?25h' if echo else '\033[?25l')
    sys.stdout.flush()

def _getch_posix(nodelay):
    _initTerminalPosix()
    if nodelay:
        if not select.select([_fd], [], [], 0)[0]:
            return None

    ch = os.read(_fd, 1)
    if not ch:
        return None
    ch = ch.decode('utf-8', errors='ignore')

    if ch == '\x1b':
        seq = ch
        while len(seq) < 4 and select.select([_fd], [], [], 0.01)[0]:
            nxt = os.read(_fd, 1).decode('utf-8', errors='ignore')
            if not nxt:
                break
            seq += nxt
            if nxt.isalpha() or nxt == '~':
                break
        return _map_escape(seq)
    return ch

def _map_escape(seq):
    table = {
        '\x1b[A': KEY_UP,    '\x1b[B': KEY_DOWN,
        '\x1b[C': KEY_RIGHT, '\x1b[D': KEY_LEFT,
        '\x1b[H': KEY_HOME,  '\x1b[F': KEY_END,
        '\x1b[1~': KEY_HOME, '\x1b[4~': KEY_END,
        '\x1b[5~': KEY_PGUP, '\x1b[6~': KEY_PGDN,
        '\x1b[3~': KEY_DEL,
        '\x1bOA': KEY_UP,    '\x1bOB': KEY_DOWN,
        '\x1bOC': KEY_RIGHT, '\x1bOD': KEY_LEFT,
    }
    if seq in table:
        return table[seq]
    if seq == '\x1b':
        return KEY_ESC
    return seq

def _getch_windows(nodelay):
    if nodelay:
        if not msvcrt.kbhit():
            return None
    ch = msvcrt.getwch()

    if ch in ('\x00', '\xe0'):
        if not msvcrt.kbhit():
            return None
        code = msvcrt.getwch()
        return {
            'H': KEY_UP,    'P': KEY_DOWN,
            'M': KEY_RIGHT, 'K': KEY_LEFT,
            'G': KEY_HOME,  'O': KEY_END,
            'I': KEY_PGUP,  'Q': KEY_PGDN,
            'S': KEY_DEL,
        }.get(code, code)
    return ch

def getch(nodelay=True):
    if os.name == 'nt':
        return _getch_windows(nodelay)
    elif os.name == 'posix':
        return _getch_posix(nodelay)
    else:
        raise RuntimeError('unsupported platform')

def exitGame():
    sys.stdout.write('\033[?25h\033[2J\033[H')
    sys.stdout.flush()
    if os.name == 'posix':
        _restoreTerminalPosix()
    sys.exit()

def frameStart():
    global _frameStartTime
    _frameStartTime = time.perf_counter()

def sleepForFrame(fps):
    if fps <= 0:
        return
    frameTime = 1.0 / fps
    elapsed = time.perf_counter() - _frameStartTime
    remain = frameTime - elapsed
    if remain > 0:
        time.sleep(remain)
