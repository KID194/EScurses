# EScurses（Fork）

一个跨平台（Windows / Linux / macOS）的终端游戏小库。
本仓库 fork 自 [KID194/EScurses](https://github.com/KID194/EScurses)，主要做跨平台修复与功能增强。

> API 使用文档见 [README-zh.md](./README-zh.md)。

以下记录本 fork 相对**上游原版**的主要改动，按模块分类。

---

## 一、核心修复 / 跨平台兼容

### 1. Windows 开启 VT 模式（关键修复）
上游在 Windows 上直接输出 `\033[...` 这类 ANSI 转义码，但 Windows 控制台**默认不解析**它们，
于是整屏会显示成 `[28;70H`、`[29;1H` 这样的原始乱码，且刷屏量巨大。
本 fork 新增 `_enableWindowsVT()`，通过 `ctypes` 调用 `SetConsoleMode`
设置 `ENABLE_VIRTUAL_TERMINAL_PROCESSING (0x0004)`，让 Windows 也能正常渲染 ANSI。
**这是"运行起来满屏乱码"问题的真正根因修复。**

### 2. 终端模式持久化 + 退出自动恢复
- 上游在每次 `getch()` 里都 `tcgetattr` → `setcbreak` → `tcsetattr` 来回切换，
  高频调用下开销大，且异常退出时终端可能卡在 raw 模式。
- 本 fork 改为：`initGame()` 时**一次性**进入 cbreak（`_initTerminalPosix`），
  并用 `atexit` 注册 `_restoreAll()`，无论正常退出还是崩溃都能恢复光标与终端设置。

### 3. 缓冲宽度保留最右列（`screenWidth - 1`）
有意让缓冲区宽度比终端少 1 列。这样每行最后一个字符落在"倒数第二列"，
**规避"写满最右列触发终端自动换行 / 滚动"的经典问题**（这也是上游原本用 `width - 1` 的真实原因）。

### 4. 去掉 subprocess 清屏
`exitGame()` 不再 `shell` 调用 `cls` / `clear`，改用纯 ANSI 序列清屏，跨平台更干净。

---

## 二、新增 API

| 名称 | 说明 |
|------|------|
| `KEY_UP / KEY_DOWN / KEY_LEFT / KEY_RIGHT` | 方向键常量（取代原来的裸字符串） |
| `KEY_HOME / KEY_END / KEY_PGUP / KEY_PGDN / KEY_DEL / KEY_ESC` | 新增功能键 |
| `drawRect(x, y, w, h, char, fill)` | 画矩形（可空心/实心） |
| `fillRect(x, y, w, h, char)` | 填充矩形 |
| `resize()` | 重新读取终端尺寸并重建缓冲 |
| `isTTY()` | `linuxTerminalCheck()` 的语义化别名 |

---

## 三、实现细节改进

- **屏幕缓冲简化**：从 `(字符, y, x)` 元组二维数组，简化为纯字符二维列表，读写更直观。
- **`refresh()` 按行批量绘制**：每行只发一次光标定位 `\033[y;1H` + 整行字符串，
  不再逐格发定位码，输出量从「格数」级降到「行数」级。
- **POSIX 输入**改用 `os.read(fd, 1)` 读字节，支持最多 4 字节的转义序列，
  能识别 Home / End / PgUp / PgDn / Delete 等。
- **Windows 输入**用扫描码映射更多按键。
- `getch()` 对不支持的平台显式抛 `RuntimeError`。

---

## 四、示例游戏 `snake.py` 完全重写

- 固定 **40 × 20** 棋盘，带偏移绘制，边框用 Unicode 制表符 `─ │ ┌ ┐ └ ┘`。
- **WASD + 方向键**双套操作。
- **P 暂停 / R 重开 / Q 退出**。
- **最高分（Best）** 记录，重开不清零。
- 每帧最多排空 8 个输入，避免快速按键丢失。
- 蛇头 `@`、蛇身 `o`、食物 `●`；撞墙或咬到自己判定。
- `try / finally` 保证退出时恢复终端。

---

## 五、已知取舍 / 注意事项

- **终端尺寸要求 44 × 26**（棋盘 40×20 + 边距）。默认 **80×24** 的终端会提示"太小"直接退出。
  这是目前最影响体验的一点，建议把 `H` 调到 18，或让棋盘尺寸自适应终端。
- 每帧 `clear()` + 全行重绘，会整屏重画；简单游戏够用，若要更顺滑可改为"只重绘变化行/差异刷新"。
- `drawText` 按「1 字符 = 1 格」处理，**CJK 宽字符（占 2 格）会错位**。
- 两个源文件结尾缺换行（PEP8 小问题）。

---

## 运行方式

```bash
# 在真实终端（Windows cmd/PowerShell、macOS Terminal/iTerm2、Linux tty）中运行
python snake.py
```

> 注意：务必在**会解析 ANSI 的真终端**里跑；部分 IDE 内嵌终端对 ANSI 支持不全。
