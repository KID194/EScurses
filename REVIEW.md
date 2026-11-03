# EScurses 代码审查报告

> 审查对象：`HEAD = 0bfac52`（"English README translated by Deepseek"）中的 `escurses.py`（110 行）
> 以及 `README.md` / `README-zh.md` / `README-en.md`。
> 审查方式：逐行阅读 + 在 Python 3.13.14 / Windows 上写探针脚本实测每一个可疑行为。
> 本报告同时记录了已经落地的修复（见「四、已完成的改动」）。

---

## 一、现有实现梳理

EScurses 是一个**单文件、零第三方依赖**的终端游戏库，靠 ANSI 转义序列在终端上"画字符"。
它自己维护一块二维字符缓冲区 `_screen`，游戏每帧先往缓冲区里写，最后 `refresh()` 一次性刷到终端。

原版 110 行、11 个函数、**0 条注释、0 个文档字符串、0 处类型标注**。按职责可以分成五组：

| 分组 | 函数（原版行号） | 作用 |
| --- | --- | --- |
| 全局状态 | `_screen`、`_screenWidth`、`_screenHeight`（:10-12）、`_frameStartTime`（:14） | 屏幕缓冲区与帧计时 |
| 颜色常量 | `COLORDEFAULT` / `RED` / `GREEN` / `YELLOW` / `BLUE`（:16-20） | 只有 5 种前景色 |
| 生命周期 | `initGame()`（:34）、`exitGame()`（:99）、`cursorEcho()`（:93） | 进入/退出"备用屏幕"、隐藏光标 |
| 绘制 | `clear()`（:44）、`drawChar()`（:51）、`refresh()`（:85） | 清缓冲、写一个字符、刷屏 |
| 输入 | `linuxTerminalCheck()`（:26）、`getch(nodelay)`（:54） | 判断是否 tty；Windows 用 msvcrt、POSIX 用 termios+select |
| 环境与帧率 | `getTerminalSize()`（:30）、`frameStart()`（:22）、`sleepForFrame(fps)`（:105） | 读终端尺寸、控帧率 |

**结论：架构本身是对的**（缓冲区 + 整帧刷新是终端游戏的正确做法），
问题几乎全部出在**实现细节的笔误**和**缺少防御性检查**上——这也解释了为什么它看起来"能跑"，
实际一用就崩。

---

## 二、问题清单与修复方案

优先级判定标准：

- **高**：直接导致程序崩溃、画面错乱或核心功能不可用，必须修。
- **中**：特定平台/特定用法下出错，或性能、可维护性明显受损。
- **低**：文档错误、代码风格、工程配套缺失，不影响运行。

### 高优先级（5 项，全部已修复）

#### H1　`initGame()` 造出的缓冲区是 24×24，而且单元格少一个字段

- **位置**：`escurses.py:40-41`
- **原代码**：
  ```python
  for i in range(_screenHeight):
      _screen.append([(' ', i+1, j+1) for j in range(_screenHeight)])
  ```
- **现象（实测）**：调用 `initGame()` 后，`len(_screen) == 24`（行数对），
  但每行只有 **24** 格（应该是 80），且每格是 **3 元组**（应该是 4 元组）。
  紧接着调用 `refresh()` 立刻崩溃：`IndexError: tuple index out of range`（`escurses.py:88`）。
- **根因**：两个笔误叠在一起。
  ① 内层循环的 `range(_screenHeight)` 应该是 `range(_screenWidth)`——列数用了高度；
  ② 元组 `(' ', i+1, j+1)` 漏了颜色字段，而 `refresh()` 会访问 `char[3]`。
- **修复方案**：把"造一块空屏幕"抽成一个函数，宽高分开传，一次性把 4 个字段都写对。
  这也是初学者最好理解的写法——**只在一个地方造缓冲区，就不会再出现"两处不一致"**：
  ```python
  def _makeBlankScreen(width, height):
      """创建一个 width 列、height 行的空白屏幕缓冲区。"""
      return [[(' ', y + 1, x + 1, COLORDEFAULT) for x in range(width)]
              for y in range(height)]
  ```
  `initGame()` 和 `clear()` 都改成调用它。
