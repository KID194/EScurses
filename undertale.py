import random
import math
import time
import escurses as es

FPS = 30

ENEMIES = [
    {
        'name': 'Froggit',
        'max_hp': 45, 'hp': 45, 'atk': 6, 'defense': 1,
        'char': 'F', 'color': es.COLOR_GREEN,
        'check': 'FROGGIT - ATK 6 DEF 1\n一只暴躁的青蛙。',
        'acts': [
            ('Compliment', 'Froggit 哼了一声，但没那么生气了。'),
            ('Threaten', 'Froggit 瞪着你，似乎更愤怒了。'),
        ],
        'spare_msg': 'Froggit 不情愿地跳走了。',
        'patterns': ['rain', 'sweep', 'wall', 'cross', 'laser', 'ring'],
    },
    {
        'name': 'Whimsun',
        'max_hp': 35, 'hp': 35, 'atk': 5, 'defense': 0,
        'char': 'W', 'color': es.COLOR_MAGENTA,
        'check': 'WHIMSUN - ATK 5 DEF 0\n一只焦躁的飞蛾。',
        'acts': [
            ('Console', 'Whimsun 稍微冷静了一点。'),
            ('Beckon', 'Whimsun 警惕地靠近。'),
        ],
        'spare_msg': 'Whimsun 慌乱地飞走了。',
        'patterns': ['spiral', 'rain', 'homing', 'burst', 'vortex', 'laser'],
    },
    {
        'name': 'Moldsmal',
        'max_hp': 70, 'hp': 70, 'atk': 7, 'defense': 2,
        'char': 'M', 'color': es.COLOR_BRIGHT_GREEN,
        'check': 'MOLDSMAL - ATK 7 DEF 2\n一坨坚硬的果冻。',
        'acts': [
            ('Flirt', 'Moldsmal 微微颤动。'),
            ('Imitate', 'Moldsmal 似乎有点兴趣。'),
        ],
        'spare_msg': 'Moldsmal 缓缓融化了。',
        'patterns': ['sweep', 'spiral', 'cross', 'wall', 'burst', 'ring', 'vortex'],
    },
]

BULLET_AREA_X = 2
BULLET_AREA_Y = 9
BULLET_AREA_W = 56
BULLET_AREA_H = 10

PLAYER_MAX_HP = 15
PLAYER_SPEED = 0.9

PATTERN_DURATION = 1.5
ENEMY_TURN_DURATION = 12.0
KEY_HOLD_TIME = 0.18

ITEMS = [
    {'name': 'Monster Candy', 'heal': 8, 'count': 2},
    {'name': 'Spider Donut', 'heal': 10, 'count': 1},
]

class Bullet:
    def __init__(self, x, y, vx, vy, char='*', color=es.COLOR_BRIGHT_WHITE, accel=0.0, turn=0.0):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.char = char
        self.color = color
        self.alive = True
        self.accel = accel
        self.turn = turn
        self.age = 0

    def update(self, dt):
        self.age += dt
        if self.accel:
            spd = math.hypot(self.vx, self.vy)
            if spd > 0.01:
                factor = (spd + self.accel * dt) / spd
                self.vx *= factor
                self.vy *= factor
        if self.turn:
            ang = math.atan2(self.vy, self.vx) + self.turn * dt
            spd = math.hypot(self.vx, self.vy)
            self.vx = math.cos(ang) * spd
            self.vy = math.sin(ang) * spd
        self.x += self.vx * dt
        self.y += self.vy * dt
        if (self.x < -3 or self.x > BULLET_AREA_W + 3 or
                self.y < -3 or self.y > BULLET_AREA_H + 3):
            self.alive = False

