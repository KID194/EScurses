import sys
import os
import time
import atexit
import ctypes

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

_screen = []
_screenWidth = None
_screenHeight = None

_frameStartTime = None

_fd = None
_oldSettings = None
_terminalInited = False

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
    global _screenWidth, _screenHeight, _screen
    _enableWindowsVT()
    scrSize = getTerminalSize()
    _screenWidth, _screenHeight = scrSize
    _screen = [[' '] * (_screenWidth - 1) for _ in range(_screenHeight)]

    if os.name == 'posix':
        _initTerminalPosix()

    sys.stdout.write('\033[?25l\033[2J\033[H')
    sys.stdout.flush()

def clear():
    sys.stdout.write('\033[2J\033[H')
    global _screen
    _screen = [[' '] * (_screenWidth - 1) for _ in range(_screenHeight)]

def resize():
    initGame()

def drawChar(x, y, char):
    if not (1 <= x <= _screenWidth - 1 and 1 <= y <= _screenHeight):
        return
    if not char:
        return
    _screen[y - 1][x - 1] = char[0]

def drawText(x, y, text):
    for i, ch in enumerate(text):
        drawChar(x + i, y, ch)

def drawRect(x, y, w, h, char='#', fill=False):
    if w <= 0 or h <= 0:
        return
    for j in range(h):
        for i in range(w):
            if fill or j in (0, h - 1) or i in (0, w - 1):
                drawChar(x + i, y + j, char)

def fillRect(x, y, w, h, char=' '):
    drawRect(x, y, w, h, char, fill=True)

def refresh():
    out = []
    for y, line in enumerate(_screen, 1):
        out.append(f'\033[{y};1H')
        out.append(''.join(line))
    sys.stdout.write(''.join(out))
    sys.stdout.flush()

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