- **影响范围**：内部数据结构。所有公开函数的签名不变，`_screen` 的结构仍然是
  `(字符, y, x, 颜色)`，只是现在**真的是** `height × width` 且每个格子字段齐全。
  修好之前 `refresh()` 根本无法工作，所以这属于"修 bug"而非"改行为"。

#### H2　备用屏幕的进入/退出序列写反了（h 和 l 抄反）

- **位置**：`escurses.py:42`（`initGame` 里）和 `escurses.py:101`（`exitGame` 里）
- **原代码**：
  ```python
  # initGame()
  sys.stdout.write("\033[?1049l")   # ← l = leave，退出备用屏幕
  # exitGame()
  sys.stdout.write("\033[?25h")
  sys.stdout.write("\033[?1049h")   # ← h = home，进入备用屏幕
  ```
- **现象（实测）**：`initGame()` 的输出里只有 `\033[?1049l`，`exitGame()` 的输出是
  `\033[?25h\033[?1049h`——**正好相反**。
  后果是：游戏开始时并没有进入备用屏幕（游戏画面直接糊在用户原来的终端内容上），
  退出时反而**进入**了备用屏幕，用户的终端看起来"被清空了"。
- **根因**：`?1049h` 是进入备用屏幕（**h**igh），`?1049l` 是退出（**l**ow），抄反了。
- **修复方案**：定义两个有名字的常量，让方向一眼可读，不再散落魔法字符串：
  ```python
  _ENTER_ALT_SCREEN = "\033[?1049h"   # 进入“备用屏幕”
  _EXIT_ALT_SCREEN  = "\033[?1049l"   # 退出备用屏幕
  ```
  `initGame()` 写 `_ENTER_ALT_SCREEN`，`endGame()` 写 `_EXIT_ALT_SCREEN`。
- **影响范围**：纯行为修正，无 API 变化。修好后"退出游戏 → 终端恢复原样"才成立。

#### H3　`clear()` 只清了 79 列（少一列）

- **位置**：`escurses.py:49`
- **原代码**：`for j in range(_screenWidth - 1)` —— 多减了 1。
- **现象（实测）**：`clear()` 后每行只有 **79** 格，`max_x == 79`；
  第 80 列永远保持上一帧的内容，且 `drawChar(80, 1, ...)` 直接
  `IndexError: list assignment index out of range`。
- **根因**：`- 1` 是笔误（大概是想着"从 0 开始数"）。
- **修复方案**：改用 H1 里的 `_makeBlankScreen(_screenWidth, _screenHeight)`，
  宽度直接用 `range(width)`，这个错误就永远不会再出现。
- **影响范围**：同 H1，属于内部实现。修好后整屏 80 列都可以正常绘制。

#### H4　`drawChar()` 没有任何边界检查

- **位置**：`escurses.py:51-52`
- **原代码**：
  ```python
  def drawChar(x, y, char, color = COLORDEFAULT):
      _screen[y-1][x-1] = (char, y, x, color)
  ```
- **现象（实测）**：
  - `drawChar(80, 1, 'A')`、`drawChar(1, 25, 'A')` → `IndexError` 崩溃；
  - 更隐蔽的是 **`drawChar(0, 1, 'A')` / `drawChar(-1, 1, 'A')` 不报错**，
    因为 Python 的负索引会**回绕**，字符被静默写到了"最后一行末列"——画面莫名其妙多出一个字，
    初学者根本查不出来；
  - 未调用 `initGame()` 就画 → `TypeError: 'NoneType' object cannot be interpreted as an integer`。
