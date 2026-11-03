"""最小的 EScurses 例子：在屏幕中间写一行字，按 q 退出。

运行方式（在仓库根目录）：python examples/hello.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import escurses


def main():
    escurses.initGame()
    try:
        escurses.clear()
        # 先问一下屏幕有多大，好把文字摆在中间。
        width, height = escurses.getTerminalSize()
        text = "Hello, EScurses!"
        escurses.drawText(
            (width - len(text)) // 2 + 1,
            height // 2,
            text,
            escurses.COLORBRIGHTCYAN,
        )
        escurses.refresh()

        # 等玩家按 q。getch(False) 是阻塞的，会一直等到有按键才返回。
        while True:
            key = escurses.getch(False)
            if key in ('q', 'Q'):
                break
    finally:
        escurses.endGame()


if __name__ == "__main__":
    main()
