# EScurses Home Page

![EScurses Icon](./Icon/EScursesIcon64x64.png)

**首页 / Home**

[跳转至中文 README](./README-zh.md)

[Turn to the English README](./README-en.md)

---

## EScurses 是什么？

一个只有单文件、零依赖的 Python 终端游戏库，面向儿童和初学者。
坐标从 `(1, 1)` 开始，`drawChar()` 画一个字符、`refresh()` 一次性刷新屏幕。

```python
import escurses

escurses.initGame()
try:
    escurses.clear()
    escurses.drawText(1, 1, "Hello, EScurses!", escurses.COLORBRIGHTCYAN)
    escurses.refresh()
    while escurses.getch(False) != "q":
        pass
finally:
    escurses.endGame()
```

完整文档请看 [中文 README](./README-zh.md) 或 [English README](./README-en.md)。
可以直接运行的例子在 [`examples/`](./examples) 目录里。

## 仓库结构

| 路径 | 说明 |
| --- | --- |
| [`escurses.py`](./escurses.py) | 库本体，就这一个文件（复制到你的项目里即可） |
| [`examples/hello.py`](./examples/hello.py) | 最小例子：在屏幕中间写字，按 q 退出 |
| [`examples/bounce.py`](./examples/bounce.py) | 用 WASD 移动小球，带帧率控制 |
| [`tests/`](./tests) | 单元测试，运行 `python -m unittest discover -s tests -v` |
| [`REVIEW.md`](./REVIEW.md) | 代码审查报告：问题清单、修复方案、优先级与影响范围 |
| [`Icon/`](./Icon) | 项目图标 |

## EScurses's other version (on forks)

**There's the other version better than original! :**

- **EScurses-fix** (By Natsuki3462): https://github.com/Natsuki3462/EScurses-fix
  fixed many bug on EScurses, and added some new feautures like: `drawRect()`, `drawText()`, `fillRect`, `resize()`
- **Escurses** (by 9178nekomc): https://github.com/9178nekomc/EScurses
  Overrided some APIs, and you also can use the original style(called 1.0 API) to code, or using the new style(called 2.0 API)
- **EScurses-h** (By Jej1111064): https://github.com/Jej1111064/EScurses-h
  If it has new feauture or fixed bug, I will write it on here
