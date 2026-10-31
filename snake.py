import random
import escurses as es

FPS = 12
W, H = 40, 20
OFFSET_X, OFFSET_Y = 2, 3

DIRS = {
    'w': (0, -1), 's': (0, 1), 'a': (-1, 0), 'd': (1, 0),
    'W': (0, -1), 'S': (0, 1), 'A': (-1, 0), 'D': (1, 0),
    es.KEY_UP:    (0, -1),
    es.KEY_DOWN:  (0, 1),
    es.KEY_LEFT:  (-1, 0),
    es.KEY_RIGHT: (1, 0),
}

def safe_draw(x, y, ch):
    sx, sy = OFFSET_X + x, OFFSET_Y + y
    if 1 <= sx <= es._screenWidth - 1 and 1 <= sy <= es._screenHeight:
        es.drawChar(sx, sy, ch)

def draw_text(x, y, text):
    for i, ch in enumerate(text):
        safe_draw(x + i, y, ch)

class Snake:
    def __init__(self):
        cx, cy = W // 2, H // 2
        self.body = [(cx, cy), (cx - 1, cy), (cx - 2, cy)]
        self.dir = (1, 0)
        self.pending_dir = self.dir
        self.grow = 0

    def set_dir(self, d):
        if d[0] == -self.dir[0] and d[1] == -self.dir[1]:
            return
        if d == self.pending_dir:
            return
        self.pending_dir = d

    def step(self):
        self.dir = self.pending_dir
        hx, hy = self.body[0]
        nx, ny = hx + self.dir[0], hy + self.dir[1]

        if not (0 <= nx < W and 0 <= ny < H):
            return False
        body_to_check = self.body if self.grow > 0 else self.body[:-1]
        if (nx, ny) in body_to_check:
            return False

        self.body.insert(0, (nx, ny))
        if self.grow > 0:
            self.grow -= 1
        else:
            self.body.pop()
        return True

class Food:
    def __init__(self, snake):
        self.pos = self._spawn(snake)

    def _spawn(self, snake):
        occupied = set(snake.body)
        free = [(x, y) for x in range(W) for y in range(H) if (x, y) not in occupied]
        return random.choice(free) if free else None

    def respawn(self, snake):
        self.pos = self._spawn(snake)

def draw_border():
    for x in range(-1, W + 1):
        safe_draw(x, -1, '─')
        safe_draw(x, H, '─')
    for y in range(-1, H + 1):
        safe_draw(-1, y, '│')
        safe_draw(W, y, '│')
    safe_draw(-1, -1, '┌'); safe_draw(W, -1, '┐')
    safe_draw(-1, H, '└');  safe_draw(W, H, '┘')

def render(snake, food, score, best, paused):
    es.clear()

    draw_text(0, -2,
              f' SNAKE   Score: {score}   Best: {best}   [WASD/arrow] move  [P] pause  [Q] quit')

    draw_border()

    if food.pos:
        safe_draw(food.pos[0], food.pos[1], '●')

    for i, (x, y) in enumerate(snake.body):
        safe_draw(x, y, '@' if i == 0 else 'o')

    if paused:
        draw_text(W // 2 - 3, H // 2, ' PAUSED ')

    es.refresh()

def main():
    try:
        es.initGame()
    except OSError:
        print('Cannot get terminal size, run in a real terminal.')
        return

    if es._screenWidth < W + 4 or es._screenHeight < H + 6:
        print(f'Terminal too small: need at least {W+4}x{H+6}, got {es._screenWidth}x{es._screenHeight}')
        return

    es.cursorEcho(False)
    es.clear()

    snake = Snake()
    food = Food(snake)
    score = 0
    best = 0
    paused = False

    try:
        while True:
            es.frameStart()

            for _ in range(8):
                ch = es.getch(nodelay=True)
                if ch is None:
                    break
                if ch in ('q', 'Q', '\x03'):
                    return
                if ch in ('p', 'P'):
                    paused = not paused
                    continue
                if paused:
                    continue
                d = DIRS.get(ch)
                if d:
                    snake.set_dir(d)

            if not paused:
                if not snake.step():
                    best = max(best, score)
                    render(snake, food, score, best, False)
                    draw_text(W // 2 - 6, H // 2, ' GAME OVER ')
                    draw_text(W // 2 - 9, H // 2 + 1, ' Press R to restart / Q to quit ')
                    es.refresh()
                    while True:
                        ch = es.getch(nodelay=False)
                        if ch in ('q', 'Q', '\x03'):
                            return
                        if ch in ('r', 'R'):
                            snake = Snake()
                            food = Food(snake)
                            score = 0
                            paused = False
                            break

                if food.pos and snake.body[0] == food.pos:
                    score += 1
                    snake.grow += 1
                    food.respawn(snake)

            render(snake, food, score, best, paused)
            es.sleepForFrame(FPS)

    finally:
        es.exitGame()

if __name__ == '__main__':
    main()