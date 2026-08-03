# game.py — Wave system, map, camera, minimap

import pygame
import math
import random
from settings import *
from zombie import Zombie, PowerUp
from bullet import ParticleSystem

# ─── Pre-baked surfaces ───────────────────────────────────────────────────────
_VIGNETTE_SURFACE: pygame.Surface | None = None
_FLOOR_SURF:       pygame.Surface | None = None

def get_vignette() -> pygame.Surface:
    global _VIGNETTE_SURFACE
    if _VIGNETTE_SURFACE is None:
        w, h = SCREEN_WIDTH, SCREEN_HEIGHT
        _VIGNETTE_SURFACE = pygame.Surface((w, h), pygame.SRCALPHA)
        steps = 55
        for i in range(steps):
            alpha = int(160 * (1 - i / steps) ** 2.2)
            thick = max(1, (steps - i) * 2)
            inset = i * (min(w, h) // 2) // steps
            pygame.draw.rect(_VIGNETTE_SURFACE, (0, 0, 0, alpha),
                             (inset, inset, w - 2 * inset, h - 2 * inset), thick)
    return _VIGNETTE_SURFACE

def get_floor_surface() -> pygame.Surface:
    global _FLOOR_SURF
    if _FLOOR_SURF is None:
        _FLOOR_SURF = _build_tile_surface()
    return _FLOOR_SURF

def _build_tile_surface() -> pygame.Surface:
    surf = pygame.Surface((MAP_WIDTH, MAP_HEIGHT))
    surf.fill((14, 18, 14))
    for col in range(MAP_COLS):
        for row in range(MAP_ROWS):
            sx = col * TILE_SIZE
            sy = row * TILE_SIZE
            shade = 22 if (col + row) % 2 == 0 else 17
            pygame.draw.rect(surf, (shade, shade + 2, shade),
                             (sx + 1, sy + 1, TILE_SIZE - 2, TILE_SIZE - 2))
            rng = random.Random(col * 997 + row * 1009)
            if rng.random() < 0.4:
                cx2   = sx + rng.randint(8, TILE_SIZE - 8)
                cy2   = sy + rng.randint(8, TILE_SIZE - 8)
                angle = rng.uniform(0, math.tau)
                length = rng.randint(6, 22)
                ex = cx2 + int(math.cos(angle) * length)
                ey = cy2 + int(math.sin(angle) * length)
                pygame.draw.line(surf, (8, 8, 8), (cx2, cy2), (ex, ey), 1)
                if rng.random() < 0.4:
                    mid = (cx2 + ex) // 2, (cy2 + ey) // 2
                    ba  = angle + rng.uniform(0.4, 1.2) * rng.choice([-1, 1])
                    bl  = rng.randint(4, 12)
                    pygame.draw.line(surf, (8, 8, 8), mid,
                                     (mid[0] + int(math.cos(ba) * bl),
                                      mid[1] + int(math.sin(ba) * bl)), 1)
            if rng.random() < 0.12:
                pygame.draw.circle(surf, (10, 12, 10),
                                   (sx + rng.randint(10, TILE_SIZE - 10),
                                    sy + rng.randint(10, TILE_SIZE - 10)),
                                   rng.randint(4, 12))
    return surf


def build_obstacle_rects() -> list[pygame.Rect]:
    rects = []
    for (col, row, w, h) in OBSTACLES:
        rects.append(pygame.Rect(col * TILE_SIZE, row * TILE_SIZE,
                                 w * TILE_SIZE, h * TILE_SIZE))
    return rects


def _draw_tile_bg(surface: pygame.Surface, cam_x: float, cam_y: float) -> None:
    floor = get_floor_surface()
    surface.blit(floor, (0, 0),
                 (int(cam_x), int(cam_y), SCREEN_WIDTH, SCREEN_HEIGHT))


def _draw_obstacles(surface: pygame.Surface, rects: list[pygame.Rect],
                    cam_x: float, cam_y: float) -> None:
    for rect in rects:
        sx = rect.x - int(cam_x)
        sy = rect.y - int(cam_y)
        if sx > SCREEN_WIDTH or sy > SCREEN_HEIGHT or \
           sx + rect.width < 0 or sy + rect.height < 0:
            continue
        w, h = rect.width, rect.height
        pygame.draw.rect(surface, (0, 0, 0), (sx + 7, sy + 7, w, h))
        pygame.draw.rect(surface, (58, 58, 60), (sx, sy, w, h))
        brick_h = 16
        for row in range(h // brick_h + 1):
            by     = sy + row * brick_h
            offset = 18 if row % 2 else 0
            for col in range(w // 36 + 2):
                bx = sx + col * 36 - offset
                clipped_bx = max(bx, sx)
                clipped_w  = min(bx + 34, sx + w) - clipped_bx
                if clipped_w > 0:
                    pygame.draw.rect(surface, (48, 48, 50),
                                     (clipped_bx, by, clipped_w, brick_h - 2))
                    pygame.draw.rect(surface, (38, 38, 40),
                                     (clipped_bx, by, clipped_w, brick_h - 2), 1)
        pygame.draw.rect(surface, (95, 95, 98), (sx, sy, w, 3))
        pygame.draw.rect(surface, (105, 105, 108), (sx, sy, w, h), 2)


# ─── Camera ───────────────────────────────────────────────────────────────────
class Camera:
    def __init__(self):
        self.x = 0.0; self.y = 0.0
        self.shake_timer      = 0.0
        self._shake_intensity = SHAKE_INTENSITY
        self.shake_x = 0.0; self.shake_y = 0.0

    def update(self, target_x: float, target_y: float, dt: float) -> None:
        self.x += (target_x - SCREEN_WIDTH  // 2 - self.x) * 9 * dt
        self.y += (target_y - SCREEN_HEIGHT // 2 - self.y) * 9 * dt
        self.x  = max(0, min(MAP_WIDTH  - SCREEN_WIDTH,  self.x))
        self.y  = max(0, min(MAP_HEIGHT - SCREEN_HEIGHT, self.y))
        if self.shake_timer > 0:
            self.shake_timer -= dt
            si = int(self._shake_intensity)
            self.shake_x = random.randint(-si, si)
            self.shake_y = random.randint(-si, si)
        else:
            self.shake_x = self.shake_y = 0

    @property
    def cx(self) -> float: return self.x + self.shake_x
    @property
    def cy(self) -> float: return self.y + self.shake_y

    def shake(self, intensity: int = SHAKE_INTENSITY,
              duration: float = SHAKE_DURATION) -> None:
        self._shake_intensity = intensity
        self.shake_timer = max(self.shake_timer, duration)


# ─── Wave Manager ─────────────────────────────────────────────────────────────
class WaveManager:
    def __init__(self):
        self.wave   = 0
        self.timer  = 0.0
        self.spawn_queue:  list[dict] = []
        self.spawn_timer   = 0.0
        self.spawned_count = 0
        self.in_break      = False
        self.break_timer   = 0.0
        self._wave_start_time = 0.0   # for wave-clear speed bonus
        self._start_next_wave()

    def _start_next_wave(self) -> None:
        self.wave  += 1
        self.timer  = 0.0
        count = int(WAVE_BASE_ZOMBIES * (WAVE_SCALE ** (self.wave - 1)))
        self._build_spawn_queue(count)
        self.in_break   = False
        self._wave_start_time = 0.0

    def _build_spawn_queue(self, count: int) -> None:
        is_boss = (self.wave % BOSS_WAVE_INTERVAL == 0)
        queue   = []
        if is_boss:
            queue.append({"type": ZOMBIE_BOSS, "delay": 2.5})
        for i in range(count):
            roll = random.random()
            if self.wave <= 2:
                ztype = ZOMBIE_NORMAL
            elif roll < 0.50:
                ztype = ZOMBIE_NORMAL
            elif roll < 0.78:
                ztype = ZOMBIE_FAST
            else:
                ztype = ZOMBIE_TANK
            delay = 0.6 + i * (1.3 / max(1, self.wave ** 0.4))
            queue.append({"type": ztype, "delay": delay})
        self.spawn_queue   = queue
        self.spawn_timer   = 0.0
        self.spawned_count = 0

    def update(self, dt: float, zombies: list, obstacles: list,
               elapsed: float = 0.0):
        """Returns (new_zombies, wave_just_started, in_break, break_ratio, wave_clear_bonus)."""
        self.timer += dt

        if self.in_break:
            self.break_timer -= dt
            if self.break_timer <= 0:
                self._start_next_wave()
                self._wave_start_time = elapsed
                return [], True, False, 0.0, 0
            return [], False, True, self.break_timer / WAVE_BREAK_DURATION, 0

        self.spawn_timer += dt
        new_zombies = []
        while self.spawn_queue and self.spawn_timer >= self.spawn_queue[0]["delay"]:
            entry = self.spawn_queue.pop(0)
            z = self._spawn_zombie(entry["type"], obstacles)
            new_zombies.append(z)
            self.spawned_count += 1

        # All spawned + all dead → wave clear
        live = [z for z in zombies if not z.dying and not z.spawning]
        if not self.spawn_queue and zombies and not live:
            self.in_break    = True
            self.break_timer = WAVE_BREAK_DURATION
            # Speed bonus: faster clear = bigger bonus
            time_taken = elapsed - self._wave_start_time
            speed_bonus = max(0, int(WAVE_CLEAR_BONUS * (1.0 - time_taken / 60.0)))
            return new_zombies, False, True, 1.0, speed_bonus

        return new_zombies, False, False, 0.0, 0

    def _spawn_zombie(self, ztype: dict, obstacles: list) -> Zombie:
        for _ in range(60):
            edge   = random.randint(0, 3)
            margin = TILE_SIZE * 2
            if edge == 0:
                x = random.uniform(margin, MAP_WIDTH - margin); y = margin
            elif edge == 1:
                x = random.uniform(margin, MAP_WIDTH - margin); y = MAP_HEIGHT - margin
            elif edge == 2:
                x = margin; y = random.uniform(margin, MAP_HEIGHT - margin)
            else:
                x = MAP_WIDTH - margin; y = random.uniform(margin, MAP_HEIGHT - margin)
            r    = ztype["radius"]
            test = pygame.Rect(x - r, y - r, r * 2, r * 2)
            if not any(obs.colliderect(test) for obs in obstacles):
                return Zombie(x, y, ztype, self.wave)
        return Zombie(MAP_WIDTH // 2 + random.randint(-300, 300),
                      MAP_HEIGHT // 2 + random.randint(-300, 300),
                      ztype, self.wave)


# ─── Minimap ──────────────────────────────────────────────────────────────────
_MINIMAP_BG: pygame.Surface | None = None

def _build_minimap_bg(obstacles: list) -> pygame.Surface:
    surf = pygame.Surface((MINIMAP_W, MINIMAP_H), pygame.SRCALPHA)
    surf.fill((10, 14, 10, MINIMAP_ALPHA))
    scale_x = MINIMAP_W / MAP_WIDTH
    scale_y = MINIMAP_H / MAP_HEIGHT
    for obs in obstacles:
        mx = int(obs.x      * scale_x)
        my = int(obs.y      * scale_y)
        mw = max(2, int(obs.width  * scale_x))
        mh = max(2, int(obs.height * scale_y))
        pygame.draw.rect(surf, (80, 80, 85, 220), (mx, my, mw, mh))
    pygame.draw.rect(surf, (80, 80, 80, 180), (0, 0, MINIMAP_W, MINIMAP_H), 1)
    return surf

def draw_minimap(surface: pygame.Surface, player, zombies: list,
                 obstacles: list, powerups: list) -> None:
    global _MINIMAP_BG
    if _MINIMAP_BG is None:
        _MINIMAP_BG = _build_minimap_bg(obstacles)

    mx = SCREEN_WIDTH  - MINIMAP_MARGIN - MINIMAP_W
    my = SCREEN_HEIGHT - MINIMAP_MARGIN - MINIMAP_H

    # Blit pre-baked background
    surface.blit(_MINIMAP_BG, (mx, my))

    scale_x = MINIMAP_W / MAP_WIDTH
    scale_y = MINIMAP_H / MAP_HEIGHT

    # Power-ups
    for pu in powerups:
        px = mx + int(pu.x * scale_x)
        py = my + int(pu.y * scale_y)
        color = tuple(min(255, c) for c in pu.data["color"])
        pygame.draw.circle(surface, color, (px, py), 2)

    # Zombies
    for z in zombies:
        if z.dying or z.spawning:
            continue
        zx = mx + int(z.x * scale_x)
        zy = my + int(z.y * scale_y)
        dot_color = z.base_color
        pygame.draw.circle(surface, dot_color, (zx, zy), 2)

    # Player — bright white dot with pulse
    px2 = mx + int(player.x * scale_x)
    py2 = my + int(player.y * scale_y)
    t   = pygame.time.get_ticks() * 0.004
    pulse_r = int(4 + math.sin(t) * 1.5)
    pygame.draw.circle(surface, (60, 160, 255), (px2, py2), pulse_r)
    pygame.draw.circle(surface, WHITE,           (px2, py2), 2)

    # Label
    from bullet import get_font
    font  = get_font("consolas", 10, bold=True)
    label = font.render("MAP", True, (100, 140, 100))
    surface.blit(label, (mx + 3, my + 2))


# ─── Low-HP danger vignette ───────────────────────────────────────────────────
def draw_danger_vignette(surface: pygame.Surface, hp: int, max_hp: int) -> None:
    """Pulsing red edge when HP is low."""
    ratio = hp / max_hp
    if ratio > 0.35:
        return
    intensity = (0.35 - ratio) / 0.35    # 0..1
    pulse     = abs(math.sin(pygame.time.get_ticks() * 0.003))
    alpha     = int(120 * intensity * pulse)
    if alpha < 5:
        return
    s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    for i in range(30):
        ring_alpha = max(0, alpha - i * 3)
        inset = i * 6
        pygame.draw.rect(s, (180, 0, 0, ring_alpha),
                         (inset, inset,
                          SCREEN_WIDTH  - 2 * inset,
                          SCREEN_HEIGHT - 2 * inset), 6)
    surface.blit(s, (0, 0))


# ─── Helpers ──────────────────────────────────────────────────────────────────
def draw_vignette(surface: pygame.Surface) -> None:
    surface.blit(get_vignette(), (0, 0))

def draw_zombie_arrows(surface: pygame.Surface, zombies: list,
                       cam_x: float, cam_y: float) -> None:
    cx, cy = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
    margin = 44
    drawn_angles = []
    for z in zombies:
        if z.dying or z.spawning:
            continue
        sx = z.x - cam_x
        sy = z.y - cam_y
        if -z.radius <= sx <= SCREEN_WIDTH + z.radius and \
           -z.radius <= sy <= SCREEN_HEIGHT + z.radius:
            continue
        dx    = sx - cx
        dy    = sy - cy
        angle = math.atan2(dy, dx)
        if any(abs(angle - a) < 0.18 for a in drawn_angles):
            continue
        drawn_angles.append(angle)
        ex = max(margin, min(SCREEN_WIDTH  - margin,
                             cx + math.cos(angle) * (cx - margin)))
        ey = max(margin, min(SCREEN_HEIGHT - margin,
                             cy + math.sin(angle) * (cy - margin)))
        tip   = (int(ex), int(ey))
        left  = (int(ex - math.cos(angle - 2.5) * 12),
                 int(ey - math.sin(angle - 2.5) * 12))
        right = (int(ex - math.cos(angle + 2.5) * 12),
                 int(ey - math.sin(angle + 2.5) * 12))
        pygame.draw.polygon(surface, z.base_color, [tip, left, right])
        pygame.draw.polygon(surface, WHITE, [tip, left, right], 1)


# ─── Score / Highscore ────────────────────────────────────────────────────────
SCORE_FILE = "highscore.dat"

def load_high_score() -> int:
    try:
        with open(SCORE_FILE, "r") as f:
            return int(f.read().strip())
    except Exception:
        return 0

def save_high_score(score: int) -> None:
    try:
        with open(SCORE_FILE, "w") as f:
            f.write(str(score))
    except Exception:
        pass