class Player:
    def __init__(self):
        self.hp = PLAYER_MAX_HP
        self.max_hp = PLAYER_MAX_HP
        self.x = BULLET_AREA_W // 2
        self.y = BULLET_AREA_H // 2
        self.invuln = 0
        self.hold_until = {'left': 0, 'right': 0, 'up': 0, 'down': 0}

    def press(self, direction):
        self.hold_until[direction] = time.perf_counter() + KEY_HOLD_TIME

    def active_keys(self):
        now = time.perf_counter()
        return {k for k, t in self.hold_until.items() if now < t}

    def update(self, dt):
        keys = self.active_keys()
        dx = dy = 0
        if 'left' in keys: dx -= 1
        if 'right' in keys: dx += 1
        if 'up' in keys: dy -= 1
        if 'down' in keys: dy += 1
        if dx and dy:
            dx *= 0.707
            dy *= 0.707
        self.x += dx * PLAYER_SPEED * dt * 10
        self.y += dy * PLAYER_SPEED * dt * 10
        self.x = max(0, min(BULLET_AREA_W - 1, self.x))
        self.y = max(0, min(BULLET_AREA_H - 1, self.y))
        if self.invuln > 0:
            self.invuln -= dt

class Game:
    def __init__(self):
        self.enemy = self.spawn_enemy()
        self.player = Player()
        self.items = [dict(it) for it in ITEMS]   # 每局独立物品数量,重开自动重置
        self.state = 'menu'
        self.menu_index = 0
        self.submenu = None
        self.submenu_index = 0
        self.dialog = []
        self.dialog_timer = 0
        self.mercy = 0
        self.turn_count = 0
        self.bullets = []
        self.spawn_timer = 0
        self.pattern_change_timer = 0
        self.enemy_turn_timer = 0
        self.pattern_order = []
        self.pattern_index = 0
        self.won = False
        self.lost = False
        self.attack_anim = 0
        self.shake = 0
        self.difficulty = 0

    def spawn_enemy(self):
        e = random.choice(ENEMIES).copy()
        e['acts'] = list(e['acts'])
        return e

    def add_dialog(self, text):
        self.dialog = text.split('\n')
        self.dialog_timer = 3.0

    def start_enemy_turn(self):
        self.state = 'enemy'
        self.bullets = []
        self.spawn_timer = 0
        self.pattern_change_timer = 0
        self.enemy_turn_timer = 0
        self.player.invuln = 0.3
        self.turn_count += 1
        self.difficulty = min(1.0, self.turn_count * 0.12)
        self.pattern_order = list(self.enemy['patterns'])
        random.shuffle(self.pattern_order)
        self.pattern_index = 0
        self.add_dialog('敌人正在攻击...WASD 闪避！')

    def end_enemy_turn(self):
        self.state = 'menu'
        self.bullets = []
        self.mercy = min(100, self.mercy + 3)
        self.add_dialog('你的回合。A/D 选择，回车确认。')

    def current_pattern(self):
        if not self.pattern_order:
            return 'rain'
        return self.pattern_order[self.pattern_index % len(self.pattern_order)]

    def menu_action(self, action):
        if action == 'FIGHT':
            self.do_fight()
        elif action == 'ACT':
            self.submenu = 'act'
            self.submenu_index = 0
        elif action == 'ITEM':
            self.submenu = 'item'
            self.submenu_index = 0
        elif action == 'MERCY':
            self.submenu = 'mercy'
            self.submenu_index = 0

    def do_fight(self):
        self.attack_anim = 1.0
        self.shake = 0.3
        dmg = random.randint(3, 7) + self.player.hp // 6
        self.enemy['hp'] -= dmg
        self.add_dialog(f'你造成了 {dmg} 点伤害！')
        if self.enemy['hp'] <= 0:
            self.enemy['hp'] = 0
            self.add_dialog(f'{self.enemy["name"]} 被击败了！')
            self.won = True
        else:
            self.start_enemy_turn()

    def do_act(self, idx):
        if idx >= len(self.enemy['acts']):
            return
        name, result = self.enemy['acts'][idx]
        self.add_dialog(result)
        self.mercy = min(100, self.mercy + 20)
        if name in ('Compliment', 'Flirt', 'Console'):
            self.mercy = min(100, self.mercy + 10)
        self.submenu = None
        self.start_enemy_turn()

    def do_item(self, idx):
        if idx >= len(self.items):
            return
        item = self.items[idx]
        if item['count'] <= 0:
            self.add_dialog('没有这个物品了。')
            return
        item['count'] -= 1
        heal = min(item['heal'], self.player.max_hp - self.player.hp)
        self.player.hp += heal
        self.add_dialog(f'使用了 {item["name"]}，恢复了 {heal} HP。')
        self.submenu = None
        self.start_enemy_turn()

    def do_mercy(self):
        if self.mercy >= 100:
            self.add_dialog(self.enemy['spare_msg'])
            self.won = True
        else:
            self.add_dialog('你不能宽恕它。\nMercy 不足。')
            self.submenu = None
            self.start_enemy_turn()

    def spawn_bullets(self, dt):
        pattern = self.current_pattern()
        self.spawn_timer += dt
        speed_mult = 1.0 + self.difficulty * 0.5
        interval_mult = 1.0 - self.difficulty * 0.3

        if pattern == 'rain':
            if self.spawn_timer > 0.22 * interval_mult:
                self.spawn_timer = 0
                for _ in range(2 if self.difficulty > 0.5 else 1):
                    x = random.randint(0, BULLET_AREA_W - 1)
                    self.bullets.append(Bullet(x, -1, 0, 10 * speed_mult, 'v', es.COLOR_BRIGHT_CYAN))

        elif pattern == 'sweep':
            if self.spawn_timer > 0.32 * interval_mult:
                self.spawn_timer = 0
                y = random.randint(0, BULLET_AREA_H - 1)
                side = random.choice([-1, 1])
                sx = -1 if side == -1 else BULLET_AREA_W
                vx = 9 * speed_mult * side
                self.bullets.append(Bullet(sx, y, vx, 0, 'o', es.COLOR_BRIGHT_RED))

        elif pattern == 'spiral':
            if self.spawn_timer > 0.09 * interval_mult:
                self.spawn_timer = 0
                cx, cy = BULLET_AREA_W / 2, BULLET_AREA_H / 2
                ang = self.enemy_turn_timer * 4.0
                spd = 6 * speed_mult
                self.bullets.append(Bullet(cx, cy, math.cos(ang) * spd, math.sin(ang) * spd,
                                           'o', es.COLOR_BRIGHT_MAGENTA, turn=0.3))

        elif pattern == 'wall':
            if self.spawn_timer > 0.95 * interval_mult:
                self.spawn_timer = 0
                if random.random() < 0.5:
                    gap = random.randint(1, BULLET_AREA_W - 2)
                    for x in range(BULLET_AREA_W):
                        if x != gap:
                            self.bullets.append(Bullet(x, -1, 0, 7 * speed_mult, '#', es.COLOR_BRIGHT_YELLOW))
                else:
                    gap = random.randint(1, BULLET_AREA_H - 2)
                    for y in range(BULLET_AREA_H):
                        if y != gap:
                            self.bullets.append(Bullet(-1, y, 7 * speed_mult, 0, '#', es.COLOR_BRIGHT_YELLOW))

        elif pattern == 'homing':
            if self.spawn_timer > 0.45 * interval_mult:
                self.spawn_timer = 0
                edge = random.randint(0, 3)
                if edge == 0:
                    x, y = random.randint(0, BULLET_AREA_W - 1), -1
                elif edge == 1:
                    x, y = random.randint(0, BULLET_AREA_W - 1), BULLET_AREA_H
                elif edge == 2:
                    x, y = -1, random.randint(0, BULLET_AREA_H - 1)
                else:
                    x, y = BULLET_AREA_W, random.randint(0, BULLET_AREA_H - 1)
                dx = self.player.x - x
                dy = self.player.y - y
                dist = max(0.1, math.hypot(dx, dy))
                spd = 4 * speed_mult
                self.bullets.append(Bullet(x, y, dx / dist * spd, dy / dist * spd,
                                           'x', es.COLOR_BRIGHT_RED, accel=2.0))

        elif pattern == 'burst':
            if self.spawn_timer > 0.7 * interval_mult:
                self.spawn_timer = 0
                cx = random.randint(6, BULLET_AREA_W - 7)
                cy = random.randint(2, BULLET_AREA_H - 3)
                n = 10
                for k in range(n):
                    ang = 2 * math.pi * k / n + self.enemy_turn_timer
                    spd = 5 * speed_mult
                    self.bullets.append(Bullet(cx, cy, math.cos(ang) * spd, math.sin(ang) * spd,
                                               '*', es.COLOR_BRIGHT_MAGENTA))

        elif pattern == 'cross':
            if self.spawn_timer > 0.5 * interval_mult:
                self.spawn_timer = 0
                cx, cy = BULLET_AREA_W / 2, BULLET_AREA_H / 2
                for ang in (0, math.pi / 2, math.pi, 3 * math.pi / 2,
                            math.pi / 4, 3 * math.pi / 4, 5 * math.pi / 4, 7 * math.pi / 4):
                    spd = 6.5 * speed_mult
                    self.bullets.append(Bullet(cx, cy, math.cos(ang) * spd, math.sin(ang) * spd,
                                               '+', es.COLOR_BRIGHT_CYAN))

        elif pattern == 'laser':
            if self.spawn_timer > 1.0 * interval_mult:
                self.spawn_timer = 0
                if random.random() < 0.5:
                    y = random.randint(0, BULLET_AREA_H - 1)
                    for x in range(0, BULLET_AREA_W, 2):
                        self.bullets.append(Bullet(x, y, 0, 0, '=', es.COLOR_BRIGHT_RED))
                else:
                    x = random.randint(0, BULLET_AREA_W - 1)
                    for y in range(0, BULLET_AREA_H, 2):
                        self.bullets.append(Bullet(x, y, 0, 0, '|', es.COLOR_BRIGHT_RED))

        elif pattern == 'ring':
            if self.spawn_timer > 0.6 * interval_mult:
                self.spawn_timer = 0
                cx, cy = BULLET_AREA_W / 2, BULLET_AREA_H / 2
                n = 16
                for k in range(n):
                    ang = 2 * math.pi * k / n
                    spd = 4.5 * speed_mult
                    self.bullets.append(Bullet(cx, cy, math.cos(ang) * spd, math.sin(ang) * spd,
                                               'o', es.COLOR_BRIGHT_YELLOW))

        elif pattern == 'vortex':
            if self.spawn_timer > 0.1 * interval_mult:
                self.spawn_timer = 0
                cx, cy = BULLET_AREA_W / 2, BULLET_AREA_H / 2
                ang = self.enemy_turn_timer * 3.0
                radius = 8
                bx = cx + math.cos(ang) * radius
                by = cy + math.sin(ang) * radius * 0.6
                dx = cx - bx
                dy = cy - by
                dist = max(0.1, math.hypot(dx, dy))
                spd = 3 * speed_mult
                self.bullets.append(Bullet(bx, by, dx / dist * spd, dy / dist * spd,
                                           '@', es.COLOR_BRIGHT_MAGENTA))

        elif pattern == 'rain_hard':
            if self.spawn_timer > 0.12 * interval_mult:
                self.spawn_timer = 0
                for _ in range(3):
                    x = random.randint(0, BULLET_AREA_W - 1)
                    self.bullets.append(Bullet(x, -1, random.uniform(-1, 1), 11 * speed_mult,
                                               'v', es.COLOR_BRIGHT_CYAN))

    def update(self, dt):
        if self.dialog_timer > 0:
            self.dialog_timer -= dt
        if self.attack_anim > 0:
            self.attack_anim -= dt
        if self.shake > 0:
            self.shake -= dt

        if self.state == 'enemy':
            self.enemy_turn_timer += dt
            self.pattern_change_timer += dt
            if self.pattern_change_timer > PATTERN_DURATION:
                self.pattern_change_timer = 0
                self.pattern_index += 1

            self.player.update(dt)
            self.spawn_bullets(dt)

            if self.difficulty > 0.6 and self.pattern_index >= 2:
                if random.random() < 0.15 * dt * 10:
                    pattern = self.current_pattern()
                    if pattern in ('rain', 'sweep'):
                        x = random.randint(0, BULLET_AREA_W - 1)
                        self.bullets.append(Bullet(x, -1, 0, 8, 'v', es.COLOR_BRIGHT_MAGENTA))

            for b in self.bullets:
                b.update(dt)
            self.bullets = [b for b in self.bullets if b.alive]

            if self.player.invuln <= 0:
                for b in self.bullets:
                    if (abs(b.x - self.player.x) < 1.2 and
                            abs(b.y - self.player.y) < 1.2):
                        dmg = random.randint(4, 6) + self.turn_count // 2
                        self.player.hp -= dmg
                        self.player.invuln = 0.9
                        self.shake = 0.2
                        self.add_dialog(f'受到 {dmg} 点伤害！')
                        if self.player.hp <= 0:
                            self.player.hp = 0
                            self.lost = True
                        break

            if self.enemy_turn_timer > ENEMY_TURN_DURATION:
                self.end_enemy_turn()

    def handle_key(self, ch):
        if self.won or self.lost:
            return

        if self.state == 'menu':
            if self.submenu is None:
                if ch in ('a', 'A'):
                    self.menu_index = (self.menu_index - 1) % 4
                elif ch in ('d', 'D'):
                    self.menu_index = (self.menu_index + 1) % 4
                elif ch in ('\r', '\n', ' '):
                    actions = ['FIGHT', 'ACT', 'ITEM', 'MERCY']
                    self.menu_action(actions[self.menu_index])
            else:
                self.handle_submenu_key(ch)

    def handle_submenu_key(self, ch):
        if self.submenu == 'act':
            opts = len(self.enemy['acts']) + 1
            if ch in ('w', 'W'):
                self.submenu_index = (self.submenu_index - 1) % opts
            elif ch in ('s', 'S'):
                self.submenu_index = (self.submenu_index + 1) % opts
            elif ch in ('\r', '\n', ' '):
                if self.submenu_index == 0:
                    self.add_dialog(self.enemy['check'])
                    self.submenu = None
                else:
                    self.do_act(self.submenu_index - 1)
            elif ch in ('a', 'A', 'x', 'X'):
                self.submenu = None
        elif self.submenu == 'item':
            if ch in ('w', 'W'):
                self.submenu_index = (self.submenu_index - 1) % len(self.items)
            elif ch in ('s', 'S'):
                self.submenu_index = (self.submenu_index + 1) % len(self.items)
            elif ch in ('\r', '\n', ' '):
                self.do_item(self.submenu_index)
            elif ch in ('a', 'A', 'x', 'X'):
                self.submenu = None
        elif self.submenu == 'mercy':
            if ch in ('w', 'W'):
                self.submenu_index = (self.submenu_index - 1) % 2
            elif ch in ('s', 'S'):
                self.submenu_index = (self.submenu_index + 1) % 2
            elif ch in ('\r', '\n', ' '):
                if self.submenu_index == 0:
                    self.do_mercy()
                else:
                    self.submenu = None
            elif ch in ('a', 'A', 'x', 'X'):
                self.submenu = None

