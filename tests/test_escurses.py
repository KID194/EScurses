"""EScurses 的自动化测试（不需要安装任何第三方库）。

运行方式（在仓库根目录）：python -m unittest discover -s tests -v
"""
import io
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import escurses


class FakeStdout(io.StringIO):
    """把终端输出收集到内存里，测试时不会真的往屏幕上乱画。"""


class EscursesTest(unittest.TestCase):
    def setUp(self):
        self.realStdout = sys.stdout
        sys.stdout = FakeStdout()
        # 测试环境不是真正的终端，把尺寸固定成 80x24，结果才稳定。
        self.realGetTerminalSize = escurses.getTerminalSize
        escurses.getTerminalSize = lambda: (80, 24)

    def tearDown(self):
        escurses.endGame()
        escurses.getTerminalSize = self.realGetTerminalSize
        sys.stdout = self.realStdout

    def outputSoFar(self):
        """取出到目前为止，假终端收到的那段输出。"""
        return sys.stdout.getvalue()

    # ---------------------------------------------------------- 初始化
    def testInitGameCreatesCorrectBuffer(self):
        escurses.initGame()
        self.assertEqual(len(escurses._screen), 24)
        self.assertEqual(len(escurses._screen[0]), 80)
        self.assertEqual(len(escurses._screen[0][0]), 4)

    def testInitGameEntersAltScreen(self):
        escurses.initGame()
        self.assertIn("\033[?1049h", self.outputSoFar())

    def testEndGameRestoresTerminal(self):
        escurses.initGame()
        escurses.endGame()
        self.assertIn("\033[?25h", self.outputSoFar())
        self.assertIn("\033[?1049l", self.outputSoFar())

    def testDrawingBeforeInitRaisesFriendlyError(self):
        with self.assertRaises(RuntimeError):
            escurses.drawChar(1, 1, "A")

    # ---------------------------------------------------------- 绘制
    def testClearKeepsFullWidth(self):
        escurses.initGame()
        escurses.clear()
        self.assertEqual(len(escurses._screen[0]), 80)
        escurses.drawChar(80, 24, "X")
        self.assertEqual(escurses._screen[23][79][0], "X")

    def testDrawCharWritesCell(self):
        escurses.initGame()
        escurses.clear()
        self.assertTrue(escurses.drawChar(3, 2, "@", escurses.COLORRED))
        cell = escurses._screen[1][2]
        self.assertEqual(cell[0], "@")
        self.assertEqual(cell[1], 2)
        self.assertEqual(cell[2], 3)
        self.assertEqual(cell[3], escurses.COLORRED)

    def testDrawCharOutOfBoundsIsIgnored(self):
        escurses.initGame()
        escurses.clear()
        self.assertFalse(escurses.drawChar(0, 1, "X"))
        self.assertFalse(escurses.drawChar(1, 0, "X"))
        self.assertFalse(escurses.drawChar(81, 1, "X"))
        self.assertFalse(escurses.drawChar(1, 25, "X"))

    def testDrawWideCharUsesTwoCells(self):
        escurses.initGame()
        escurses.clear()
        self.assertTrue(escurses.drawChar(1, 1, "你"))
        self.assertEqual(escurses._screen[0][0][0], "你")
        self.assertEqual(escurses._screen[0][1][0], "")
        self.assertFalse(escurses.drawChar(80, 1, "你"))

    def testDrawTextDrawsEveryChar(self):
        escurses.initGame()
        escurses.clear()
        width = escurses.drawText(1, 3, "Hi!")
        self.assertEqual(width, 3)
        self.assertEqual(escurses._screen[2][0][0], "H")
        self.assertEqual(escurses._screen[2][2][0], "!")

    # ---------------------------------------------------------- 刷新
    def testRefreshDoesNotCrashOnFreshInit(self):
        escurses.initGame()
        escurses.refresh()

    def testRefreshDrawsAllRows(self):
        escurses.initGame()
        escurses.clear()
        escurses.drawChar(80, 24, "X")
        escurses.refresh()
        output = self.outputSoFar()
        # 每一行都应该被定位过（行首的空白会被跳过，所以列号不一定是 1）。
        for row in range(1, 25):
            self.assertIn("\033[%d;" % row, output)
        self.assertIn("X", output)

    def testRefreshOutputIsNotTooLarge(self):
        escurses.initGame()
        escurses.clear()
        escurses.refresh()
        # 按行输出后，80x24 的屏幕一帧应该远小于逐格输出的 3 万字节。
        self.assertLess(len(self.outputSoFar()), 5000)

    # ---------------------------------------------------------- 输入/尺寸
    def testGetTerminalSizeReturnsPositiveNumbers(self):
        escurses.getTerminalSize = self.realGetTerminalSize
        size = escurses.getTerminalSize()
        self.assertEqual(len(size), 2)
        self.assertGreater(size[0], 0)
        self.assertGreater(size[1], 0)

    def testGetchNonBlockingReturnsNoneWithoutKey(self):
        self.assertIsNone(escurses.getch(True))

    # ---------------------------------------------------------- 帧率
    def testSleepForFrameKeepsRequestedRate(self):
        escurses.frameStart()
        start = time.perf_counter()
        frames = 10
        for _ in range(frames):
            escurses.frameStart()
            escurses.sleepForFrame(60)
        average = (time.perf_counter() - start) / frames
        self.assertAlmostEqual(average, 1 / 60, delta=0.004)

    def testSleepForFrameRejectsBadFps(self):
        with self.assertRaises(ValueError):
            escurses.sleepForFrame(0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
