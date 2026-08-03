#!/usr/bin/env python3
# main.py — Dead Zone: Zombie Survival

import pygame
import sys
import math
import random

from settings import *
from player import Player, Weapon
from zombie import Zombie, PowerUp, apply_separation
from bullet import Bullet, Grenade, ParticleSystem
from game import (
    Camera, WaveManager, build_obstacle_rects,
    load_high_score, save_high_score,
    _draw_tile_bg, _draw_obstacles,
    draw_vignette, draw_zombie_arrows,
    draw_minimap, draw_danger_vignette,
    get_floor_surface, get_vignette,
)
from ui import HUD, MenuScreen, GameOverScreen, PauseScreen

STATE_MENU     = "menu"
STATE_PLAYING  = "playing"
STATE_PAUSED   = "paused"
STATE_GAMEOVER = "gameover"


class GameSession:
    def __init__(self, high_score_ref: list):
        self.high_score_ref = high_score_ref
        self.obstacles      = build_obstacle_rects()
        self.player         = Player(700, 640)
        self.bullets: list[Bullet]   = []
        self.grenades: list[Grenade] = []
        self.zombies: list[Zombie]   = []
        self.powerups: list[PowerUp] = []
        self.particles  = ParticleSystem()
        self.camera     = Camera()
        self.wave_mgr   = WaveManager()
        self.hud        = HUD()
        self.score      = 0
        self.elapsed    = 0.0
        self.kills      = 0
        self._moving    = False

        # Snap camera
        self.camera.x = self.player.x - SCREEN_WIDTH  // 2
        self.camera.y = self.player.y - SCREEN_HEIGHT // 2

        # Track weapon switch for popup
        self._last_weapon_idx = 0

    # ── Update ────────────────────────────────────────────────────────────────
    def update(self, dt: float, keys, mouse_pos, mouse_buttons) -> bool:
        self.elapsed += dt
        self.hud.update(dt)

        p = self.player

        # Input & movement
        self._moving = p.handle_input(keys, dt, self.obstacles)
        p.update_aim(mouse_pos, self.camera.cx, self.camera.cy)
        p.try_reload(keys)

        # Weapon switch
        if p.switch_weapon(keys):
            w = p.weapon
            self.hud.add_popup(f"[ {w.name} ]", w.color_accent, 0.7)
            self.hud.kill_feed.add(f"Switched to {w.name}", w.color_accent)

        p.update(dt, self._moving, self.particles)

        # Shoot — returns list of bullets
        new_bullets = p.try_shoot(mouse_buttons, self.particles)
        if new_bullets:
            self.bullets.extend(new_bullets)
            intensity = SHAKE_INTENSITY * 2 if p.weapon.kind == Weapon.SHOTGUN else SHAKE_INTENSITY
            self.camera.shake(intensity, SHAKE_DURATION)

        # Grenade
        new_grenade = p.try_throw_grenade(keys, mouse_pos,
                                           self.camera.cx, self.camera.cy)
        if new_grenade:
            self.grenades.append(new_grenade)
            self.hud.add_popup("GRENADE!", ORANGE, 0.8)

        # Camera
        self.camera.update(p.x, p.y, dt)

        # Bullets — update (no cleanup yet)
        for b in self.bullets:
            b.update(dt, self.obstacles)

        # Grenades
        self._update_grenades(dt)

        # Separation
        apply_separation(self.zombies)

        # Wave manager
        new_zs, wave_started, in_break, break_ratio, wave_bonus = \
            self.wave_mgr.update(dt, self.zombies, self.obstacles, self.elapsed)

        self.zombies.extend(new_zs)
        # Emit spawn effect for fresh zombies
        for z in new_zs:
            self.particles.emit_spawn_rise(z.x, z.y, z.base_color)

        self.hud.set_wave_break(in_break, break_ratio)
        if wave_started:
            self.hud.wave_announcement(self.wave_mgr.wave)
        if wave_bonus > 0:
            self.score += wave_bonus
            self.hud.show_wave_bonus(wave_bonus)
            self.hud.kill_feed.add(f"Speed clear +{wave_bonus}!", YELLOW)

        # Boss bar
        boss = next((z for z in self.zombies
                     if z.name == "BOSS" and not z.dying), None)
        self.hud.boss_bar.set_boss(boss)

        # Zombies update
        for z in self.zombies:
            hit = z.update(dt, p, self.obstacles)
            if hit:
                self.camera.shake(SHAKE_INTENSITY + 4, SHAKE_DURATION + 0.05)

        # Bullet-zombie collision (BEFORE cleanup)
        self._resolve_bullet_hits()

        # Cleanup bullets
        self.bullets = [b for b in self.bullets if b.alive]

        # Power-ups
        self._update_powerups(dt)

        # Cleanup
        self.zombies  = [z for z in self.zombies if z.alive or z.dying]
        self.powerups = [pu for pu in self.powerups if pu.alive]
        self.particles.update(dt)

        if p.hurt_flash > 0.2:
            self.camera.shake(SHAKE_INTENSITY + 2, 0.1)

        return p.alive

    def _update_grenades(self, dt: float) -> None:
        alive_g = []
        for g in self.grenades:
            exploded = g.update(dt, self.obstacles)
            if exploded:
                self._explode_grenade(g)
            elif g.alive:
                alive_g.append(g)
        self.grenades = alive_g

    def _explode_grenade(self, g: Grenade) -> None:
        self.particles.emit_explosion(g.x, g.y)
        self.camera.shake(SHAKE_INTENSITY * 3, SHAKE_DURATION * 2.5)

        killed_count = 0
        for z in self.zombies:
            if z.dying or z.spawning:
                continue
            dist = math.hypot(z.x - g.x, z.y - g.y)
            if dist < GRENADE_RADIUS + z.radius:
                falloff = 1.0 - (dist / (GRENADE_RADIUS + z.radius)) * 0.5
                dmg     = int(GRENADE_DAMAGE * falloff)
                killed  = z.take_damage(dmg)
                self.particles.add_damage_number(z.x, z.y, dmg, critical=killed)
                if killed:
                    self._on_zombie_kill(z)
                    killed_count += 1
                else:
                    self.particles.emit_blood(z.x, z.y, 8)

        if killed_count > 1:
            bonus = killed_count * 10 * killed_count
            self.score += bonus
            self.hud.add_popup(f"MULTI-KILL x{killed_count}! +{bonus}", ORANGE, 2.0)
            self.hud.kill_feed.add(f"GRENADE x{killed_count} MULTI-KILL!", ORANGE)
        elif killed_count == 1:
            self.hud.add_popup("GRENADE KILL!", ORANGE, 1.2)

    def _resolve_bullet_hits(self) -> None:
        for b in self.bullets:
            if not b.alive:
                continue
            for z in self.zombies:
                if z.dying or z.spawning:
                    continue
                dx = b.x - z.x
                dy = b.y - z.y
                if dx * dx + dy * dy < (b.radius + z.radius) ** 2:
                    b.alive = False
                    self.particles.emit_hit_spark(b.x, b.y)
                    killed  = z.take_damage(b.damage)
                    # Floating damage number
                    self.particles.add_damage_number(
                        z.x, z.y, b.damage, critical=killed)
                    if killed:
                        self._on_zombie_kill(z)
                    else:
                        self.particles.emit_blood(z.x, z.y, 5)
                    break

    def _on_zombie_kill(self, z: Zombie) -> None:
        mult   = max(1, self.hud.combo.combo + 1)
        earned = z.score_value * mult
        self.score += earned
        self.kills += 1
        self.hud.combo.register_kill()
        self.particles.emit_blood(z.x, z.y, 20)
        self.camera.shake()

        if z.name == "BOSS":
            self.hud.kill_feed.add(f"BOSS SLAIN! +{earned}", RED)
            self.hud.add_popup(f"BOSS DOWN! +{earned}", RED, 2.5)
        elif mult >= 3:
            self.hud.kill_feed.add(f"x{mult} COMBO! +{earned}", YELLOW)
        else:
            self.hud.kill_feed.add(f"{z.name} +{earned}", LIGHT_GRAY)

        if random.random() < POWERUP_CHANCE:
            ptype = random.choices(
                ["health", "ammo", "speed", "grenade"],
                weights=[0.35, 0.35, 0.20, 0.10])[0]
            self.powerups.append(PowerUp(z.x, z.y, ptype))

    def _update_powerups(self, dt: float) -> None:
        p = self.player
        for pu in self.powerups:
            pu.update(dt)
            if not pu.alive:
                continue
            if p.rect.colliderect(pu.rect):
                self._apply_powerup(pu)
                pu.alive = False

    def _apply_powerup(self, pu: PowerUp) -> None:
        p = self.player
        msgs = {
            "health":  (lambda: p.add_health(40),       "+40 HP",       GREEN),
            "ammo":    (lambda: p.add_ammo(),            "+AMMO",        CYAN),
            "speed":   (lambda: p.add_speed_boost(6.0), "SPEED BOOST!", YELLOW),
            "grenade": (lambda: p.add_grenade(2),        "+2 GRENADES",  ORANGE),
        }
        fn, popup_text, color = msgs[pu.ptype]
        fn()
        self.hud.add_popup(popup_text, color, 1.5)
        self.hud.kill_feed.add(f"{popup_text} collected", color)
        self.particles.emit_powerup(pu.x, pu.y, pu.data["color"], 16)

    # ── Draw ──────────────────────────────────────────────────────────────────
    def draw(self, surface: pygame.Surface) -> None:
        cx, cy = self.camera.cx, self.camera.cy

        _draw_tile_bg(surface, cx, cy)
        self.particles.draw_decals(surface, cx, cy)
        _draw_obstacles(surface, self.obstacles, cx, cy)

        for pu in self.powerups:
            pu.draw(surface, cx, cy)

        self.particles.draw(surface, cx, cy)

        for b in self.bullets:
            b.draw(surface, cx, cy)

        for g in self.grenades:
            g.draw(surface, cx, cy)

        for z in sorted(self.zombies, key=lambda z: z.dying):
            z.draw(surface, cx, cy)

        self.player.draw(surface, cx, cy, self._moving)

        draw_zombie_arrows(surface, self.zombies, cx, cy)
        draw_vignette(surface)

        # Low HP danger pulse
        draw_danger_vignette(surface, self.player.hp, self.player.max_hp)

        # Explosion flash
        self.particles.draw_flash(surface)

        self.hud.draw(surface, self.player, self.wave_mgr.wave,
                      self.elapsed, self.score, self.high_score_ref[0])

        # Minimap
        draw_minimap(surface, self.player, self.zombies,
                     self.obstacles, self.powerups)

        # Hurt tint
        if self.player.hurt_flash > 0:
            s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            alpha = int(90 * self.player.hurt_flash / 0.25)
            s.fill((180, 0, 0, min(110, alpha)))
            surface.blit(s, (0, 0))


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    pygame.init()
    pygame.display.set_caption(TITLE)
    pygame.mouse.set_visible(False)

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock  = pygame.time.Clock()

    print("Building world surfaces...")
    get_floor_surface()
    get_vignette()
    print("Ready — DEAD ZONE started.")

    high_score_ref = [load_high_score()]

    state       = STATE_MENU
    session     = None
    menu        = MenuScreen()
    gameover    = GameOverScreen()
    pause_scr   = PauseScreen()
    new_record  = False
    final_score = final_wave = final_kills = 0
    final_time  = 0.0

    while True:
        dt = min(clock.tick(FPS) / 1000.0, 0.05)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            if state == STATE_MENU:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        session = GameSession(high_score_ref)
                        state   = STATE_PLAYING
                    elif event.key in (pygame.K_q, pygame.K_ESCAPE):
                        pygame.quit(); sys.exit()

            elif state == STATE_PLAYING:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        state = STATE_PAUSED

            elif state == STATE_PAUSED:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        state = STATE_PLAYING
                    elif event.key == pygame.K_m:
                        state = STATE_MENU

            elif state == STATE_GAMEOVER:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        session    = GameSession(high_score_ref)
                        new_record = False
                        state      = STATE_PLAYING
                    elif event.key in (pygame.K_m, pygame.K_ESCAPE):
                        state = STATE_MENU

        keys          = pygame.key.get_pressed()
        mouse_pos     = pygame.mouse.get_pos()
        mouse_buttons = pygame.mouse.get_pressed()

        if state == STATE_MENU:
            menu.update(dt)

        elif state == STATE_PLAYING:
            alive = session.update(dt, keys, mouse_pos, mouse_buttons)
            if not alive:
                final_score = session.score
                final_wave  = session.wave_mgr.wave
                final_time  = session.elapsed
                final_kills = session.kills
                if final_score > high_score_ref[0]:
                    high_score_ref[0] = final_score
                    save_high_score(high_score_ref[0])
                    new_record = True
                else:
                    new_record = False
                state = STATE_GAMEOVER

        elif state == STATE_GAMEOVER:
            gameover.update(dt)

        # Draw
        if state == STATE_MENU:
            menu.draw(screen, high_score_ref[0])
        elif state == STATE_PLAYING:
            session.draw(screen)
            session.player.draw_crosshair(screen, mouse_pos)
        elif state == STATE_PAUSED:
            if session: session.draw(screen)
            pause_scr.draw(screen)
        elif state == STATE_GAMEOVER:
            if session: session.draw(screen)
            gameover.draw(screen, final_score, high_score_ref[0],
                          final_wave, final_time, new_record, final_kills)

        pygame.display.flip()


if __name__ == "__main__":
    main()
