"""用方向键（或 WASD）移动一个小球的例子。

运行方式（在仓库根目录）：python examples/bounce.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import escurses

FPS = 30

# 按键到“移动方向”的映射。x 向右、y 向下。
MOVES = {
    'a': (-1, 0), 'A': (-1, 0), 'h': (-1, 0),
    'd': (1, 0), 'D': (1, 0), 'l': (1, 0),
    'w': (0, -1), 'W': (0, -1), 'k': (0, -1),
    's': (0, 1), 'S': (0, 1), 'j': (0, 1),
}


def main():
    escurses.initGame()
    try:
        width, height = escurses.getTerminalSize()
        ballX = width // 2
        ballY = height // 2
        score = 0

        while True:
            escurses.frameStart()

            # 1) 读取按键：无阻塞模式，没按键就返回 None，不会卡住游戏。
            key = escurses.getch(True)
            if key in ('q', 'Q', '\x1b'):
                break
            if key in MOVES:
                dx, dy = MOVES[key]
                # drawChar 遇到越界坐标会安静地返回 False，所以不用自己判断边界。
                if escurses.drawChar(ballX + dx, ballY + dy, '@', escurses.COLORRED):
                    ballX += dx
                    ballY += dy
                    score += 1

            # 2) 绘制：先清屏，再画，最后 refresh 一次性刷到终端上。
            escurses.clear()
            escurses.drawChar(ballX, ballY, '@', escurses.COLORRED)
            escurses.drawText(1, 1, "Move with WASD. q = quit", escurses.COLORYELLOW)
            escurses.drawText(1, height, "steps: " + str(score), escurses.COLORCYAN)
            escurses.refresh()

            # 3) 控制帧率：让主循环每秒跑 FPS 次。
            escurses.sleepForFrame(FPS)
    finally:
        escurses.endGame()


if __name__ == "__main__":
    main()