def draw_box(x, y, w, h, color=es.COLOR_WHITE):
    for i in range(w):
        es.drawChar(x + i, y, '-', color)
        es.drawChar(x + i, y + h - 1, '-', color)
    for j in range(h):
        es.drawChar(x, y + j, '|', color)
        es.drawChar(x + w - 1, y + j, '|', color)
    es.drawChar(x, y, '+', color)
    es.drawChar(x + w - 1, y, '+', color)
    es.drawChar(x, y + h - 1, '+', color)
    es.drawChar(x + w - 1, y + h - 1, '+', color)

def render(game):
    es.clear()
    W = es._screenWidth

    ox = 0
    oy = 0
    if game.shake > 0:
        ox = random.choice([-1, 0, 1])
        oy = random.choice([-1, 0, 1])

    top_y = 1 + oy
    enemy_w = 40
    enemy_h = 5
    enemy_x = W // 2 - enemy_w // 2 + ox
    draw_box(enemy_x, top_y, enemy_w, enemy_h, es.COLOR_BRIGHT_WHITE)
    es.drawText(enemy_x + 2, top_y + 1, game.enemy['name'], game.enemy['color'])
    es.drawText(enemy_x + 2, top_y + 2, f'HP: {game.enemy["hp"]}/{game.enemy["max_hp"]}', es.COLOR_WHITE)

    bar_len = 20
    hp_ratio = game.enemy['hp'] / game.enemy['max_hp']
    filled = int(bar_len * hp_ratio)
    for i in range(bar_len):
        color = es.COLOR_BRIGHT_GREEN if i < filled else es.COLOR_RED
        es.drawChar(enemy_x + 2 + i, top_y + 3, '#', color)

    mercy_len = 20
    mercy_filled = int(mercy_len * game.mercy / 100)
    es.drawText(enemy_x + 24, top_y + 3, 'Mercy:', es.COLOR_YELLOW)
    for i in range(mercy_len):
        color = es.COLOR_BRIGHT_YELLOW if i < mercy_filled else es.COLOR_WHITE
        es.drawChar(enemy_x + 31 + i, top_y + 3, '|', color)

    ex = enemy_x + enemy_w - 6
    ey = top_y + 2
    es.drawChar(ex, ey, game.enemy['char'][0], game.enemy['color'])

    player_hp_y = top_y + enemy_h + 1
    es.drawText(2, player_hp_y, 'HP', es.COLOR_WHITE)
    ph = game.player.hp / game.player.max_hp
    for i in range(20):
        color = es.COLOR_BRIGHT_YELLOW if i < int(20 * ph) else es.COLOR_RED
        es.drawChar(5 + i, player_hp_y, '#', color)
    es.drawText(26, player_hp_y, f'{game.player.hp}/{game.player.max_hp}', es.COLOR_WHITE)

    if game.won:
        show_bottom_box('VICTORY', '你赢了！按 R 重开 / Q 退出', es.COLOR_BRIGHT_GREEN)
    elif game.lost:
        show_bottom_box('GAME OVER', '你倒下了...按 R 重开 / Q 退出', es.COLOR_RED)
    else:
        if game.state == 'enemy':
            draw_bullet_phase(game, ox, oy)
        else:
            draw_menu_phase(game, ox, oy)

    es.refresh()

