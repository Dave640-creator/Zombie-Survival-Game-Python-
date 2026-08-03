# bullet.py — Bullet, Grenade, DamageNumber, Decal & Particle system

import pygame
import math
import random
from settings import *

# ─── Font cache ───────────────────────────────────────────────────────────────
_FONT_CACHE: dict = {}

def get_font(name: str, size: int, bold: bool = False) -> pygame.font.Font:
    key = (name, size, bold)
    if key not in _FONT_CACHE:
        _FONT_CACHE[key] = pygame.font.SysFont(name, size, bold=bold)
    return _FONT_CACHE[key]
def _cc(*args):
    """Clamp color values to valid 0-255 range."""
    if len(args) == 1:
        return tuple(max(0, min(255, int(c))) for c in args[0])
    return tuple(max(0, min(255, int(c))) for c in args)



# ─── Bullet ───────────────────────────────────────────────────────────────────
class Bullet:
    def __init__(self, x: float, y: float, angle: float,
                 speed: float = BULLET_SPEED, damage: int = BULLET_DAMAGE,
                 color: tuple = BULLET_COLOR, radius: int = BULLET_RADIUS):
        self.x = x
        self.y = y
        self.angle = angle
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.lifetime = BULLET_LIFETIME
        self.alive = True
        self.radius = radius
        self.damage = damage
        self.color = color
        self.trail: list[tuple] = []

    def update(self, dt: float, obstacles: list) -> None:
        self.trail.append((self.x, self.y))
        if len(self.trail) > 7:
            self.trail.pop(0)

        self.x += self.vx * dt
        self.y += self.vy * dt
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.alive = False
            return

        rect = pygame.Rect(self.x - self.radius, self.y - self.radius,
                           self.radius * 2, self.radius * 2)
        for obs in obstacles:
            if obs.colliderect(rect):
                self.alive = False
                return

        if not (0 <= self.x <= MAP_WIDTH and 0 <= self.y <= MAP_HEIGHT):
            self.alive = False

    def draw(self, surface: pygame.Surface, cam_x: float, cam_y: float) -> None:
        for i, (tx, ty) in enumerate(self.trail):
            ratio = i / max(1, len(self.trail))
            r = max(1, self.radius - 2)
            c = self.color
            faded = (max(0,min(255,int(c[0]*ratio))), max(0,min(255,int(c[1]*ratio*0.7))), max(0,min(255,int(c[2]*ratio*0.3))))
            sx, sy = int(tx - cam_x), int(ty - cam_y)
            if 0 <= sx <= SCREEN_WIDTH and 0 <= sy <= SCREEN_HEIGHT:
                pygame.draw.circle(surface, faded, (sx, sy), r)

        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)
        pygame.draw.circle(surface, tuple(min(255, c + 80) for c in self.color),
                           (sx, sy), self.radius + 2)
        pygame.draw.circle(surface, self.color, (sx, sy), self.radius)


# ─── Grenade ──────────────────────────────────────────────────────────────────
class Grenade:
    def __init__(self, x: float, y: float, angle: float):
        self.x = x
        self.y = y
        self.vx = math.cos(angle) * GRENADE_THROW_SPEED
        self.vy = math.sin(angle) * GRENADE_THROW_SPEED
        self.fuse = GRENADE_FUSE
        self.alive = True
        self.exploded = False
        self.radius = 8
        self.pulse = 0.0
        self.friction = 0.92

    def update(self, dt: float, obstacles: list) -> bool:
        if self.exploded:
            return False
        self.pulse += dt * 10
        self.fuse -= dt

        nx = self.x + self.vx * dt
        ny = self.y + self.vy * dt

        tr = pygame.Rect(nx - self.radius, self.y - self.radius,
                         self.radius * 2, self.radius * 2)
        if any(obs.colliderect(tr) for obs in obstacles):
            self.vx *= -0.5
            nx = self.x
        tr2 = pygame.Rect(self.x - self.radius, ny - self.radius,
                          self.radius * 2, self.radius * 2)
        if any(obs.colliderect(tr2) for obs in obstacles):
            self.vy *= -0.5
            ny = self.y

        self.x = max(TILE_SIZE, min(MAP_WIDTH  - TILE_SIZE, nx))
        self.y = max(TILE_SIZE, min(MAP_HEIGHT - TILE_SIZE, ny))
        self.vx *= self.friction ** (dt * 60)
        self.vy *= self.friction ** (dt * 60)

        if self.fuse <= 0:
            self.exploded = True
            self.alive = False
            return True
        return False

    def draw(self, surface: pygame.Surface, cam_x: float, cam_y: float) -> None:
        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)
        blink_rate = 1.0 + (1.0 - max(0, self.fuse / GRENADE_FUSE)) * 8
        blink = math.sin(self.pulse * blink_rate) > 0
        color = (255, 80, 0) if blink else (180, 50, 0)
        pygame.draw.circle(surface, (0, 0, 0), (sx + 2, sy + 2), self.radius)
        pygame.draw.circle(surface, color, (sx, sy), self.radius)
        pygame.draw.circle(surface, (255, 200, 80) if blink else (200, 120, 40),
                           (sx, sy), self.radius, 2)
        pygame.draw.line(surface, LIGHT_GRAY,
                         (sx, sy - self.radius), (sx + 4, sy - self.radius - 4), 2)
        ratio = max(0, self.fuse / GRENADE_FUSE)
        if ratio > 0:
            arc_rect = pygame.Rect(sx - 14, sy - 14, 28, 28)
            try:
                pygame.draw.arc(surface, YELLOW, arc_rect, 0, ratio * math.tau, 3)
            except Exception:
                pass