- **修复方案**：三层防御，每一层都给出对初学者友好的结果：
  1. **没初始化** → 抛带中文提示的 `RuntimeError`（比 `TypeError` 好懂一万倍）；
  2. **坐标越界** → **返回 `False` 并安静忽略**，不崩；
  3. **多字符** → 只取第一个字符（原版会把 `'ab'` 整个塞进一格，`refresh()` 输出时错位）。
  ```python
  def drawChar(x, y, char, color=COLORDEFAULT):
      _ensureInited("drawChar")
      if not char:
          return False
      character = char[0]
      if x < 1 or y < 1 or x > _screenWidth or y > _screenHeight:
          return False
      ...
      return True
  ```
- **影响范围**：`drawChar()` 的返回值从 `None` 变成 `bool`。
  旧代码如果只是"调用完不管返回值"，完全不受影响（这是绝大多数情况）；
  新代码可以用返回值判断是否撞墙（`examples/bounce.py` 就是这么用的）。
  越界不再抛异常是**行为改变**，但这正是游戏需要的行为——角色走出屏幕不应该让程序崩。
  如果确实想捕获越界，看返回值即可。

#### H5　`sleepForFrame()` 的帧率被"地板"卡在 100 fps

- **位置**：`escurses.py:105-110`
- **原代码**：
  ```python
  frameTime = 1 / fps
  elapsedTime = time.perf_counter() - _frameStartTime
  time.sleep(max(0, (frameTime - elapsedTime) - 0.01))
  while time.perf_counter() - _frameStartTime < 0.01:   # ← 这里
      pass
  ```
- **现象（实测）**：`sleepForFrame(60)` 的实测帧周期是 **10.00 ms**（≈100 fps，应该 16.67 ms）；
  `sleepForFrame(120)`、`sleepForFrame(240)` 也全都是 10.00 ms。
  也就是说**帧率最高只能到 100 fps，写多少都白搭**。而且每次忙等约 43524 次空转。
- **根因**：忙等的条件是 `time.perf_counter() - _frameStartTime < 0.01`——
  用的是**绝对 0.01 秒**，而不是"这一帧应该在什么时候结束"。
  于是整个函数等价于 `max(1/fps - 0.01, 0.01)`。
- **修复方案**：先算出"这一帧的目标结束时刻"，再朝那个时刻收敛：
  ```python
  targetTime = _frameStartTime + frameTime
  remain = targetTime - time.perf_counter()
  if remain > 0:
      time.sleep(max(0.0, remain - 0.001))          # 先睡掉大部分
      while time.perf_counter() < targetTime:       # 最后最多忙等 1 ms
          pass
  ```
  另外补两个友好处理：`fps <= 0` 抛 `ValueError`（原来是 `ZeroDivisionError`）；
  忘了调 `frameStart()` 时不再 `TypeError`，而是把当前时刻当作本帧起点。
- **影响范围**：纯内部修正，签名不变。修好后 `sleepForFrame(60)` 实测 ≈16.7 ms/帧。
  唯一的行为变化是 `fps <= 0` 的异常类型从 `ZeroDivisionError` 变成 `ValueError`（都是崩溃，影响可忽略）。

### 中优先级（7 项）

#### M1　POSIX 阻塞模式下 `getch(False)` 要先按回车

- **位置**：`escurses.py:76-83`
- **现象**：Linux/macOS 上 `getch(False)`（阻塞模式）必须先按回车才返回，
  而且输入的字符会回显在屏幕上。`getch(True)` 反而是好的。
- **根因**：非阻塞分支里有 `tty.setcbreak(fd)`，阻塞分支**漏了这一行**——
  于是终端还停在"规范模式"（行缓冲 + 回显）。
- **修复方案**：两个分支都先 `tty.setcbreak(fd)`，并用 `try/finally` 保证恢复：
  ```python
  try:
      tty.setcbreak(fd)      # 阻塞和非阻塞都要先进 cbreak 模式
      if nodelay:
          if select.select([fd], [], [], 0)[0]:
              return sys.stdin.read(1)
          return None
      return sys.stdin.read(1)
  finally:
      termios.tcsetattr(fd, termios.TCSADRAIN, oldSettings)
  ```
