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
| `COLOR_*`（16 色） | 前景色常量：`COLOR_RED`、`COLOR_BRIGHT_CYAN` 等 |
| `drawChar / drawText / drawRect / fillRect(..., color=)` | 所有绘制函数新增 `color` 参数，支持彩色输出 |
| `resize()` | 重新读取终端尺寸并重建缓冲 |
| `isTTY()` | `linuxTerminalCheck()` 的语义化别名 |

---

## 三、实现细节改进

- **屏幕缓冲简化**：从 `(字符, y, x)` 元组二维数组，简化为纯字符二维列表，读写更直观。
- **`refresh()` 按行批量绘制**：每行只发一次光标定位 `\033[y;1H` + 整行字符串，
  不再逐格发定位码，输出量从「格数」级降到「行数」级。
- **脏行增量刷新**：用 `_dirtyRows` 记录发生变化的行，`refresh()` 只重绘这些行。
- **彩色输出**：每个格子单独记录颜色，`refresh()` 在颜色变化处插入 SGR 码，行尾重置。
- **中文宽字符对齐**：用 `unicodedata.east_asian_width` 判断全角字符（占 2 列），
  在缓冲里用一个「占位格」标记第二列，`drawText` 按显示宽度推进，中文不再错位。
- **POSIX 输入**改用 `os.read(fd, 1)` 读字节，支持最多 4 字节的转义序列，
  能识别 Home / End / PgUp / PgDn / Delete 等。
- **Windows 输入**用扫描码映射更多按键。
- `getch()` 对不支持的平台显式抛 `RuntimeError`。

---

## 四、示例游戏

### `snake.py` —— 贪吃蛇
- 固定 **40 × 20** 棋盘，带偏移绘制，边框用 Unicode 制表符 `─ │ ┌ ┐ └ ┘`。
- **WASD + 方向键**双套操作。
- **P 暂停 / R 重开 / Q 退出**。
- **最高分（Best）** 记录，重开不清零。
- 每帧最多排空 8 个输入，避免快速按键丢失。
- 蛇头 `@`、蛇身 `o`、食物 `●`；撞墙或咬到自己判定。
- `try / finally` 保证退出时恢复终端。

### `undertale.py` —— Undertale 风格弹幕战斗（新）
一个致敬《Undertale》的回合制弹幕小游戏，主要用来展示库的**颜色 + 全角字符 + 实时弹幕**能力。

- **战斗流程**：每回合选 `FIGHT / ACT / ITEM / MERCY`，选完进入敌人回合，在弹幕框里用 **WASD** 闪避。
- **3 种敌人**（Froggit / Whimsun / Moldsmal），各有 HP / ATK / DEF 与专属 ACT 对话。
- **10 种弹幕模式**：`rain`、`sweep`、`spiral`、`wall`、`homing`、`burst`、`cross`、`laser`、`ring`、`vortex`，随机轮换，难度随回合数提升。
- **Mercy 宽恕**：通过 ACT 累积 Mercy，满 100 可 Spare 敌人，和平通关。
- **道具**：Monster Candy / Spider Donut 回血，每局独立计数，重开自动重置。
- **结算**：`R` 重开、`Q` 退出；带受击抖动、无敌闪烁等效果。
- 操作：`A/D` 选择菜单，`W/S` 选择子项，`回车` 确认，敌人回合 `WASD` 闪避。

---

## 五、已知取舍 / 注意事项

- **终端尺寸**：`snake.py` 需 ≥ 43×23，`undertale.py` 需 ≥ 64×24；默认 **80×24** 即可运行。
- **颜色**依赖终端支持 ANSI（Windows 已由 VT 模式开启），极少数老终端可能不支持彩色。
- 每帧 `clear()` + 全行重绘，会整屏重画；`_dirtyRows` 已就绪，若游戏侧不每帧 `clear()` 即可享受增量刷新。
- 全角字符按 2 列处理，已对齐；但极端情况下（如 emoji 组合序列）宽度判断可能不准。

---

## 运行方式

```bash
# 在真实终端（Windows cmd/PowerShell、macOS Terminal/iTerm2、Linux tty）中运行
python snake.py        # 贪吃蛇
python undertale.py    # Undertale 风格弹幕战斗
```

> 注意：务必在**会解析 ANSI 的真终端**里跑；部分 IDE 内嵌终端对 ANSI 支持不全。
