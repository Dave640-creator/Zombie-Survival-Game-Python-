# player.py — Player with dual weapons

import pygame
import math
import random
from settings import *
from bullet import Bullet, Grenade, ParticleSystem, get_font


class Weapon:
    """Encapsulates weapon stats and state."""
    PISTOL   = "pistol"
    SHOTGUN  = "shotgun"

    def __init__(self, kind: str):
        self.kind = kind
        if kind == self.PISTOL:
            self.mag_size     = MAG_SIZE
            self.mags_left    = MAX_MAGS
            self.bullets_in_mag = MAG_SIZE
            self.reload_time  = RELOAD_TIME
            self.shoot_delay  = 0.18
            self.damage       = BULLET_DAMAGE
            self.color        = BULLET_COLOR
            self.name         = "PISTOL"
            self.color_accent = (60, 180, 255)
        else:  # shotgun
            self.mag_size     = SHOTGUN_MAG_SIZE
            self.mags_left    = SHOTGUN_MAGS
            self.bullets_in_mag = SHOTGUN_MAG_SIZE
            self.reload_time  = SHOTGUN_RELOAD_TIME
            self.shoot_delay  = SHOTGUN_DELAY
            self.damage       = SHOTGUN_DAMAGE
            self.color        = (255, 160, 60)
            self.name         = "SHOTGUN"
            self.color_accent = (255, 140, 0)

        self.reloading      = False
        self.reload_timer   = 0.0
        self.shoot_cooldown = 0.0

    def update(self, dt: float) -> None:
        self.shoot_cooldown = max(0.0, self.shoot_cooldown - dt)
        if self.reloading:
            self.reload_timer -= dt
            if self.reload_timer <= 0:
                self.mags_left -= 1
                self.bullets_in_mag = self.mag_size
                self.reloading = False

    def start_reload(self) -> None:
        if self.mags_left <= 0 or self.reloading:
            return
        self.reloading    = True
        self.reload_timer = self.reload_time

    def can_shoot(self) -> bool:
        return (not self.reloading and
                self.bullets_in_mag > 0 and
                self.shoot_cooldown <= 0)

    @property
    def reload_progress(self) -> float:
        if not self.reloading:
            return 1.0
        return 1.0 - self.reload_timer / self.reload_time


