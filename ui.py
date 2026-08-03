# ui.py — HUD, menus, kill feed, combo, boss bar, weapon HUD, pause

import pygame
import math
import random
from settings import *
from bullet import get_font


class KillFeed:
    def __init__(self):
        self._entries: list[dict] = []

    def add(self, text: str, color: tuple = WHITE) -> None:
        self._entries.insert(0, {"text": text, "color": color, "timer": 3.0})

    def update(self, dt: float) -> None:
        for e in self._entries:
            e["timer"] -= dt
        self._entries = [e for e in self._entries if e["timer"] > 0]

    def draw(self, surface: pygame.Surface) -> None:
        font = get_font("consolas", 13, bold=True)
        x = SCREEN_WIDTH - HUD_MARGIN - 230
        y = HUD_MARGIN + 120
        for e in self._entries[:6]:
            ratio = min(1.0, e["timer"] / 0.6)
            color = tuple(max(0, min(255, int(c * ratio))) for c in e["color"])
            label = font.render(e["text"], True, color)
            surface.blit(label, (x, y))
            y += 18


class ComboDisplay:
    def __init__(self):
        self.combo = 0
        self.timer = 0.0
        self._flash = 0.0

    def register_kill(self) -> None:
        self.combo += 1
        self.timer  = COMBO_WINDOW
        self._flash = 0.3

    def update(self, dt: float) -> int:
        self._flash = max(0.0, self._flash - dt)
        if self.timer > 0:
            self.timer -= dt
        else:
            self.combo = 0
        return max(1, self.combo)

    def draw(self, surface: pygame.Surface) -> None:
        if self.combo < 2:
            return
        cx = SCREEN_WIDTH // 2
        cy = SCREEN_HEIGHT - 130

        heat  = min(COMBO_MAX, self.combo) / COMBO_MAX
        color = (255, int(200 - 160 * heat), 20)
        if self._flash > 0:
            color = (255, 255, 100)

        font_big = get_font("impact", 44)
        label  = font_big.render(f"x{self.combo}  COMBO!", True, color)
        shadow = font_big.render(f"x{self.combo}  COMBO!", True, (0, 0, 0))
        surface.blit(shadow, (cx - label.get_width() // 2 + 2, cy + 2))
        surface.blit(label,  (cx - label.get_width() // 2, cy))

        bar_w = 170
        ratio = max(0.0, self.timer / COMBO_WINDOW)
        pygame.draw.rect(surface, DARK_GRAY, (cx - bar_w // 2, cy + 50, bar_w, 6))
        pygame.draw.rect(surface, color,     (cx - bar_w // 2, cy + 50,
                                               int(bar_w * ratio), 6))


class BossHealthBar:
    def __init__(self):
        self._boss = None

    def set_boss(self, zombie) -> None:
        self._boss = zombie

    def update(self) -> None:
        if self._boss and (self._boss.dying or not self._boss.alive):
            self._boss = None

    def draw(self, surface: pygame.Surface) -> None:
        if not self._boss or self._boss.dying:
            return
        bar_w = 600
        bar_h = 22
        x = SCREEN_WIDTH // 2 - bar_w // 2
        y = 14
        pygame.draw.rect(surface, (0, 0, 0), (x - 2, y - 2, bar_w + 4, bar_h + 4))
        pygame.draw.rect(surface, DARK_RED, (x, y, bar_w, bar_h))
        ratio   = self._boss.hp / self._boss.max_hp
        filled  = int(bar_w * ratio)
        pulse   = abs(math.sin(pygame.time.get_ticks() * 0.003)) * 30
        pygame.draw.rect(surface, (min(255, 180 + int(pulse)), 0, 0),
                         (x, y, filled, bar_h))
        pygame.draw.rect(surface, (255, 80, 80), (x, y, filled, bar_h // 3))
        pygame.draw.rect(surface, WHITE, (x, y, bar_w, bar_h), 2)
        font  = get_font("impact", 22)
        label = font.render(f"★  BOSS  {self._boss.hp}/{self._boss.max_hp}  ★", True, WHITE)
        surface.blit(label, (SCREEN_WIDTH // 2 - label.get_width() // 2, y + 28))


class HUD:
    def __init__(self):
        self._popup_messages: list[dict] = []
        self._wave_flash  = 0.0
        self._wave_num    = 1
        self.kill_feed    = KillFeed()
        self.combo        = ComboDisplay()
        self.boss_bar     = BossHealthBar()
        self._break_visible = False
        self._break_ratio   = 0.0
        self._wave_bonus    = 0
        self._wave_bonus_timer = 0.0

    def wave_announcement(self, wave: int) -> None:
        self._wave_flash = 3.0
        self._wave_num   = wave

    def show_wave_bonus(self, bonus: int) -> None:
        self._wave_bonus       = bonus
        self._wave_bonus_timer = 2.5

    def add_popup(self, text: str, color: tuple = WHITE, duration: float = 1.5) -> None:
        self._popup_messages.append({
            "text": text, "color": color,
            "timer": duration, "max": duration, "y_offset": 0.0
        })

    def set_wave_break(self, in_break: bool, ratio: float) -> None:
        self._break_visible = in_break
        self._break_ratio   = ratio

    def update(self, dt: float) -> None:
        self._wave_flash = max(0.0, self._wave_flash - dt)
        self._wave_bonus_timer = max(0.0, self._wave_bonus_timer - dt)
        alive = []
        for m in self._popup_messages:
            m["timer"]    -= dt
            m["y_offset"] -= 48 * dt
            if m["timer"] > 0:
                alive.append(m)
        self._popup_messages = alive
        self.kill_feed.update(dt)
        self.combo.update(dt)
        self.boss_bar.update()

    def draw(self, surface: pygame.Surface, player, wave: int,
             elapsed: float, score: int, high_score: int) -> None:
        self._draw_health_bar(surface, player)
        self._draw_weapon_hud(surface, player)
        self._draw_grenades(surface, player)
        self._draw_wave_info(surface, wave, elapsed)
        self._draw_score(surface, score, high_score)
        self._draw_wave_flash(surface)
        self._draw_popups(surface)
        self._draw_wave_break(surface)
        self._draw_wave_bonus(surface)
        self.kill_feed.draw(surface)
        self.combo.draw(surface)
        self.boss_bar.draw(surface)

        if player.reloading:
            self._draw_reload_bar(surface, player)
        if player.speed_boost_timer > 0:
            self._draw_speed_indicator(surface, player)

    def _draw_health_bar(self, surface, player) -> None:
        x, y = HUD_MARGIN, HUD_MARGIN
        get_font("consolas", 14, bold=True)
        label = get_font("consolas", 14, bold=True).render("HEALTH", True, LIGHT_GRAY)
        surface.blit(label, (x, y))
        y += 18

        pygame.draw.rect(surface, BLACK, (x - 2, y - 2, BAR_WIDTH + 4, BAR_HEIGHT + 4))
        pygame.draw.rect(surface, DARK_GRAY, (x, y, BAR_WIDTH, BAR_HEIGHT))

        ratio = player.hp / player.max_hp
        filled = int(BAR_WIDTH * ratio)
        if ratio > 0.6:
            bar_color = (40, 200, 60)
        elif ratio > 0.3:
            bar_color = (220, 160, 0)
        else:
            pulse = abs(math.sin(pygame.time.get_ticks() * 0.005)) * 50
            bar_color = (min(255, 200 + int(pulse)), 20, 20)

        if filled > 0:
            pygame.draw.rect(surface, bar_color, (x, y, filled, BAR_HEIGHT))
            pygame.draw.rect(surface, tuple(max(0, min(255, c + 50)) for c in bar_color),
                             (x, y, filled, BAR_HEIGHT // 3))
        pygame.draw.rect(surface, WHITE, (x, y, BAR_WIDTH, BAR_HEIGHT), 2)
        hp_text = get_font("consolas", 13, bold=True).render(
            f"{player.hp}/{player.max_hp}", True, WHITE)
        surface.blit(hp_text, (x + BAR_WIDTH // 2 - hp_text.get_width() // 2, y + 3))

    def _draw_weapon_hud(self, surface, player) -> None:
        x, y = HUD_MARGIN, HUD_MARGIN + 60
        w    = player.weapon

        # Weapon name
        accent = w.color_accent
        name_label = get_font("consolas", 14, bold=True).render(
            f"[{player.weapon_index + 1}] {w.name}", True, accent)
        surface.blit(name_label, (x, y))
        y += 18

        # Bullet icons
        bul_w = 7 if w.kind == "shotgun" else 9
        bul_h = 18 if w.kind == "shotgun" else 22
        gap   = 4 if w.mag_size <= 8 else 3
        for i in range(w.mag_size):
            bx = x + i * (bul_w + gap)
            by = y
            if i < w.bullets_in_mag:
                pygame.draw.rect(surface, (int(accent[0] * 0.7), int(accent[1] * 0.7),
                                            int(accent[2] * 0.7)), (bx, by, bul_w, 5))
                pygame.draw.rect(surface, accent, (bx, by + 5, bul_w, bul_h - 5))
            else:
                pygame.draw.rect(surface, (40, 40, 40), (bx, by, bul_w, bul_h))
            pygame.draw.rect(surface, GRAY, (bx, by, bul_w, bul_h), 1)

        y += bul_h + 6
        mag_color = accent if w.mags_left > 1 else RED
        mag_text = get_font("consolas", 13, bold=True).render(
            f"MAGS: {w.mags_left}", True, mag_color)
        surface.blit(mag_text, (x, y))

        # Weapon switch hint
        hint_y = y + 18
        hint = get_font("consolas", 11, bold=False).render(
            "[ 1 ] Pistol  [ 2 ] Shotgun", True, GRAY)
        surface.blit(hint, (x, hint_y))

    def _draw_grenades(self, surface, player) -> None:
        x = HUD_MARGIN
        y = HUD_MARGIN + 170
        label = get_font("consolas", 14, bold=True).render(
            f"[F] NADES: {player.grenades}",
            True, ORANGE if player.grenades > 0 else GRAY)
        surface.blit(label, (x, y))
        if player.grenade_cooldown > 0:
            ratio = 1.0 - player.grenade_cooldown / GRENADE_COOLDOWN
            bar_w = 100
            pygame.draw.rect(surface, DARK_GRAY, (x, y + 18, bar_w, 5))
            pygame.draw.rect(surface, ORANGE,    (x, y + 18, int(bar_w * ratio), 5))

    def _draw_reload_bar(self, surface, player) -> None:
        cx    = SCREEN_WIDTH // 2
        cy    = SCREEN_HEIGHT - 90
        bar_w = 200
        label = get_font("consolas", 20, bold=True).render("RELOADING...", True, ORANGE)
        surface.blit(label, (cx - label.get_width() // 2, cy - 30))
        pygame.draw.rect(surface, BLACK, (cx - bar_w // 2 - 2, cy - 2, bar_w + 4, 18))
        pygame.draw.rect(surface, DARK_GRAY, (cx - bar_w // 2, cy, bar_w, 14))
        filled = int(bar_w * player.reload_progress)
        if filled > 0:
            pygame.draw.rect(surface, player.weapon.color_accent,
                             (cx - bar_w // 2, cy, filled, 14))
        pygame.draw.rect(surface, WHITE, (cx - bar_w // 2, cy, bar_w, 14), 2)

    def _draw_wave_info(self, surface, wave: int, elapsed: float) -> None:
        x = SCREEN_WIDTH - HUD_MARGIN - 220
        y = HUD_MARGIN
        font = get_font("consolas", 20, bold=True)
        surface.blit(font.render(f"WAVE  {wave}", True, ORANGE), (x, y))
        mins = int(elapsed) // 60
        secs = int(elapsed) % 60
        surface.blit(font.render(f"TIME  {mins:02d}:{secs:02d}", True, CYAN), (x, y + 28))

    def _draw_score(self, surface, score: int, high_score: int) -> None:
        x = SCREEN_WIDTH - HUD_MARGIN - 220
        y = HUD_MARGIN + 68
        surface.blit(get_font("consolas", 20, bold=True).render(
            f"SCORE {score:>6}", True, WHITE), (x, y))
        surface.blit(get_font("consolas", 14, bold=True).render(
            f"BEST  {high_score:>6}", True, LIGHT_GRAY), (x, y + 28))

    def _draw_wave_flash(self, surface) -> None:
        if self._wave_flash <= 0:
            return
        is_boss = (self._wave_num % BOSS_WAVE_INTERVAL == 0)
        text    = f"★  BOSS WAVE {self._wave_num}  ★" if is_boss else f"—  WAVE  {self._wave_num}  —"
        color   = RED if is_boss else ORANGE

        if self._wave_flash > 2.0:
            alpha_ratio = 3.0 - self._wave_flash
        elif self._wave_flash < 0.6:
            alpha_ratio = self._wave_flash / 0.6
        else:
            alpha_ratio = 1.0

        font   = get_font("impact", 64)
        label  = font.render(text, True, color)
        shadow = font.render(text, True, BLACK)
        scale  = 0.7 + 0.3 * alpha_ratio
        w2 = max(1, int(label.get_width()  * scale))
        h2 = max(1, int(label.get_height() * scale))
        label  = pygame.transform.scale(label,  (w2, h2))
        shadow = pygame.transform.scale(shadow, (w2, h2))
        cx = SCREEN_WIDTH  // 2 - w2 // 2
        cy = SCREEN_HEIGHT // 3
        surface.blit(shadow, (cx + 3, cy + 3))
        surface.blit(label,  (cx, cy))

    def _draw_popups(self, surface) -> None:
        cx     = SCREEN_WIDTH // 2
        base_y = SCREEN_HEIGHT // 2 - 80
        font   = get_font("consolas", 20, bold=True)
        for m in self._popup_messages:
            ratio = min(1.0, m["timer"] / m["max"])
            color = tuple(max(0, min(255, int(c * ratio))) for c in m["color"])
            label = font.render(m["text"], True, color)
            y     = base_y + int(m["y_offset"])
            surface.blit(label, (cx - label.get_width() // 2, y))

    def _draw_wave_break(self, surface) -> None:
        if not self._break_visible or self._break_ratio <= 0:
            return
        font_l = get_font("impact", 40)
        font_s = get_font("consolas", 18, bold=True)
        secs   = int(self._break_ratio * WAVE_BREAK_DURATION) + 1
        label  = font_l.render("WAVE CLEARED!", True, GREEN)
        sub    = font_s.render(f"Next wave in  {secs}s...", True, LIGHT_GRAY)
        cx, cy = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 40
        surface.blit(label, (cx - label.get_width() // 2, cy))
        surface.blit(sub,   (cx - sub.get_width()   // 2, cy + 52))
        bar_w = 300
        pygame.draw.rect(surface, DARK_GRAY, (cx - bar_w // 2, cy + 82, bar_w, 10))
        pygame.draw.rect(surface, GREEN,
                         (cx - bar_w // 2, cy + 82,
                          int(bar_w * (1.0 - self._break_ratio)), 10))
        pygame.draw.rect(surface, WHITE, (cx - bar_w // 2, cy + 82, bar_w, 10), 2)

    def _draw_wave_bonus(self, surface) -> None:
        if self._wave_bonus_timer <= 0 or self._wave_bonus <= 0:
            return
        ratio  = self._wave_bonus_timer / 2.5
        color  = (int(255 * ratio), int(220 * ratio), 0)
        font   = get_font("impact", 32)
        label  = font.render(f"SPEED CLEAR BONUS  +{self._wave_bonus}", True, color)
        cx     = SCREEN_WIDTH // 2
        surface.blit(label, (cx - label.get_width() // 2, SCREEN_HEIGHT // 2 + 20))

    def _draw_speed_indicator(self, surface, player) -> None:
        pulse = abs(math.sin(pygame.time.get_ticks() * 0.005))
        color = (int(100 + 155 * pulse), int(220 + 35 * pulse), int(80 + 80 * pulse))
        label = get_font("consolas", 14, bold=True).render(
            f"⚡ SPEED  {player.speed_boost_timer:.1f}s", True, color)
        surface.blit(label, (HUD_MARGIN, SCREEN_HEIGHT - 52))


# ─── Menu ─────────────────────────────────────────────────────────────────────
class MenuScreen:
    def __init__(self):
        self._pulse = 0.0
        self._bg_zombies = [(random.randint(0, SCREEN_WIDTH),
                             random.randint(0, SCREEN_HEIGHT),
                             random.uniform(0, math.tau),
                             random.uniform(20, 50))
                            for _ in range(14)]

    def update(self, dt: float) -> None:
        self._pulse += dt * 2.2
        new_bz = []
        for (x, y, ang, spd) in self._bg_zombies:
            nx = x + math.cos(ang) * spd * dt
            ny = y + math.sin(ang) * spd * dt
            if nx < -60: nx = SCREEN_WIDTH  + 40
            if nx > SCREEN_WIDTH + 60: nx = -40
            if ny < -60: ny = SCREEN_HEIGHT + 40
            if ny > SCREEN_HEIGHT + 60: ny = -40
            new_bz.append((nx, ny, ang, spd))
        self._bg_zombies = new_bz

    def draw(self, surface: pygame.Surface, high_score: int) -> None:
        surface.fill((6, 9, 12))
        for col in range(0, SCREEN_WIDTH, 80):
            pygame.draw.line(surface, (16, 22, 16), (col, 0), (col, SCREEN_HEIGHT))
        for row in range(0, SCREEN_HEIGHT, 80):
            pygame.draw.line(surface, (16, 22, 16), (0, row), (SCREEN_WIDTH, row))

        for (x, y, ang, spd) in self._bg_zombies:
            a = 32
            pygame.draw.circle(surface, (0, a, 0), (int(x), int(y)), 24)
            pygame.draw.circle(surface, (0, a // 2, 0), (int(x), int(y)), 18)
            pygame.draw.circle(surface, (40, 0, 0), (int(x) + 7, int(y) - 6), 4)
            pygame.draw.circle(surface, (40, 0, 0), (int(x) - 7, int(y) - 6), 4)

        title  = get_font("impact", 90).render("DEAD ZONE", True, RED)
        shadow = get_font("impact", 90).render("DEAD ZONE", True, (50, 0, 0))
        tx = SCREEN_WIDTH // 2 - title.get_width() // 2
        ty = SCREEN_HEIGHT // 5
        surface.blit(shadow, (tx + 5, ty + 5))
        surface.blit(title,  (tx, ty))
        sub = get_font("impact", 36).render("ZOMBIE SURVIVAL", True, ORANGE)
        surface.blit(sub, (SCREEN_WIDTH // 2 - sub.get_width() // 2, ty + 100))
        pygame.draw.line(surface, (60, 0, 0),
                         (SCREEN_WIDTH // 2 - 200, ty + 142),
                         (SCREEN_WIDTH // 2 + 200, ty + 142), 2)

        pa    = int(180 + 75 * math.sin(self._pulse))
        start = get_font("consolas", 28, bold=True).render(
            "[ ENTER ]  START GAME", True, (pa, pa, 0))
        surface.blit(start, (SCREEN_WIDTH // 2 - start.get_width() // 2,
                              SCREEN_HEIGHT // 2 + 40))
        quit_t = get_font("consolas", 18, bold=True).render("[ Q ]  QUIT", True, GRAY)
        surface.blit(quit_t, (SCREEN_WIDTH // 2 - quit_t.get_width() // 2,
                               SCREEN_HEIGHT // 2 + 90))

        ctrl_x = SCREEN_WIDTH // 2 - 280
        ctrl_y = SCREEN_HEIGHT * 3 // 4 - 20
        pygame.draw.rect(surface, BLACK,     (ctrl_x - 10, ctrl_y - 10, 560, 128))
        pygame.draw.rect(surface, (40, 40, 40), (ctrl_x - 10, ctrl_y - 10, 560, 128), 2)
        controls = [
            ("WASD / ARROWS", "Move"),
            ("MOUSE + LMB",   "Shoot"),
            ("R",             "Reload"),
            ("1 / 2",         "Switch weapon"),
            ("F",             "Throw Grenade"),
            ("ESC",           "Pause"),
        ]
        font_ctrl = get_font("consolas", 13, bold=True)
        for i, (key, action) in enumerate(controls):
            col = i % 2; row = i // 2
            cx2 = ctrl_x + col * 280
            cy2 = ctrl_y + row * 22
            surface.blit(font_ctrl.render(key,        True, YELLOW),     (cx2, cy2))
            surface.blit(font_ctrl.render(f"— {action}", True, LIGHT_GRAY),
                         (cx2 + 90, cy2))

        if high_score > 0:
            hs = get_font("consolas", 20, bold=True).render(
                f"★  BEST SCORE:  {high_score}", True, YELLOW)
            surface.blit(hs, (SCREEN_WIDTH // 2 - hs.get_width() // 2,
                               SCREEN_HEIGHT - 50))


class PauseScreen:
    def draw(self, surface: pygame.Surface) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surface.blit(overlay, (0, 0))
        cx = SCREEN_WIDTH // 2
        label  = get_font("impact", 72).render("PAUSED", True, WHITE)
        shadow = get_font("impact", 72).render("PAUSED", True, (40, 40, 40))
        surface.blit(shadow, (cx - label.get_width() // 2 + 3, SCREEN_HEIGHT // 3 + 3))
        surface.blit(label,  (cx - label.get_width() // 2,     SCREEN_HEIGHT // 3))
        for text, color, y in [
            ("[ ESC ]  Resume",    YELLOW,     SCREEN_HEIGHT // 2 + 20),
            ("[ M ]  Main Menu",   LIGHT_GRAY, SCREEN_HEIGHT // 2 + 60),
        ]:
            t = get_font("consolas", 22, bold=True).render(text, True, color)
            surface.blit(t, (cx - t.get_width() // 2, y))


class GameOverScreen:
    def __init__(self):
        self._pulse = 0.0

    def update(self, dt: float) -> None:
        self._pulse += dt * 2.8

    def draw(self, surface: pygame.Surface, score: int, high_score: int,
             wave: int, elapsed: float, new_record: bool, kills: int = 0) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        surface.blit(overlay, (0, 0))
        cx = SCREEN_WIDTH // 2

        title  = get_font("impact", 74).render("YOU DIED", True, RED)
        shadow = get_font("impact", 74).render("YOU DIED", True, (60, 0, 0))
        surface.blit(shadow, (cx - title.get_width() // 2 + 4, SCREEN_HEIGHT // 6 + 4))
        surface.blit(title,  (cx - title.get_width() // 2,     SCREEN_HEIGHT // 6))

        mins = int(elapsed) // 60
        secs = int(elapsed) % 60
        y    = SCREEN_HEIGHT // 4 + 10
        for text, color in [
            (f"SCORE     {score:>7}", WHITE),
            (f"WAVE      {wave:>7}", ORANGE),
            (f"KILLS     {kills:>7}", RED),
            (f"TIME      {mins:02d}:{secs:02d}     ", CYAN),
            (f"BEST      {high_score:>7}", YELLOW),
        ]:
            label = get_font("consolas", 20, bold=True).render(text, True, color)
            surface.blit(label, (cx - label.get_width() // 2, y))
            y += 38

        if new_record:
            t = self._pulse
            rc = (int(200 + 55 * math.sin(t)), int(200 + 55 * math.sin(t + 1)), 0)
            rec = get_font("impact", 38).render("★  NEW RECORD!  ★", True, rc)
            surface.blit(rec, (cx - rec.get_width() // 2, y + 8))
            y += 52

        pa   = int(170 + 85 * math.sin(self._pulse))
        play = get_font("consolas", 20, bold=True).render(
            "[ ENTER ]  Play Again", True, (pa, pa, 0))
        menu = get_font("consolas", 20, bold=True).render(
            "[ M ]  Main Menu", True, LIGHT_GRAY)
        surface.blit(play, (cx - play.get_width() // 2, SCREEN_HEIGHT - 110))
        surface.blit(menu, (cx - menu.get_width() // 2, SCREEN_HEIGHT - 70))