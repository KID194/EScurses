# EScurses

一个可以让你用 Python 做出终端小游戏的库 —— 只有一个文件，不用安装任何第三方库。

[跳转至首页](./README.md) | [English README](./README-en.md)

## 为什么你有必要选择 EScurses?

- **跨平台支持**
  它可以在 Windows 上用，也可以在 Linux 上用。
  所以你不用因为这个库不兼容系统而担心，除非你在用 macOS。
- **易用**
  你只需要下载它然后把它丢进你的代码目录里，然后你就可以用了！
- **受维护**
  你应该不知道 pycurses，那是个很老很老的库，早就没人维护了。
  而 EScurses 比它新太多了，这意味着你可以不用担心它突然断更。
  但作者也是要上学的 QAQ（我只是个五年级的小孩）。

> 我并没有 MacBook，因为这并不是个常见的东西，它太贵了，至少对我来说是这样。
> 所以……如果你有 MacBook，帮我测试一下这个库能不能在 macOS 上用。
> 我需要帮助 :)

## 安装

EScurses 不需要 `pip install`，只要把 `escurses.py` 这一个文件复制到你的代码目录里：

```
你的项目/
├── escurses.py      ← 复制这一个文件过来
└── mygame.py        ← 你自己的游戏
```

然后在你的代码里 `import escurses` 就可以了。

要求：Python 3.7 或更新的版本。

> **Windows 用户注意**：EScurses 会自动帮你打开控制台的“虚拟终端”支持，
> 这样颜色和定位才能正常显示。如果你用的是很老的 Windows 或者某些第三方终端，
> 显示可能不正常，请换用 Windows Terminal 或新版 cmd。

## 快速上手

保存成 `mygame.py`，然后运行 `python mygame.py`：

```python
import escurses

escurses.initGame()
try:
    escurses.clear()
    escurses.drawText(1, 1, "Hello, EScurses!", escurses.COLORBRIGHTCYAN)
    escurses.drawChar(1, 3, "@", escurses.COLORRED)
    escurses.refresh()

    # 一直等到玩家按 q 才退出
    while True:
        key = escurses.getch(False)
        if key == "q":
            break
finally:
    escurses.endGame()
```

`try ... finally` 很重要：就算游戏里出了错，`endGame()` 也会把终端恢复原样，
不会让终端一直停留在游戏画面里。

## 游戏循环是怎么写的

几乎所有终端游戏都是同一个套路：

```python
import escurses

escurses.initGame()
try:
    while True:
        escurses.frameStart()        # 1. 记下这一帧的开始时间

        key = escurses.getch(True)   # 2. 读按键（无阻塞，没按就返回 None）
        if key == "q":
            break

        escurses.clear()             # 3. 清空上一帧
        escurses.drawChar(5, 5, "@") # 4. 画这一帧
        escurses.refresh()           # 5. 一次性刷到屏幕上

        escurses.sleepForFrame(30)   # 6. 把帧率控制在 30 帧/秒
finally:
    escurses.endGame()
```

更多可以直接运行的例子在 [`examples/`](./examples) 目录里：

| 例子 | 内容 |
| --- | --- |
| [`examples/hello.py`](./examples/hello.py) | 在屏幕中间写一行字，按 q 退出 |
| [`examples/bounce.py`](./examples/bounce.py) | 用 WASD 移动一个小球，带帧率控制 |

## 坐标系

屏幕左上角是 **(1, 1)**，不是 (0, 0)！

```
(1,1) ──────────► x 变大
  │
  │
  ▼
 y 变大
```

`drawChar(x, y, ...)` 的第一个参数是 x（横着数），第二个是 y（竖着数）。

## 文档

### 颜色常量

把下面这些常量传给 `drawChar()` 或 `drawText()` 的 `color` 参数，就能给字符上色：

| 常量 | 说明 |
| --- | --- |
| `COLORDEFAULT` | 终端默认颜色（默认值） |
| `COLORBLACK` | 黑色 |
| `COLORRED` | 红色 |
| `COLORGREEN` | 绿色 |
| `COLORYELLOW` | 黄色 |
| `COLORBLUE` | 蓝色 |
| `COLORMAGENTA` | 紫色 |
| `COLORCYAN` | 青色 |
| `COLORWHITE` | 白色 |
| `COLORBRIGHTRED` | 亮红 |
| `COLORBRIGHTGREEN` | 亮绿 |
| `COLORBRIGHTYELLOW` | 亮黄 |
| `COLORBRIGHTBLUE` | 亮蓝 |
| `COLORBRIGHTMAGENTA` | 亮紫 |
| `COLORBRIGHTCYAN` | 亮青 |
| `COLORBRIGHTWHITE` | 亮白 |

### 初始化与退出

- **`initGame()`**
  初始化游戏：读取终端尺寸、创建内部屏幕缓冲区、进入“备用屏幕”
  （这样游戏画面不会弄乱你原来的终端内容）。
  每个游戏都要在开头调用它一次，在它之后才能调用 `clear()`、`drawChar()`、`refresh()` 等函数。
  如果忘了调用就先画东西，会得到一个带中文提示的 `RuntimeError`。
- **`endGame()`**
  结束游戏、把终端恢复原样（显示光标、退出备用屏幕），但**不会**退出 Python 程序。
  适合放在 `finally` 里。
- **`exitGame()`**
  恢复终端并直接退出程序（内部会调用 `endGame()`）。
- **`resize()`**
  重新读取终端尺寸并重建屏幕缓冲区。玩家拖动窗口改变了大小时可以调用它，
  注意已经画好的内容会被清空。

### 尺寸与环境