def draw_bullet_phase(game, ox, oy):
    bx = (es._screenWidth - BULLET_AREA_W) // 2 - 2 + ox
    by = BULLET_AREA_Y + oy
    draw_box(bx, by, BULLET_AREA_W + 4, BULLET_AREA_H + 2, es.COLOR_BRIGHT_WHITE)

    pattern = game.current_pattern()
    es.drawText(bx + 2, by + BULLET_AREA_H + 3,
                f'模式: {pattern}  回合: {game.turn_count}  难度: {"*" * int(game.difficulty * 10)}',
                es.COLOR_BRIGHT_CYAN)

    for b in game.bullets:
        sx = int(bx + 2 + b.x)
        sy = int(by + 1 + b.y)
        if bx + 2 <= sx < bx + 2 + BULLET_AREA_W and by + 1 <= sy < by + 1 + BULLET_AREA_H:
            es.drawChar(sx, sy, b.char, b.color)

    px = int(bx + 2 + game.player.x)
    py = int(by + 1 + game.player.y)
    if game.player.invuln > 0 and int(game.player.invuln * 10) % 2 == 0:
        es.drawChar(px, py, ' ', es.COLOR_WHITE)
    else:
        es.drawChar(px, py, 'H', es.COLOR_BRIGHT_RED)

    if game.dialog_timer > 0:
        dy = by + BULLET_AREA_H + 4
        for i, line in enumerate(game.dialog):
            es.drawText(bx + 2, dy + i, line, es.COLOR_WHITE)

