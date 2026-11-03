"""catalog_data.py - Catálogo oficial de juegos y categorías de C.C.I. SYSTEM.
100% Python puro sin dependencias externas (Pygame/OpenCV/Pymunk).
Utilizado tanto por el launcher nativo como por la landing page web oficial.
Autora: Camila Carolina Ianni
"""
from __future__ import annotations

CATEGORIES: list[str] = [
    "TODOS", "ACCIÓN", "PLATAFORMAS", "PUZZLE", "SHOOTER", "RPG", "ARCADE"
]

CATALOG: list[dict] = [
    {
        "id": "davinci", "title": "DA VINCI FIGHTERS", "subtitle": "Combate arcade 1v1.",
        "developer": "C.C.I. System", "year": "2026", "genre": "Acción / Lucha",
        "players": "1–2", "tags": "ACCIÓN  ·  ARCADE", "categories": {"ACCIÓN", "ARCADE"},
        "game_key": "davinci", "slot": 0,
    },
    {
        "id": "asteroids", "title": "ASTEROIDS", "subtitle": "Sobrevive al campo de asteroides.",
        "developer": "Atari", "year": "1979", "genre": "Arcade / Shooter",
        "players": "1", "tags": "ARCADE  ·  SHOOTER", "categories": {"ARCADE", "SHOOTER"},
        "game_key": "asteroids", "slot": 1,
    },
    {
        "id": "mario", "title": "SUPER MARIO BROS", "subtitle": "Aventura clásica de plataformas.",
        "developer": "Nintendo", "year": "1985", "genre": "Plataformas", "players": "1",
        "tags": "PLATAFORMAS  ·  AVENTURA", "categories": {"PLATAFORMAS"},
        "game_key": "mario", "slot": 2,
    },
    {
        "id": "zelda", "title": "THE LEGEND OF ZELDA", "subtitle": "Explora y lucha en Hyrule.",
        "developer": "Nintendo", "year": "1986", "genre": "Acción / RPG", "players": "1",
        "tags": "ACCIÓN  ·  RPG", "categories": {"ACCIÓN", "RPG"},
        "game_key": "zelda", "slot": 3,
    },
    {
        "id": "pacman", "title": "PAC-MAN", "subtitle": "Come puntos y esquiva fantasmas.",
        "developer": "Namco", "year": "1980", "genre": "Arcade / Laberinto", "players": "1–2",
        "tags": "ARCADE  ·  CLÁSICO", "categories": {"ARCADE"},
        "game_key": "pacman", "slot": 4,
    },
    {
        "id": "tetris", "title": "TETRIS", "subtitle": "Encaja piezas y limpia líneas.",
        "developer": "C.C.I. System", "year": "2026", "genre": "Puzzle", "players": "1",
        "tags": "PUZZLE  ·  CLÁSICO", "categories": {"PUZZLE"},
        "game_key": "tetris", "slot": 5,
    },
    {
        "id": "space_invaders", "title": "SPACE INVADERS", "subtitle": "Defiende la Tierra de la invasión.",
        "developer": "Taito", "year": "1978", "genre": "Shooter / Arcade", "players": "1–2",
        "tags": "SHOOTER  ·  ARCADE", "categories": {"SHOOTER", "ARCADE"},
        "game_key": "space_invaders", "slot": 6,
    },
    {
        "id": "metalslug", "title": "METAL SLUG", "subtitle": "Run and gun con acción y vehículos.",
        "developer": "SNK", "year": "1996", "genre": "Acción / Shooter", "players": "1–2",
        "tags": "ACCIÓN  ·  SHOOTER", "categories": {"ACCIÓN", "SHOOTER"},
        "game_key": "metalslug", "slot": 7,
    },
    {
        "id": "doom", "title": "DOOM", "subtitle": "Shooter en primera persona con motor raycasting.",
        "developer": "id Software", "year": "1993", "genre": "Shooter / FPS", "players": "1",
        "tags": "SHOOTER  ·  FPS", "categories": {"SHOOTER"},
        "game_key": "doom", "slot": 8,
    },
    {
        "id": "flappy", "title": "FLAPPY BIRD", "subtitle": "Vuela entre tuberías y supera tu récord.",
        "developer": "C.C.I. System", "year": "2026", "genre": "Arcade", "players": "1",
        "tags": "ARCADE  ·  HABILIDAD", "categories": {"ARCADE"},
        "external": ("Flappy-Bird", "main.py"), "slot": 9,
    },
    {
        "id": "dino", "title": "DINO RUN", "subtitle": "Corre, salta y evita obstáculos.",
        "developer": "C.C.I. System", "year": "2026", "genre": "Arcade / Plataformas", "players": "1",
        "tags": "ARCADE  ·  PLATAFORMAS", "categories": {"ARCADE", "PLATAFORMAS"},
        "external": ("Dino", "main.py"), "slot": 10,
    },
    {
        "id": "ghostbusters", "title": "GHOSTBUSTERS", "subtitle": "Aventura de acción contra fantasmas.",
        "developer": "C.C.I. System", "year": "2026", "genre": "Acción / Aventura", "players": "1",
        "tags": "ACCIÓN  ·  AVENTURA", "categories": {"ACCIÓN"},
        "external": ("GhostBusters", "main.py"), "slot": 11,
    },
    {
        "id": "cyberpunk", "title": "CYBERPUNK", "subtitle": "Metroidvania retrofuturista con combate y parkour.",
        "developer": "C.C.I. System", "year": "2026", "genre": "Acción / Plataformas",
        "players": "1", "tags": "ACCIÓN  ·  PLATAFORMAS", "categories": {"ACCIÓN", "PLATAFORMAS"},
        "external": ("Cyberpunk-Metroidvania/Platformer 01-04-2022", "main.py"), "slot": 12,
    },
    {
        "id": "pokemon", "title": "POKÉMON", "subtitle": "Aventura RPG clásica por el mundo de Kanto.",
        "developer": "Game Freak", "year": "1996", "genre": "RPG / Aventura",
        "players": "1", "tags": "RPG  ·  AVENTURA", "categories": {"RPG"},
        "external": ("pokemon", "main.py"), "slot": 13,
    },
    {
        "id": "megaman", "title": "MEGA MAN", "subtitle": "Plataformas de acción robótica retro.",
        "developer": "Capcom", "year": "1987", "genre": "Acción / Plataformas",
        "players": "1", "tags": "PLATAFORMAS  ·  ACCIÓN", "categories": {"ACCIÓN", "PLATAFORMAS"},
        "external": ("MegamanPygame", "Game.py"), "slot": 16,
    },
    {
        "id": "castlevania", "title": "CASTLEVANIA", "subtitle": "Aventura gótica y látigo contra Drácula.",
        "developer": "Konami", "year": "1986", "genre": "Acción / Plataformas",
        "players": "1", "tags": "ACCIÓN  ·  PLATAFORMAS", "categories": {"ACCIÓN", "PLATAFORMAS"},
        "external": ("castlevania", "Main.py"), "slot": 17,
    },
    {
        "id": "bubblebobble", "title": "BUBBLE BOBBLE", "subtitle": "Atrapa monstruos en burbujas mágicas.",
        "developer": "Taito", "year": "1986", "genre": "Arcade / Plataformas",
        "players": "1–2", "tags": "ARCADE  ·  PLATAFORMAS", "categories": {"ARCADE", "PLATAFORMAS"},
        "external": ("bubble-bobble", "main.py"), "slot": 18,
    },
    {
        "id": "plantsvszombies", "title": "PLANTS VS. ZOMBIES", "subtitle": "Defiende tu jardín de los no-muertos.",
        "developer": "PopCap", "year": "2009", "genre": "Estrategia / Tower Defense",
        "players": "1", "tags": "ESTRATEGIA  ·  ARCADE", "categories": {"ACCIÓN", "ARCADE"},
        "external": ("PlantsVSZombies", "main.py"), "slot": 19,
    },
    {
        "id": "donkeykong", "title": "DONKEY KONG", "subtitle": "Salta barriles y rescata a Pauline.",
        "developer": "Nintendo", "year": "1981", "genre": "Arcade / Plataformas",
        "players": "1–2", "tags": "ARCADE  ·  CLÁSICO", "categories": {"ARCADE", "PLATAFORMAS"},
        "external": ("PythonDonkeyKong", "main.py"), "slot": 20,
    },
]
