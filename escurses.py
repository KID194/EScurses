"""EScurses —— 一个面向儿童和初学者的终端游戏小库。

它只有一个文件、不依赖任何第三方库：把 escurses.py 复制到你的代码目录，
然后 `import escurses` 就能开始写终端小游戏。

最小例子::

    import escurses

    escurses.initGame()
    try:
        while True:
            escurses.frameStart()
            escurses.clear()
            escurses.drawText(1, 1, "Hello EScurses!")
            escurses.drawChar(10, 5, "@", escurses.COLORRED)
            escurses.refresh()
            key = escurses.getch()
            if key == "q":
                break
            escurses.sleepForFrame(30)
    finally:
        escurses.endGame()

坐标系：屏幕左上角是 (1, 1)，x 向右增大，y 向下增大。
"""

import sys
import os
import ctypes
import time
import atexit
import shutil
import unicodedata
from typing import List, Optional, Tuple

if os.name == 'posix':
    import termios, tty, select
if os.name == 'nt':
    import msvcrt

# ---------------------------------------------------------------- 颜色常量
# 这些数字是 ANSI 转义序列里的“前景色”代码，可以直接传给
# drawChar() / drawText() 的 color 参数。
COLORDEFAULT = 0
COLORBLACK = 30
COLORRED = 31
COLORGREEN = 32
COLORYELLOW = 33
COLORBLUE = 34
COLORMAGENTA = 35
COLORCYAN = 36
COLORWHITE = 37
COLORBRIGHTRED = 91
COLORBRIGHTGREEN = 92
COLORBRIGHTYELLOW = 93
COLORBRIGHTBLUE = 94
COLORBRIGHTMAGENTA = 95
COLORBRIGHTCYAN = 96
COLORBRIGHTWHITE = 97

# ------------------------------------------------------------ 内部常量
# 把难记的 ANSI 转义序列起个名字，代码里就不用写一堆 \033[... 了。
_ESCAPE = "\033["
_ENTER_ALT_SCREEN = "\033[?1049h"   # 进入“备用屏幕”（游戏画面不会弄乱原来的终端）
_EXIT_ALT_SCREEN = "\033[?1049l"    # 退出备用屏幕，恢复原来的终端内容
_HIDE_CURSOR = "\033[?25l"
_SHOW_CURSOR = "\033[?25h"
_CLEAR_SCREEN = "\033[2J\033[H"
_ERASE_LINE = "\033[K"    # 从光标位置擦到行尾
_RESET_COLOR = "\033[0m"

# 一“格”屏幕的内容：(字符, y 坐标, x 坐标, 颜色)。
# 坐标从 1 开始；空字符串 '' 表示这一格被左边的全角字符占用了，绘制时跳过。
_ScreenCell = Tuple[str, int, int, int]

# ------------------------------------------------------------ 内部状态
_screen: List[List[_ScreenCell]] = []
_screenWidth: Optional[int] = None
_screenHeight: Optional[int] = None

_frameStartTime: Optional[float] = None

_gameInited = False
_atexitRegistered = False


def _makeBlankScreen(width: int, height: int) -> List[List[_ScreenCell]]:
    """创建一个 width 列、height 行的空白屏幕缓冲区。"""
    return [
        [(' ', y + 1, x + 1, COLORDEFAULT) for x in range(width)]
        for y in range(height)
    ]


def _getCharWidth(character: str) -> int:
    """返回一个字符在终端里占几格：汉字等全角字符占 2 格，普通字符占 1 格。"""
    if unicodedata.east_asian_width(character) in ('W', 'F'):
        return 2
    return 1


def _ensureInited(apiName: str) -> None:
    """如果还没调用 initGame()，就给出对初学者友好的错误提示。"""
    if not _gameInited:
        raise RuntimeError(
            "请先调用 initGame()，再调用 " + apiName + "()。"
        )


def _enableWindowsAnsi() -> None:
    """在 Windows 上打开控制台的“虚拟终端”支持。

    旧版 Windows 控制台默认不认识 \\033[...m 这类颜色/定位序列，会把它
    当成普通文字显示成乱码。Windows 10 以后系统提供了这个开关，
    这里用 ctypes 把它打开；如果打不开（比如输出被重定向了），就安静跳过。
    """
    if os.name != 'nt':
        return
    try:
        kernel32 = ctypes.windll.kernel32
        stdOutputHandle = kernel32.GetStdHandle(-11)  # -11 是“标准输出”的句柄编号
        consoleMode = ctypes.c_ulong()
        if kernel32.GetConsoleMode(stdOutputHandle, ctypes.byref(consoleMode)):
            enableVirtualTerminalProcessing = 0x0004
            if not consoleMode.value & enableVirtualTerminalProcessing:
                kernel32.SetConsoleMode(
                    stdOutputHandle,
                    consoleMode.value | enableVirtualTerminalProcessing,
                )
    except (AttributeError, OSError):
        # 不是 Windows、或者当前没有真正的控制台：忽略即可。
        pass


def frameStart() -> None:
    """记录这一帧的开始时间，用来配合 sleepForFrame() 控制帧率。

    请把它放在主循环的最开头（前面不要放别的代码）。
    """
    global _frameStartTime
    _frameStartTime = time.perf_counter()


