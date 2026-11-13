#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RATO E GATOS  -  réplica do Pac-Man clássico
    Pac-Man  -> Rato
    Fantasmas -> Gatos (mesma IA do original: perseguidor, emboscador, esperto, distraído)
    Frutas   -> Queijos

Requisitos:  pip install pygame
Controles :  SETAS / WASD mover | P pausar | M som | R reiniciar | ESC menu/sair
"""
import math
import os
import random
import sys
from array import array

import pygame

try:
    pygame.mixer.pre_init(22050, -16, 1, 512)
except Exception:
    pass
pygame.init()

# ----------------------------------------------------------------------------
# Constantes
# ----------------------------------------------------------------------------
TILE = 18
COLS, ROWS = 28, 31
TOP, BOT = 54, 46
W = COLS * TILE
H = ROWS * TILE + TOP + BOT
FPS = 60
U = TILE * 9.5 / 60.0            # px/frame a 100% de velocidade (como no original)
HALF = TILE // 2

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BLUE = (50, 70, 255)
YELLOW = (255, 255, 0)
DOT = (255, 200, 170)
PINK_DOOR = (255, 184, 222)
RED = (255, 40, 40)
PINK = (255, 150, 200)
CYAN = (70, 230, 255)
ORANGE = (255, 165, 50)

UP, LEFT, DOWN, RIGHT = (0, -1), (-1, 0), (0, 1), (1, 0)
DIR_ORDER = [UP, LEFT, DOWN, RIGHT]          # ordem de desempate do original
DIR_INDEX = {UP: 0, LEFT: 1, DOWN: 2, RIGHT: 3}

MAZE = [
    "############################",
    "#............##............#",
    "#.####.#####.##.#####.####.#",
    "#o####.#####.##.#####.####o#",
    "#.####.#####.##.#####.####.#",
    "#..........................#",
    "#.####.##.########.##.####.#",
    "#.####.##.########.##.####.#",
    "#......##....##....##......#",
    "######.##### ## #####.######",
    "     #.##### ## #####.#     ",
    "     #.##          ##.#     ",
    "     #.## ###--### ##.#     ",
    "######.## #      # ##.######",
    "      .   #      #   .      ",
    "######.## #      # ##.######",
    "     #.## ######## ##.#     ",
    "     #.##          ##.#     ",
    "     #.## ######## ##.#     ",
    "######.## ######## ##.######",
    "#............##............#",
    "#.####.#####.##.#####.####.#",
    "#.####.#####.##.#####.####.#",
    "#o..##.......  .......##..o#",
    "###.##.##.########.##.##.###",
    "###.##.##.########.##.##.###",
    "#......##....##....##......#",
    "#.##########.##.##########.#",
    "#.##########.##.##########.#",
    "#..........................#",
    "############################",
]
assert len(MAZE) == ROWS and all(len(r) == COLS for r in MAZE)

TUNNEL_ROW = 14
NO_UP = {(12, 11), (15, 11), (12, 23), (15, 23)}   # zonas onde gatos não viram p/ cima
HOUSE_Y = 14 * TILE + HALF
EXIT_Y = 11 * TILE + HALF
DOOR_X = 14 * TILE
DOOR_CELL = (13, 12)

SPR = 30  # tamanho dos sprites


def tile_at(cx, cy):
    if cy == TUNNEL_ROW and cx in (-1, COLS):
        return " "
    if 0 <= cx < COLS and 0 <= cy < ROWS:
        return MAZE[cy][cx]
    return "#"


def walkable(cx, cy, door=False):
    t = tile_at(cx, cy)
    if t == "#":
        return False
    if t == "-":
        return door
    return True


def build_dist_map():
    """BFS a partir da porta da casa dos gatos (para gatos 'comidos' voltarem)."""
    dist = {DOOR_CELL: 0}
    queue = [DOOR_CELL]
    while queue:
        cx, cy = queue.pop(0)
        for d in DIR_ORDER:
            n = (cx + d[0], cy + d[1])
            if n in dist or not walkable(n[0], n[1], door=True):
                continue
            dist[n] = dist[(cx, cy)] + 1
            queue.append(n)
    return dist


DIST_MAP = build_dist_map()

# ----------------------------------------------------------------------------
# Fontes
# ----------------------------------------------------------------------------
FAMS = "couriernew,consolas,dejavusansmono,liberationmono,monospace"
F_SMALL = pygame.font.SysFont(FAMS, 14, bold=True)
F_MID = pygame.font.SysFont(FAMS, 20, bold=True)
F_BIG = pygame.font.SysFont(FAMS, 46, bold=True)


def draw_text(surf, txt, x, y, color=WHITE, font=F_MID, center=False, shadow=False):
    img = font.render(txt, True, color)
    r = img.get_rect()
    if center:
        r.center = (x, y)
    else:
        r.topleft = (x, y)
    if shadow:
        sh = font.render(txt, True, (0, 0, 0))
        surf.blit(sh, r.move(3, 3))
    surf.blit(img, r)


# ----------------------------------------------------------------------------
# Labirinto (pré-renderizado com contorno neon estilo arcade)
# ----------------------------------------------------------------------------
def build_maze(color):
    m = TILE
    big = pygame.Surface((W + 2 * m, ROWS * TILE + 2 * m))
    big.fill(BLACK)
    inner = pygame.Surface(big.get_size(), pygame.SRCALPHA)
    walls, opens = [], []
    for y in range(-1, ROWS + 1):
        for x in range(-1, COLS + 1):
            r = pygame.Rect((x + 1) * m, (y + 1) * m, m, m)
            if 0 <= x < COLS and 0 <= y < ROWS and MAZE[y][x] == "#":
                walls.append(r)
            else:
                opens.append(r)
    for r in walls:
        pygame.draw.rect(big, color, r)
        pygame.draw.rect(inner, (0, 0, 0, 255), r)
    for r in opens:
        pygame.draw.rect(big, BLACK, r.inflate(4, 4), border_radius=4)
        pygame.draw.rect(inner, (0, 0, 0, 0), r.inflate(10, 10), border_radius=6)
    big.blit(inner, (0, 0))
    return big.subsurface((m, m, W, ROWS * TILE)).copy()


# ----------------------------------------------------------------------------
# Sprites desenhados em código (64x64, depois reduzidos com suavização)
# ----------------------------------------------------------------------------
def new_canvas():
    return pygame.Surface((64, 64), pygame.SRCALPHA)


def shrink(s, size=SPR):
    return pygame.transform.smoothscale(s, (size, size))


def make_rat(frame):
    s = new_canvas()
    GR, DK, LT, PK = (150, 150, 170), (100, 100, 125), (200, 200, 215), (255, 150, 175)
    wag = [-3, 0, 3][frame]
    fo = [-3, 0, 3][frame]
    pygame.draw.lines(s, PK, False, [(20, 40), (13, 43 + wag), (8, 38), (2, 41 + wag)], 3)
    pygame.draw.circle(s, DK, (30, 22), 7)
    pygame.draw.ellipse(s, PK, (20 + fo, 47, 10, 7))
    pygame.draw.ellipse(s, PK, (36 - fo, 47, 10, 7))
    pygame.draw.ellipse(s, GR, (12, 20, 36, 30))
    pygame.draw.ellipse(s, LT, (18, 34, 26, 14))
    pygame.draw.ellipse(s, GR, (36, 22, 20, 22))
    pygame.draw.polygon(s, GR, [(46, 24), (63, 34), (46, 42)])
    pygame.draw.circle(s, DK, (40, 20), 9)
    pygame.draw.circle(s, PK, (40, 20), 5)
    pygame.draw.circle(s, (235, 80, 115), (62, 34), 3)
    pygame.draw.circle(s, (20, 20, 30), (49, 30), 3)
    pygame.draw.circle(s, WHITE, (50, 29), 1)
    if frame == 2:
        pygame.draw.polygon(s, (90, 20, 40), [(50, 38), (62, 37), (53, 45)])
    pygame.draw.line(s, (235, 235, 240), (54, 36), (64, 31), 1)
    pygame.draw.line(s, (235, 235, 240), (54, 38), (64, 41), 1)
    return shrink(s, 28)


def lighten(c, v=70):
    return tuple(min(255, k + v) for k in c)


def cat_base(s, col, anim):
    pygame.draw.polygon(s, col, [(11, 24), (12, 1), (29, 13)])
    pygame.draw.polygon(s, col, [(53, 24), (52, 1), (35, 13)])
    pygame.draw.circle(s, col, (32, 30), 22)
    pts = [(10, 30), (54, 30)]
    for i in range(9):
        pts.append((54 - i * 5.5, 58 if (i + anim) % 2 == 0 else 50))
    pygame.draw.polygon(s, col, pts)
    inner = lighten(col, 80)
    pygame.draw.polygon(s, inner, [(15, 19), (15, 8), (24, 14)])
    pygame.draw.polygon(s, inner, [(49, 19), (49, 8), (40, 14)])


def cat_eyes(s, d, white=WHITE):
    for ex in (15, 33):
        pygame.draw.ellipse(s, white, (ex, 22, 16, 18))
        cx = ex + 8 + d[0] * 3
        cy = 31 + d[1] * 3
        pygame.draw.ellipse(s, (15, 15, 40), (cx - 3, cy - 7, 6, 14))


def make_cat(col, d, anim):
    s = new_canvas()
    cat_base(s, col, anim)
    cat_eyes(s, d)
    pygame.draw.polygon(s, (255, 110, 140), [(29, 40), (35, 40), (32, 44)])
    pygame.draw.line(s, (50, 20, 40), (32, 44), (27, 48), 2)
    pygame.draw.line(s, (50, 20, 40), (32, 44), (37, 48), 2)
    for a, b in (((12, 41), (1, 37)), ((12, 45), (1, 47)), ((52, 41), (63, 37)), ((52, 45), (63, 47))):
        pygame.draw.line(s, WHITE, a, b, 1)
    return shrink(s)


def make_scared(anim, flash):
    s = new_canvas()
    body = WHITE if flash else (40, 50, 255)
    face = (255, 0, 0) if flash else (255, 190, 175)
    cat_base(s, body, anim)
    pygame.draw.circle(s, face, (24, 28), 4)
    pygame.draw.circle(s, face, (40, 28), 4)
    pts = [(12, 48), (19, 41), (26, 48), (32, 41), (38, 48), (45, 41), (52, 48)]
    pygame.draw.lines(s, face, False, pts, 3)
    return shrink(s)


def make_eyes(d):
    s = new_canvas()
    cat_eyes(s, d)
    return shrink(s)


def draw_wedge(s, body, rind, top):
    pygame.draw.polygon(s, body, [(6, 48), (58, 48), (58, 20)])
    pygame.draw.line(s, top, (6, 48), (58, 20), 3)
    pygame.draw.rect(s, rind, (6, 44, 52, 5))


def make_cheese(kind):
    s = new_canvas()
    if kind == 0:      # suíço
        draw_wedge(s, (255, 214, 60), (230, 170, 30), (255, 240, 150))
        for x, y, r in ((40, 40, 4), (50, 32, 3), (26, 42, 3), (53, 41, 2)):
            pygame.draw.circle(s, (225, 165, 25), (x, y), r)
        pygame.draw.rect(s, (230, 170, 30), (6, 44, 52, 5))
    elif kind == 1:    # minas
        pygame.draw.rect(s, (255, 244, 190), (8, 22, 48, 28), border_radius=5)
        pygame.draw.rect(s, (255, 252, 225), (8, 22, 48, 8), border_radius=5)
        pygame.draw.rect(s, (225, 205, 140), (8, 22, 48, 28), 3, border_radius=5)
        for x, y in ((18, 38), (30, 42), (42, 36), (48, 44)):
            pygame.draw.circle(s, (225, 205, 140), (x, y), 2)
    elif kind == 2:    # cheddar
        draw_wedge(s, (255, 150, 25), (200, 100, 15), (255, 195, 100))
    elif kind == 3:    # gouda
        pygame.draw.circle(s, (205, 35, 45), (32, 32), 22)
        pygame.draw.circle(s, (240, 90, 90), (24, 24), 5)
        pygame.draw.polygon(s, (255, 210, 70), [(32, 32), (51, 24), (51, 40)])
        pygame.draw.circle(s, (150, 20, 30), (32, 32), 22, 3)
    elif kind == 4:    # brie
        pygame.draw.circle(s, (248, 236, 190), (32, 32), 22)
        pygame.draw.polygon(s, (255, 250, 210), [(32, 32), (51, 24), (51, 40)])
        pygame.draw.circle(s, (215, 195, 130), (32, 32), 22, 3)
        pygame.draw.circle(s, WHITE, (22, 22), 3)
    elif kind == 5:    # parmesão
        pygame.draw.rect(s, (240, 205, 110), (8, 22, 48, 28), border_radius=3)
        pygame.draw.rect(s, (190, 150, 70), (8, 44, 48, 6))
        pygame.draw.rect(s, (190, 150, 70), (8, 22, 5, 28))
        for x, y in ((22, 30), (32, 36), (42, 28), (48, 38), (26, 40)):
            pygame.draw.circle(s, (215, 170, 70), (x, y), 2)
    elif kind == 6:    # gorgonzola
        draw_wedge(s, (245, 240, 205), (190, 185, 140), WHITE)
        for a, b in (((24, 44), (32, 38)), ((38, 42), (46, 34)), ((44, 44), (52, 38)), ((18, 46), (22, 42))):
            pygame.draw.line(s, (60, 140, 170), a, b, 3)
    else:              # dourado
        draw_wedge(s, (255, 200, 10), (210, 150, 0), (255, 245, 150))
        for x, y in ((46, 36), (30, 42)):
            pygame.draw.circle(s, (235, 170, 0), (x, y), 3)
        pygame.draw.line(s, WHITE, (52, 6), (52, 18), 2)
        pygame.draw.line(s, WHITE, (46, 12), (58, 12), 2)
    return shrink(s)


CHEESE_NAMES = ["SUÍÇO", "MINAS", "CHEDDAR", "GOUDA", "BRIE", "PARMESÃO", "GORGONZOLA", "DOURADO"]
CHEESE_POINTS = [100, 300, 500, 700, 1000, 2000, 3000, 5000]


# ----------------------------------------------------------------------------
# Som (gerado por código, sem arquivos)
# ----------------------------------------------------------------------------
class Sounds:
    def __init__(self):
        self.ok = False
        self.muted = False
        self.s = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 1, 512)
            self.freq, _, self.ch = pygame.mixer.get_init()
            self._build()
            self.ok = True
        except Exception:
            self.ok = False

    def _tone(self, f, ms, vol=0.2, slide=0.0, wave="square"):
        n = int(self.freq * ms / 1000)
        buf = array("h")
        ph = 0.0
        for i in range(n):
            ph += 2 * math.pi * (f + slide * i / max(1, n)) / self.freq
            sn = math.sin(ph)
            v = (1.0 if sn >= 0 else -1.0) if wave == "square" else sn
            env = min(1.0, (n - i) / (self.freq * 0.02), (i + 1) / (self.freq * 0.004))
            buf.append(int(v * vol * 32767 * env))
        return buf

    def _gap(self, ms):
        return array("h", [0] * int(self.freq * ms / 1000))

    def _mk(self, parts):
        data = array("h")
        for p in parts:
            data.extend(p)
        if self.ch > 1:
            out = array("h")
            for v in data:
                out.extend([v] * self.ch)
            data = out
        return pygame.mixer.Sound(buffer=data.tobytes())

    def _notes(self, notes, vol=0.2):
        parts = []
        for f, ms in notes:
            parts.append(self._tone(f, ms, vol))
            parts.append(self._gap(15))
        return parts

    def _build(self):
        t = self._tone
        self.s["waka0"] = self._mk([t(200, 70, 0.18, 250)])
        self.s["waka1"] = self._mk([t(450, 70, 0.18, -250)])
        self.s["power"] = self._mk([t(200, 260, 0.18, 500)])
        self.s["eatghost"] = self._mk([t(300, 200, 0.22, 800)])
        self.s["death"] = self._mk([t(950 - i * 65, 110, 0.22, -140) for i in range(11)])
        self.s["start"] = self._mk(self._notes(
            [(262, 110), (330, 110), (392, 110), (523, 200), (392, 110), (523, 330), (330, 110), (392, 110), (523, 400)]))
        self.s["bonus"] = self._mk(self._notes([(660, 70), (880, 70), (1100, 140)]))
        self.s["extra"] = self._mk(self._notes([(523, 80), (659, 80), (784, 80), (1047, 220)]))

    def play(self, name):
        if self.ok and not self.muted and name in self.s:
            self.s[name].play()


# ----------------------------------------------------------------------------
# Parâmetros por fase
# ----------------------------------------------------------------------------
FRIGHT_SECS = [6, 5, 4, 3, 2, 5, 2, 2, 1, 5, 2, 1, 1, 3, 1, 1, 0, 1]
ELROY_DOTS = [20, 30, 40, 40, 40, 50, 50, 50, 60, 60, 60, 80, 80, 80, 100, 100, 100, 100, 120]


def level_params(level):
    if level == 1:
        p = dict(pac=0.80, gh=0.75, tun=0.40, fpac=0.90, fgh=0.50)
    elif level <= 4:
        p = dict(pac=0.90, gh=0.85, tun=0.45, fpac=0.95, fgh=0.55)
    elif level <= 20:
        p = dict(pac=1.00, gh=0.95, tun=0.50, fpac=1.00, fgh=0.60)
    else:
        p = dict(pac=0.90, gh=0.95, tun=0.50, fpac=0.90, fgh=0.60)
    p["fright"] = FRIGHT_SECS[level - 1] if level <= len(FRIGHT_SECS) else 0
    return p


def mode_schedule(level):
    if level == 1:
        s = [7, 20, 7, 20, 5, 20, 5, None]
    elif level <= 4:
        s = [7, 20, 7, 20, 5, 1033, 1 / 60, None]
    else:
        s = [5, 20, 5, 20, 5, 1037, 1 / 60, None]
    return [10 ** 9 if v is None else max(1, int(v * 60)) for v in s]


# ----------------------------------------------------------------------------
# Atores
# ----------------------------------------------------------------------------
class Player:
    def __init__(self):
        self.reset()

    def reset(self):
        self.x = 14 * TILE
        self.y = 23 * TILE + HALF
        self.dir = LEFT
        self.next = LEFT
        self.face = LEFT
        self.acc = 0.0
        self.anim = 0.0
        self.moving = True

    @property
    def cell(self):
        return (self.x // TILE, self.y // TILE)

    def press(self, d):
        self.next = d
        if self.dir != (0, 0) and d == (-self.dir[0], -self.dir[1]):
            self.dir = d

    def step(self):
        if self.x % TILE == HALF and self.y % TILE == HALF:
            cx, cy = self.x // TILE, self.y // TILE
            if cx < 0 and self.dir[0] < 0:
                self.x = COLS * TILE + HALF
                cx = COLS
            elif cx >= COLS and self.dir[0] > 0:
                self.x = -HALF
                cx = -1
            if self.next != (0, 0) and walkable(cx + self.next[0], cy + self.next[1]):
                self.dir = self.next
            if self.dir != (0, 0) and not walkable(cx + self.dir[0], cy + self.dir[1]):
                self.dir = (0, 0)
        if self.dir != (0, 0):
            self.x += self.dir[0]
            self.y += self.dir[1]
            self.face = self.dir

    def update(self, speed):
        self.acc += speed
        n = int(self.acc)
        self.acc -= n
        before = (self.x, self.y)
        for _ in range(n):
            self.step()
        self.moving = (self.x, self.y) != before
        if self.moving:
            self.anim += 0.22


class Ghost:
    NAMES = ["TIGRE", "MINGAU", "BIGODE", "FELPUDO"]
    COLORS = [RED, PINK, CYAN, ORANGE]
    SCATTER = [(25, -3), (2, -3), (27, 31), (0, 31)]
    STARTS = [(14 * TILE, EXIT_Y), (14 * TILE, HOUSE_Y), (12 * TILE, HOUSE_Y), (16 * TILE, HOUSE_Y)]

    def __init__(self, idx):
        self.idx = idx
        self.color = Ghost.COLORS[idx]
        self.scatter = Ghost.SCATTER[idx]
        self.reset()

    def reset(self):
        self.x, self.y = Ghost.STARTS[self.idx]
        self.state = "normal" if self.idx == 0 else "house"
        self.dir = LEFT
        self.frightened = False
        self.reverse = False
        self.acc = 0.0

    @property
    def cell(self):
        return (self.x // TILE, self.y // TILE)

    def step(self, g):
        if self.state == "house":
            return
        if self.state == "leaving":
            if self.x != DOOR_X:
                if self.y != HOUSE_Y:
                    self.y += 1 if self.y < HOUSE_Y else -1
                else:
                    self.x += 1 if self.x < DOOR_X else -1
            elif self.y > EXIT_Y:
                self.y -= 1
            else:
                self.state = "normal"
                self.dir = LEFT
                self.reverse = False
            return
        if self.state == "entering":
            if self.y < HOUSE_Y:
                self.y += 1
            else:
                self.state = "leaving"
                self.frightened = False
            return
        if self.x % TILE == HALF and self.y % TILE == HALF:
            self.decide(g)
        self.x += self.dir[0]
        self.y += self.dir[1]

    def decide(self, g):
        cx, cy = self.x // TILE, self.y // TILE
        if cx < 0 and self.dir[0] < 0:
            self.x = COLS * TILE + HALF
            cx = COLS
        elif cx >= COLS and self.dir[0] > 0:
            self.x = -HALF
            cx = -1
        if self.state == "eaten":
            if (cx, cy) == DOOR_CELL:
                self.state = "entering"
                self.dir = DOWN
                return
            best = None
            for d in DIR_ORDER:
                n = (cx + d[0], cy + d[1])
                if not walkable(n[0], n[1], door=True) or n not in DIST_MAP:
                    continue
                if best is None or DIST_MAP[n] < best[0]:
                    best = (DIST_MAP[n], d)
            if best:
                self.dir = best[1]
            return
        rev = (-self.dir[0], -self.dir[1])
        if self.reverse:
            self.reverse = False
            if walkable(cx + rev[0], cy + rev[1]):
                self.dir = rev
                return
        opts = []
        for d in DIR_ORDER:
            if d == rev:
                continue
            if not walkable(cx + d[0], cy + d[1]):
                continue
            if d == UP and (cx, cy) in NO_UP and not self.frightened:
                continue
            opts.append(d)
        if not opts:
            self.dir = rev
            return
        if len(opts) == 1:
            self.dir = opts[0]
            return
        if self.frightened:
            self.dir = random.choice(opts)
            return
        tx, ty = g.target(self)
        self.dir = min(opts, key=lambda d: (cx + d[0] - tx) ** 2 + (cy + d[1] - ty) ** 2)

    def update(self, g):
        self.acc += g.ghost_speed(self)
        n = int(self.acc)
        self.acc -= n
        for _ in range(n):
            self.step(g)


# ----------------------------------------------------------------------------
# Jogo
# ----------------------------------------------------------------------------
HS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rato_highscore.txt")


class Game:
    def __init__(self):
        try:
            self.screen = pygame.display.set_mode((W, H), pygame.SCALED | pygame.RESIZABLE)
        except Exception:
            self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption("Rato e Gatos")
        self.clock = pygame.time.Clock()
        self.snd = Sounds()

        self.maze_blue = build_maze(BLUE)
        self.maze_white = build_maze(WHITE)

        self.rat = [make_rat(i) for i in range(3)]
        base = self.rat
        self.rat_spr = {}
        for d in DIR_ORDER:
            frames = []
            for f in base:
                if d == RIGHT:
                    frames.append(f)
                elif d == LEFT:
                    frames.append(pygame.transform.flip(f, True, False))
                elif d == UP:
                    frames.append(pygame.transform.rotate(f, 90))
                else:
                    frames.append(pygame.transform.rotate(f, -90))
            self.rat_spr[d] = frames
        self.cat_spr = [[[make_cat(c, d, a) for a in range(2)] for d in DIR_ORDER] for c in Ghost.COLORS]
        self.scared_spr = [[make_scared(a, fl) for a in range(2)] for fl in (False, True)]
        self.eyes_spr = [make_eyes(d) for d in DIR_ORDER]
        self.cheese_spr = [make_cheese(k) for k in range(8)]
        self.icon_spr = pygame.transform.smoothscale(self.rat_spr[LEFT][1], (22, 22))
        self.icon_cheese = [pygame.transform.smoothscale(c, (22, 22)) for c in self.cheese_spr]

        self.player = Player()
        self.ghosts = [Ghost(i) for i in range(4)]
        self.high = self.load_high()
        self.state = "menu"
        self.paused = False
        self.frame = 0
        self.timer = 0
        self.score = 0
        self.level = 1
        self.extra = 2
        self.popups = []
        self.dots = {}
        self.pause_ghost = None

    # ---------- persistência ----------
    def load_high(self):
        try:
            with open(HS_FILE) as f:
                return int(f.read().strip())
        except Exception:
            return 0

    def save_high(self):
        try:
            with open(HS_FILE, "w") as f:
                f.write(str(self.high))
        except Exception:
            pass

    # ---------- fluxo ----------
    def new_game(self):
        self.score = 0
        self.level = 1
        self.extra = 2
        self.next_extra = 10000
        self.load_level()
        self.reset_positions()
        self.start_ready(True)

    def load_level(self):
        self.dots = {}
        for y, row in enumerate(MAZE):
            for x, ch in enumerate(row):
                if ch in ".o":
                    self.dots[(x, y)] = ch
        self.total_dots = len(self.dots)
        self.bonus = None
        self.bonus_spawned = [False, False]
        self.params = level_params(self.level)

    def reset_positions(self):
        self.player.reset()
        for g in self.ghosts:
            g.reset()
        self.schedule = mode_schedule(self.level)
        self.mode_idx = 0
        self.mode_timer = self.schedule[0]
        self.fright_timer = 0
        self.chain = 0
        self.house_counter = 0
        self.idle = 0
        self.popups = []
        self.pause_ghost = None
        self.waka = 0

    def start_ready(self, intro):
        self.state = "ready"
        self.intro = intro
        self.timer = 240 if intro else 120
        if intro:
            self.snd.play("start")

    @property
    def mode(self):
        return "scatter" if self.mode_idx % 2 == 0 else "chase"

    def elroy(self):
        left = len(self.dots)
        thr = ELROY_DOTS[min(self.level - 1, len(ELROY_DOTS) - 1)]
        if left <= thr // 2:
            return 2
        if left <= thr:
            return 1
        return 0

    # ---------- IA ----------
    def target(self, gh):
        p = self.player
        px, py = p.cell
        if self.mode == "scatter" and not (gh.idx == 0 and self.elroy() > 0):
            return gh.scatter
        if gh.idx == 0:
            return (px, py)
        fx, fy = p.face
        if gh.idx == 1:
            if p.face == UP:
                return (px - 4, py - 4)
            return (px + 4 * fx, py + 4 * fy)
        if gh.idx == 2:
            if p.face == UP:
                ax, ay = px - 2, py - 2
            else:
                ax, ay = px + 2 * fx, py + 2 * fy
            bx, by = self.ghosts[0].cell
            return (2 * ax - bx, 2 * ay - by)
        cx, cy = gh.cell
        if (cx - px) ** 2 + (cy - py) ** 2 > 64:
            return (px, py)
        return gh.scatter

    def ghost_speed(self, gh):
        p = self.params
        if gh.state == "house":
            return 0
        if gh.state == "eaten":
            return U * 1.7
        if gh.state in ("leaving", "entering"):
            return U * 0.5
        cx, cy = gh.cell
        if cy == TUNNEL_ROW and (cx < 6 or cx > 21):
            return U * p["tun"]
        if gh.frightened:
            return U * p["fgh"]
        sp = p["gh"]
        if gh.idx == 0:
            sp += 0.05 * self.elroy()
        return U * sp

    # ---------- atualização ----------
    def update(self):
        self.frame += 1
        if self.state == "menu" or self.paused:
            return
        for pp in self.popups:
            pp[3] -= 1
        self.popups = [pp for pp in self.popups if pp[3] > 0]

        if self.state == "ready":
            self.timer -= 1
            if self.timer <= 0:
                self.state = "playing"
        elif self.state == "playing":
            self.update_playing()
        elif self.state == "ghostpause":
            self.timer -= 1
            if self.timer <= 0:
                self.pause_ghost = None
                self.state = "playing"
        elif self.state == "dying":
            self.timer -= 1
            if self.timer <= 0:
                self.after_death()
        elif self.state == "win":
            self.timer -= 1
            if self.timer <= 0:
                self.level += 1
                self.load_level()
                self.reset_positions()
                self.start_ready(False)
        elif self.state == "gameover":
            self.timer -= 1
            if self.timer <= 0:
                self.state = "menu"

    def update_playing(self):
        p = self.player
        # modos scatter/chase e tempo de susto
        if self.fright_timer > 0:
            self.fright_timer -= 1
            if self.fright_timer == 0:
                for g in self.ghosts:
                    g.frightened = False
        else:
            self.mode_timer -= 1
            if self.mode_timer <= 0 and self.mode_idx < len(self.schedule) - 1:
                self.mode_idx += 1
                self.mode_timer = self.schedule[self.mode_idx]
                for g in self.ghosts:
                    if g.state == "normal":
                        g.reverse = True

        # rato
        pm = self.params["fpac"] if self.fright_timer > 0 else self.params["pac"]
        p.update(U * pm)
        self.eat_dots()
        self.update_bonus()
        self.release_ghosts()

        # gatos
        for g in self.ghosts:
            g.update(self)
        self.check_collisions()

        if not self.dots and self.state == "playing":
            self.state = "win"
            self.timer = 160

    def eat_dots(self):
        p = self.player
        c = p.cell
        self.idle += 1
        if c in self.dots:
            kind = self.dots.pop(c)
            self.idle = 0
            self.house_counter += 1
            self.snd.play("waka%d" % self.waka)
            self.waka ^= 1
            if kind == "o":
                self.add_score(50)
                self.power()
            else:
                self.add_score(10)
            eaten = self.total_dots - len(self.dots)
            for i, thr in enumerate((70, 170)):
                if eaten >= thr and not self.bonus_spawned[i]:
                    self.bonus_spawned[i] = True
                    self.bonus = [14 * TILE, 17 * TILE + HALF, random.randint(540, 600)]

    def power(self):
        secs = self.params["fright"]
        self.chain = 0
        if secs <= 0:
            for g in self.ghosts:
                if g.state == "normal":
                    g.reverse = True
            return
        self.fright_timer = secs * 60
        self.snd.play("power")
        for g in self.ghosts:
            if g.state != "eaten":
                g.frightened = True
                if g.state == "normal":
                    g.reverse = True

    def add_score(self, v):
        self.score += v
        if self.score > self.high:
            self.high = self.score
        if self.score >= self.next_extra:
            self.next_extra = 10 ** 12
            self.extra += 1
            self.snd.play("extra")

    def update_bonus(self):
        b = self.bonus
        if not b:
            return
        b[2] -= 1
        if b[2] <= 0:
            self.bonus = None
            return
        p = self.player
        if (p.x - b[0]) ** 2 + (p.y - b[1]) ** 2 < (TILE * 0.9) ** 2:
            kind = min(self.level - 1, 7)
            pts = CHEESE_POINTS[kind]
            self.add_score(pts)
            self.popups.append([b[0], b[1], str(pts), 100, (255, 140, 255)])
            self.snd.play("bonus")
            self.bonus = None

    def release_ghosts(self):
        waiting = [g for g in self.ghosts if g.state == "house"]
        if not waiting:
            return
        g = waiting[0]
        limits = {1: 0, 2: 30 if self.level == 1 else 0, 3: 60 if self.level == 1 else (50 if self.level == 2 else 0)}
        idle_limit = (4 if self.level < 5 else 3) * 60
        if self.house_counter >= limits[g.idx] or self.idle >= idle_limit:
            g.state = "leaving"
            self.house_counter = 0
            self.idle = 0

    def check_collisions(self):
        p = self.player
        for g in self.ghosts:
            if g.state != "normal":
                continue
            if (g.x - p.x) ** 2 + (g.y - p.y) ** 2 < (TILE * 0.75) ** 2:
                if g.frightened:
                    pts = 200 << min(self.chain, 3)
                    self.chain += 1
                    self.add_score(pts)
                    g.state = "eaten"
                    g.frightened = False
                    self.popups.append([g.x, g.y, str(pts), 50, CYAN])
                    self.pause_ghost = g
                    self.state = "ghostpause"
                    self.timer = 50
                    self.snd.play("eatghost")
                    return
                self.state = "dying"
                self.timer = 140
                self.snd.play("death")
                return

    def after_death(self):
        if self.extra <= 0:
            self.state = "gameover"
            self.timer = 260
            self.save_high()
        else:
            self.extra -= 1
            self.reset_positions()
            self.start_ready(False)

    # ---------- entrada ----------
    def handle_key(self, key):
        if key == pygame.K_m:
            self.snd.muted = not self.snd.muted
            return
        if self.state == "menu":
            if key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.new_game()
            return
        if key == pygame.K_p and self.state in ("ready", "playing", "ghostpause"):
            self.paused = not self.paused
            return
        if key == pygame.K_r:
            self.paused = False
            self.new_game()
            return
        if self.state == "gameover" and key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.new_game()
            return
        d = {pygame.K_RIGHT: RIGHT, pygame.K_d: RIGHT, pygame.K_LEFT: LEFT, pygame.K_a: LEFT,
             pygame.K_UP: UP, pygame.K_w: UP, pygame.K_DOWN: DOWN, pygame.K_s: DOWN}.get(key)
        if d and self.state in ("ready", "playing", "ghostpause"):
            self.player.press(d)

    # ---------- desenho ----------
    def blit_c(self, spr, x, y):
        self.screen.blit(spr, (int(x) - spr.get_width() // 2, int(y) - spr.get_height() // 2 + TOP))

    def rat_sprite(self):
        p = self.player
        return self.rat_spr[p.face][int(p.anim) % 3 if p.moving else 1]

    def ghost_sprite(self, g):
        anim = (self.frame // 8) % 2
        di = DIR_INDEX.get(g.dir, 1)
        if g.state in ("eaten", "entering"):
            return self.eyes_spr[di]
        if g.frightened:
            flash = self.fright_timer < 120 and (self.fright_timer // 14) % 2 == 0
            return self.scared_spr[1 if flash else 0][anim]
        return self.cat_spr[g.idx][di][anim]

    def draw_hud(self):
        s = self.screen
        if (self.frame // 30) % 2 == 0 or self.state == "menu" or self.paused:
            draw_text(s, "1UP", 36, 4, WHITE, F_MID)
        draw_text(s, "%d" % self.score if self.state != "menu" else "00", 36, 26, WHITE, F_MID)
        draw_text(s, "RECORDE", W // 2, 14, WHITE, F_MID, center=True)
        draw_text(s, "%d" % self.high, W // 2, 36, WHITE, F_MID, center=True)
        by = TOP + ROWS * TILE
        for i in range(self.extra if self.state != "menu" else 0):
            s.blit(self.icon_spr, (12 + i * 28, by + 10))
        lv = self.level
        shown = list(range(max(1, lv - 6), lv + 1))
        for i, l in enumerate(reversed(shown)):
            k = min(l - 1, 7)
            s.blit(self.icon_cheese[k], (W - 34 - i * 26, by + 10))

    def draw_dots(self):
        blink = (self.frame // 15) % 2 == 0
        for (x, y), k in self.dots.items():
            px, py = x * TILE + HALF, y * TILE + HALF + TOP
            if k == ".":
                pygame.draw.rect(self.screen, DOT, (px - 2, py - 2, 4, 4))
            elif blink or self.paused:
                pygame.draw.circle(self.screen, DOT, (px, py), 7)

    def draw_playfield(self, maze, show_player=True, show_ghosts=True):
        s = self.screen
        s.blit(maze, (0, TOP))
        pygame.draw.rect(s, PINK_DOOR, (13 * TILE, TOP + 12 * TILE + 6, 2 * TILE, 4))
        self.draw_dots()
        if self.bonus and not (self.bonus[2] < 120 and (self.frame // 6) % 2):
            self.blit_c(self.cheese_spr[min(self.level - 1, 7)], self.bonus[0], self.bonus[1])
        if show_ghosts:
            for g in self.ghosts:
                if g is self.pause_ghost and self.state == "ghostpause":
                    continue
                oy = int(4 * math.sin(self.frame * 0.12 + g.idx * 2)) if g.state == "house" else 0
                self.blit_c(self.ghost_sprite(g), g.x, g.y + oy)
        if show_player and not (self.state == "ghostpause"):
            self.blit_c(self.rat_sprite(), self.player.x, self.player.y)
        for x, y, txt, t, col in self.popups:
            draw_text(s, txt, x, y + TOP, col, F_SMALL, center=True, shadow=True)

    def draw_dying(self):
        p = self.player
        t = 140 - self.timer
        s = self.screen
        s.blit(self.maze_blue, (0, TOP))
        pygame.draw.rect(s, PINK_DOOR, (13 * TILE, TOP + 12 * TILE + 6, 2 * TILE, 4))
        self.draw_dots()
        if t < 35:
            for g in self.ghosts:
                self.blit_c(self.ghost_sprite(g), g.x, g.y)
            self.blit_c(self.rat_sprite(), p.x, p.y)
        elif t < 115:
            k = (t - 35) / 80.0
            spr = pygame.transform.rotozoom(self.rat_spr[RIGHT][1], k * 720, max(0.05, 1 - k))
            self.blit_c(spr, p.x, p.y)
        elif t < 135:
            k = (t - 115) / 20.0
            cx, cy = p.x, p.y + TOP
            for i in range(8):
                a = i * math.pi / 4
                r1, r2 = 6 + k * 14, 12 + k * 18
                pygame.draw.line(s, YELLOW, (cx + math.cos(a) * r1, cy + math.sin(a) * r1),
                                 (cx + math.cos(a) * r2, cy + math.sin(a) * r2), 2)

    def draw(self):
        s = self.screen
        s.fill(BLACK)
        if self.state == "menu":
            self.draw_menu()
            pygame.display.flip()
            return
        if self.state == "dying":
            self.draw_dying()
        elif self.state == "win":
            t = 160 - self.timer
            maze = self.maze_white if (t > 40 and (t // 14) % 2 == 0) else self.maze_blue
            self.draw_playfield(maze, show_ghosts=t < 25)
        elif self.state == "gameover":
            self.draw_playfield(self.maze_blue, show_player=False, show_ghosts=False)
        else:
            self.draw_playfield(self.maze_blue)

        ty = TOP + 17 * TILE + HALF
        if self.state == "ready":
            draw_text(s, "PRONTO!", W // 2, ty, YELLOW, F_MID, center=True)
            if self.intro:
                draw_text(s, "JOGADOR 1", W // 2, TOP + 8 * TILE + HALF, CYAN, F_MID, center=True)
        if self.state == "gameover":
            draw_text(s, "FIM DE JOGO", W // 2, ty, RED, F_MID, center=True)
        if self.paused:
            ov = pygame.Surface((W, ROWS * TILE), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 150))
            s.blit(ov, (0, TOP))
            draw_text(s, "PAUSADO", W // 2, TOP + ROWS * TILE // 2, YELLOW, F_BIG, center=True, shadow=True)
            draw_text(s, "P para continuar", W // 2, TOP + ROWS * TILE // 2 + 40, WHITE, F_SMALL, center=True)
        self.draw_hud()
        if self.snd.muted:
            draw_text(s, "MUDO", W - 8 - F_SMALL.size("MUDO")[0], 4, (160, 160, 160), F_SMALL)
        pygame.display.flip()

    def draw_menu(self):
        s = self.screen
        draw_text(s, "RATO", W // 2, 80, YELLOW, F_BIG, center=True, shadow=True)
        draw_text(s, "E GATOS", W // 2, 130, (255, 120, 120), F_BIG, center=True, shadow=True)
        info = ["PERSEGUIDOR", "EMBOSCADOR", "ESPERTO", "DISTRAÍDO"]
        for i in range(4):
            y = 215 + i * 44
            s.blit(self.cat_spr[i][3][(self.frame // 10) % 2], (90, y - SPR // 2))
            draw_text(s, Ghost.NAMES[i], 140, y - 10, Ghost.COLORS[i], F_MID)
            draw_text(s, info[i], 270, y - 8, (190, 190, 210), F_SMALL)
        draw_text(s, "10", 120, 410, WHITE, F_SMALL)
        pygame.draw.rect(s, DOT, (100, 417 - 2, 4, 4))
        draw_text(s, "50", 120, 432, WHITE, F_SMALL)
        pygame.draw.circle(s, DOT, (102, 440), 7)
        draw_text(s, "QUEIJOS BÔNUS:", 200, 410, WHITE, F_SMALL)
        for i in range(8):
            s.blit(self.icon_cheese[i], (200 + i * 30, 428))
        # corrida do rato e dos gatos
        P = 2 * (W + 340)
        pos = (self.frame * 2.6) % P
        y = 520
        if pos < W + 340:
            rx = pos - 70
            self.screen.blit(self.rat_spr[RIGHT][(self.frame // 6) % 3], (rx - 14, y - 14))
            for i in range(4):
                s.blit(self.cat_spr[i][3][(self.frame // 8) % 2], (rx - 50 - i * 36 - 15, y - 15))
        else:
            rx = W + 70 - (pos - (W + 340))
            s.blit(self.rat_spr[LEFT][(self.frame // 6) % 3], (rx - 14, y - 14))
            for i in range(4):
                fl = self.frame % 40 > 28
                s.blit(self.scared_spr[1 if fl else 0][(self.frame // 8) % 2], (rx - 50 - i * 36 - 15, y - 15))
        if (self.frame // 30) % 2 == 0:
            draw_text(s, "PRESSIONE ENTER", W // 2, 575, YELLOW, F_MID, center=True)
        draw_text(s, "SETAS/WASD mover  P pausa  M som  R reiniciar", W // 2, 610, (150, 160, 190), F_SMALL, center=True)
        draw_text(s, "RECORDE %d" % self.high, W // 2, 635, WHITE, F_SMALL, center=True)

    # ---------- loop principal ----------
    def run(self):
        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.save_high()
                    pygame.quit()
                    sys.exit()
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE:
                        if self.state == "menu":
                            self.save_high()
                            pygame.quit()
                            sys.exit()
                        self.save_high()
                        self.paused = False
                        self.state = "menu"
                    else:
                        self.handle_key(e.key)
            self.update()
            self.draw()
            self.clock.tick(FPS)


if __name__ == "__main__":
    Game().run()