- **`getTerminalSize()`**
  返回一个元组 `(宽, 高)`，单位是字符数，例如 `(80, 24)`。
  注意顺序是**先宽后高**（先横着的列数，再竖着的行数）。
  如果读不到尺寸（比如输出被重定向到文件），会返回默认的 `(80, 24)`。
- **`linuxTerminalCheck()`**
  检查标准输入是不是一个真正的终端（tty）。
  返回 `True` 表示可以正常读按键；返回 `False` 表示输入被重定向了
  （比如从文件读），这时阻塞式的 `getch()` 可能会表现异常。
  在 Windows 上也可以用它来判断当前是不是真正的控制台。

### 绘制

- **`clear()`**
  清空内部屏幕缓冲区，准备画新的一帧。
  它只清空“准备画什么”的缓冲区，屏幕上真正的旧内容会在下一次 `refresh()` 时被整行覆盖掉，
  所以标准写法是 `clear()` → 重新画 → `refresh()`。
- **`drawChar(x, y, char, color=COLORDEFAULT)`**
  在坐标 `(x, y)` 画一个字符。
  坐标超出屏幕范围时不会报错，只是这一笔被忽略（返回 `False`），
  所以游戏里的角色走出屏幕也不会让程序崩溃。
  汉字等全角字符会自动占两格。
  返回 `True` 表示画上去了。
- **`drawText(x, y, text, color=COLORDEFAULT)`**
  从坐标 `(x, y)` 开始，把 `text` 里的字符一个接一个画出来。
  返回实际画出来的宽度（以格为单位），方便你接着往后画。
- **`refresh()`**
  把内部缓冲区的内容画到终端上。
  它会按行输出，并且颜色没变时不重复发送颜色代码，所以比逐格画快很多。
  正常情况下每帧只需要调用一次 `refresh()`。
- **`cursorEcho(echo=False)`**
  传入 `False`（默认）隐藏光标，传入 `True` 显示光标。

### 输入

- **`getch(nodelay=True)`**
  读取一个按键。这是最难实现的一个，因为它同时包含了 Windows 的输入和 Linux 的输入，
  而且两个系统的输入都有阻塞版和无阻塞版，通过 `nodelay` 参数来控制，默认是 `True`。
  - `nodelay=True`：没按任何键时立刻返回 `None`，游戏不会卡住。
  - `nodelay=False`：一直等到你按下按键才返回。
  - 返回的是单个字符。Windows 下方向键等特殊键会返回特殊字符，需要自己判断。
  - 在 Linux 上，两种模式都按一下键就立刻返回，不需要再按回车。

### 帧率

- **`frameStart()`**
  记录这一帧的开始时间。在每次主循环的**最最最开头**调用它，
  前面不能有其他代码，然后配合 `sleepForFrame()` 使用，就可以控制帧率。
- **`sleepForFrame(fps)`**
  把帧率控制在 `fps` 帧/秒（例如 `sleepForFrame(60)` 就是每秒 60 帧）。
  它会先睡一会儿，最后再忙等一小会儿把误差收掉，所以帧率会比较准。
  `fps` 必须大于 0。

## 常见问题（FAQ）

**Q：运行后屏幕一片空白，或者显示一堆 `←[31m` 之类的乱码？**
A：这是终端不认识 ANSI 转义序列。Windows 上请用 Windows Terminal 或新版 cmd；
如果是在 IDE 的输出窗口里运行（比如 PyCharm、VS Code 的内置终端），
请改成在真正的终端里运行 `python mygame.py`。

**Q：按了键没反应，或者方向键没反应？**
A：`getch()` 返回的是单个字符。在 Windows 上，方向键之类的特殊键会返回特殊字符，
需要你自己判断。另外请确认你调用的是 `getch(True)` 还是 `getch(False)`——
前者不会等你按键，后者会一直等。

**Q：程序报错退出后，终端变成一片空白 / 光标不见了？**
A：这说明没有正确调用 `endGame()`。请把游戏主循环包在 `try ... finally` 里，
在 `finally` 中调用 `escurses.endGame()`。实在救不回来时，在终端里输入 `reset` 回车即可。

**Q：可以在 macOS 上用吗？**
A：作者没有 MacBook，没法测试。理论上 macOS 属于 posix 系统，应该能用，
但还没有人验证过。如果你测试了，欢迎反馈。

**Q：怎么改变终端窗口大小？**
A：用鼠标拖动窗口边缘。程序里可以调用 `resize()` 重新读取尺寸并重建缓冲区。

**Q：为什么坐标是 (1,1) 而不是 (0,0)？**
A：这是为了和 ANSI 转义序列的约定保持一致（终端里的行列也是从 1 开始数的）。
`drawChar()` 内部会帮你把 x 和 y 处理好，你不用操心。

## 开发与测试

```bash
# 跑单元测试
python -m unittest discover -s tests -v

# 跑例子
python examples/hello.py
python examples/bounce.py
```

测试不需要安装任何第三方库。

想了解这个库原来有哪些问题、是怎么修的，请看 [代码审查报告](./REVIEW.md)。

## 其他版本（来自 fork）

- **EScurses-fix**（作者 Natsuki3462）：https://github.com/Natsuki3462/EScurses-fix
  修好了 EScurses 的很多 bug，还加了 `drawRect()`、`drawText()`、`fillRect()`、`resize()` 等新功能。
- **Escurses**（作者 9178nekomc）：https://github.com/9178nekomc/EScurses
  重写了一些 API，你既可以用原来的风格（1.0 API）写代码，也可以用新风格（2.0 API）。
- **EScurses-h**（作者 Jej1111064）：https://github.com/Jej1111064/EScurses-h
  如果有新功能或者修了 bug，会写在这里。

这基本就是全部内容了，祝你们能做出好的游戏！（虽然这个库基本没啥用）