- **影响范围**：POSIX 平台的行为修正，Windows 分支不受影响。

#### M2　`getTerminalSize()` 在输出被重定向时直接崩溃

- **位置**：`escurses.py:30-32`
- **现象（实测）**：把 stdout 重定向到文件/管道后调用 → `OSError: [WinError 6] 句柄无效`；
  `stdin` 是 `StringIO` 时 `linuxTerminalCheck()` → `UnsupportedOperation: fileno`。
  这意味着**在 IDE 输出窗口、CI、单元测试里根本用不了**。
- **根因**：直接用 `os.get_terminal_size()`，没有兜底。
- **修复方案**：改用标准库自带兜底的 `shutil.get_terminal_size(fallback=(80, 24))`；
  `linuxTerminalCheck()` 用 `try/except (AttributeError, ValueError, OSError)` 包住。
- **影响范围**：签名不变；读不到真实尺寸时返回 80×24 而不是崩溃。

#### M3　`import ctypes` 导入了却从没用过

- **位置**：`escurses.py:3`
- **现象**：静态检查会报"unused import"。但**直接删掉是错的**——它应该被用起来。
- **根因**：Windows 10 以前的控制台默认不认 ANSI 转义序列，
  会把 `\033[31m` 原样打成 `←[31m` 这种乱码。要让它认识，必须打开
  `ENABLE_VIRTUAL_TERMINAL_PROCESSING` 这个开关，而这需要 `ctypes` 调 Win32 API。
- **修复方案**：新增 `_enableWindowsAnsi()`，在 `initGame()` 最开头调用；
  取不到句柄（输出被重定向）时安静跳过，不影响 Linux：
  ```python
  kernel32 = ctypes.windll.kernel32
  stdOutputHandle = kernel32.GetStdHandle(-11)
  consoleMode = ctypes.c_ulong()
  if kernel32.GetConsoleMode(stdOutputHandle, ctypes.byref(consoleMode)):
      ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
      if not consoleMode.value & ENABLE_VIRTUAL_TERMINAL_PROCESSING:
          kernel32.SetConsoleMode(stdOutputHandle,
                                  consoleMode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING)
  ```
- **影响范围**：只影响 Windows 的显示效果（乱码 → 正常颜色），API 不变。
  **待人工验证**：旧版 Windows（Win7/8）是否仍然可用——那里没有这个开关，只能靠用户换终端。

#### M4　`refresh()` 逐格写，一帧 5688 次 `write`

- **位置**：`escurses.py:85-91`
- **现象（实测）**：80×24 屏幕一帧要调用 **5688 次** `sys.stdout.write`、
  输出 **31305 字节**，其中包含 **3792 个**重复的 `\033[0m` 复位序列。
- **根因**：对**每一个格子**都发三条转义序列：
  `颜色码` + `光标定位+字符` + `复位`。逐格定位是终端渲染里最慢的做法之一。
- **修复方案**：改成**按行**输出——
  1. 每行只在行首发一次 `\033[{row};1H`；
  2. 颜色**变了才发**颜色码（用一个 `currentColor` 变量记住当前颜色）；
  3. 行尾的空白不真写，最后用 `\033[K`（擦到行尾）一次抹掉；
  4. 整个屏幕的字符串拼好后**一次** `write` + 一次 `flush`。
- **影响范围**：输出格式变了，但**画出来的画面完全一样**。
  实测收益见「三、性能对比」。

#### M5　没初始化时 `refresh()` 静默什么都不做（最难查的 bug）

- **位置**：`escurses.py:85`
- **现象**：忘了调 `initGame()` 时，`refresh()` 遍历空的 `_screen`，**不报错、不输出、也不提示**。
  初学者会以为"画的东西丢了"，实际是根本没初始化。