def draw_menu_phase(game, ox, oy):
    W = es._screenWidth
    menu_y = 11 + oy
    menu_w = 64
    menu_x = (W - menu_w) // 2 + ox
    draw_box(menu_x, menu_y, menu_w, 5, es.COLOR_BRIGHT_WHITE)

    actions = ['FIGHT', 'ACT', 'ITEM', 'MERCY']
    colors = [es.COLOR_BRIGHT_RED, es.COLOR_BRIGHT_YELLOW, es.COLOR_BRIGHT_GREEN, es.COLOR_BRIGHT_CYAN]
    for i, (a, c) in enumerate(zip(actions, colors)):
        x = menu_x + 2 + i * 15
        prefix = '>' if i == game.menu_index and game.submenu is None else ' '
        es.drawText(x, menu_y + 1, f'{prefix}{a}', c if i == game.menu_index else es.COLOR_WHITE)

    es.drawText(menu_x + 2, menu_y + 3, '* A/D 选择，回车确认', es.COLOR_WHITE)

    if game.submenu == 'act':
        draw_submenu(game, 'ACT 行动', [('Check', '检查敌人')] + list(game.enemy['acts']), menu_y + 5, ox)
    elif game.submenu == 'item':
        items = [(f'{it["name"]} x{it["count"]}', f'恢复{it["heal"]}HP') for it in game.items]
        draw_submenu(game, 'ITEM 物品', items, menu_y + 5, ox)
    elif game.submenu == 'mercy':
        draw_submenu(game, 'MERCY 宽恕', [('Spare', '宽恕敌人'), ('Flee', '逃跑')], menu_y + 5, ox)

    if game.dialog_timer > 0:
        dy = menu_y + 10
        for i, line in enumerate(game.dialog):
            es.drawText(menu_x + 2, dy + i, line, es.COLOR_WHITE)