class Player:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.radius = PLAYER_RADIUS
        self.hp     = PLAYER_MAX_HP
        self.max_hp = PLAYER_MAX_HP

        # Weapons
        self.weapons      = [Weapon(Weapon.PISTOL), Weapon(Weapon.SHOTGUN)]
        self.weapon_index = 0

        # Grenades
        self.grenades         = GRENADE_COUNT
        self.grenade_cooldown = 0.0

        # Combat state
        self.facing_angle = 0.0
        self.alive        = True

        # Visual timers
        self.hurt_flash       = 0.0
        self.invincible_timer = 0.0
        self.bob_timer        = 0.0
        self._last_pos        = (x, y)
        self._step_timer      = 0.0   # footstep dust interval

        # Power-ups
        self.speed_boost_timer = 0.0
        self.current_speed     = PLAYER_SPEED

    # ── Convenience properties ────────────────────────────────────────────────
    @property
    def weapon(self) -> Weapon:
        return self.weapons[self.weapon_index]

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(self.x - self.radius, self.y - self.radius,
                           self.radius * 2, self.radius * 2)

    @property
    def bullets_in_mag(self):  return self.weapon.bullets_in_mag
    @property
    def mags_left(self):       return self.weapon.mags_left
    @property
    def reloading(self):       return self.weapon.reloading
    @property
    def reload_progress(self): return self.weapon.reload_progress

    # ── Input / update ────────────────────────────────────────────────────────
    def handle_input(self, keys, dt: float, obstacles: list) -> bool:
        dx = dy = 0
        if keys[pygame.K_w] or keys[pygame.K_UP]:    dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:  dy += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:  dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx += 1

        moving = bool(dx or dy)
        spd = self.current_speed
        if dx and dy:
            spd *= 0.707

        nx = self.x + dx * spd * dt
        tr = pygame.Rect(nx - self.radius, self.y - self.radius,
                         self.radius * 2, self.radius * 2)
        if not any(obs.colliderect(tr) for obs in obstacles):
            self.x = nx

        ny = self.y + dy * spd * dt
        tr = pygame.Rect(self.x - self.radius, ny - self.radius,
                         self.radius * 2, self.radius * 2)
        if not any(obs.colliderect(tr) for obs in obstacles):
            self.y = ny

        self.x = max(self.radius + TILE_SIZE,
                     min(MAP_WIDTH  - self.radius - TILE_SIZE, self.x))
        self.y = max(self.radius + TILE_SIZE,
                     min(MAP_HEIGHT - self.radius - TILE_SIZE, self.y))

        if moving:
            self.bob_timer   += dt * 8
            self._step_timer -= dt

        self._last_pos = (self.x, self.y)
        return moving

    def update_aim(self, mouse_pos: tuple, cam_x: float, cam_y: float) -> None:
        wx = mouse_pos[0] + cam_x
        wy = mouse_pos[1] + cam_y
        self.facing_angle = math.atan2(wy - self.y, wx - self.x)

    def switch_weapon(self, keys) -> bool:
        """Returns True if weapon was switched."""
        if keys[pygame.K_1] and self.weapon_index != 0:
            self.weapon_index = 0
            return True
        if keys[pygame.K_2] and self.weapon_index != 1:
            self.weapon_index = 1
            return True
        return False

    def try_shoot(self, mouse_buttons, particles: ParticleSystem) -> list:
        """Returns a list of Bullet objects fired this frame."""
        if not mouse_buttons[0]:
            return []
        w = self.weapon
        if not w.can_shoot():
            if w.bullets_in_mag <= 0 and not w.reloading:
                w.start_reload()
            return []

        w.shoot_cooldown = w.shoot_delay
        w.bullets_in_mag -= 1

        mx = self.x + math.cos(self.facing_angle) * (self.radius + 10)
        my = self.y + math.sin(self.facing_angle) * (self.radius + 10)

        if w.kind == Weapon.PISTOL:
            particles.emit_muzzle(mx, my, self.facing_angle)
            return [Bullet(mx, my, self.facing_angle,
                           damage=w.damage, color=w.color)]
        else:  # shotgun
            particles.emit_shotgun_muzzle(mx, my, self.facing_angle)
            pellets = []
            for i in range(SHOTGUN_PELLETS):
                spread = random.uniform(-SHOTGUN_SPREAD, SHOTGUN_SPREAD)
                pellets.append(Bullet(mx, my, self.facing_angle + spread,
                                      speed=BULLET_SPEED * 0.9,
                                      damage=w.damage, color=w.color,
                                      radius=4))
            return pellets

    def try_reload(self, keys) -> None:
        if keys[pygame.K_r] and not self.weapon.reloading:
            self.weapon.start_reload()

    def try_throw_grenade(self, keys, mouse_pos: tuple,
                          cam_x: float, cam_y: float) -> "Grenade | None":
        if not keys[pygame.K_f]:
            return None
        if self.grenades <= 0 or self.grenade_cooldown > 0:
            return None
        self.grenades -= 1
        self.grenade_cooldown = GRENADE_COOLDOWN
        wx = mouse_pos[0] + cam_x
        wy = mouse_pos[1] + cam_y
        angle = math.atan2(wy - self.y, wx - self.x)
        return Grenade(self.x, self.y, angle)

    def update(self, dt: float, moving: bool, particles: ParticleSystem) -> None:
        self.hurt_flash       = max(0.0, self.hurt_flash - dt)
        self.invincible_timer = max(0.0, self.invincible_timer - dt)
        self.grenade_cooldown = max(0.0, self.grenade_cooldown - dt)

        if self.speed_boost_timer > 0:
            self.speed_boost_timer -= dt
            self.current_speed = PLAYER_SPEED * 1.7
        else:
            self.current_speed = PLAYER_SPEED

        for w in self.weapons:
            w.update(dt)

        # Footstep dust
        if moving and self._step_timer <= 0:
            self._step_timer = 0.18
            particles.emit_dust(self.x, self.y)

    def take_damage(self, amount: int) -> None:
        if self.invincible_timer > 0:
            return
        self.hp -= amount
        self.hurt_flash       = 0.25
        self.invincible_timer = 0.4
        if self.hp <= 0:
            self.hp    = 0
            self.alive = False

    def add_health(self, amount: int) -> None:
        self.hp = min(self.max_hp, self.hp + amount)

    def add_ammo(self) -> None:
        self.weapons[0].mags_left = min(MAX_MAGS + 3, self.weapons[0].mags_left + 2)
        self.weapons[1].mags_left = min(SHOTGUN_MAGS + 3, self.weapons[1].mags_left + 1)

    def add_speed_boost(self, duration: float = 5.0) -> None:
        self.speed_boost_timer = duration

    def add_grenade(self, count: int = 1) -> None:
        self.grenades = min(9, self.grenades + count)

    # ── Draw ──────────────────────────────────────────────────────────────────
    def draw(self, surface: pygame.Surface, cam_x: float, cam_y: float,
             moving: bool = False) -> None:
        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)
        bob_y = int(math.sin(self.bob_timer) * 2) if moving else 0
        r = self.radius
        fa = self.facing_angle
        cy = sy + bob_y

        # Soft shadow
        shadow = pygame.Surface((r * 3, r * 2), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 90), shadow.get_rect())
        surface.blit(shadow, (sx - r * 1.5, sy + r - 6 + bob_y))

        # Speed aura / hurt glow / invincibility flicker (unrotated, behind body)
        if self.speed_boost_timer > 0:
            pulse = abs(math.sin(self.bob_timer * 2)) * 4
            pygame.draw.circle(surface, (60, 255, 200), (sx, cy), int(r + 9 + pulse), 2)
        if self.hurt_flash > 0:
            pygame.draw.circle(surface, (255, 60, 60), (sx, cy), r + 6)
        elif self.invincible_timer > 0 and int(self.invincible_timer * 20) % 2 == 0:
            pygame.draw.circle(surface, (255, 255, 255), (sx, cy), r + 3, 2)

        skin       = (222, 186, 150)
        pants_col  = (45, 50, 42)
        vest_color = PLAYER_COLOR if self.hurt_flash <= 0 else (255, 130, 130)
        vest_dark  = (20, 60, 100) if self.hurt_flash <= 0 else (170, 60, 60)
        is_shotgun = self.weapon.kind == Weapon.SHOTGUN
        accent     = self.weapon.color_accent

        def capsule(surf, p1, p2, width, color):
            pygame.draw.line(surf, color, p1, p2, width)
            pygame.draw.circle(surf, color, (int(p1[0]), int(p1[1])), width // 2)
            pygame.draw.circle(surf, color, (int(p2[0]), int(p2[1])), width // 2)

        # ── Build the character facing local +x, then rotate as a rigid sprite ──
        pad  = r + 22
        size = r * 2 + pad * 2
        char = pygame.Surface((size, size), pygame.SRCALPHA)
        cx = cyl = size // 2

        # Legs — stride fore/aft along the movement axis (proper walk cycle)
        leg_w = max(5, int(r * 0.42))
        for side, phase in ((1, 0.0), (-1, math.pi)):
            swing = math.sin(self.bob_timer * 2 + phase) * (r * 0.55 if moving else 0.0)
            hip  = (cx - r * 0.15, cyl + side * r * 0.32)
            foot = (cx - r * 0.15 + swing, cyl + side * r * 0.32)
            capsule(char, hip, foot, leg_w, pants_col)
            pygame.draw.circle(char, (25, 25, 25), (int(foot[0]), int(foot[1])), max(3, int(r * 0.22)))

        # Backpack
        pygame.draw.circle(char, (30, 80, 55), (int(cx - r * 0.85), cyl), max(6, int(r * 0.42)))

        # Torso — rounded block (armored vest), clearly human proportioned
        torso_w, torso_h = int(r * 1.5), int(r * 1.7)
        torso = pygame.Rect(0, 0, torso_w, torso_h)
        torso.center = (int(cx - r * 0.05), cyl)
        pygame.draw.rect(char, (12, 35, 55), torso.inflate(6, 6), border_radius=torso_h // 2)
        pygame.draw.rect(char, vest_color, torso, border_radius=torso_h // 2)
        pygame.draw.rect(char, (30, 100, 180), torso.inflate(-10, -10), border_radius=torso_h // 3)
        pygame.draw.line(char, vest_dark, torso.midtop, torso.midbottom, 2)
        pygame.draw.rect(char, WHITE, torso, 2, border_radius=torso_h // 2)

        # Shoulders
        for side in (1, -1):
            shx, shy = cx + r * 0.15, cyl + side * r * 0.72
            pygame.draw.circle(char, (10, 30, 55), (int(shx), int(shy)), max(4, int(r * 0.28)))
            pygame.draw.circle(char, (50, 130, 210), (int(shx), int(shy)), max(4, int(r * 0.28)), 1)

        # Arms — shoulder → elbow → hand, both gripping the rifle
        grip_x, grip_y = cx + r * 1.05, cyl
        for side in (1, -1):
            shoulder = (cx + r * 0.15, cyl + side * r * 0.65)
            elbow    = (cx + r * 0.65, cyl + side * r * 0.35)
            hand     = (grip_x - (0 if side == 1 else r * 0.45), grip_y)
            capsule(char, shoulder, elbow, max(4, int(r * 0.3)), skin)
            capsule(char, elbow, hand, max(4, int(r * 0.26)), skin)

        # Weapon — visible stock, receiver and long barrel, both hands on it
        stock_x = grip_x - r * 0.55
        barrel_len = r * (2.3 if is_shotgun else 2.0)
        muzzle_x = grip_x + barrel_len
        pygame.draw.line(char, (40, 30, 20), (stock_x, grip_y), (grip_x - r * 0.1, grip_y), 7)   # stock
        pygame.draw.rect(char, DARK_GRAY, (int(grip_x - r * 0.15), int(grip_y - 6), int(r * 0.3), 12))  # receiver
        barrel_w = 8 if is_shotgun else 6
        pygame.draw.line(char, DARK_GRAY, (grip_x, grip_y), (muzzle_x, grip_y), barrel_w + 3)
        pygame.draw.line(char, LIGHT_GRAY, (grip_x, grip_y), (muzzle_x, grip_y), barrel_w)
        pygame.draw.line(char, accent, (grip_x, grip_y), (muzzle_x, grip_y), 2)
        pygame.draw.circle(char, DARK_GRAY, (int(muzzle_x), int(grip_y)), barrel_w // 2 + 2)
        if is_shotgun:
            pygame.draw.circle(char, (90, 60, 20), (int(grip_x + barrel_len * 0.4), int(grip_y)), 4)
        pygame.draw.circle(char, skin, (int(grip_x - r * 0.15), grip_y), max(3, int(r * 0.22)))  # front hand
        pygame.draw.circle(char, skin, (int(grip_x - r * 0.5), grip_y), max(3, int(r * 0.2)))    # rear hand

        # Head — clearly human, in front, with helmet + visor
        head_r = max(8, int(r * 0.6))
        head_c = (int(cx + r * 0.95), cyl)
        pygame.draw.circle(char, (10, 30, 55), head_c, head_r + 2)
        pygame.draw.circle(char, skin, head_c, head_r)
        helmet_rect = pygame.Rect(0, 0, head_r * 2 + 2, int(head_r * 1.6))
        helmet_rect.center = (head_c[0] - int(head_r * 0.15), head_c[1])
        pygame.draw.ellipse(char, (35, 55, 78), helmet_rect)
        pygame.draw.circle(char, (150, 220, 255), (head_c[0] + int(head_r * 0.55), head_c[1]),
                           max(2, int(head_r * 0.38)))
        pygame.draw.circle(char, WHITE, head_c, head_r, 1)

        rotated = pygame.transform.rotate(char, -math.degrees(fa))
        rect = rotated.get_rect(center=(sx, cy))
        surface.blit(rotated, rect)

    def draw_crosshair(self, surface: pygame.Surface, mouse_pos: tuple) -> None:
        mx, my = mouse_pos
        w = self.weapon
        if w.kind == Weapon.SHOTGUN:
            # Larger spread indicator for shotgun
            size, gap = 18, 7
            spread_r = 22
            color = (255, 140, 0) if self.hurt_flash <= 0 else (255, 80, 80)
            pygame.draw.circle(surface, color, (mx, my), spread_r, 1)
        else:
            size, gap = 14, 5
            color = (255, 255, 255) if self.hurt_flash <= 0 else (255, 80, 80)

        thick = 2
        pygame.draw.line(surface, color, (mx - size, my), (mx - gap, my), thick)
        pygame.draw.line(surface, color, (mx + gap,  my), (mx + size, my), thick)
        pygame.draw.line(surface, color, (mx, my - size), (mx, my - gap), thick)
        pygame.draw.line(surface, color, (mx, my + gap),  (mx, my + size), thick)
        pygame.draw.circle(surface, color, (mx, my), 2)