- **根因**：缺少状态检查。
- **修复方案**：加 `_ensureInited()`，在所有绘制/刷新 API 开头调用，
  抛一条看得懂的中文错误：
  ```python
  raise RuntimeError("请先调用 initGame()，再调用 refresh()。")
  ```
- **影响范围**：错误从"静默失败"变成"立刻报错并说明原因"。
  对正确使用的代码零影响。

#### M6　全角字符（汉字）只占一格，导致整行错位

- **位置**：`escurses.py:51-52`
- **现象（实测）**：`drawChar(1, 2, '汉')` 只占 1 格。
  但终端里汉字实际占 **2 格**，于是同一行后面的所有字符都会整体左移一格，
  屏幕右下角还会"吃掉"一个字符。
- **根因**：库把"一个 Python 字符"等同于"一格屏幕"，这在中文环境下不成立。
- **修复方案**：用 `unicodedata.east_asian_width()` 判断宽度（`'W'`/`'F'` 算 2 格）：
  ```python
  def _getCharWidth(character):
      if unicodedata.east_asian_width(character) in ('W', 'F'):
          return 2
      return 1
  ```
  全角字符占两格：第一格存字符本身，第二格存 `''` 当"占位标记"，
  `refresh()` 看到 `''` 就跳过（因为终端已经把这两格都画出来了）。
  另外 `_clearCell()` 负责"擦格子时把另一半也擦掉"，避免屏幕上留下半个汉字。
- **影响范围**：新增内部函数，公开 API 不变。`drawChar` 在最后一列遇到全角字符时返回 `False`
  （放不下两个格子，宁可不画，避免错位）。

#### M7　没有 `atexit` 兜底，异常退出会把终端弄坏

- **位置**：`escurses.py:99-103`
- **现象**：游戏里抛了没捕获的异常，`exitGame()` 不会执行，
  终端就停在"隐藏光标 + 备用屏幕"状态，用户得手动敲 `reset` 才能恢复。
- **修复方案**：`initGame()` 里 `atexit.register(endGame)`（只注册一次），
  并把"恢复终端"抽成独立的 `endGame()`，这样它既能被 `finally` 调用，
  也能被 `atexit` 调用，而且**不会 `sys.exit()`**（在 `finally` 里 `sys.exit()` 会吞掉原异常）。
- **影响范围**：新增 `endGame()` 公开函数；`exitGame()` 保留，内部改成 `endGame() + sys.exit()`，
  老代码继续可用。

### 低优先级（11 项）

| 编号 | 问题 | 修复 |
| --- | --- | --- |
| L1 | `README-zh.md` / `README-en.md` 把 `getTerminalSize()` 的返回值顺序写反（写成"高, 宽"） | 统一写"**(宽, 高)**"，并注明单位是字符数 |
| L2 | 两份 README 提到不存在的 `_maxScreenWidth` / `_maxScreenHeight` | 改成真实变量名 `_screenWidth` / `_screenHeight` |
| L3 | 中文 README 的 `drawChar(x, y, char)` 缺 `color` 参数 | 补上参数说明 + 颜色常量表 |
| L4 | 只有 5 个颜色常量，缺黑/洋红/青/白和全部亮色 | 补齐 16 个（30-37 + 91-97） |
| L5 | 全库 0 注释、0 docstring、0 类型标注 | 每个公开函数加 docstring（含参数、返回值、坐标约定），全部加类型标注 |
| L6 | 无 LICENSE | 建议补 MIT（需作者确认，见「六、后续建议」） |
| L7 | 无 `.gitignore` | 已补（`__pycache__/`、`*.py[cod]`、IDE 目录等） |
| L8 | 无 examples/、tests/，README 也没教怎么跑 | 已补两个可运行例子 + 16 个单元测试 |
| L9 | `cursorEcho()` 只 write 不 flush，隐藏光标可能延迟生效 | 补 `flush()` |
| L10 | `refresh()` 不处理窗口 resize；`initGame()` 不隐藏光标 | 新增 `resize()`；`initGame()` 里发 `\033[?25l` |
| L11 | `exitGame()` 裸 `sys.exit()`，退出码是 `None`；放在 `finally` 里会吞掉原异常 | 拆出 `endGame()`（不退出），`exitGame()` = `endGame() + sys.exit()` |
| L12 | 第 40 行行尾多余空格、第 49 行多缩进 4 格、文件末尾无换行 | 已清理（新文件全部符合 PEP 8 缩进、末尾有换行） |