# ─── Floating Damage Number ───────────────────────────────────────────────────
class DamageNumber:
    """Floats upward from a zombie showing damage dealt."""
    def __init__(self, x: float, y: float, amount: int, critical: bool = False):
        self.x = x + random.uniform(-12, 12)
        self.y = y - 10
        self.amount = amount
        self.critical = critical
        self.lifetime = DMG_NUM_LIFETIME
        self.max_lifetime = DMG_NUM_LIFETIME
        self.alive = True
        self.vx = random.uniform(-15, 15)

    def update(self, dt: float) -> None:
        self.y -= DMG_NUM_RISE * dt
        self.x += self.vx * dt
        self.vx *= 0.92
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.alive = False

    def draw(self, surface: pygame.Surface, cam_x: float, cam_y: float) -> None:
        ratio = self.lifetime / self.max_lifetime
        alpha = int(255 * min(1.0, ratio * 2))
        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)
        if not (-20 <= sx <= SCREEN_WIDTH + 20 and -20 <= sy <= SCREEN_HEIGHT + 20):
            return

        if self.critical:
            size = 22
            color = (255, max(0, min(255, int(220 * ratio))), 0)
            text = f"CRIT {self.amount}!"
        else:
            size = 16
            color = (255, max(0, min(255, int(160 * ratio))), max(0, min(255, int(60 * ratio))))
            text = str(self.amount)

        font = get_font("impact", size)
        # Shadow
        shadow = font.render(text, True, (0, 0, 0))
        surface.blit(shadow, (sx - shadow.get_width() // 2 + 2,
                              sy - shadow.get_height() // 2 + 2))
        label = font.render(text, True, color)
        surface.blit(label, (sx - label.get_width() // 2,
                             sy - label.get_height() // 2))


# ─── Particle ─────────────────────────────────────────────────────────────────
class Particle:
    __slots__ = ('x','y','vx','vy','color','lifetime','max_lifetime',
                 'radius','gravity','alive')

    def __init__(self, x, y, color, vx, vy, lifetime, radius=4, gravity=0):
        self.x = x; self.y = y
        self.color = color
        self.vx = vx; self.vy = vy
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.radius = radius
        self.gravity = gravity
        self.alive = True

    def update(self, dt: float) -> None:
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += self.gravity * dt
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.alive = False

    def draw(self, surface: pygame.Surface, cam_x: float, cam_y: float) -> None:
        ratio = max(0.0, self.lifetime / self.max_lifetime)
        r = max(1, int(self.radius * ratio))
        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)
        if -10 <= sx <= SCREEN_WIDTH + 10 and -10 <= sy <= SCREEN_HEIGHT + 10:
            color = tuple(max(0, min(255, int(c * ratio))) for c in self.color)
            pygame.draw.circle(surface, color, (sx, sy), r)


# ─── Blood Decal ──────────────────────────────────────────────────────────────
class BloodDecal:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.lifetime = DECAL_LIFETIME
        self.max_lifetime = DECAL_LIFETIME
        self.radius = random.randint(10, 24)
        self.alive = True
        self.satellites = [
            (random.randint(-24, 24), random.randint(-24, 24), random.randint(3, 10))
            for _ in range(random.randint(2, 6))
        ]

    def update(self, dt: float) -> None:
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.alive = False

    def draw(self, surface: pygame.Surface, cam_x: float, cam_y: float) -> None:
        ratio = min(1.0, self.lifetime / (self.max_lifetime * 0.15))
        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)
        if sx < -60 or sx > SCREEN_WIDTH + 60 or sy < -60 or sy > SCREEN_HEIGHT + 60:
            return
        dark = (int(70 * ratio), 0, 0)
        pygame.draw.circle(surface, dark, (sx, sy), self.radius)
        for ox, oy, r in self.satellites:
            pygame.draw.circle(surface, dark, (sx + ox, sy + oy), r)


# ─── Particle System ──────────────────────────────────────────────────────────
class ParticleSystem:
    def __init__(self):
        self.particles: list[Particle] = []
        self.decals: list[BloodDecal]  = []
        self.dmg_numbers: list[DamageNumber] = []
        # Explosion flash state
        self.flash_timer = 0.0
        self.flash_color = (255, 255, 255)

    def emit_blood(self, x: float, y: float, count: int = 12) -> None:
        if len(self.decals) < MAX_DECALS:
            self.decals.append(BloodDecal(x, y))
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(60, 260)
            lt    = random.uniform(0.3, 0.9)
            shade = random.randint(100, 180)
            self.particles.append(Particle(
                x, y, (shade, 0, 0),
                math.cos(angle) * speed, math.sin(angle) * speed,
                lt, random.randint(3, 8), gravity=200))

    def emit_explosion(self, x: float, y: float) -> None:
        self.flash_timer = 0.12
        self.flash_color = (255, 220, 120)
        for _ in range(70):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(80, 520)
            lt    = random.uniform(0.3, 1.3)
            color = random.choice([
                (255, 160, 20), (255, 80, 20),
                (255, 240, 80), (200, 200, 200)])
            self.particles.append(Particle(
                x, y, color,
                math.cos(angle) * speed, math.sin(angle) * speed,
                lt, random.randint(4, 14), gravity=80))
        for _ in range(24):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(20, 130)
            lt    = random.uniform(0.8, 2.2)
            shade = random.randint(70, 140)
            self.particles.append(Particle(
                x, y, (shade, shade, shade),
                math.cos(angle) * speed, math.sin(angle) * speed,
                lt, random.randint(8, 20), gravity=-12))

    def emit_muzzle(self, x: float, y: float, angle: float) -> None:
        for _ in range(10):
            spread = random.uniform(-0.6, 0.6)
            speed  = random.uniform(60, 220)
            lt     = random.uniform(0.04, 0.14)
            color  = random.choice([(255, 255, 160), (255, 200, 60), (255, 120, 30)])
            self.particles.append(Particle(
                x, y, color,
                math.cos(angle + spread) * speed,
                math.sin(angle + spread) * speed,
                lt, random.randint(3, 7)))

    def emit_shotgun_muzzle(self, x: float, y: float, angle: float) -> None:
        for _ in range(20):
            spread = random.uniform(-SHOTGUN_SPREAD * 1.2, SHOTGUN_SPREAD * 1.2)
            speed  = random.uniform(80, 280)
            lt     = random.uniform(0.06, 0.18)
            color  = random.choice([(255, 200, 80), (255, 140, 30), (255, 80, 20)])
            self.particles.append(Particle(
                x, y, color,
                math.cos(angle + spread) * speed,
                math.sin(angle + spread) * speed,
                lt, random.randint(4, 9)))

    def emit_powerup(self, x: float, y: float, color: tuple, count: int = 14) -> None:
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(40, 140)
            lt    = random.uniform(0.4, 1.1)
            self.particles.append(Particle(
                x, y, color,
                math.cos(angle) * speed, math.sin(angle) * speed,
                lt, random.randint(4, 9)))

    def emit_hit_spark(self, x: float, y: float) -> None:
        for _ in range(5):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(80, 180)
            lt    = random.uniform(0.05, 0.15)
            self.particles.append(Particle(
                x, y, (255, 240, 120),
                math.cos(angle) * speed, math.sin(angle) * speed,
                lt, random.randint(2, 4)))

    def emit_dust(self, x: float, y: float) -> None:
        """Footstep dust puff while running."""
        for _ in range(2):
            angle = random.uniform(math.pi * 0.6, math.pi * 1.4)
            speed = random.uniform(15, 45)
            lt    = random.uniform(0.15, 0.35)
            shade = random.randint(30, 55)
            self.particles.append(Particle(
                x, y, (shade, shade + 4, shade),
                math.cos(angle) * speed, math.sin(angle) * speed,
                lt, random.randint(4, 8), gravity=-20))

    def emit_spawn_rise(self, x: float, y: float, color: tuple) -> None:
        """Visual effect when a zombie spawns (rising from ground)."""
        for _ in range(18):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(20, 80)
            lt    = random.uniform(0.4, 0.9)
            self.particles.append(Particle(
                x, y, color,
                math.cos(angle) * speed * 0.5,
                math.sin(angle) * speed - 60,   # mostly upward
                lt, random.randint(5, 12), gravity=40))

    def add_damage_number(self, x: float, y: float,
                          amount: int, critical: bool = False) -> None:
        self.dmg_numbers.append(DamageNumber(x, y, amount, critical))

    def update(self, dt: float) -> None:
        self.flash_timer = max(0.0, self.flash_timer - dt)
        self.particles    = [p for p in self.particles if p.alive]
        self.decals       = [d for d in self.decals if d.alive]
        self.dmg_numbers  = [n for n in self.dmg_numbers if n.alive]
        for p in self.particles:
            p.update(dt)
        for d in self.decals:
            d.update(dt)
        for n in self.dmg_numbers:
            n.update(dt)

    def draw_decals(self, surface, cam_x, cam_y) -> None:
        for d in self.decals:
            d.draw(surface, cam_x, cam_y)

    def draw(self, surface, cam_x, cam_y) -> None:
        for p in self.particles:
            p.draw(surface, cam_x, cam_y)
        for n in self.dmg_numbers:
            n.draw(surface, cam_x, cam_y)

    def draw_flash(self, surface: pygame.Surface) -> None:
        if self.flash_timer <= 0:
            return
        alpha = int(160 * self.flash_timer / 0.12)
        s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        s.fill((*self.flash_color, min(180, alpha)))
        surface.blit(s, (0, 0))