def linuxTerminalCheck() -> bool:
    """检查标准输入是不是一个真正的终端（tty）。

    返回 True 表示可以正常读取按键；返回 False 表示输入被重定向了
    （比如从文件读），这时阻塞式 getch() 可能会表现异常。
    在 Windows 上也可以用，用来判断当前是不是真正的控制台。
    """
    try:
        return os.isatty(sys.stdin.fileno())
    except (AttributeError, ValueError, OSError):
        return False


def getTerminalSize() -> Tuple[int, int]:
    """返回终端尺寸 (宽, 高)，单位是字符数。

    如果读不到（比如输出被重定向到文件），就返回默认的 (80, 24)。
    """
    terminalSize = shutil.get_terminal_size(fallback=(80, 24))
    return (terminalSize.columns, terminalSize.lines)


def initGame() -> None:
    """初始化游戏：读取终端尺寸、创建内部屏幕缓冲区，并进入“备用屏幕”。

    每个游戏都要在开头调用它一次；在它之后才能调用 clear()、drawChar()、
    refresh() 等绘制函数。退出时请调用 endGame()（或 exitGame()）。
    """
    global _screenWidth, _screenHeight, _screen, _gameInited
    global _frameStartTime, _atexitRegistered
    _enableWindowsAnsi()
    _screenWidth, _screenHeight = getTerminalSize()
    _screen = _makeBlankScreen(_screenWidth, _screenHeight)
    _gameInited = True
    _frameStartTime = None
    if not _atexitRegistered:
        # 程序意外结束（比如按了 Ctrl+C）时也尽量把终端恢复原样。
        atexit.register(endGame)
        _atexitRegistered = True
    sys.stdout.write(_ENTER_ALT_SCREEN + _CLEAR_SCREEN + _HIDE_CURSOR)
    sys.stdout.flush()


def resize() -> None:
    """重新读取终端尺寸并重建屏幕缓冲区（已经画好的内容会被清空）。

    当用户拖动改变了终端窗口大小时，可以调用它。
    """
    global _screenWidth, _screenHeight, _screen
    _ensureInited("resize")
    _screenWidth, _screenHeight = getTerminalSize()
    _screen = _makeBlankScreen(_screenWidth, _screenHeight)
    sys.stdout.write(_CLEAR_SCREEN)
    sys.stdout.flush()


def clear() -> None:
    """清空内部屏幕缓冲区。

    注意：它只清空“准备画什么”的缓冲区，屏幕上真正的内容会在下一次
    refresh() 时被整行覆盖掉。所以标准写法是 clear() → 重新画 → refresh()。
    """
    global _screen
    _ensureInited("clear")
    _screen = _makeBlankScreen(_screenWidth, _screenHeight)


def _clearCell(row: List[_ScreenCell], x: int) -> None:
    """把第 x 格（从 1 开始数）恢复成普通空格。

    因为全角字符占两格，所以擦掉一格时，如果它属于一个全角字符，
    要把同一个字的另一半也一起擦掉，否则屏幕上会留下半个字。
    """
    index = x - 1
    cell = row[index]
    if cell[0] == '':
        # 这一格本身是某个全角字的“右半边”：把它的左半边也擦掉。
        if index > 0:
            row[index - 1] = (' ', row[index - 1][1], x - 1, COLORDEFAULT)
        row[index] = (' ', cell[1], x, COLORDEFAULT)
        return
    row[index] = (' ', cell[1], x, COLORDEFAULT)
    if index + 1 < len(row) and row[index + 1][0] == '':
        # 这一格是某个全角字的“左半边”：把它的右半边也擦掉。
        row[index + 1] = (' ', row[index + 1][1], x + 1, COLORDEFAULT)


def drawChar(x: int, y: int, char: str, color: int = COLORDEFAULT) -> bool:
    """在坐标 (x, y) 画一个字符。

    坐标原点在左上角，是 (1, 1) 而不是 (0, 0)；x 向右、y 向下。
    坐标超出屏幕范围时，这个字符会被安静地忽略（不会报错），
    这样游戏里的角色走出屏幕时也不会让程序崩溃。
    汉字等全角字符会自动占两格。

    返回 True 表示真的画上去了，False 表示被忽略（越界或 char 为空）。
    """
    _ensureInited("drawChar")
    if not char:
        return False
    character = char[0]
    if x < 1 or y < 1 or x > _screenWidth or y > _screenHeight:
        return False
    charWidth = _getCharWidth(character)
    if charWidth == 2 and x >= _screenWidth:
        # 全角字符要占两格，最后一格放不下就不画，避免屏幕错位。
        return False
    row = _screen[y - 1]
    # 先把它要覆盖的格子（连同可能残留的半个全角字）擦干净。
    _clearCell(row, x)
    if charWidth == 2:
        _clearCell(row, x + 1)
    row[x - 1] = (character, y, x, color)
    if charWidth == 2:
        # 全角字符占两格：第二格放一个空字符串当“占位标记”，
        # refresh() 看到空字符串就知道这一格不用再画。
        row[x] = ('', y, x + 1, color)
    return True


