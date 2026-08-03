# zombie.py — Zombie AI with lunge, spawn effect, floating numbers

import pygame
import math
import random
from settings import *
from bullet import get_font


class Zombie:
    def __init__(self, x: float, y: float, ztype: dict, wave: int = 1):
        self.x = x
        self.y = y
        self.ztype      = ztype
        self.name       = ztype["name"]
        self.radius     = ztype["radius"]
        self.can_lunge  = ztype.get("lunge", False)

        wave_scale  = 1.0 + (wave - 1) * 0.08
        self.max_hp = int(ztype["hp"] * wave_scale)
        self.hp     = self.max_hp
        self.speed  = ztype["speed"] * (1.0 + (wave - 1) * 0.04)
        self.base_color   = ztype["color"]
        self.score_value  = ztype["score"]
        self.damage       = ztype["damage"]
        self.attack_range = ztype["attack_range"] + self.radius
        self.attack_rate  = ztype["attack_rate"]

        # State
        self.alive     = True
        self.dying     = False
        self.die_timer = 0.0
        self.die_duration = 0.55

        # Spawn-rise effect (zombies "emerge from ground")
        self.spawn_timer    = 0.5        # seconds of spawn animation
        self.spawning       = True

        self.attack_timer   = 0.0
        self.hit_flash      = 0.0

        # Lunge state
        self.lunge_timer    = 0.0        # cooldown between lunges
        self.lunge_cd       = random.uniform(3.0, 6.0)
        self.lunging        = False
        self.lunge_vx       = 0.0
        self.lunge_vy       = 0.0
        self.lunge_duration = 0.22

        # Wander
        self.wander_angle = random.uniform(0, math.tau)
        self.wander_timer = random.uniform(0, 1.5)

        # Separation
        self.sep_vx = 0.0
        self.sep_vy = 0.0

        # Facing direction (used for eyes/mouth/arms orientation)
        self.facing_angle = random.uniform(0, math.tau)
        self.walk_timer = random.uniform(0, 6.0)

        # Per-instance body silhouette — ragged, non-circular flesh
        self._jag_n = 10
        self.body_jags = [random.uniform(0.8, 1.18) for _ in range(self._jag_n)]
        self.wounds = [(random.uniform(0.3, math.tau), random.uniform(0.35, 0.75),
                        random.uniform(2, 4)) for _ in range(random.randint(2, 4))]
        self.limp_phase = random.uniform(0, math.tau)

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(self.x - self.radius, self.y - self.radius,
                           self.radius * 2, self.radius * 2)

    def update(self, dt: float, player, obstacles: list) -> bool:
        """Returns True if player was attacked this frame."""
        # Spawn animation — zombie just visible, can't act
        if self.spawning:
            self.spawn_timer -= dt
            if self.spawn_timer <= 0:
                self.spawning = False
            return False

        if self.dying:
            self.die_timer += dt
            if self.die_timer >= self.die_duration:
                self.alive = False
            return False

        self.hit_flash    = max(0.0, self.hit_flash - dt)
        self.attack_timer -= dt

        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy)

        dealt_damage = False

        # ── Lunge logic (Fast zombie) ──
        if self.lunging:
            self.lunge_timer -= dt
            nx = self.x + self.lunge_vx * dt
            ny = self.y + self.lunge_vy * dt
            tr = pygame.Rect(nx - self.radius, self.y - self.radius,
                             self.radius * 2, self.radius * 2)
            if not any(obs.colliderect(tr) for obs in obstacles):
                self.x = nx
            tr2 = pygame.Rect(self.x - self.radius, ny - self.radius,
                              self.radius * 2, self.radius * 2)
            if not any(obs.colliderect(tr2) for obs in obstacles):
                self.y = ny
            if self.lunge_timer <= 0:
                self.lunging = False
                self.lunge_timer = self.lunge_cd
            # Check if lunge hit player
            if math.hypot(self.lunge_vx, self.lunge_vy) > 0:
                self.facing_angle = math.atan2(self.lunge_vy, self.lunge_vx)
            if math.hypot(self.x - player.x, self.y - player.y) < self.attack_range:
                if self.attack_timer <= 0:
                    self.attack_timer = self.attack_rate
                    player.take_damage(int(self.damage * 1.5))  # lunge does more damage
                    dealt_damage = True
            return dealt_damage

        # ── Attack ──
        if dist < self.attack_range:
            if dist > 0:
                self.facing_angle = math.atan2(dy, dx)
            if self.attack_timer <= 0:
                self.attack_timer = self.attack_rate
                player.take_damage(self.damage)
                dealt_damage = True
        else:
            # ── Lunge initiation ──
            if self.can_lunge and dist < 200 and not self.lunging:
                self.lunge_timer -= dt
                if self.lunge_timer <= 0:
                    # Launch lunge
                    self.lunging  = True
                    self.lunge_timer = self.lunge_duration
                    speed = self.speed * 4.5
                    if dist > 0:
                        self.lunge_vx = (dx / dist) * speed
                        self.lunge_vy = (dy / dist) * speed

            # ── Normal movement ──
            self.wander_timer -= dt
            if self.wander_timer <= 0:
                self.wander_timer = random.uniform(0.8, 2.2)
                self.wander_angle = random.uniform(-0.5, 0.5)

            if dist > 0:
                nx_d = dx / dist
                ny_d = dy / dist
                wx = math.cos(self.wander_angle) * 0.18
                wy = math.sin(self.wander_angle) * 0.18
                mx = nx_d + wx + self.sep_vx
                my = ny_d + wy + self.sep_vy
                mag = math.hypot(mx, my)
                if mag:
                    mx /= mag
                    my /= mag
                    self.facing_angle = math.atan2(my, mx)

                self.walk_timer += dt * (3 + self.speed * 0.015)
                new_x = self.x + mx * self.speed * dt
                new_y = self.y + my * self.speed * dt

                tr = pygame.Rect(new_x - self.radius, self.y - self.radius,
                                 self.radius * 2, self.radius * 2)
                if not any(obs.colliderect(tr) for obs in obstacles):
                    self.x = new_x

                tr2 = pygame.Rect(self.x - self.radius, new_y - self.radius,
                                  self.radius * 2, self.radius * 2)
                if not any(obs.colliderect(tr2) for obs in obstacles):
                    self.y = new_y

                self.x = max(self.radius, min(MAP_WIDTH  - self.radius, self.x))
                self.y = max(self.radius, min(MAP_HEIGHT - self.radius, self.y))

        self.sep_vx = 0.0
        self.sep_vy = 0.0
        return dealt_damage

    def take_damage(self, amount: int) -> bool:
        if self.dying or self.spawning:
            return False
        self.hp -= amount
        self.hit_flash = 0.12
        if self.hp <= 0:
            self.hp    = 0
            self.dying = True
            return True
        return False

    def draw(self, surface: pygame.Surface, cam_x: float, cam_y: float) -> None:
        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)

        if sx < -80 or sx > SCREEN_WIDTH + 80 or sy < -80 or sy > SCREEN_HEIGHT + 80:
            return

        # Spawn rise animation — zombie emerges from ground
        if self.spawning:
            ratio = 1.0 - self.spawn_timer / 0.5
            r = max(3, int(self.radius * ratio))
            alpha_color = tuple(int(c * ratio * 0.7) for c in self.base_color)
            pygame.draw.circle(surface, alpha_color, (sx, sy), r)
            # Rising particles drawn externally via emit_spawn_rise
            return

        if self.dying:
            ratio   = 1.0 - (self.die_timer / self.die_duration)
            r       = max(1, int(self.radius * ratio))
            ring_r  = int(self.radius * (1 + self.die_timer / self.die_duration * 1.8))
            pygame.draw.circle(surface, (200, 20, 20), (sx, sy), max(1, ring_r),
                               max(1, int(3 * ratio)))
            fade = tuple(max(0, min(255, int(c * ratio))) for c in
                         (min(255, self.base_color[0] + 80), 30, 30))
            pygame.draw.circle(surface, fade, (sx, sy), r)
            return

        r = self.radius
        fa = self.facing_angle

        # Shadow
        pygame.draw.ellipse(surface, (0, 0, 0), (sx - r, sy + r - 5, r * 2, 8))

        # Lunge streak (world space, behind sprite)
        if self.lunging:
            cf, sf = math.cos(fa), math.sin(fa)
            streak_color = tuple(max(0, min(255, c + 80)) for c in self.base_color)
            for i in range(1, 4):
                off = i * 8
                pygame.draw.circle(surface, streak_color,
                                   (int(sx - cf * off), int(sy - sf * off)),
                                   max(1, r - i * 3))

        body_color  = (255, 255, 255) if self.hit_flash > 0.08 else self.base_color
        limb_color  = tuple(max(0, min(255, c - 55)) for c in self.base_color)
        inner       = tuple(max(0, min(255, c - 40)) for c in self.base_color)
        wound_color = tuple(max(0, min(255, c - 70)) for c in self.base_color)

        def capsule(surf, p1, p2, width, color):
            pygame.draw.line(surf, color, p1, p2, width)
            pygame.draw.circle(surf, color, (int(p1[0]), int(p1[1])), width // 2)
            pygame.draw.circle(surf, color, (int(p2[0]), int(p2[1])), width // 2)

        # ── Build the zombie facing local +x, then rotate as a rigid sprite ──
        pad  = r + 24
        size = r * 2 + pad * 2
        char = pygame.Surface((size, size), pygame.SRCALPHA)
        cx = cyl = size // 2

        # Legs — uneven shuffling stride, one leg dragging
        leg_w = max(5, int(r * 0.4))
        step1 = math.sin(self.walk_timer) * r * 0.4
        step2 = math.sin(self.walk_timer * 0.55 + 1.6) * r * 0.15   # shorter/dragging
        for side, step in ((1, step1), (-1, step2)):
            hip  = (cx - r * 0.2, cyl + side * r * 0.3)
            foot = (cx - r * 0.2 + step, cyl + side * r * 0.3)
            capsule(char, hip, foot, leg_w, limb_color)
            pygame.draw.circle(char, (25, 22, 18), (int(foot[0]), int(foot[1])), max(3, int(r * 0.2)))

        # Torso — hunched, rounded but ragged block (not a blob, still reads as a person)
        torso_w, torso_h = int(r * 1.4), int(r * 1.6)
        torso = pygame.Rect(0, 0, torso_w, torso_h)
        torso.center = (int(cx - r * 0.1), cyl)
        pygame.draw.rect(char, inner, torso.inflate(6, 6), border_radius=torso_h // 3)
        pygame.draw.rect(char, body_color, torso, border_radius=torso_h // 3)
        if self.hit_flash <= 0.08:
            pygame.draw.rect(char, inner, torso.inflate(-torso_w * 0.5, -torso_h * 0.3),
                             border_radius=torso_h // 4)
            # Torn clothing notches on the silhouette edge
            for wa, wr, wsz in self.wounds:
                wx = torso.centerx + math.cos(wa) * torso_w * 0.4
                wy = torso.centery + math.sin(wa) * torso_h * 0.4
                pygame.draw.circle(char, wound_color, (int(wx), int(wy)), int(wsz))
        pygame.draw.rect(char, tuple(max(0, min(255, c + 50)) for c in self.base_color),
                         torso, 2, border_radius=torso_h // 3)

        # Arms — one always reaching forward with claws, other hangs bent
        reach = 1.7 if self.lunging else 1.3
        for side, is_reacher in ((1, True), (-1, False)):
            shoulder = (cx + r * 0.15, cyl + side * r * 0.6)
            if is_reacher:
                elbow = (cx + r * 0.75, cyl + side * r * 0.55)
                hand  = (cx + r * reach, cyl + side * r * 0.15)
            else:
                elbow = (cx + r * 0.35, cyl + side * r * 0.85)
                hand  = (cx + r * 0.15, cyl + side * r * 1.05)
            capsule(char, shoulder, elbow, max(4, int(r * 0.26)), limb_color)
            capsule(char, elbow, hand, max(3, int(r * 0.2)), limb_color)
            for c in (-0.35, 0, 0.35):
                clawx = hand[0] + math.cos(c) * r * 0.3
                clawy = hand[1] + math.sin(c) * r * 0.3 * side
                pygame.draw.line(char, (225, 225, 215), hand, (clawx, clawy), 2)

        # Head — tilted, decayed, with open jaw and glowing eyes
        head_r = max(6, int(r * 0.48))
        head_c = (cx + r * 0.95, cyl + r * 0.05)
        pygame.draw.circle(char, inner, head_c, head_r)
        if self.hit_flash <= 0.08:
            jaw_r = head_r * 1.3
            j1 = (head_c[0] + math.cos(-0.35) * jaw_r, head_c[1] + math.sin(-0.35) * jaw_r)
            j2 = (head_c[0] + math.cos(0.35) * jaw_r, head_c[1] + math.sin(0.35) * jaw_r)
            jt = (head_c[0] + jaw_r * 1.3, head_c[1])
            pygame.draw.polygon(char, (35, 5, 5), [j1, j2, jt])
            eye_r = max(3, int(r * 0.2))
            for side in (1, -1):
                ex_ = head_c[0] + head_r * 0.35
                ey_ = head_c[1] + side * head_r * 0.55
                pygame.draw.circle(char, (180, 0, 0), (int(ex_), int(ey_)), eye_r + 2)
                pygame.draw.circle(char, (255, 60, 60), (int(ex_), int(ey_)), eye_r)
                pygame.draw.circle(char, (255, 210, 210), (int(ex_), int(ey_)), max(1, eye_r - 2))
        pygame.draw.circle(char, tuple(max(0, min(255, c + 50)) for c in self.base_color), head_c, head_r, 2)

        # Per-type flair
        if self.hit_flash <= 0.08:
            if self.name == "Tank":
                for i in range(5):
                    ang = math.pi + (i - 2) * 0.5
                    bx = torso.centerx + math.cos(ang) * (torso_w * 0.55)
                    by = torso.centery + math.sin(ang) * (torso_h * 0.5)
                    tip = (bx + math.cos(ang) * 10, by + math.sin(ang) * 10)
                    side1 = (bx + math.cos(ang + 0.2) * 6, by + math.sin(ang + 0.2) * 6)
                    pygame.draw.polygon(char, (75, 75, 80), [(bx, by), side1, tip])
            elif self.name == "Fast":
                hood = [(head_c[0] - head_r * 1.3, head_c[1] - head_r * 1.2),
                        (head_c[0] - head_r * 2.2, head_c[1]),
                        (head_c[0] - head_r * 1.3, head_c[1] + head_r * 1.2),
                        (head_c[0] + head_r * 0.2, head_c[1])]
                pygame.draw.polygon(char, (28, 28, 24), hood)
            elif self.name == "BOSS":
                for i in range(7):
                    ang = -0.9 + i * 0.28
                    bx = head_c[0] + math.cos(ang) * head_r * 0.7
                    by = head_c[1] + math.sin(ang) * head_r * 0.7 - head_r * 0.4
                    tip = (bx + math.cos(ang) * 14, by - 14)
                    pygame.draw.line(char, (255, 200, 0), (bx, by), tip, 3)

        rotated = pygame.transform.rotate(char, -math.degrees(fa))
        rect = rotated.get_rect(center=(sx, sy))
        surface.blit(rotated, rect)

        # HP bar
        if self.hp < self.max_hp:
            bar_w  = self.radius * 2 + 4
            bar_h  = 5
            bx     = sx - bar_w // 2
            by     = sy - self.radius - 12
            pygame.draw.rect(surface, (60, 0, 0), (bx - 1, by - 1, bar_w + 2, bar_h + 2))
            pygame.draw.rect(surface, DARK_RED, (bx, by, bar_w, bar_h))
            hp_ratio  = self.hp / self.max_hp
            hp_color  = GREEN if hp_ratio > 0.5 else ORANGE if hp_ratio > 0.25 else RED
            pygame.draw.rect(surface, hp_color, (bx, by, int(bar_w * hp_ratio), bar_h))
            pygame.draw.rect(surface, WHITE, (bx, by, bar_w, bar_h), 1)

        if self.name == "BOSS":
            font  = get_font("arial", 11, bold=True)
            label = font.render("★ BOSS ★", True, (255, 60, 60))
            surface.blit(label, (sx - label.get_width() // 2, sy - self.radius - 24))


def apply_separation(zombies: list) -> None:
    n = len(zombies)
    for i in range(n):
        a = zombies[i]
        if a.dying or a.spawning:
            continue
        for j in range(i + 1, n):
            b = zombies[j]
            if b.dying or b.spawning:
                continue
            dx      = a.x - b.x
            dy      = a.y - b.y
            dist_sq = dx * dx + dy * dy
            min_d   = a.radius + b.radius + SEPARATION_RADIUS
            if 0.001 < dist_sq < min_d * min_d:
                dist  = math.sqrt(dist_sq)
                force = SEPARATION_FORCE * (1.0 - dist / min_d) / dist
                fx, fy = dx * force * 0.01, dy * force * 0.01
                a.sep_vx += fx;  a.sep_vy += fy
                b.sep_vx -= fx;  b.sep_vy -= fy


class PowerUp:
    TYPES = {
        "health":  {"color": (60, 220, 80),  "label": "+HP",   "icon_color": GREEN},
        "ammo":    {"color": (60, 160, 255),  "label": "+AMMO", "icon_color": BLUE},
        "speed":   {"color": (255, 210, 30),  "label": "+SPD",  "icon_color": YELLOW},
        "grenade": {"color": (255, 120, 30),  "label": "+NADE", "icon_color": ORANGE},
    }

    def __init__(self, x: float, y: float, ptype: str):
        self.x        = x
        self.y        = y
        self.ptype    = ptype
        self.data     = self.TYPES[ptype]
        self.radius   = POWERUP_RADIUS
        self.lifetime = POWERUP_LIFETIME
        self.alive    = True
        self.pulse    = 0.0
        self.float_offset = 0.0

    def update(self, dt: float) -> None:
        self.lifetime -= dt
        self.pulse    += dt * 3.5
        self.float_offset = math.sin(self.pulse) * 4
        if self.lifetime <= 0:
            self.alive = False

    def draw(self, surface: pygame.Surface, cam_x: float, cam_y: float) -> None:
        sx   = int(self.x - cam_x)
        sy   = int(self.y - cam_y + self.float_offset)
        fade = min(1.0, self.lifetime / 3.0)
        color = tuple(int(c * fade) for c in self.data["color"])

        pygame.draw.ellipse(surface, (0, 0, 0),
                            (sx - self.radius, sy + self.radius - 3,
                             self.radius * 2, 6))
        pr = int(self.radius + 3 + abs(math.sin(self.pulse)) * 5)
        pygame.draw.circle(surface, color, (sx, sy), pr, 2)
        pygame.draw.circle(surface, color, (sx, sy), self.radius)
        pygame.draw.circle(surface, WHITE, (sx, sy), self.radius, 2)
        pygame.draw.circle(surface, WHITE,
                           (sx - self.radius // 3, sy - self.radius // 3),
                           self.radius // 4)
        font  = get_font("arial", 11, bold=True)
        label = font.render(self.data["label"], True, BLACK)
        surface.blit(label, (sx - label.get_width() // 2,
                              sy - label.get_height() // 2))

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(self.x - self.radius, self.y - self.radius,
                           self.radius * 2, self.radius * 2)