---

## 三、性能对比（80×24 屏幕，输出到 StringIO，取 300 帧平均）

| 场景 | 原版（HEAD） | 新版 | 提升 |
| --- | --- | --- | --- |
| `refresh()` 的 `write` 调用次数 | **5688 次/帧** | **1 次/帧** | ≈ 5688× |
| 空屏一帧输出字节 | 31305 B | **260 B** | ≈ 120× |
| 满屏 80×24 文字一帧 | 31305 B | **2181 B** | ≈ 14× |
| 24 行短文本一帧 | 31305 B | **808 B** | ≈ 39× |
| 一帧耗时（StringIO） | 362.7 µs | **78.7 ~ 115.8 µs** | ≈ 3~4× |

> 说明：原版因为 H3 的 bug 实际只有 24×79 格，字节数仍然远高于新版。
> 在真实终端上，`write` 次数的影响比字节数更大（每次 write 都是一次系统调用 + 一次终端解析），
> 所以"每帧 1 次 write"的收益比表格里的数字更明显。

帧率修复前后的实测对比（`sleepForFrame`）：

| 请求帧率 | 原版实测帧周期 | 新版实测帧周期 | 理论值 |
| --- | --- | --- | --- |
| 10 fps | 90.28 ms（偏快 10%） | **100.00 ms** | 100 ms |
| 30 fps | 23.88 ms（偏快 28%） | **33.34 ms** | 33.33 ms |
| 60 fps | **10.00 ms（错，快了 40%）** | **16.67 ms** | 16.67 ms |
| 120 fps | **10.00 ms（错，慢了 20%）** | **8.33 ms** | 8.33 ms |

> 原版无论请求多少帧，周期都被卡在 10 ms 附近（最低 100 fps 的地板效应）；
> 新版在 10/30/60/120 fps 下全部与理论值一致（误差 < 0.1%）。

---

## 四、已完成的改动

### 4.1 `escurses.py`（110 行 → 403 行）

**保留了全部旧 API 的名字和调用方式**，只做修复 + 新增，不删不改语义：

| 原有 API | 状态 | 说明 |
| --- | --- | --- |
| `frameStart()` | 保留 | 不变 |
| `linuxTerminalCheck()` | 保留 | 加了异常兜底 |
| `getTerminalSize()` | 保留 | 返回 `(宽, 高)`，读不到时兜底 80×24 |
| `initGame()` | 保留 | 修 H1/H2、开 Windows VT、隐藏光标、注册 atexit |
| `clear()` | 保留 | 只清缓冲区（不再发全屏清除序列，见下） |
| `drawChar(x, y, char, color=COLORDEFAULT)` | 保留 | 加边界检查（返回 `bool`）、支持全角 |
| `getch(nodelay=True)` | 保留 | 修 POSIX 阻塞模式 |
| `refresh()` | 保留 | 改成按行输出，性能大幅提升 |
| `cursorEcho(echo=False)` | 保留 | 补 `flush()` |
| `exitGame()` | 保留 | 内部改为 `endGame() + sys.exit()` |
| `sleepForFrame(fps)` | 保留 | 修 H5 |

**新增 API**（都是"补全"，不破坏兼容）：