def drawText(x: int, y: int, text: str, color: int = COLORDEFAULT) -> int:
    """从坐标 (x, y) 开始，把 text 里的字符一个接一个地画出来。

    返回实际画出来的宽度（以格为单位），方便你接着往后画。
    """
    _ensureInited("drawText")
    currentX = x
    for character in text:
        if currentX > _screenWidth:
            break
        if drawChar(currentX, y, character, color):
            currentX += _getCharWidth(character)
        else:
            currentX += 1
    return currentX - x


def getch(nodelay: bool = True) -> Optional[str]:
    """读取一个按键。

    nodelay=True（默认）是无阻塞模式：没有按键时立刻返回 None。
    nodelay=False 是阻塞模式：会一直等到你按下按键才返回。
    返回的是单个字符；Windows 下方向键等特殊键会返回特殊字符，需要自己判断。
    """
    if os.name == 'nt':
        if nodelay:
            if msvcrt.kbhit():
                return msvcrt.getwch()
            return None
        return msvcrt.getwch()

    if os.name == 'posix':
        fd = sys.stdin.fileno()
        try:
            oldSettings = termios.tcgetattr(fd)
        except termios.error:
            raise RuntimeError(
                "当前环境不是终端（tty），无法读取按键；"
                "请先用 linuxTerminalCheck() 检查一下。"
            ) from None
        try:
            # 阻塞和非阻塞都要先进入 cbreak 模式：这样按一个键就立刻返回，
            # 不需要再按回车。
            tty.setcbreak(fd)
            if nodelay:
                if select.select([fd], [], [], 0)[0]:
                    return sys.stdin.read(1)
                return None
            return sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, oldSettings)

    # 其他系统：不支持读取按键。
    return None


def refresh() -> None:
    """把内部屏幕缓冲区的内容画到终端上。

    为了快，它会按行输出：每行只定位一次，颜色没变时不重复发送颜色代码，
    行尾的空白用“擦到行尾”的转义序列补上（不用真的写一串空格）。
    正常情况下每帧只需要调用一次 refresh()。
    """
    _ensureInited("refresh")
    outputParts: List[str] = []
    currentColor: Optional[int] = None
    for rowIndex, row in enumerate(_screen):
        # 先定位到这一行的第 1 列，保证整行都被重画一遍，不会留下上一帧的残影。
        outputParts.append(_ESCAPE + str(rowIndex + 1) + ";1H")
        rowParts: List[str] = []
        for cell in row:
            character = cell[0]
            if character == '':
                # 这一格被左边的全角字符占用了，跳过。
                continue
            color = cell[3]
            if color != currentColor:
                rowParts.append(_ESCAPE + str(color) + "m")
                currentColor = color
            rowParts.append(character)
        # 行尾的空白不用真写：先把它去掉，最后用“擦到行尾”补上。
        while rowParts and rowParts[-1] == ' ':
            rowParts.pop()
        outputParts.extend(rowParts)
        outputParts.append(_ERASE_LINE)
    outputParts.append(_RESET_COLOR)
    sys.stdout.write(''.join(outputParts))
    sys.stdout.flush()


def cursorEcho(echo: bool = False) -> None:
    """显示或隐藏光标。echo=False（默认）隐藏光标，True 显示光标。"""
    if echo:
        sys.stdout.write(_SHOW_CURSOR)
    else:
        sys.stdout.write(_HIDE_CURSOR)
    sys.stdout.flush()


def endGame() -> None:
    """结束游戏、把终端恢复原样（显示光标、退出备用屏幕），但不会退出 Python。

    可以放在 finally 里调用；exitGame() 也会替你调用它。
    """
    global _gameInited
    if not _gameInited:
        return
    sys.stdout.write(_RESET_COLOR + _SHOW_CURSOR + _EXIT_ALT_SCREEN)
    sys.stdout.flush()
    _gameInited = False


def exitGame() -> None:
    """恢复终端并退出程序（内部会调用 endGame()）。"""
    endGame()
    sys.exit()


def sleepForFrame(fps: float) -> None:
    """把帧率控制在 fps 帧/秒。

    用法：在每帧的最后调用它。它会根据 frameStart() 记录的本帧开始时间，
    计算还差多少时间，然后先睡一会儿、最后再忙等一小会儿，把误差收掉。
    """
    global _frameStartTime
    if fps <= 0:
        raise ValueError("fps 必须大于 0，例如 sleepForFrame(60)。")
    frameTime = 1.0 / fps
    if _frameStartTime is None:
        # 没有调用 frameStart() 时，就把现在当成这一帧的开始。
        _frameStartTime = time.perf_counter()
    targetTime = _frameStartTime + frameTime
    remain = targetTime - time.perf_counter()
    if remain > 0:
        # 先 sleep 掉大部分时间（少睡 1 毫秒，避免 sleep 精度不够导致睡过头）。
        time.sleep(max(0.0, remain - 0.001))
        # 最后最多忙等 1 毫秒，把误差收掉（不同系统上 sleep 的精度不一样）。
        while time.perf_counter() < targetTime:
            pass