def draw_submenu(game, title, options, sy, ox):
    W = es._screenWidth
    sw = 40
    sh = len(options) + 3
    sx = (W - sw) // 2 + ox
    draw_box(sx, sy, sw, sh, es.COLOR_BRIGHT_CYAN)
    es.drawText(sx + 2, sy + 1, title, es.COLOR_BRIGHT_CYAN)
    for i, (name, desc) in enumerate(options):
        color = es.COLOR_BRIGHT_YELLOW if i == game.submenu_index else es.COLOR_WHITE
        prefix = '>' if i == game.submenu_index else ' '
        es.drawText(sx + 2, sy + 2 + i, f'{prefix}{name}', color)

def show_bottom_box(title, msg, color):
    W = es._screenWidth
    H = es._screenHeight
    bw = 50
    bh = 5
    bx = (W - bw) // 2
    by = H - bh
    draw_box(bx, by, bw, bh, color)
    es.drawText(bx + 2, by + 2, title, color)
    es.drawText(bx + 2, by + 3, msg, es.COLOR_WHITE)

def main():
    try:
        es.initGame()
    except OSError:
        print('无法获取终端大小，请在真实终端运行')
        return

    if es._screenWidth < 64 or es._screenHeight < 24:
        print(f'终端太小：需要至少 64x24，当前 {es._screenWidth}x{es._screenHeight}')
        return

    es.cursorEcho(False)
    es.clear()

    game = Game()
    game.add_dialog('一只凶猛的怪物出现了！WASD 闪避。')

    try:
        while True:
            es.frameStart()
            dt = 1.0 / FPS

            while True:
                ch = es.getch(nodelay=True)
                if ch is None:
                    break

                if ch in ('q', 'Q', '\x03'):
                    if game.won or game.lost:
                        return
                if ch == 'r' and (game.won or game.lost):
                    game = Game()
                    game.add_dialog('一只凶猛的怪物出现了！WASD 闪避。')
                    continue

                if game.state == 'enemy' and not (game.won or game.lost):
                    if ch in ('a', 'A'): game.player.press('left')
                    elif ch in ('d', 'D'): game.player.press('right')
                    elif ch in ('w', 'W'): game.player.press('up')
                    elif ch in ('s', 'S'): game.player.press('down')
                else:
                    game.handle_key(ch)

            game.update(dt)
            render(game)

            if game.won or game.lost:
                for _ in range(5):
                    ch = es.getch(nodelay=False)
                    if ch in ('q', 'Q', '\x03'):
                        return
                    if ch in ('r', 'R'):
                        game = Game()
                        game.add_dialog('一只凶猛的怪物出现了！WASD 闪避。')
                        break

            es.sleepForFrame(FPS)

    finally:
        es.exitGame()

if __name__ == '__main__':
    main()