| 新增 | 作用 |
| --- | --- |
| `drawText(x, y, text, color=COLORDEFAULT) -> int` | 一次画一串字符，返回实际占的格数 |
| `endGame()` | 恢复终端但**不退出程序**，适合放在 `finally` |
| `resize()` | 重新读取终端尺寸并重建缓冲区 |
| 16 个颜色常量 | 补齐 `COLORBLACK` / `MAGENTA` / `CYAN` / `WHITE` 和全部亮色（91-97） |

**一个需要说明的行为变化**：`clear()` 不再向终端发 `\033[2J\033[H`（全屏清除），
只把内部缓冲区清空。原因是 `refresh()` 现在会整行重画并用 `\033[K` 擦掉行尾，
每帧多发一次全屏清除只会造成**闪屏**，没有好处。
标准写法仍然是 `clear() → 重新画 → refresh()`，视觉效果完全一致。
这一点已经写进 `clear()` 的 docstring 和两份 README。

### 4.2 新增 `tests/test_escurses.py`（150 行，16 个用例，全部通过）

用 `FakeStdout(io.StringIO)` 把终端输出收进内存，不依赖真实终端，`python -m unittest discover -s tests` 即可运行。
覆盖：缓冲区尺寸、备用屏幕进出序列、未初始化报错、`clear()` 全宽、
`drawChar` 写入/越界/全角、`drawText`、`refresh` 不崩且输出不过大、
`getTerminalSize` 返回正数、`getch` 无按键返回 `None`、`sleepForFrame` 帧率准确与非法参数。

### 4.3 新增 `examples/`

- `examples/hello.py`：最小例子，屏幕居中写字，按 q 退出。
- `examples/bounce.py`：WASD/方向键移动小球，带帧率控制和步数统计，
  演示了"用 `drawChar` 的返回值判断是否撞墙"的写法。

### 4.4 文档

- `README-zh.md`（257 行）：安装、快速上手、游戏循环六步模板、坐标系图示、
  16 色表、完整 API 说明、FAQ 7 条、开发与测试。
- `README-en.md`（268 行）：英文对应版。
- `README.md`（54 行）：首页 + 仓库结构表 + 中英文档入口。
- `.gitignore`：忽略 `__pycache__/`、`*.py[cod]`、IDE 目录等。

---

## 五、验证方式

```bash
# 跑单元测试（16 个用例）
python -m unittest discover -s tests -v

# 跑例子
python examples/hello.py
python examples/bounce.py
```

实测结果：`Ran 16 tests ... OK`（0.17s），两个例子在模拟环境下跑通、无异常。

---

## 六、后续建议（未实施，需要作者决定）

1. **补 LICENSE**。仓库目前没有任何许可证文件，法律上等于"保留所有权利"，
   别人不敢用、也不能合法地帮你改。对这类面向儿童的开源项目，**MIT** 是最常见、
   最宽松的选择。因为涉及版权归属（原作者 KID194），建议由作者确认后再加。
2. **macOS 验证**。作者没有 Mac，`posix` 分支在 macOS 上理论上可用但从未验证过。
   建议在 README 的 FAQ 里继续保留"求测试"的说明，或者找人在 macOS 上跑一遍
   `examples/bounce.py` 确认按键和帧率正常。
3. **旧版 Windows 验证**。M3 的 `ENABLE_VIRTUAL_TERMINAL_PROCESSING` 需要 Win10+，
   Win7/8 上大概率仍然乱码。建议在 README 里明确写"要求 Windows 10 或更高版本"。
4. **可选：`pyproject.toml`**。如果以后想让人 `pip install escurses`，
   加一个最小的 `pyproject.toml` 即可；目前"复制单个文件"的方式对初学者更友好，
   不急着改。
5. **可选：更多绘制原语**（`drawRect` / `fillRect` / `drawLine`）。
   原仓库的 fork `EScurses-fix` 已经实现了这些，可以参考它的 API 设计保持一致。
