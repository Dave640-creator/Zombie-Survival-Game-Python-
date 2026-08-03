# settings.py — Global constants

# Screen
SCREEN_WIDTH  = 1280
SCREEN_HEIGHT = 720
FPS           = 60
TITLE         = "DEAD ZONE — Zombie Survival"

# Colors
BLACK      = (0, 0, 0)
WHITE      = (255, 255, 255)
RED        = (200, 30, 30)
DARK_RED   = (120, 0, 0)
GREEN      = (30, 200, 80)
DARK_GREEN = (0, 80, 20)
BLUE       = (30, 100, 200)
YELLOW     = (255, 220, 40)
ORANGE     = (255, 140, 0)
GRAY       = (80, 80, 80)
DARK_GRAY  = (30, 30, 30)
LIGHT_GRAY = (160, 160, 160)
BROWN      = (100, 60, 20)
DARK_BROWN = (60, 35, 10)
PURPLE     = (140, 0, 200)
CYAN       = (0, 220, 220)

# Map / World
TILE_SIZE  = 64
MAP_COLS   = 30
MAP_ROWS   = 20
MAP_WIDTH  = TILE_SIZE * MAP_COLS   # 1920
MAP_HEIGHT = TILE_SIZE * MAP_ROWS   # 1280

# Player
PLAYER_SPEED       = 220
PLAYER_MAX_HP      = 100
PLAYER_RADIUS      = 18
PLAYER_COLOR       = (60, 180, 255)
PLAYER_SHOOT_RANGE = 800

# Ammo
MAG_SIZE    = 12
MAX_MAGS    = 5
RELOAD_TIME = 2.0

# Bullet
BULLET_SPEED    = 700
BULLET_RADIUS   = 5
BULLET_COLOR    = (255, 255, 120)
BULLET_LIFETIME = 1.5
BULLET_DAMAGE   = 25

# Shotgun
SHOTGUN_MAG_SIZE    = 6
SHOTGUN_PELLETS     = 7
SHOTGUN_SPREAD      = 0.35      # radians half-angle
SHOTGUN_DAMAGE      = 18        # per pellet
SHOTGUN_RELOAD_TIME = 2.5
SHOTGUN_DELAY       = 0.75      # fire rate
SHOTGUN_MAGS        = 3

# Grenade
GRENADE_COOLDOWN    = 8.0
GRENADE_RADIUS      = 120
GRENADE_DAMAGE      = 120
GRENADE_FUSE        = 1.8
GRENADE_THROW_SPEED = 480
GRENADE_COUNT       = 3

# Zombie types
ZOMBIE_NORMAL = {
    "name": "Normal", "speed": 90, "hp": 60,
    "radius": 20, "color": (60, 160, 60), "score": 10, "damage": 10,
    "attack_range": 28, "attack_rate": 1.0, "lunge": False,
}
ZOMBIE_FAST = {
    "name": "Fast", "speed": 200, "hp": 30,
    "radius": 15, "color": (200, 200, 40), "score": 20, "damage": 12,
    "attack_range": 24, "attack_rate": 0.6, "lunge": True,
}
ZOMBIE_TANK = {
    "name": "Tank", "speed": 55, "hp": 200,
    "radius": 30, "color": (100, 60, 160), "score": 50, "damage": 20,
    "attack_range": 38, "attack_rate": 1.5, "lunge": False,
}
ZOMBIE_BOSS = {
    "name": "BOSS", "speed": 70, "hp": 600,
    "radius": 45, "color": (180, 0, 0), "score": 200, "damage": 35,
    "attack_range": 58, "attack_rate": 1.2, "lunge": False,
}

# Wave settings
WAVE_BASE_ZOMBIES   = 6
WAVE_SCALE          = 1.4
BOSS_WAVE_INTERVAL  = 5
WAVE_BREAK_DURATION = 4.0
WAVE_CLEAR_BONUS    = 150       # base score bonus for clearing a wave

# Combo system
COMBO_WINDOW = 3.5
COMBO_MAX    = 10

# Power-up
POWERUP_CHANCE   = 0.22
POWERUP_RADIUS   = 16
POWERUP_LIFETIME = 14.0

# UI
HUD_MARGIN = 18
BAR_WIDTH  = 220
BAR_HEIGHT = 22

# Camera shake
SHAKE_DURATION  = 0.18
SHAKE_INTENSITY = 8

# Blood decals
MAX_DECALS    = 100
DECAL_LIFETIME = 30.0

# Zombie separation
SEPARATION_RADIUS = 45
SEPARATION_FORCE  = 60

# Floating damage numbers
DMG_NUM_LIFETIME = 1.1
DMG_NUM_RISE     = 55          # px/sec upward drift

# Minimap
MINIMAP_W      = 160
MINIMAP_H      = 107           # proportional to map aspect
MINIMAP_MARGIN = 14
MINIMAP_ALPHA  = 180

# Improved map layout
OBSTACLES = [
    # Border walls
    *[(c, 0, 1, 1) for c in range(MAP_COLS)],
    *[(c, MAP_ROWS - 1, 1, 1) for c in range(MAP_COLS)],
    *[(0, r, 1, 1) for r in range(MAP_ROWS)],
    *[(MAP_COLS - 1, r, 1, 1) for r in range(MAP_ROWS)],

    # --- Top-left compound ---
    (2,  2,  4, 1),   # horizontal wall
    (2,  3,  1, 3),   # left side
    (5,  3,  1, 2),   # right side (gap at row 5)
    (2,  6,  2, 1),   # bottom partial

    # --- Top-centre barrier ---
    (10, 2,  1, 4),
    (11, 5,  3, 1),
    (13, 2,  1, 3),

    # --- Top-right bunker ---
    (22, 2,  5, 1),
    (22, 3,  1, 3),
    (26, 3,  1, 3),
    (23, 5,  3, 1),

    # --- Mid-left L-shape ---
    (3,  9,  1, 4),
    (4,  9,  3, 1),

    # --- Centre cross ---
    (13, 8,  4, 1),
    (14, 9,  1, 3),
    (13,12,  4, 1),

    # --- Mid-right block ---
    (20, 8,  3, 1),
    (22, 9,  1, 3),
    (20,11,  3, 1),

    # --- Bottom-left ---
    (2, 14,  2, 4),
    (4, 14,  2, 1),
    (4, 17,  2, 1),

    # --- Bottom-centre ---
    (10,14,  1, 3),
    (11,16,  4, 1),
    (14,14,  1, 3),

    # --- Bottom-right corner ---
    (22,14,  5, 1),
    (22,15,  1, 3),
    (26,15,  1, 3),
    (23,17,  3, 1),

    # --- Scattered pillars ---
    (7,  7,  1, 1),
    (17, 6,  1, 1),
    (17,13,  1, 1),
    (7, 13,  1, 1),
]

SPAWN_MARGINS = 150
