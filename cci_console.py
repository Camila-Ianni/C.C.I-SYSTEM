"""C.C.I. System: pantallas interactivas del launcher Pygame.

Las imágenes finales son fondos visuales; navegación, foco, selección, búsqueda,
perfil, logros, ajustes y ejecución de juegos se gestionan con Pygame.
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import time
import unicodedata
from array import array
from datetime import datetime
from pathlib import Path

import pygame
from sidebar_ui import SIDEBAR_W, draw_sidebar, load_sidebar, make_sidebar_font, sidebar_destination

LOGICAL_W, LOGICAL_H = 1280, 720
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / ".cci-user-data"
DATA_FILE = DATA_DIR / "system.json"

DARK = (7, 8, 10)
PANEL = (10, 11, 13)
MID = (95, 98, 103)
LIGHT = (218, 220, 224)
WHITE = (246, 247, 249)
MUTED = (153, 157, 163)

ACHIEVEMENT_SPRITE_RECTS = {
    "bronze": pygame.Rect(1207, 198, 68, 72),
    "silver": pygame.Rect(1284, 198, 68, 72),
    "gold": pygame.Rect(1358, 198, 68, 72),
    "locked": pygame.Rect(1452, 212, 36, 43),
    "progress_track": pygame.Rect(887, 574, 207, 22),
    "arrow_left": pygame.Rect(544, 698, 49, 44),
    "arrow_right": pygame.Rect(608, 698, 49, 44),
    "game_davinci": pygame.Rect(29, 191, 106, 76),
    "game_asteroids": pygame.Rect(149, 191, 106, 76),
    "game_mario": pygame.Rect(271, 191, 106, 76),
    "game_zelda": pygame.Rect(395, 191, 106, 76),
    "game_pacman": pygame.Rect(29, 322, 106, 76),
    "game_tetris": pygame.Rect(150, 322, 106, 76),
    "game_space_invaders": pygame.Rect(271, 322, 106, 76),
    "game_metalslug": pygame.Rect(396, 322, 106, 76),
    "game_minecraft": pygame.Rect(29, 455, 106, 76),
    "game_flappy": pygame.Rect(150, 455, 106, 76),
    "game_dino": pygame.Rect(271, 455, 106, 76),
    "game_ghostbusters": pygame.Rect(396, 455, 106, 76),
    "game_cyberpunk": pygame.Rect(29, 578, 106, 76),
    **{f"avatar_{i}": pygame.Rect(545 + i * 77, 188, 73, 90) for i in range(8)},
}

SETTINGS_SPRITE_RECTS = {
    "preview_panel": pygame.Rect(626, 215, 499, 180),
    "slider_track": pygame.Rect(1186, 385, 266, 22),
    "switch_on": pygame.Rect(1183, 418, 79, 33),
    "switch_off": pygame.Rect(1184, 456, 78, 33),
    "button_primary": pygame.Rect(1180, 495, 327, 54),
    "button_secondary": pygame.Rect(1180, 551, 327, 50),
    "network_off": pygame.Rect(1349, 676, 154, 42),
    "controller_panel": pygame.Rect(600, 465, 542, 275),
}

ACHIEVEMENT_GAME_TILE_RECTS = (
    pygame.Rect(310, 170, 112, 80),
    pygame.Rect(430, 170, 112, 80),
    pygame.Rect(550, 170, 112, 80),
    pygame.Rect(670, 170, 112, 80),
    pygame.Rect(790, 170, 154, 80),
)
ACHIEVEMENT_ROW_RECT = pygame.Rect(296, 284, 680, 58)
ACHIEVEMENT_ROW_Y = (284, 350, 415, 480, 545)
ACHIEVEMENT_LEFT_ARROW_RECT = pygame.Rect(286, 187, 19, 34)
ACHIEVEMENT_RIGHT_ARROW_RECT = pygame.Rect(962, 187, 20, 34)


CATALOG = [
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
        "id": "minecraft", "title": "MINECRAFT", "subtitle": "Construye, explora y sobrevive en un mundo 3D.",
        "developer": "Mojang / Ursina", "year": "2011", "genre": "Sandbox / Aventura",
        "players": "1", "tags": "SANDBOX  ·  AVENTURA", "categories": {"ACCIÓN", "ARCADE"},
        "external": ("Minecraft", "UrsaCraft_video.py"), "slot": 12,
    },
    {
        "id": "cyberpunk", "title": "CYBERPUNK", "subtitle": "Metroidvania retrofuturista con combate y parkour.",
        "developer": "C.C.I. System", "year": "2026", "genre": "Acción / Plataformas",
        "players": "1", "tags": "ACCIÓN  ·  PLATAFORMAS", "categories": {"ACCIÓN", "PLATAFORMAS"},
        "external": ("Cyberpunk-Metroidvania/Platformer 01-04-2022", "main.py"), "slot": 13,
    },
    {
        "id": "pokemon", "title": "POKÉMON", "subtitle": "Aventura RPG clásica por el mundo de Kanto.",
        "developer": "Game Freak", "year": "1996", "genre": "RPG / Aventura",
        "players": "1", "tags": "RPG  ·  AVENTURA", "categories": {"RPG"},
        "external": ("pokemon", "main.py"), "slot": 14,
    },
    {
        "id": "fighter", "title": "STREET FIGHTER II", "subtitle": "Combate arcade legendario 1v1 con Ryu.",
        "developer": "Capcom", "year": "1991", "genre": "Lucha / Arcade",
        "players": "1–2", "tags": "LUCHA  ·  ARCADE", "categories": {"ACCIÓN", "ARCADE"},
        "external": ("fighter", "main.py"), "slot": 15,
    },
    {
        "id": "sonic", "title": "SONIC THE HEDGEHOG", "subtitle": "Corre a toda velocidad por Green Hill Zone.",
        "developer": "SEGA", "year": "1991", "genre": "Plataformas / Velocidad",
        "players": "1–2", "tags": "PLATAFORMAS  ·  ARCADE", "categories": {"PLATAFORMAS", "ARCADE"},
        "external": ("sonic", "main.py"), "slot": 16,
    },
    {
        "id": "bomberman", "title": "BOMBERMAN", "subtitle": "Coloca bombas y elimina a tus rivales.",
        "developer": "Hudson Soft", "year": "1983", "genre": "Arcade / Estrategia",
        "players": "1–2", "tags": "ARCADE  ·  ACCIÓN", "categories": {"ACCIÓN", "ARCADE"},
        "external": ("Bomberman", "main.py"), "slot": 17,
    },
    {
        "id": "frogger", "title": "FROGGER", "subtitle": "Cruza la autopista y el río a salvo.",
        "developer": "Konami", "year": "1981", "genre": "Arcade / Habilidad",
        "players": "1", "tags": "ARCADE  ·  CLÁSICO", "categories": {"ARCADE"},
        "external": ("frogger", "frogger.py"), "slot": 18,
    },
    {
        "id": "megaman", "title": "MEGA MAN", "subtitle": "Plataformas de acción robótica retro.",
        "developer": "Capcom", "year": "1987", "genre": "Acción / Plataformas",
        "players": "1", "tags": "PLATAFORMAS  ·  ACCIÓN", "categories": {"ACCIÓN", "PLATAFORMAS"},
        "external": ("MegamanPygame", "Game.py"), "slot": 19,
    },
    {
        "id": "mkultra", "title": "MORTAL KOMBAT", "subtitle": "Combate visceral uno contra uno.",
        "developer": "Midway", "year": "1992", "genre": "Lucha / Acción",
        "players": "1–2", "tags": "LUCHA  ·  ARCADE", "categories": {"ACCIÓN", "ARCADE"},
        "external": ("MK-Ultra", "MKUltra.py"), "slot": 20,
    },
    {
        "id": "castlevania", "title": "CASTLEVANIA", "subtitle": "Aventura gótica y látigo contra Drácula.",
        "developer": "Konami", "year": "1986", "genre": "Acción / Plataformas",
        "players": "1", "tags": "ACCIÓN  ·  PLATAFORMAS", "categories": {"ACCIÓN", "PLATAFORMAS"},
        "external": ("castlevania", "Main.py"), "slot": 21,
    },
    {
        "id": "bubblebobble", "title": "BUBBLE BOBBLE", "subtitle": "Atrapa monstruos en burbujas mágicas.",
        "developer": "Taito", "year": "1986", "genre": "Arcade / Plataformas",
        "players": "1–2", "tags": "ARCADE  ·  PLATAFORMAS", "categories": {"ARCADE", "PLATAFORMAS"},
        "external": ("bubble-bobble", "main.py"), "slot": 22,
    },
    {
        "id": "plantsvszombies", "title": "PLANTS VS. ZOMBIES", "subtitle": "Defiende tu jardín de los no-muertos.",
        "developer": "PopCap", "year": "2009", "genre": "Estrategia / Tower Defense",
        "players": "1", "tags": "ESTRATEGIA  ·  ARCADE", "categories": {"ACCIÓN", "ARCADE"},
        "external": ("PlantsVSZombies", "main.py"), "slot": 23,
    },
    {
        "id": "donkeykong", "title": "DONKEY KONG", "subtitle": "Salta barriles y rescata a Pauline.",
        "developer": "Nintendo", "year": "1981", "genre": "Arcade / Plataformas",
        "players": "1–2", "tags": "ARCADE  ·  CLÁSICO", "categories": {"ARCADE", "PLATAFORMAS"},
        "external": ("PythonDonkeyKong", "main.py"), "slot": 24,
    },
    {
        "id": "qbert", "title": "Q*BERT", "subtitle": "Cambia el color de la pirámide esquivando enemigos.",
        "developer": "Gottlieb", "year": "1982", "genre": "Arcade / Puzzle",
        "players": "1", "tags": "ARCADE  ·  PUZZLE", "categories": {"ARCADE", "PUZZLE"},
        "external": ("qbert", "Qbert.py"), "slot": 25,
    },
]

CATEGORIES = ["TODOS", "ACCIÓN", "PLATAFORMAS", "PUZZLE", "SHOOTER", "RPG", "ARCADE"]
CATEGORY_RECTS = [
    pygame.Rect(280, 142, 78, 38), pygame.Rect(358, 142, 76, 38),
    pygame.Rect(434, 142, 110, 38), pygame.Rect(544, 142, 81, 38),
    pygame.Rect(625, 142, 81, 38), pygame.Rect(706, 142, 57, 38),
    pygame.Rect(763, 142, 80, 38),
]
GRID_RECTS = [
    pygame.Rect(282 + col * 145, 194 + row * 120, 133, 108)
    for row in range(3) for col in range(4)
]
LIBRARY_PAGE_SIZE = 12
LIBRARY_PREV_PAGE_RECT = pygame.Rect(486, 560, 32, 24)
LIBRARY_NEXT_PAGE_RECT = pygame.Rect(620, 560, 32, 24)

# Recortes de tarjetas a color de pantallas/Biblioteca de Juegos Retro Pixel Art.png.
# El kit no contiene DOOM; ese juego conserva su carátula local existente.
COLOR_LIBRARY_RECTS = {
    "davinci": pygame.Rect(238, 132, 186, 154),
    "asteroids": pygame.Rect(432, 132, 186, 154),
    "mario": pygame.Rect(626, 132, 191, 154),
    "zelda": pygame.Rect(826, 132, 183, 154),
    "pacman": pygame.Rect(238, 293, 185, 151),
    "tetris": pygame.Rect(432, 293, 186, 151),
    "space_invaders": pygame.Rect(626, 293, 191, 151),
    "metalslug": pygame.Rect(826, 293, 183, 152),
    "flappy": pygame.Rect(432, 451, 186, 154),
    "dino": pygame.Rect(626, 451, 191, 154),
    "ghostbusters": pygame.Rect(826, 451, 183, 154),
    "minecraft": pygame.Rect(238, 451, 186, 154),
    "cyberpunk": pygame.Rect(238, 609, 186, 154),
}

GAME_ACHIEVEMENTS = {
    "davinci": [
        {"title": "PRIMER ASALTO", "description": "Inicia tu primer combate en Da Vinci Fighters.", "type": "launch", "goal": 1},
        {"title": "COMBO EN CADENA", "description": "Pelea durante 15 minutos en la arena de combate.", "type": "minutes", "goal": 15},
        {"title": "FAVORITO DEL DOJO", "description": "Agrega Da Vinci Fighters a tus favoritos.", "type": "favorite", "goal": 1},
        {"title": "CINTURÓN NEGRO", "description": "Acumula 60 minutos dominando artes marciales.", "type": "minutes", "goal": 60},
        {"title": "CAMPEÓN DEL TORNEO", "description": "Alcanza un 50% de progreso en el torneo.", "type": "progress", "goal": 50},
    ],
    "asteroids": [
        {"title": "PILOTO EN ÓRBITA", "description": "Inicia un vuelo por el cinturón de asteroides.", "type": "launch", "goal": 1},
        {"title": "HIPERESPACIO", "description": "Sobrevive 15 minutos esquivando escombros cósmicos.", "type": "minutes", "goal": 15},
        {"title": "AS DEL RADAR", "description": "Agrega Asteroids a tus favoritos.", "type": "favorite", "goal": 1},
        {"title": "COMANDANTE ESTELAR", "description": "Juega 60 minutos destruyendo rocas espaciales.", "type": "minutes", "goal": 60},
        {"title": "SECTOR DESPEJADO", "description": "Alcanza un 50% de progreso en el espacio profundo.", "type": "progress", "goal": 50},
    ],
    "mario": [
        {"title": "MUNDO 1-1", "description": "Inicia una aventura en el Reino Champiñón.", "type": "launch", "goal": 1},
        {"title": "SALTADOR EXPERTO", "description": "Juega 15 minutos aplastando Goombas.", "type": "minutes", "goal": 15},
        {"title": "HÉROE DEL REINO", "description": "Agrega Super Mario Bros a tus favoritos.", "type": "favorite", "goal": 1},
        {"title": "RESCATE DE PEACH", "description": "Acumula 60 minutos explorando mundos.", "type": "minutes", "goal": 60},
        {"title": "SUPER ESTRELLA", "description": "Alcanza un 50% de progreso con Mario.", "type": "progress", "goal": 50},
    ],
    "zelda": [
        {"title": "ES PELIGROSO IR SOLO", "description": "Inicia tu aventura en The Legend of Zelda.", "type": "launch", "goal": 1},
        {"title": "ESPADA DE MADERA", "description": "Explora durante 15 minutos las tierras de Hyrule.", "type": "minutes", "goal": 15},
        {"title": "TRIFUERZA DEL VALOR", "description": "Agrega The Legend of Zelda a tus favoritos.", "type": "favorite", "goal": 1},
        {"title": "HÉROE DEL TIEMPO", "description": "Acumula 60 minutos buscando mazmorras.", "type": "minutes", "goal": 60},
        {"title": "MAESTRO DE HYRULE", "description": "Alcanza un 50% de progreso en Hyrule.", "type": "progress", "goal": 50},
    ],
    "pacman": [
        {"title": "WAKA WAKA", "description": "Inicia una partida en el laberinto clásico.", "type": "launch", "goal": 1},
        {"title": "COME-FANTASMAS", "description": "Sobrevive 15 minutos devorando píldoras de poder.", "type": "minutes", "goal": 15},
        {"title": "FIEBRE AMARILLA", "description": "Agrega Pac-Man a tus favoritos.", "type": "favorite", "goal": 1},
        {"title": "LABERINTO SIN FIN", "description": "Acumula 60 minutos huyendo de los fantasmas.", "type": "minutes", "goal": 60},
        {"title": "PUNTUACIÓN PERFECTA", "description": "Alcanza un 50% de progreso en el laberinto.", "type": "progress", "goal": 50},
    ],
    "tetris": [
        {"title": "PRIMER TETROMINÓ", "description": "Inicia tu primera partida de Tetris.", "type": "launch", "goal": 1},
        {"title": "LÍNEA PERFECTA", "description": "Juega 15 minutos completando líneas.", "type": "minutes", "goal": 15},
        {"title": "AMANTE DEL PUZZLE", "description": "Agrega Tetris a tus juegos favoritos.", "type": "favorite", "goal": 1},
        {"title": "MAESTRO DE LA GRAVEDAD", "description": "Juega 60 minutos en Tetris.", "type": "minutes", "goal": 60},
        {"title": "GRAN MAESTRO", "description": "Alcanza al menos un 50% de progreso en Tetris.", "type": "progress", "goal": 50},
    ],
    "space_invaders": [
        {"title": "INVASIÓN DETECTADA", "description": "Inicia una defensa contra la invasión alienígena.", "type": "launch", "goal": 1},
        {"title": "BARRERA DEFENSIVA", "description": "Resiste 15 minutos el bombardeo extraterrestre.", "type": "minutes", "goal": 15},
        {"title": "FAVORITO CÓSMICO", "description": "Agrega Space Invaders a tus favoritos.", "type": "favorite", "goal": 1},
        {"title": "DEFENSOR DE LA TIERRA", "description": "Acumula 60 minutos defendiendo el planeta.", "type": "minutes", "goal": 60},
        {"title": "VICTORIA GALÁCTICA", "description": "Alcanza un 50% de progreso espacial.", "type": "progress", "goal": 50},
    ],
    "metalslug": [
        {"title": "MISSION START!", "description": "Inicia una misión con el escuadrón Peregrine.", "type": "launch", "goal": 1},
        {"title": "HEAVY MACHINE GUN", "description": "Combate durante 15 minutos en el frente de batalla.", "type": "minutes", "goal": 15},
        {"title": "FAVORITO DEL GENERAL", "description": "Agrega Metal Slug a tus favoritos.", "type": "favorite", "goal": 1},
        {"title": "VETERANO DE GUERRA", "description": "Acumula 60 minutos de acción arcade sin tregua.", "type": "minutes", "goal": 60},
        {"title": "MISIÓN CUMPLIDA", "description": "Alcanza un 50% de progreso militar.", "type": "progress", "goal": 50},
    ],
    "doom": [
        {"title": "ENTRANDO AL INFIERNO", "description": "Inicia tu primera partida de DOOM.", "type": "launch", "goal": 1},
        {"title": "GATILLO FÁCIL", "description": "Sobrevive 15 minutos en los pasillos de Phobos.", "type": "minutes", "goal": 15},
        {"title": "ARSENAL DE LA UAC", "description": "Agrega DOOM a tus juegos favoritos.", "type": "favorite", "goal": 1},
        {"title": "PESADILLA MARCIANA", "description": "Combate durante 60 minutos contra la horda.", "type": "minutes", "goal": 60},
        {"title": "DOOM SLAYER", "description": "Alcanza un 50% de progreso en DOOM.", "type": "progress", "goal": 50},
    ],
    "flappy": [
        {"title": "PRIMER ALETEO", "description": "Inicia tu primer vuelo en Flappy Bird.", "type": "launch", "goal": 1},
        {"title": "RITMO CARDÍACO", "description": "Sobrevive 15 minutos esquivando tuberías verdes.", "type": "minutes", "goal": 15},
        {"title": "FAVORITO DE LAS ALTURAS", "description": "Agrega Flappy Bird a tus favoritos.", "type": "favorite", "goal": 1},
        {"title": "SEÑOR DEL CIELO", "description": "Acumula 60 minutos volando con paciencia.", "type": "minutes", "goal": 60},
        {"title": "VUELO LEGENDARIO", "description": "Alcanza un 50% de progreso en el aire.", "type": "progress", "goal": 50},
    ],
    "dino": [
        {"title": "SIN CONEXIÓN", "description": "Inicia tu primera carrera con el T-Rex.", "type": "launch", "goal": 1},
        {"title": "SALTO DE CACTUS", "description": "Corre durante 15 minutos por el desierto jurásico.", "type": "minutes", "goal": 15},
        {"title": "FAVORITO FÓSIL", "description": "Agrega Dino Run a tus favoritos.", "type": "favorite", "goal": 1},
        {"title": "MARATÓN PREHISTÓRICO", "description": "Acumula 60 minutos esquivando pterodáctilos.", "type": "minutes", "goal": 60},
        {"title": "REY DEL MESOZOICO", "description": "Alcanza un 50% de progreso con el T-Rex.", "type": "progress", "goal": 50},
    ],
    "ghostbusters": [
        {"title": "¿A QUIÉN VAS A LLAMAR?", "description": "Inicia tu primer turno como Cazafantasmas.", "type": "launch", "goal": 1},
        {"title": "RAYO DE PROTONES", "description": "Patrulla la ciudad durante 15 minutos.", "type": "minutes", "goal": 15},
        {"title": "EQUIPO PARANORMAL", "description": "Agrega Ghostbusters a tus favoritos.", "type": "favorite", "goal": 1},
        {"title": "TRAMPA ACTIVA", "description": "Acumula 60 minutos capturando apariciones.", "type": "minutes", "goal": 60},
        {"title": "SALVADOR DE NUEVA YORK", "description": "Alcanza un 50% de progreso paranormal.", "type": "progress", "goal": 50},
    ],
    "minecraft": [
        {"title": "LA EDAD DE PIEDRA", "description": "Inicia tu primer mundo de supervivencia en Minecraft.", "type": "launch", "goal": 1},
        {"title": "¡DIAMANTES!", "description": "Explora y construye durante 15 minutos.", "type": "minutes", "goal": 15},
        {"title": "BLOQUE FAVORITO", "description": "Agrega Minecraft a tus favoritos.", "type": "favorite", "goal": 1},
        {"title": "SUPERVIVENCIA EXTREMA", "description": "Acumula 60 minutos explorando cavernas.", "type": "minutes", "goal": 60},
        {"title": "ARQUITECTO DEL MUNDO", "description": "Alcanza un 50% de progreso en tu mundo.", "type": "progress", "goal": 50},
    ],
    "cyberpunk": [
        {"title": "CONEXIÓN NEURAL", "description": "Inicia tu incursión en la ciudad cyberpunk.", "type": "launch", "goal": 1},
        {"title": "CALLES DE NEÓN", "description": "Explora durante 15 minutos los callejones oscuros.", "type": "minutes", "goal": 15},
        {"title": "FAVORITO DEL SUBURBIO", "description": "Agrega Cyberpunk a tus favoritos.", "type": "favorite", "goal": 1},
        {"title": "HACKER FANTASMA", "description": "Acumula 60 minutos desafiando megacorporaciones.", "type": "minutes", "goal": 60},
        {"title": "OVERDRIVE", "description": "Alcanza un 50% de progreso cibernético.", "type": "progress", "goal": 50},
    ],
    "pokemon": [
        {"title": "¡TE ELIJO A TI!", "description": "Inicia tu aventura Pokémon en Pueblo Paleta.", "type": "launch", "goal": 1},
        {"title": "ENTRENADOR NOVATO", "description": "Explora durante 15 minutos capturando criaturas.", "type": "minutes", "goal": 15},
        {"title": "POKÉ-FAVORITO", "description": "Agrega Pokémon a tus favoritos.", "type": "favorite", "goal": 1},
        {"title": "MAESTRO POKÉMON", "description": "Acumula 60 minutos de viaje Pokémon.", "type": "minutes", "goal": 60},
        {"title": "LÍDER DE GIMNASIO", "description": "Alcanza un 50% de progreso en tu Pokédex.", "type": "progress", "goal": 50},
    ],
    "fighter": [
        {"title": "HADOKEN!", "description": "Inicia un combate en Street Fighter II.", "type": "launch", "goal": 1},
        {"title": "GUERRERO MUNDIAL", "description": "Lucha durante 15 minutos en el torneo callejero.", "type": "minutes", "goal": 15},
        {"title": "LUCHADOR FAVORITO", "description": "Agrega Street Fighter II a tus favoritos.", "type": "favorite", "goal": 1},
        {"title": "SHORYUKEN MAESTRO", "description": "Acumula 60 minutos dominando las artes marciales.", "type": "minutes", "goal": 60},
        {"title": "CAMPEÓN CALLEJERO", "description": "Alcanza un 50% de progreso en el torneo.", "type": "progress", "goal": 50},
    ],
    "sonic": [
        {"title": "SUPER SONIC", "description": "Inicia tu carrera por Green Hill Zone.", "type": "launch", "goal": 1},
        {"title": "COLECTOR DE ANILLOS", "description": "Corre durante 15 minutos esquivando trampas.", "type": "minutes", "goal": 15},
        {"title": "FAVORITO AZUL", "description": "Agrega Sonic a tus favoritos.", "type": "favorite", "goal": 1},
        {"title": "SONIC BOOM", "description": "Acumula 60 minutos a máxima velocidad.", "type": "minutes", "goal": 60},
        {"title": "ESMERALDA DEL CAOS", "description": "Alcanza un 50% de progreso en las zonas.", "type": "progress", "goal": 50},
    ],
    "bomberman": [
        {"title": "MECHA ENCENDIDA", "description": "Inicia tu primera partida en Bomberman.", "type": "launch", "goal": 1},
        {"title": "BOMBARDEO TÁCTICO", "description": "Juega durante 15 minutos colocando bombas.", "type": "minutes", "goal": 15},
        {"title": "PIROTÉCNICO", "description": "Agrega Bomberman a tus favoritos.", "type": "favorite", "goal": 1},
        {"title": "MAESTRO DE LA DINAMITA", "description": "Acumula 60 minutos detonando laberintos.", "type": "minutes", "goal": 60},
        {"title": "SUPERVIVIENTE", "description": "Alcanza un 50% de progreso en el juego.", "type": "progress", "goal": 50},
    ],
    "frogger": [
        {"title": "SALTO INICIAL", "description": "Inicia tu primera travesía en Frogger.", "type": "launch", "goal": 1},
        {"title": "CRUZA-CALLES", "description": "Sobrevive 15 minutos esquivando tráfico y corrientes.", "type": "minutes", "goal": 15},
        {"title": "RANA FAVORITA", "description": "Agrega Frogger a tus favoritos.", "type": "favorite", "goal": 1},
        {"title": "REINA DEL ESTANQUE", "description": "Acumula 60 minutos guiando a las ranas al hogar.", "type": "minutes", "goal": 60},
        {"title": "SALTO PERFECTO", "description": "Alcanza un 50% de progreso cruzando el río.", "type": "progress", "goal": 50},
    ],
    "megaman": [
        {"title": "ROBOT GUERRERO", "description": "Inicia tu primera misión con Mega Man.", "type": "launch", "goal": 1},
        {"title": "BUSTER CARGADO", "description": "Lucha durante 15 minutos contra los robots maestros.", "type": "minutes", "goal": 15},
        {"title": "BOMBARDERO AZUL", "description": "Agrega Mega Man a tus favoritos.", "type": "favorite", "goal": 1},
        {"title": "DERROTA AL DR. WILY", "description": "Acumula 60 minutos de combate robótico retro.", "type": "minutes", "goal": 60},
        {"title": "CHIP DE PODER", "description": "Alcanza un 50% de progreso en las fases.", "type": "progress", "goal": 50},
    ],
    "mkultra": [
        {"title": "TEST YOUR MIGHT", "description": "Inicia tu primer combate en Mortal Kombat.", "type": "launch", "goal": 1},
        {"title": "GUERRERO DE LA TIERRA", "description": "Combate durante 15 minutos en el torneo.", "type": "minutes", "goal": 15},
        {"title": "KOMBATIENTE FAVORITO", "description": "Agrega Mortal Kombat a tus favoritos.", "type": "favorite", "goal": 1},
        {"title": "FATALITY LEGENDARIA", "description": "Acumula 60 minutos de combate sangriento.", "type": "minutes", "goal": 60},
        {"title": "CAMPEÓN DE OUTWORLD", "description": "Alcanza un 50% de progreso en el torneo.", "type": "progress", "goal": 50},
    ],
    "castlevania": [
        {"title": "CAZADOR DE VAMPIROS", "description": "Inicia tu primera partida en Castlevania.", "type": "launch", "goal": 1},
        {"title": "LÁTIGO SAGRADO", "description": "Explora el castillo durante 15 minutos.", "type": "minutes", "goal": 15},
        {"title": "CORAZÓN GÓTICO", "description": "Agrega Castlevania a tus favoritos.", "type": "favorite", "goal": 1},
        {"title": "NOCHE ETERNA", "description": "Acumula 60 minutos enfrentando a las sombras.", "type": "minutes", "goal": 60},
        {"title": "DERROTA A DRÁCULA", "description": "Alcanza un 50% de progreso en el castillo.", "type": "progress", "goal": 50},
    ],
    "bubblebobble": [
        {"title": "BURBUJAS MÁGICAS", "description": "Inicia tu primera partida en Bubble Bobble.", "type": "launch", "goal": 1},
        {"title": "HERMANOS DRAGÓN", "description": "Salta y dispara burbujas durante 15 minutos.", "type": "minutes", "goal": 15},
        {"title": "AMIGO DE BUB", "description": "Agrega Bubble Bobble a tus favoritos.", "type": "favorite", "goal": 1},
        {"title": "LLUVIA DE DULCES", "description": "Acumula 60 minutos superando niveles arcade.", "type": "minutes", "goal": 60},
        {"title": "MAESTRO DE BURBUJAS", "description": "Alcanza un 50% de progreso en la caverna.", "type": "progress", "goal": 50},
    ],
    "plantsvszombies": [
        {"title": "JARDÍN DEFENSIVO", "description": "Inicia tu defensa botánica contra los zombis.", "type": "launch", "goal": 1},
        {"title": "SOL RADIANTE", "description": "Siembra y combate durante 15 minutos continuos.", "type": "minutes", "goal": 15},
        {"title": "BOTÁNICO FAVORITO", "description": "Agrega Plants vs. Zombies a tus favoritos.", "type": "favorite", "goal": 1},
        {"title": "OLEADA FINAL", "description": "Acumula 60 minutos defendiendo tu patio.", "type": "minutes", "goal": 60},
        {"title": "TROFEO DORADO", "description": "Alcanza un 50% de progreso en el jardín.", "type": "progress", "goal": 50},
    ],
    "donkeykong": [
        {"title": "SALTA BARRILES", "description": "Inicia tu ascenso en Donkey Kong.", "type": "launch", "goal": 1},
        {"title": "MARTILLO EN MANO", "description": "Esquiva obstáculos y fuego durante 15 minutos.", "type": "minutes", "goal": 15},
        {"title": "RESCATE CLÁSICO", "description": "Agrega Donkey Kong a tus favoritos.", "type": "favorite", "goal": 1},
        {"title": "CIMA DE LAS VIGAS", "description": "Acumula 60 minutos desafiando al gran simio.", "type": "minutes", "goal": 60},
        {"title": "RESCATA A PAULINE", "description": "Alcanza un 50% de progreso en las vigas.", "type": "progress", "goal": 50},
    ],
    "qbert": [
        {"title": "PIRÁMIDE DE COLORES", "description": "Inicia tu salto por la pirámide de Q*bert.", "type": "launch", "goal": 1},
        {"title": "¡@!#?@", "description": "Esquiva a Coily y sus secuaces durante 15 minutos.", "type": "minutes", "goal": 15},
        {"title": "NARIZ DE TROMPETA", "description": "Agrega Q*bert a tus favoritos.", "type": "favorite", "goal": 1},
        {"title": "DISCO FLOTANTE", "description": "Acumula 60 minutos completando pirámides.", "type": "minutes", "goal": 60},
        {"title": "COLOR PERFECTO", "description": "Alcanza un 50% de progreso en el tablero.", "type": "progress", "goal": 50},
    ],
}

DEFAULT_DATA = {
    "version": 1,
    "player_name": "CAMI",
    "avatar": 0,
    "total_seconds": 0,
    "launch_count": 0,
    "last_session": "",
    "history": [],
    "favorites": [],
    "game_stats": {},
    "settings": {
        "resolution": "1280 x 720", "fullscreen": False,
        "crt_filter": False, "crt_intensity": 50,
        "volume_menu": 80, "volume_game": 75, "volume_fx": 70,
        "vibration": True, "sensitivity": 50, "network_enabled": False,
    },
}


def _deep_default():
    return json.loads(json.dumps(DEFAULT_DATA))


def _normal(text: str) -> str:
    return unicodedata.normalize("NFC", text).casefold()


def _find_file(folder: Path, starts: str, ends: str = ".png") -> Path | None:
    wanted = _normal(starts)
    search_dirs = [folder]
    for extra in (ROOT, ROOT / "pantallas"):
        if extra not in search_dirs and extra.exists():
            search_dirs.append(extra)
    for d in search_dirs:
        if not d.exists():
            continue
        for path in d.iterdir():
            if path.is_file() and _normal(path.name).startswith(wanted) and path.suffix.lower() == ends.lower():
                return path
    return None


class UserData:
    """Carga/guarda perfil, configuración, partidas recientes y logros localmente."""

    def __init__(self, path: Path = DATA_FILE):
        self.path = path
        self.data = _deep_default()
        try:
            if self.path.exists():
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    self._merge(self.data, loaded)
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            print(f"[CCI] No se pudo leer el perfil guardado: {exc}")

    @staticmethod
    def _merge(target, source):
        for key, value in source.items():
            if key not in target:
                target[key] = value
            elif isinstance(target[key], dict) and isinstance(value, dict):
                UserData._merge(target[key], value)
            else:
                target[key] = value

    def save(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(self.path)
        except OSError as exc:
            print(f"[CCI] No se pudo guardar el perfil: {exc}")

    @property
    def settings(self):
        return self.data["settings"]

    def record_launch(self, game: dict, elapsed: float):
        now = datetime.now()
        game_id = game["id"]
        seconds = max(0, int(elapsed))
        stats = self.data["game_stats"].setdefault(game_id, {"seconds": 0, "launches": 0, "progress": 0})
        stats["seconds"] = int(stats.get("seconds", 0)) + seconds
        stats["launches"] = int(stats.get("launches", 0)) + 1
        stats["progress"] = min(100, max(int(stats.get("progress", 0)), int(stats["seconds"] / 3600 * 25)))
        stats["last_played"] = now.isoformat(timespec="minutes")
        self.data["total_seconds"] = int(self.data.get("total_seconds", 0)) + seconds
        self.data["launch_count"] = int(self.data.get("launch_count", 0)) + 1
        self.data["last_session"] = now.isoformat(timespec="minutes")
        history = self.data.setdefault("history", [])
        history.insert(0, {"id": game_id, "title": game["title"], "date": now.strftime("%d/%m/%Y"), "time": now.strftime("%H:%M"), "seconds": seconds})
        del history[20:]
        self.save()

    def achievement_rows(self):
        stats = self.data.get("game_stats", {})
        favorites = set(self.data.get("favorites", []))
        rows = []
        for game in CATALOG:
            gid = game["id"]
            gstats = stats.get(gid, {})
            launches = int(gstats.get("launches", 0))
            minutes = int(gstats.get("seconds", 0)) // 60
            progress = int(gstats.get("progress", 0))
            fav = gid in favorites

            defs = GAME_ACHIEVEMENTS.get(gid, [
                {"title": game["title"], "description": f"Inicia una partida de {game['title']}.", "type": "launch", "goal": 1},
                {"title": f"FAVORITO: {game['title']}", "description": f"Agrega {game['title']} a favoritos.", "type": "favorite", "goal": 1},
                {"title": f"UNA HORA: {game['title']}", "description": f"Juega 60 minutos a {game['title']}.", "type": "minutes", "goal": 60},
            ])

            for ach in defs:
                ach_type = ach.get("type", "launch")
                goal = int(ach.get("goal", 1))
                if ach_type == "launch":
                    cur = min(launches, goal)
                    unlocked = launches >= goal
                    label = f"{cur}/{goal}"
                elif ach_type == "minutes":
                    cur = min(minutes, goal)
                    unlocked = minutes >= goal
                    label = f"{cur}/{goal} min"
                elif ach_type == "favorite":
                    cur = int(fav)
                    unlocked = fav
                    label = f"{cur}/1"
                elif ach_type == "progress":
                    cur = min(progress, goal)
                    unlocked = progress >= goal
                    label = f"{cur}%/{goal}%"
                else:
                    cur = 0
                    unlocked = False
                    label = f"0/{goal}"

                rows.append({
                    "game_id": gid,
                    "title": ach["title"],
                    "description": ach["description"],
                    "progress": cur,
                    "goal": goal,
                    "progress_label": label,
                    "unlocked": unlocked,
                })
        return rows

    def unlocked_count(self):
        return sum(1 for row in self.achievement_rows() if row["unlocked"])


class CCIConsoleState:
    """Vista Pygame funcional para biblioteca, perfil, logros y configuración."""

    def __init__(self, state_machine, page: str, user_data: UserData, apply_display=None):
        self.state_machine = state_machine
        self.page = page
        self.user_data = user_data
        self.apply_display = apply_display
        self.canvas = pygame.Surface((LOGICAL_W, LOGICAL_H))
        self.background = self._load_background(page)
        self.sidebar_surface = self._load_shared_sidebar()
        self.sidebar_font = make_sidebar_font()
        self.scaled_background = None
        self.scaled_size = None
        self.font_cache = {}
        self.ui_sound = self._make_ui_sound()
        self.avatar_surfaces = self._load_avatars() if page == "profile" else []
        self.profile_icons = self._load_profile_icons() if page == "profile" else {}
        self.achievement_sprites = self._load_achievement_sprites() if page == "achievements" else {}
        needs_game_art = page in {"library", "profile", "achievements"}
        self.card_surfaces = self._load_library_cards() if needs_game_art else []
        self.color_library_cards = self._load_color_library_cards() if page == "library" else {}
        self.color_library_art = {
            game_id: card.subsurface(pygame.Rect(8, 8, card.get_width() - 16, 108)).copy()
            for game_id, card in self.color_library_cards.items()
            if card.get_width() > 16 and card.get_height() >= 116
        }
        mc_hero = ROOT / "assets_cards" / "minecraft_hero.png"
        if mc_hero.is_file():
            try:
                self.color_library_art["minecraft"] = pygame.image.load(str(mc_hero)).convert()
            except (pygame.error, OSError):
                pass
        self.game_art = self._load_game_art() if needs_game_art else {}
        self.settings_sprites = self._load_settings_sprites() if page == "settings" else {}
        self.category = "TODOS"
        self.search_query = ""
        self.search_active = False
        self.text_input_active = False
        self.name_buffer = ""
        self.modal = ""
        self.toast = ""
        self.toast_until = 0.0
        self.selected_game_id = "davinci"
        self.selected_achievement = 0
        initial_achievement_game = CATALOG[0]
        self.selected_achievement_game = initial_achievement_game["id"]
        self.achievement_game_offset = 0
        initial_rows = self._achievement_rows_for_filter()
        if initial_rows:
            self.selected_achievement = initial_rows[0][0]
        self.selected_setting = 0
        self.sort_mode = 0
        self.library_page = 0
        self.anim_time = 0.0
        self.last_drawn_size = None

    def _load_background(self, page: str):
        folder = ROOT / "pantallas" / "finales_entrega"
        fallback = ROOT / "pantallas"
        prefixes = {
            "library": "Interfaz futurista de biblioteca de juegos FINAL",
            "profile": "Interfaz C.C.I — Perfil de Usuario FINAL",
            "achievements": "Interfaz futurista de logros FINAL",
            "settings": "Interfaz futurista de configuracio",
        }
        ends = {
            "library": "Interfaz futurista de biblioteca de juegos.png",
            "profile": "Interfaz C.C.I — Perfil de Usuario.png",
            "achievements": "Interfaz futurista de logros vacía.png",
            "settings": "Interfaz futurista de configuración C.C.I System.png",
        }
        path = (
            _find_file(fallback, ends[page])
            if page == "achievements"
            else _find_file(folder, prefixes[page]) or _find_file(fallback, ends[page])
        )
        if path is None:
            return pygame.Surface((LOGICAL_W, LOGICAL_H))
        try:
            return pygame.image.load(str(path)).convert()
        except (pygame.error, OSError) as exc:
            print(f"[CCI] No se pudo cargar {path}: {exc}")
            return pygame.Surface((LOGICAL_W, LOGICAL_H))

    def set_user_data(self, user_data: UserData):
        self.user_data = user_data

    def _load_shared_sidebar(self):
        """Usa en todas las vistas la barra de la plantilla base de logros."""
        return load_sidebar()

    def _load_avatars(self):
        path = _find_file(ROOT / "pantallas", "Kit de interfaz pixel art de ciencia ficción") or _find_file(ROOT / "pantallas", "Kit de interfaz retro para perfil")
        if path is None:
            return []
        try:
            sheet = pygame.image.load(str(path)).convert()
            coords = [(26 + c * 111, 117 + r * 141, 105, 126) for r in range(2) for c in range(4)]
            result = []
            for x, y, w, h in coords:
                rect = pygame.Rect(x, y, w, h).clip(sheet.get_rect())
                if rect.w and rect.h:
                    avatar = sheet.subsurface(rect).copy()
                    result.append(avatar)
            return result
        except (pygame.error, OSError) as exc:
            print(f"[CCI] No se pudieron cargar avatares: {exc}")
            return []

    def _load_profile_icons(self):
        """Recorta los iconos originales de métricas y edición del kit de perfil."""
        path = _find_file(ROOT / "pantallas", "Kit de interfaz pixel art de ciencia ficción") or _find_file(ROOT / "pantallas", "Kit de interfaz retro para perfil")
        if path is None:
            return {}
        try:
            sheet = pygame.image.load(str(path)).convert()
            is_new = "ciencia" in path.name.lower() or "pixel" in path.name.lower()
            if is_new:
                rects = {
                    "clock": pygame.Rect(28, 915, 48, 48),
                    "trophy": pygame.Rect(87, 915, 48, 48),
                    "calendar": pygame.Rect(146, 915, 48, 48),
                    "edit": pygame.Rect(205, 915, 48, 48),
                    "trash": pygame.Rect(264, 915, 48, 48),
                }
            else:
                rects = {
                    "clock": pygame.Rect(40, 934, 29, 29),
                    "trophy": pygame.Rect(99, 934, 29, 29),
                    "calendar": pygame.Rect(158, 934, 29, 29),
                    "edit": pygame.Rect(207, 924, 48, 48),
                }
            icons = {}
            for name, rect in rects.items():
                if rect.right > sheet.get_width() or rect.bottom > sheet.get_height():
                    continue
                icon = sheet.subsurface(rect).copy()
                if not is_new and name != "edit":
                    icon = icon.convert_alpha()
                    for ix in range(icon.get_width()):
                        for iy in range(icon.get_height()):
                            r, g, b, _a = icon.get_at((ix, iy))
                            if max(r, g, b) < 82:
                                icon.set_at((ix, iy), (r, g, b, 0))
                icons[name] = icon
            return icons
        except (pygame.error, OSError) as exc:
            print(f"[CCI] No se pudieron cargar iconos del perfil: {exc}")
            return {}

    def _load_achievement_sprites(self):
        """Extrae iconografía de logros de la hoja de alta definición."""
        path = _find_file(ROOT / "pantallas", "Panel de logros retro en blanco y negro") or _find_file(ROOT / "pantallas", "Hoja de interfaz C.C.I. de logros retro")
        if path is None:
            return {}
        try:
            sheet = pygame.image.load(str(path)).convert()
            sprites = {}
            for name, rect in ACHIEVEMENT_SPRITE_RECTS.items():
                if rect.right > sheet.get_width() or rect.bottom > sheet.get_height():
                    continue
                sprite = sheet.subsurface(rect).copy()
                if name != "progress_track":
                    sprite = sprite.convert_alpha()
                    for x in range(sprite.get_width()):
                        for y in range(sprite.get_height()):
                            r, g, b, _a = sprite.get_at((x, y))
                            if max(r, g, b) < 34:
                                sprite.set_at((x, y), (r, g, b, 0))
                sprites[name] = sprite
            return sprites
        except (pygame.error, OSError) as exc:
            print(f"[CCI] No se pudieron cargar los sprites de logros: {exc}")
            return {}

    def _load_settings_sprites(self):
        """Extrae componentes de la hoja de configuración de alta definición."""
        path = _find_file(ROOT / "pantallas", "Panel de configuración C.C.I. System") or _find_file(ROOT / "pantallas", "Hoja de interfaz futurista C.C.I System")
        if path is None:
            return {}
        try:
            sheet = pygame.image.load(str(path)).convert()
            return {
                name: sheet.subsurface(rect).copy()
                for name, rect in SETTINGS_SPRITE_RECTS.items()
                if rect.right <= sheet.get_width() and rect.bottom <= sheet.get_height()
            }
        except (pygame.error, OSError) as exc:
            print(f"[CCI] No se pudieron cargar los sprites de configuración: {exc}")
            return {}

    def _load_library_cards(self):
        """Recorta tarjetas de la pantalla final como sprites reutilizables."""
        folder = ROOT / "pantallas" / "finales_entrega"
        path = _find_file(folder, "Interfaz futurista de biblioteca de juegos FINAL")
        source = self.background
        if path:
            try:
                source = pygame.image.load(str(path)).convert()
            except (pygame.error, OSError) as exc:
                print(f"[CCI] No se pudieron cargar las tarjetas de biblioteca: {exc}")
        scaled = pygame.transform.smoothscale(source, (LOGICAL_W, LOGICAL_H))
        cards = []
        for rect in GRID_RECTS:
            cards.append(scaled.subsurface(rect).copy())
        return cards

    def _load_color_library_cards(self):
        """Recorta las tarjetas a color de la hoja retro en alta definición."""
        path = _find_file(ROOT / "pantallas", "Biblioteca de Juegos Retro en Alta Definición") or _find_file(ROOT / "pantallas", "Biblioteca de Juegos Retro Pixel Art")
        if path is None:
            return {}
        try:
            sheet = pygame.image.load(str(path)).convert()
            cards = {
                game_id: sheet.subsurface(rect).copy()
                for game_id, rect in COLOR_LIBRARY_RECTS.items()
                if rect.right <= sheet.get_width() and rect.bottom <= sheet.get_height()
            }
            extra_ids = (
                "pokemon", "fighter", "sonic", "streetfighter", "bomberman", "frogger",
                "megaman", "mkultra", "castlevania", "bubblebobble", "plantsvszombies",
                "donkeykong", "qbert"
            )
            for extra in extra_ids:
                if extra not in cards:
                    p = ROOT / "assets_cards" / f"{extra}_clean.png"
                    if not p.is_file():
                        p = ROOT / "assets_cards" / f"{extra}.png"
                    if p.is_file():
                        try:
                            cards[extra] = pygame.image.load(str(p)).convert()
                        except (pygame.error, OSError):
                            pass
            return cards
        except (pygame.error, OSError) as exc:
            print(f"[CCI] No se pudieron recortar las tarjetas a color: {exc}")
            return {}

    def _load_game_art(self):
        """Carga banners fuente de alta resolución; usa la tarjeta de biblioteca como fallback."""
        art = {}
        for game in CATALOG:
            path = ROOT / "assets_cards" / f"{game['id']}_clean.png"
            slot = game.get("slot", 0)
            fallback = self.card_surfaces[slot] if 0 <= slot < len(self.card_surfaces) else pygame.Surface((133, 108))
            try:
                art[game["id"]] = pygame.image.load(str(path)).convert() if path.is_file() else fallback
            except (pygame.error, OSError):
                art[game["id"]] = fallback
        return art

    def enter(self, **kwargs):
        pygame.display.set_caption(f"C.C.I. SYSTEM — {self.page.upper()}")
        if self.page == "library" and self.search_active:
            pygame.key.start_text_input()
        self.scaled_size = None

    def exit(self):
        if self.text_input_active or self.search_active:
            try:
                pygame.key.stop_text_input()
            except pygame.error:
                pass
        self.text_input_active = False
        self.search_active = False

    def update(self, dt):
        self.anim_time += dt
        if self.toast and time.monotonic() > self.toast_until:
            self.toast = ""

    def draw(self, screen):
        self.canvas.fill(DARK)
        self.canvas.blit(self._scaled_background(), (0, 0))
        self._draw_common_sidebar()
        if self.page == "library":
            self._draw_library()
        elif self.page == "profile":
            self._draw_profile()
        elif self.page == "achievements":
            self._draw_achievements()
        elif self.page == "settings":
            self._draw_settings()
        if self.user_data.settings.get("crt_filter"):
            self._draw_crt()
        self._draw_toast()
        if self.modal or self.text_input_active:
            self._draw_modal()
        out = pygame.transform.smoothscale(self.canvas, screen.get_size()) if screen.get_size() != (LOGICAL_W, LOGICAL_H) else self.canvas
        screen.blit(out, (0, 0))

    def _scaled_background(self):
        if self.scaled_background is None:
            self.scaled_background = pygame.transform.smoothscale(self.background, (LOGICAL_W, LOGICAL_H))
        return self.scaled_background

    def _font(self, size=16, bold=False):
        key = (size, bold)
        if key not in self.font_cache:
            font = None
            for candidate in (
                ROOT / "Zelda/extracted/15 - fixes audio/graphics/font/joystix.ttf",
                ROOT / "Space-invaders/font/Pixeled.ttf",
                ROOT / "tetris/mario.ttf",
                ROOT / "Mario/resources/fonts/Fixedsys500c.ttf",
            ):
                if candidate.exists():
                    try:
                        font = pygame.font.Font(str(candidate), size)
                        break
                    except (pygame.error, OSError):
                        pass
            if font is None:
                font = pygame.font.SysFont("Courier New", size, bold=bold)
            self.font_cache[key] = font
        return self.font_cache[key]

    def _text(self, text, x, y, size=16, color=WHITE, bold=False, max_width=None):
        surface = self._font(size, bold).render(str(text), True, color)
        if max_width and surface.get_width() > max_width:
            while len(text) > 3 and surface.get_width() > max_width:
                text = str(text)[:-2] + "…"
                surface = self._font(size, bold).render(text, True, color)
        self.canvas.blit(surface, (int(x), int(y)))
        return surface.get_rect(topleft=(int(x), int(y)))

    def _achievement_font(self, size=12, bold=False):
        key = ("achievement-body", size, bold)
        if key not in self.font_cache:
            self.font_cache[key] = pygame.font.SysFont("Courier New", size, bold=bold)
        return self.font_cache[key]

    def _achievement_text(self, text, x, y, size=12, color=LIGHT, bold=False, max_width=None):
        text = str(text)
        font = self._achievement_font(size, bold)
        surface = font.render(text, True, color)
        while max_width and surface.get_width() > max_width and len(text) > 4:
            text = text[:-2] + "…"
            surface = font.render(text, True, color)
        self.canvas.blit(surface, (int(x), int(y)))
        return surface.get_rect(topleft=(int(x), int(y)))

    def _achievement_wrap(self, text, x, y, width, size=12, color=LIGHT, bold=False, line_gap=3, max_lines=3):
        font = self._achievement_font(size, bold)
        lines, line = [], ""
        for word in str(text).split():
            candidate = f"{line} {word}".strip()
            if font.size(candidate)[0] <= width:
                line = candidate
            else:
                if line:
                    lines.append(line)
                line = word
        if line:
            lines.append(line)
        for i, content in enumerate(lines[:max_lines]):
            self._achievement_text(content, x, y + i * (size + line_gap), size, color, bold)

    def _wrap(self, text, x, y, width, size=13, color=MUTED, line_gap=5, max_lines=3):
        words = text.split()
        lines, line = [], ""
        font = self._font(size)
        for word in words:
            test = f"{line} {word}".strip()
            if font.size(test)[0] <= width:
                line = test
            else:
                if line:
                    lines.append(line)
                line = word
        if line:
            lines.append(line)
        for i, item in enumerate(lines[:max_lines]):
            self._text(item, x, y + i * (size + line_gap), size, color)
        return lines[:max_lines]

    def _make_ui_sound(self):
        mixer = pygame.mixer.get_init()
        if not mixer or mixer[1] != -16:
            return None
        frequency, _, channels = mixer
        frames = max(1, int(frequency * 0.045))
        samples = array("h")
        for i in range(frames):
            envelope = 1.0 - i / frames
            sample = int(2600 * envelope * math.sin(2 * math.pi * 740 * i / frequency))
            samples.extend([sample] * channels)
        try:
            return pygame.mixer.Sound(buffer=samples.tobytes())
        except pygame.error:
            return None

    def _feedback(self):
        if self.ui_sound:
            try:
                self.ui_sound.set_volume(max(0.0, min(1.0, int(self.user_data.settings.get("volume_menu", 80)) / 100)))
                self.ui_sound.play()
            except pygame.error:
                pass
        if not self.user_data.settings.get("vibration"):
            return
        try:
            if pygame.joystick.get_init() and pygame.joystick.get_count():
                joystick = pygame.joystick.Joystick(0)
                if not joystick.get_init():
                    joystick.init()
                if hasattr(joystick, "rumble"):
                    joystick.rumble(0.18, 0.22, 45)
        except pygame.error:
            pass

    def _logical_mouse(self, pos):
        screen = pygame.display.get_surface()
        if not screen:
            return pos
        width, height = screen.get_size()
        return (pos[0] * LOGICAL_W / max(width, 1), pos[1] * LOGICAL_H / max(height, 1))

    def _visible_games(self):
        games = [g for g in CATALOG if self.category == "TODOS" or self.category in g["categories"]]
        if self.search_query:
            q = _normal(self.search_query)
            games = [g for g in games if q in _normal(g["title"] + " " + g["genre"] + " " + g["developer"])]
        if self.sort_mode == 1:
            games.sort(key=lambda g: g["title"])
        elif self.sort_mode == 2:
            favorites = set(self.user_data.data.get("favorites", []))
            games.sort(key=lambda g: (g["id"] not in favorites, g["title"]))
        return games

    def _selected_game(self):
        return next((g for g in CATALOG if g["id"] == self.selected_game_id), CATALOG[0])

    def _draw_common_sidebar(self):
        """Pinta el diseño de logros con tipografía legible y estado activo."""
        draw_sidebar(self.canvas, self.sidebar_surface, self.page, self.sidebar_font)

    def _blit_contained(self, image, rect):
        """Escala arte respetando su relación de aspecto y sin estirar el pixel art."""
        if image is None or image.get_width() <= 0 or image.get_height() <= 0:
            return
        scale = min(rect.w / image.get_width(), rect.h / image.get_height())
        size = (max(1, int(image.get_width() * scale)), max(1, int(image.get_height() * scale)))
        scaled = pygame.transform.scale(image, size)
        self.canvas.blit(scaled, scaled.get_rect(center=rect.center))

    def _blit_cover(self, image, rect):
        """Llena el marco con un recorte central, conservando la proporción del arte."""
        if image is None or image.get_width() <= 0 or image.get_height() <= 0:
            return
        scale = max(rect.w / image.get_width(), rect.h / image.get_height())
        size = (max(1, round(image.get_width() * scale)), max(1, round(image.get_height() * scale)))
        scaled = pygame.transform.scale(image, size)
        area = pygame.Rect(
            max(0, (scaled.get_width() - rect.w) // 2),
            max(0, (scaled.get_height() - rect.h) // 2),
            rect.w,
            rect.h,
        )
        self.canvas.blit(scaled, rect.topleft, area)

    def _draw_library(self):
        games = self._visible_games()
        if games and self.selected_game_id not in {g["id"] for g in games}:
            self.selected_game_id = games[0]["id"]
        # Limpiar la cuadrícula y zona de paginación
        pygame.draw.rect(self.canvas, DARK, (274, 188, 580, 410))
        total_pages = max(1, (len(games) + LIBRARY_PAGE_SIZE - 1) // LIBRARY_PAGE_SIZE)
        if games:
            ids = [g["id"] for g in games]
            if self.selected_game_id in ids:
                self.library_page = ids.index(self.selected_game_id) // LIBRARY_PAGE_SIZE
        self.library_page = max(0, min(self.library_page, total_pages - 1))
        start_slot = self.library_page * LIBRARY_PAGE_SIZE

        for slot, rect in enumerate(GRID_RECTS):
            game_idx = start_slot + slot
            if game_idx >= len(games):
                continue
            game = games[game_idx]
            if game["id"] == "doom":
                self._draw_doom_card(rect)
            else:
                color_card = self.color_library_cards.get(game["id"])
                if color_card is not None:
                    self._blit_contained(color_card, rect)
                else:
                    slot_idx = game.get("slot", 0)
                    if 0 <= slot_idx < len(self.card_surfaces):
                        self.canvas.blit(self.card_surfaces[slot_idx], rect)
                    else:
                        pygame.draw.rect(self.canvas, (18, 20, 24), rect, border_radius=4)
                        self._text(game["title"], rect.x + 8, rect.centery - 6, 11, WHITE, True, rect.w - 16)
            if game["id"] == self.selected_game_id:
                pulse = 2 + int((1 + pygame.math.Vector2(1, 0).rotate(self.anim_time * 90).x) * 1.3)
                pygame.draw.rect(self.canvas, WHITE, rect.inflate(pulse * 2, pulse * 2), max(2, pulse), border_radius=5)

        if total_pages > 1:
            mouse_pos = self._logical_mouse(pygame.mouse.get_pos())
            prev_hover = LIBRARY_PREV_PAGE_RECT.collidepoint(mouse_pos)
            next_hover = LIBRARY_NEXT_PAGE_RECT.collidepoint(mouse_pos)
            pygame.draw.rect(self.canvas, (28, 30, 36) if prev_hover else (16, 17, 20), LIBRARY_PREV_PAGE_RECT, border_radius=4)
            pygame.draw.rect(self.canvas, (75, 79, 85), LIBRARY_PREV_PAGE_RECT, 1, border_radius=4)
            self._text("<", LIBRARY_PREV_PAGE_RECT.x + 11, LIBRARY_PREV_PAGE_RECT.y + 4, 13, WHITE if self.library_page > 0 else MUTED, True)

            pygame.draw.rect(self.canvas, (28, 30, 36) if next_hover else (16, 17, 20), LIBRARY_NEXT_PAGE_RECT, border_radius=4)
            pygame.draw.rect(self.canvas, (75, 79, 85), LIBRARY_NEXT_PAGE_RECT, 1, border_radius=4)
            self._text(">", LIBRARY_NEXT_PAGE_RECT.x + 11, LIBRARY_NEXT_PAGE_RECT.y + 4, 13, WHITE if self.library_page < total_pages - 1 else MUTED, True)

            page_label = f"PÁG {self.library_page + 1} / {total_pages}"
            self._text(page_label, 526, 565, 11, LIGHT, True, 88)

        self._draw_category_highlight()
        self._draw_game_detail(self._selected_game())
        pygame.draw.rect(self.canvas, DARK, (160, 649, 550, 43))
        hint = "←→ ELEGIR   Q/E FILTRO   PgUp/Dn PÁGINA   ENTER JUGAR   F FAVORITO   F3 BUSCAR"
        self._text(hint, 188, 668, 11, MUTED, max_width=510)
        if self.search_query:
            self._text(f"BÚSQUEDA: {self.search_query}", 283, 584, 13, WHITE, max_width=520)
        if self.search_active:
            self._draw_search_modal()

    def _draw_doom_card(self, rect):
        pygame.draw.rect(self.canvas, (12, 13, 15), rect, border_radius=5)
        pygame.draw.rect(self.canvas, (165, 169, 176), rect, 2, border_radius=5)
        pygame.draw.rect(self.canvas, (42, 44, 48), rect.inflate(-8, -8), 1, border_radius=3)
        banner_path = ROOT / "assets_cards" / "doom_clean.png"
        try:
            banner = pygame.image.load(str(banner_path)).convert()
            max_w, max_h = rect.w - 12, 44
            scale = min(max_w / banner.get_width(), max_h / banner.get_height())
            banner = pygame.transform.scale(banner, (int(banner.get_width() * scale), int(banner.get_height() * scale)))
            self.canvas.blit(banner, banner.get_rect(center=(rect.centerx, rect.y + 43)))
        except (pygame.error, OSError):
            self._text("DOOM", rect.x + 26, rect.y + 36, 18, WHITE, True)
        self._text("DOOM", rect.x + 33, rect.bottom - 27, 13, WHITE, True)

    def _draw_category_highlight(self):
        try:
            index = CATEGORIES.index(self.category)
        except ValueError:
            index = 0
        rect = CATEGORY_RECTS[index]
        pygame.draw.rect(self.canvas, WHITE, rect, 2, border_radius=4)

    def _draw_game_detail(self, game):
        """Ficha única, alineada al panel de la plantilla y con arte sin deformar."""
        outer = pygame.Rect(858, 132, 402, 474)
        pygame.draw.rect(self.canvas, (8, 9, 11), outer, border_radius=8)
        pygame.draw.rect(self.canvas, (118, 122, 129), outer, 2, border_radius=8)
        area = outer.inflate(-10, -10)
        pygame.draw.rect(self.canvas, PANEL, area, border_radius=6)
        self._text(game["title"], 880, 154, 18, WHITE, True, 350)
        self._text(game["tags"], 880, 184, 11, LIGHT, max_width=210)
        if game["id"] in self.user_data.data.get("favorites", []):
            self._text("★ FAVORITO", 1090, 184, 10, WHITE, True, 140)

        thumb_rect = pygame.Rect(878, 207, 360, 143)
        pygame.draw.rect(self.canvas, (15, 16, 18), thumb_rect, border_radius=4)
        detail_art = self.color_library_art.get(game["id"])
        if detail_art is not None:
            self._blit_cover(detail_art, thumb_rect.inflate(-8, -8))
        else:
            self._blit_contained(self.game_art[game["id"]], thumb_rect.inflate(-8, -8))
        pygame.draw.rect(self.canvas, (72, 76, 82), thumb_rect, 1, border_radius=4)

        self._wrap(game["subtitle"], 880, 358, 346, 13, LIGHT, max_lines=2)
        self._text(f"DESARROLLADOR: {game['developer']}", 880, 401, 11, MUTED, max_width=345)
        self._text(f"AÑO: {game['year']}   JUGADORES: {game['players']}", 880, 424, 11, MUTED, max_width=345)
        self._text(f"GÉNERO: {game['genre']}", 880, 447, 11, MUTED, max_width=345)
        stats = self.user_data.data.get("game_stats", {}).get(game["id"], {})
        progress = int(stats.get("progress", 0))
        self._text(f"TIEMPO HACIA META (4H): {progress}%", 880, 473, 11, LIGHT)
        bar = pygame.Rect(880, 492, 174, 11)
        pygame.draw.rect(self.canvas, (24, 25, 28), bar, border_radius=5)
        pygame.draw.rect(self.canvas, (150, 154, 160), (bar.x, bar.y, int(bar.w * progress / 100), bar.h), border_radius=5)
        pygame.draw.rect(self.canvas, (130, 134, 140), bar, 1, border_radius=5)
        button = pygame.Rect(1082, 529, 150, 43)
        available = self._is_available(game)
        pygame.draw.rect(self.canvas, (35, 37, 41) if available else (20, 21, 23), button, border_radius=5)
        pygame.draw.rect(self.canvas, (215, 217, 220) if available else (90, 92, 96), button, 2, border_radius=5)
        self._text("JUGAR" if available else "NO DISPONIBLE", button.x + 12, button.y + 13, 12, WHITE if available else MUTED, True, button.w - 20)
        if not available:
            self._text("Revisá la instalación del juego.", 880, 558, 10, MUTED, max_width=190)

    def _is_available(self, game):
        if "external" in game:
            folder, entry = game["external"]
            return (ROOT / folder / entry).is_file()
        return True

    def _draw_profile(self):
        name = str(self.user_data.data.get("player_name", "CAMI"))[:18]
        avatar_count = max(1, len(self.avatar_surfaces))
        avatar_index = int(self.user_data.data.get("avatar", 0)) % avatar_count
        # Retrato original con su marco integrado en el asset del kit.
        pygame.draw.rect(self.canvas, DARK, (360, 185, 422, 130))
        if self.avatar_surfaces:
            self._blit_contained(self.avatar_surfaces[avatar_index], pygame.Rect(300, 180, 116, 136))
        self._text("JUGADOR", 445, 184, 13, MUTED)
        self._text(name, 445, 207, 24, WHITE, True, 270)
        edit_icon = self.profile_icons.get("edit")
        if edit_icon is not None:
            self.canvas.blit(pygame.transform.scale(edit_icon, (28, 28)), (746, 203))

        # Botón Cambiar Usuario (conduce a USER_SELECT)
        btn_switch = pygame.Rect(620, 178, 120, 24)
        pygame.draw.rect(self.canvas, (18, 24, 36), btn_switch, border_radius=4)
        pygame.draw.rect(self.canvas, (0, 229, 255), btn_switch, 1, border_radius=4)
        self._text("CAMBIAR USUARIO", btn_switch.x + 8, btn_switch.y + 6, 9, (0, 229, 255), True)

        seconds = int(self.user_data.data.get("total_seconds", 0))
        xp = (seconds // 60) * 10
        level = xp // 1000 + 1
        level_xp = xp % 1000
        self._text(f"NIVEL {level}", 445, 248, 16, LIGHT, True)
        self._text(f"EXP {level_xp} / 1000", 634, 252, 13, LIGHT, max_width=150)
        pygame.draw.rect(self.canvas, (18, 19, 21), (445, 281, 290, 13), border_radius=3)
        pygame.draw.rect(self.canvas, (204, 207, 211), (445, 281, int(290 * level_xp / 1000), 13), border_radius=3)
        pygame.draw.rect(self.canvas, MID, (445, 281, 290, 13), 1, border_radius=3)
        hours, mins = divmod(seconds // 60, 60)
        percent = min(100, int(self.user_data.unlocked_count() / 56 * 100))
        last = self.user_data.data.get("last_session", "")
        if last:
            try:
                last = datetime.fromisoformat(last).strftime("%d/%m/%Y")
            except ValueError:
                last = "—"
        else:
            last = "—"
        pygame.draw.rect(self.canvas, DARK, (292, 319, 504, 66))
        for x, icon_key, label, value in (
            (303, "clock", "TIEMPO TOTAL", f"{hours:02d} h {mins:02d} min"),
            (464, "trophy", "PROGRESO GENERAL", f"{percent}%"),
            (621, "calendar", "ÚLTIMA SESIÓN", last),
        ):
            icon = self.profile_icons.get(icon_key)
            if icon is not None:
                self.canvas.blit(pygame.transform.scale(icon, (20, 20)), (x + 1, 341))
            text_x = x + 25
            self._text(label, text_x, 330, 9, MUTED, max_width=132)
            self._text(value, text_x, 352, 12, WHITE, True, 132)
        # Selector clicable de los 8 avatares en rejilla 2x4.
        if self.avatar_surfaces:
            for i in range(len(self.avatar_surfaces)):
                col = i % 4
                row = i // 4
                w, h = 90, 80
                rect = pygame.Rect(315 + col * 114, 415 + row * 92, w, h)
                frame = pygame.transform.scale(self.avatar_surfaces[i], rect.size)
                self.canvas.blit(frame, rect)
                if i == avatar_index:
                    pygame.draw.rect(self.canvas, (0, 229, 255), rect.inflate(4, 4), 2, border_radius=4)
        # Partidas guardadas: datos reales de sesiones recientes.
        pygame.draw.rect(self.canvas, DARK, (832, 194, 403, 366))
        history = self.user_data.data.get("history", [])[:4]
        pygame.draw.rect(self.canvas, DARK, (837, 163, 398, 28))
        self._text("SESIONES RECIENTES", 843, 170, 14, WHITE, True)
        for row in range(4):
            y = 199 + row * 89
            rect = pygame.Rect(837, y, 399, 80)
            pygame.draw.rect(self.canvas, (12, 13, 15), rect, border_radius=6)
            pygame.draw.rect(self.canvas, (75, 79, 85), rect, 1, border_radius=6)
            if row < len(history):
                item = history[row]
                game = next((g for g in CATALOG if g["id"] == item.get("id")), None)
                if game:
                    crop_rect = pygame.Rect(rect.x + 7, rect.y + 8, 120, 64)
                    self._blit_contained(self.game_art[game["id"]], crop_rect)
                title = item.get("title", "JUEGO")
                date = item.get("date", "—")
                elapsed = int(item.get("seconds", 0))
                h_play, m_play = divmod(elapsed // 60, 60)
                self._text(title, rect.x + 137, rect.y + 11, 14, WHITE, True, 245)
                self._text("SESIÓN REGISTRADA", rect.x + 137, rect.y + 35, 10, MUTED, max_width=245)
                self._text(f"{date} {item.get('time', '')}  {h_play:02d}h {m_play:02d}m", rect.x + 137, rect.y + 54, 10, LIGHT, max_width=245)
            else:
                self._text("SIN PARTIDAS GUARDADAS", rect.x + 14, rect.y + 28, 11, MUTED)
        self._text("F2 EDITAR NOMBRE   F3 CAMBIAR USUARIO   ←→ CAMBIAR AVATAR", 192, 665, 12, MUTED, max_width=580)

    def _achievement_game_for_row(self, item):
        return item.get("game_id")

    def _achievement_rows_for_filter(self):
        rows = self.user_data.achievement_rows()
        selected_game = self.selected_achievement_game
        if not selected_game:
            return list(enumerate(rows))
        return [(index, item) for index, item in enumerate(rows) if item.get("game_id") == selected_game]

    def _change_achievement_filter(self, direction):
        filters = [game["id"] for game in CATALOG]
        try:
            current = filters.index(self.selected_achievement_game)
        except ValueError:
            current = 0
        current = (current + direction) % len(filters)
        self.selected_achievement_game = filters[current]
        self.achievement_game_offset = current
        filtered = self._achievement_rows_for_filter()
        if filtered:
            self.selected_achievement = filtered[0][0]

    def _achievement_game_tiles(self):
        count = len(CATALOG)
        start = self.achievement_game_offset % max(1, count)
        return [CATALOG[(start + slot) % count] for slot in range(5)]

    def _achievement_display_title(self, item):
        title = str(item.get("title", "")).title()
        return title.replace("C.c.i.", "C.C.I.").replace("Doom", "DOOM")

    def _draw_achievement_sprite(self, key, rect):
        sprite = self.achievement_sprites.get(key)
        if sprite is None:
            return False
        scale = min(rect.w / sprite.get_width(), rect.h / sprite.get_height())
        size = (max(1, round(sprite.get_width() * scale)), max(1, round(sprite.get_height() * scale)))
        image = pygame.transform.scale(sprite, size)
        self.canvas.blit(image, image.get_rect(center=rect.center))
        return True

    def _draw_achievement_game_art(self, game_id, item, rect):
        if game_id and self._draw_achievement_sprite(f"game_{game_id}", rect):
            return
        art = self.game_art.get(game_id)
        if art:
            self.canvas.blit(pygame.transform.scale(art, rect.size), rect)
            return
        self._draw_achievement_icon(item, rect.center, min(rect.w, rect.h))

    def _draw_achievements(self):
        rows = self.user_data.achievement_rows()
        if not rows:
            return
        unlocked = sum(1 for item in rows if item["unlocked"])
        pct = int(unlocked / len(rows) * 100)
        filtered = self._achievement_rows_for_filter()
        indices = [index for index, _item in filtered]
        if indices and self.selected_achievement not in indices:
            self.selected_achievement = indices[0]
        selected_position = indices.index(self.selected_achievement) if indices else 0

        # Perfil de jugador en el hueco superior derecho de la plantilla.
        pygame.draw.rect(self.canvas, (7, 8, 10), (951, 29, 216, 53))
        pygame.draw.rect(self.canvas, (76, 79, 84), pygame.Rect(951, 29, 216, 53), 1)
        avatar_index = int(self.user_data.data.get("avatar", 0)) % 8
        self._draw_achievement_sprite(f"avatar_{avatar_index}", pygame.Rect(954, 31, 54, 48))
        player = str(self.user_data.data.get("player_name", "JUGADOR")).strip() or "JUGADOR"
        self._text(player.upper(), 1018, 33, 12, WHITE, True, 139)
        total_seconds = int(self.user_data.data.get("total_seconds", 0))
        level = 1 + total_seconds // 3600
        self._text(f"NIVEL {level}  ·  {unlocked} LOGROS", 1018, 50, 9, LIGHT, max_width=139)
        self._draw_achievement_progress(pygame.Rect(1018, 69, 146, 8), (total_seconds % 3600) / 3600)

        # La plantilla ya contiene el trofeo, la etiqueta y el marco de progreso.
        # Se reemplazan únicamente los marcadores numéricos del contador.
        pygame.draw.rect(self.canvas, (7, 8, 10), (885, 96, 105, 24))
        self._text(f"{unlocked} / {len(rows)}", 888, 96, 17, WHITE, True, 100)
        pygame.draw.rect(self.canvas, (7, 8, 10), (1199, 95, 42, 22))
        self._text(f"{pct}%", 1201, 96, 14, WHITE, True, 38)
        self._draw_achievement_progress(pygame.Rect(1059, 123, 176, 10), pct / 100)

        # Las cinco tarjetas llenan las ranuras originales sin tapar su marco.
        game_labels = {
            "davinci": "DA VINCI", "asteroids": "ASTEROIDS", "mario": "SUPER MARIO",
            "zelda": "ZELDA", "pacman": "PAC-MAN", "tetris": "TETRIS",
            "space_invaders": "SPACE INV.", "metalslug": "METAL SLUG", "doom": "DOOM",
            "flappy": "FLAPPY BIRD", "dino": "DINO", "ghostbusters": "GHOSTBUSTERS",
            "minecraft": "MINECRAFT", "cyberpunk": "CYBERPUNK",
            "pokemon": "POKÉMON", "fighter": "STREET FIGHTER", "sonic": "SONIC",
            "bomberman": "BOMBERMAN", "frogger": "FROGGER", "megaman": "MEGA MAN", "mkultra": "MORTAL KOMBAT",
            "castlevania": "CASTLEVANIA", "bubblebobble": "BUBBLE BOBBLE", "plantsvszombies": "PLANTS VS ZOMBIES",
            "donkeykong": "DONKEY KONG", "qbert": "Q*BERT",
        }
        for tile, game in zip(ACHIEVEMENT_GAME_TILE_RECTS, self._achievement_game_tiles()):
            active = self.selected_achievement_game == game["id"]
            art_rect = pygame.Rect(tile.x + 7, tile.y + 5, tile.w - 14, 50)
            self._draw_achievement_game_art(game["id"], {"unlocked": False, "goal": 1, "title": game["title"]}, art_rect)
            self._text(game_labels.get(game["id"], game["title"]).upper(), tile.x + 4, tile.y + 61, 9, WHITE if active else LIGHT, active, tile.w - 8)
            if active:
                pygame.draw.rect(self.canvas, WHITE, tile, 2)

        # Las cinco filas usan los marcos vacíos de la plantilla como tarjetas.
        visible_start = max(0, min(selected_position - 2, len(filtered) - 5))
        for slot in range(5):
            entry_pos = visible_start + slot
            if entry_pos >= len(filtered):
                break
            index, item = filtered[entry_pos]
            row_rect = pygame.Rect(ACHIEVEMENT_ROW_RECT.x, ACHIEVEMENT_ROW_Y[slot], ACHIEVEMENT_ROW_RECT.w, ACHIEVEMENT_ROW_RECT.h)
            selected = index == self.selected_achievement
            if selected:
                pygame.draw.rect(self.canvas, WHITE, row_rect.inflate(-2, -2), 2)
            game_id = self._achievement_game_for_row(item)
            self._draw_achievement_game_art(game_id, item, pygame.Rect(row_rect.x + 10, row_rect.y + 8, 46, 42))
            title_color = WHITE if item["unlocked"] else (183, 186, 191)
            self._text(self._achievement_display_title(item), row_rect.x + 75, row_rect.y + 10, 13, title_color, True, 350)
            self._text(item["description"], row_rect.x + 75, row_rect.y + 33, 10, LIGHT, max_width=350)
            self._draw_achievement_icon(item, (row_rect.x + 505, row_rect.centery), 34)
            status = "DESBLOQUEADO" if item["unlocked"] else "PENDIENTE"
            self._text(status, row_rect.x + 538, row_rect.y + 9, 9, LIGHT if item["unlocked"] else MUTED, True, 92)
            progress = item.get("progress_label", f"{item['progress']}/{item['goal']}")
            self._text(progress, row_rect.x + 538, row_rect.y + 32, 10, LIGHT, max_width=85)
            if not item["unlocked"]:
                self._draw_achievement_sprite("locked", pygame.Rect(row_rect.right - 29, row_rect.y + 18, 17, 23))
            pygame.draw.line(self.canvas, (52, 55, 60), (row_rect.x + 474, row_rect.y + 7), (row_rect.x + 474, row_rect.bottom - 7), 1)

        # Ficha lateral dentro del panel vertical original.
        item = next((it for idx, it in filtered if idx == self.selected_achievement), filtered[0][1] if filtered else rows[0])
        game_id = self._achievement_game_for_row(item)
        detail = pygame.Rect(1016, 159, 243, 460)
        icon_frame = pygame.Rect(1065, 222, 138, 130)
        if game_id:
            self._draw_achievement_game_art(game_id, item, icon_frame.inflate(-22, -22))
        else:
            self._draw_achievement_icon(item, icon_frame.center, 76)
        if not item["unlocked"]:
            self._draw_achievement_sprite("locked", pygame.Rect(icon_frame.right - 28, icon_frame.bottom - 31, 17, 22))
        title_lines = self._wrap(self._achievement_display_title(item), detail.x + 24, 375, detail.w - 46, 14, WHITE, max_lines=2)
        desc_y = 375 + len(title_lines) * 18 + 6
        self._wrap(item["description"], detail.x + 24, desc_y, detail.w - 46, 10, LIGHT, max_lines=3)
        pygame.draw.line(self.canvas, (94, 97, 102), (detail.x + 24, 475), (detail.right - 21, 475), 1)
        status = "DESBLOQUEADO" if item["unlocked"] else "PENDIENTE"
        game = next((entry for entry in CATALOG if entry["id"] == game_id), None)
        context = f"Juego: {game['title'].title()}" if game else "Juego: C.C.I. System"
        self._text(context, detail.x + 24, 489, 9, LIGHT, max_width=detail.w - 46)
        kind = f"Tipo: {game['genre']}" if game else "Tipo: General"
        self._text(kind, detail.x + 24, 512, 9, LIGHT, max_width=detail.w - 46)
        self._text(f"Estado: {status.title()}", detail.x + 24, 535, 9, WHITE if item["unlocked"] else MUTED, max_width=detail.w - 46)
        detail_progress = item.get("progress_label", f"{item['progress']}/{item['goal']}")
        self._text(f"Progreso: {detail_progress}", detail.x + 24, 558, 9, LIGHT, max_width=detail.w - 46)

        # El footer ya trae marcos y controles: se completa solo el retrato y la ayuda.
        self._draw_achievement_sprite(f"avatar_{avatar_index}", pygame.Rect(49, 649, 94, 55))
        self._text("Revisa tus logros, trofeos y el progreso", 177, 657, 12, LIGHT, max_width=435)
        self._text("de cada juego.", 177, 675, 12, LIGHT, max_width=435)
        self._text("—", 177, 695, 10, LIGHT)

    def _achievement_icon_key(self, item):
        if not item.get("unlocked"):
            return "locked" if "LEYENDA" in str(item.get("title", "")).upper() else "silver"
        title = str(item.get("title", "")).upper()
        goal = int(item.get("goal", 1))
        if "LEYENDA" in title or "MAESTRO" in title or goal > 10:
            return "gold"
        return "silver"

    def _draw_achievement_icon(self, item, center, size):
        sprite = self.achievement_sprites.get(self._achievement_icon_key(item))
        if sprite is None:
            return
        scale = min(size / sprite.get_width(), size / sprite.get_height())
        scaled_size = (
            max(1, round(sprite.get_width() * scale)),
            max(1, round(sprite.get_height() * scale)),
        )
        scaled = pygame.transform.scale(sprite, scaled_size)
        self.canvas.blit(scaled, scaled.get_rect(center=center))

    def _draw_achievement_progress(self, rect, ratio):
        track = self.achievement_sprites.get("progress_track")
        if track is not None:
            self.canvas.blit(pygame.transform.scale(track, rect.size), rect)
        else:
            return
        inner = rect.inflate(-4, -4)
        pygame.draw.rect(self.canvas, (19, 20, 22), inner)
        if ratio > 0:
            fill = pygame.Rect(inner.x, inner.y, int(inner.w * max(0, min(1, ratio))), inner.h)
            pygame.draw.rect(self.canvas, (192, 195, 200), fill)

    def _settings_rows(self):
        return [
            ("resolution", pygame.Rect(292, 173, 485, 25), "Resolución"),
            ("fullscreen", pygame.Rect(292, 200, 485, 25), "Modo de visualización"),
            ("crt_filter", pygame.Rect(292, 227, 485, 25), "Filtro retro (CRT)"),
            ("crt_intensity", pygame.Rect(292, 254, 485, 25), "Intensidad CRT"),
            ("volume_menu", pygame.Rect(292, 327, 485, 24), "Volumen del menú"),
            ("volume_game", pygame.Rect(292, 354, 485, 24), "Volumen del juego"),
            ("volume_fx", pygame.Rect(292, 381, 485, 24), "Efectos de sonido"),
            ("vibration", pygame.Rect(292, 455, 485, 24), "Vibración"),
            ("sensitivity", pygame.Rect(292, 482, 485, 24), "Sensibilidad de control"),
            ("network_enabled", pygame.Rect(292, 557, 485, 26), "Estado de conexión"),
        ]

    def _draw_settings(self):
        settings = self.user_data.settings
        rows = self._settings_rows()
        preview = pygame.Rect(820, 172, 418, 172)
        preview_sprite = self.settings_sprites.get("preview_panel")
        if preview_sprite:
            self.canvas.blit(pygame.transform.scale(preview_sprite, preview.size), preview)
        self._text("VISTA ACTUAL DEL SISTEMA", preview.x + 18, preview.y + 19, 11, LIGHT, True, 310)
        resolution = str(settings.get("resolution", "1280 x 720"))
        self._text(resolution, preview.x + 22, preview.y + 52, 21, WHITE, True, preview.w - 44)
        mode = "PANTALLA COMPLETA" if settings.get("fullscreen") else "MODO VENTANA"
        crt = "CRT ACTIVADO" if settings.get("crt_filter") else "CRT DESACTIVADO"
        self._text(mode, preview.x + 22, preview.y + 91, 11, LIGHT, max_width=170)
        self._text(crt, preview.x + 208, preview.y + 91, 11, LIGHT, max_width=174)
        self._text(f"INTENSIDAD CRT  {int(settings.get('crt_intensity', 50))}%", preview.x + 22, preview.y + 117, 10, MUTED, max_width=260)
        display_values = {
            "resolution": str(settings.get("resolution", "1280 x 720")),
            "fullscreen": "Pantalla completa" if settings.get("fullscreen") else "Ventana",
            "crt_filter": "Activado" if settings.get("crt_filter") else "Desactivado",
            "crt_intensity": f"{int(settings.get('crt_intensity', 50))}%",
            "volume_menu": f"{int(settings.get('volume_menu', 80))}%",
            "volume_game": f"{int(settings.get('volume_game', 75))}%",
            "volume_fx": f"{int(settings.get('volume_fx', 70))}%",
            "vibration": "Activada" if settings.get("vibration") else "Desactivada",
            "sensitivity": f"{int(settings.get('sensitivity', 50))}%",
            "network_enabled": "Desconectado",
        }
        for i, (key, rect, label) in enumerate(rows):
            pygame.draw.rect(self.canvas, (19, 20, 23) if i == self.selected_setting else (8, 9, 11), rect)
            if i == self.selected_setting:
                pygame.draw.rect(self.canvas, (190, 193, 198), rect, 1)
            self._text(label, rect.x + 10, rect.y + 5, 12, WHITE if i == self.selected_setting else LIGHT, max_width=235)
            if key in {"crt_intensity", "volume_menu", "volume_game", "volume_fx", "sensitivity"}:
                value = int(settings.get(key, 50))
                slider = pygame.Rect(rect.x + 285, rect.y + 6, 145, 12)
                self._draw_settings_slider(slider, value)
                self._text(display_values[key], rect.x + 439, rect.y + 3, 12, WHITE, True)
            elif key in {"fullscreen", "crt_filter", "vibration"}:
                self._text(display_values[key], rect.x + 285, rect.y + 4, 12, WHITE, True, 135)
                switch_name = "switch_on" if settings.get(key) else "switch_off"
                switch = self.settings_sprites.get(switch_name)
                if switch:
                    switch_rect = pygame.Rect(rect.right - 55, rect.y + 1, 52, 22)
                    self.canvas.blit(pygame.transform.scale(switch, switch_rect.size), switch_rect)
            elif key == "network_enabled":
                pygame.draw.rect(self.canvas, (8, 9, 11), (rect.x + 275, rect.y + 1, 118, 24))
                network = self.settings_sprites.get("network_off")
                if network:
                    network_rect = pygame.Rect(rect.right - 100, rect.y + 1, 96, 24)
                    self.canvas.blit(pygame.transform.scale(network, network_rect.size), network_rect)
            else:
                self._text(display_values[key], rect.x + 285, rect.y + 4, 12, WHITE, True, 190)
        pygame.draw.rect(self.canvas, (15, 16, 18), (292, 584, 485, 29))
        self._text("Conectar (opcional)", 302, 591, 11, LIGHT)
        self._text("Configurar", 625, 591, 11, WHITE, True)
        ctrl = self.settings_sprites.get("controller_panel")
        if ctrl:
            ctrl_rect = pygame.Rect(812, 350, 436, 216)
            self.canvas.blit(pygame.transform.smoothscale(ctrl, ctrl_rect.size), ctrl_rect)
        self._draw_settings_button("button_primary", pygame.Rect(815, 574, 170, 40), "RESTABLECER", LIGHT)
        self._draw_settings_button("button_secondary", pygame.Rect(1065, 574, 170, 40), "GUARDAR", WHITE)
        self._text("↑↓ ELEGIR   ←→ AJUSTAR   ENTER CONFIRMAR   F PANTALLA COMPLETA", 192, 665, 11, MUTED, max_width=650)

    def _draw_settings_slider(self, rect, value):
        sprite = self.settings_sprites.get("slider_track")
        if sprite is None:
            return
        pygame.draw.rect(self.canvas, (8, 9, 11), rect.inflate(3, 3))
        self.canvas.blit(pygame.transform.scale(sprite, rect.size), rect)
        inner = rect.inflate(-4, -6)
        pygame.draw.rect(self.canvas, (23, 24, 26), inner)
        fill = pygame.Rect(inner.x, inner.y, int(inner.w * max(0, min(100, value)) / 100), inner.h)
        if fill.w:
            pygame.draw.rect(self.canvas, (196, 199, 203), fill)

    def _draw_settings_button(self, sprite_key, rect, label, color):
        sprite = self.settings_sprites.get(sprite_key)
        if sprite is None:
            return
        pygame.draw.rect(self.canvas, (8, 9, 11), rect.inflate(4, 4))
        self.canvas.blit(pygame.transform.scale(sprite, rect.size), rect)
        inner = rect.inflate(-28, -16)
        pygame.draw.rect(self.canvas, (28, 29, 32), inner)
        font = self._font(11, True)
        text_width = font.size(label)[0]
        self._text(label, rect.centerx - text_width // 2, rect.centery - 7, 11, color, True, rect.w - 34)

    def _draw_search_modal(self):
        shade = pygame.Surface((LOGICAL_W, LOGICAL_H), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 175))
        self.canvas.blit(shade, (0, 0))
        rect = pygame.Rect(340, 286, 600, 130)
        pygame.draw.rect(self.canvas, PANEL, rect, border_radius=6)
        pygame.draw.rect(self.canvas, LIGHT, rect, 2, border_radius=6)
        self._text("BUSCAR EN LA BIBLIOTECA", 370, 312, 16, WHITE, True)
        shown = self.search_query or "Escribí un título o género…"
        self._text(shown, 370, 353, 14, LIGHT if self.search_query else MUTED, max_width=530)
        self._text("ENTER APLICAR    ESC CANCELAR", 370, 384, 11, MUTED)



    def _handle_search(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.search_active = False
                    pygame.key.stop_text_input()
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.search_active = False
                    pygame.key.stop_text_input()
                    self.library_page = 0
                    games = self._visible_games()
                    if games:
                        self.selected_game_id = games[0]["id"]
                elif event.key == pygame.K_BACKSPACE:
                    self.search_query = self.search_query[:-1]
                    self.library_page = 0
            elif event.type == pygame.TEXTINPUT:
                self.search_query = (self.search_query + event.text)[:32]
                self.library_page = 0

    def _handle_key(self, key):
        if key == pygame.K_ESCAPE:
            self.state_machine.change_state("MENU")
            return True
        if key == pygame.K_F1:
            self.modal = "controls"
            return True
        page_shortcuts = {
            pygame.K_F4: "LIBRARY", pygame.K_F5: "MENU", pygame.K_F6: "PROFILE",
            pygame.K_F7: "ACHIEVEMENTS", pygame.K_F8: "SETTINGS",
            pygame.K_j: "PROFILE", pygame.K_k: "ACHIEVEMENTS", pygame.K_p: "SETTINGS",
        }
        if key == pygame.K_b:
            self.state_machine.change_state("MENU")
            return True
        if key in page_shortcuts:
            self.state_machine.change_state(page_shortcuts[key])
            return True
        if self.page == "library":
            return self._handle_library_key(key)
        if self.page == "profile":
            return self._handle_profile_key(key)
        if self.page == "achievements":
            return self._handle_achievement_key(key)
        if self.page == "settings":
            return self._handle_settings_key(key)
        return False

    def _handle_library_key(self, key):
        games = self._visible_games()
        if key in (pygame.K_F3, pygame.K_SLASH):
            self.search_active = True
            pygame.key.start_text_input()
            return True
        if key in (pygame.K_q, pygame.K_e, pygame.K_TAB):
            direction = -1 if key == pygame.K_q else 1
            self.category = CATEGORIES[(CATEGORIES.index(self.category) + direction) % len(CATEGORIES)]
            self.library_page = 0
            games = self._visible_games()
            if games:
                self.selected_game_id = games[0]["id"]
            self._feedback()
            return True
        if key in (pygame.K_PAGEUP, pygame.K_LEFTBRACKET):
            total_pages = max(1, (len(games) + LIBRARY_PAGE_SIZE - 1) // LIBRARY_PAGE_SIZE)
            if self.library_page > 0:
                self.library_page -= 1
                new_idx = self.library_page * LIBRARY_PAGE_SIZE
                if new_idx < len(games):
                    self.selected_game_id = games[new_idx]["id"]
                self._feedback()
            return True
        if key in (pygame.K_PAGEDOWN, pygame.K_RIGHTBRACKET):
            total_pages = max(1, (len(games) + LIBRARY_PAGE_SIZE - 1) // LIBRARY_PAGE_SIZE)
            if self.library_page < total_pages - 1:
                self.library_page += 1
                new_idx = self.library_page * LIBRARY_PAGE_SIZE
                if new_idx < len(games):
                    self.selected_game_id = games[new_idx]["id"]
                self._feedback()
            return True
        if key in (pygame.K_LEFT, pygame.K_a):
            self._move_game(-1, games)
            return True
        if key in (pygame.K_RIGHT, pygame.K_d):
            self._move_game(1, games)
            return True
        if key in (pygame.K_UP, pygame.K_w):
            self._move_game(-4, games)
            return True
        if key in (pygame.K_DOWN, pygame.K_s):
            self._move_game(4, games)
            return True
        if key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self._launch_selected()
            return True
        if key == pygame.K_f:
            game_id = self.selected_game_id
            favorites = self.user_data.data.setdefault("favorites", [])
            if game_id in favorites:
                favorites.remove(game_id)
                self.toast = "QUITADO DE FAVORITOS"
            else:
                favorites.append(game_id)
                self.toast = "AGREGADO A FAVORITOS"
            self.toast_until = time.monotonic() + 1.8
            self.user_data.save()
            return True
        if key == pygame.K_o:
            self.sort_mode = (self.sort_mode + 1) % 3
            self.toast = ("ORDEN: PREDETERMINADO", "ORDEN: A–Z", "ORDEN: FAVORITOS") [self.sort_mode]
            self.toast_until = time.monotonic() + 1.5
            return True
        return False

    def _move_game(self, delta, games):
        if not games:
            return
        ids = [g["id"] for g in games]
        try:
            index = ids.index(self.selected_game_id)
        except ValueError:
            index = 0
        self.selected_game_id = ids[(index + delta) % len(ids)]
        self._feedback()

    def _launch_selected(self):
        game = self._selected_game()
        if not self._is_available(game):
            self.toast = "ESTE JUEGO NO ESTÁ INSTALADO"
            self.toast_until = time.monotonic() + 2.4
            return
        start = time.monotonic()
        try:
            if "external" in game:
                folder, entry = game["external"]
                path = ROOT / folder / entry
                self.toast = f"INICIANDO {game['title']}…"
                self.toast_until = time.monotonic() + 2.0
                self._draw_toast()
                pygame.display.flip()
                env = os.environ.copy()
                env.setdefault("SDL_VIDEO_CENTERED", "1")
                subprocess.run([sys.executable, str(path)], cwd=str(path.parent), env=env, check=False)
                pygame.event.clear()
                pygame.display.set_caption("C.C.I. SYSTEM — BIBLIOTECA")
            else:
                current = pygame.display.get_surface()
                if current and current.get_size() != (LOGICAL_W, LOGICAL_H):
                    flags = pygame.FULLSCREEN if self.user_data.settings.get("fullscreen") else pygame.RESIZABLE
                    self.state_machine.screen = pygame.display.set_mode((LOGICAL_W, LOGICAL_H), flags)
                self.state_machine.change_state("PLAYING", game_key=game["game_key"])
                if current and current.get_size() != (LOGICAL_W, LOGICAL_H):
                    self._apply_settings()
            elapsed = max(1, time.monotonic() - start)
            self.user_data.record_launch(game, elapsed)
            self.toast = f"SESIÓN GUARDADA · {game['title']}"
            self.toast_until = time.monotonic() + 2.5
        except Exception as exc:
            print(f"[CCI] Error al lanzar {game['title']}: {exc}")
            self.toast = f"NO SE PUDO INICIAR {game['title']}"
            self.toast_until = time.monotonic() + 3.0

    def _handle_profile_key(self, key):
        if self.text_input_active:
            if key == pygame.K_RETURN:
                self.user_data.data["player_name"] = self.name_buffer.strip()[:18] or "JUGADOR"
                self.user_data.save()
                self.text_input_active = False
                pygame.key.stop_text_input()
            elif key == pygame.K_ESCAPE:
                self.text_input_active = False
                pygame.key.stop_text_input()
            elif key == pygame.K_BACKSPACE:
                self.name_buffer = self.name_buffer[:-1]
            return True
        if key == pygame.K_F2:
            self.text_input_active = True
            self.name_buffer = str(self.user_data.data.get("player_name", "CAMI"))
            pygame.key.start_text_input()
            return True
        if key == pygame.K_F3:
            self.state_machine.change_state("USER_SELECT")
            return True
        if key in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
            delta = -1 if key in (pygame.K_LEFT, pygame.K_a) else 1
            count = max(1, len(self.avatar_surfaces))
            self.user_data.data["avatar"] = (int(self.user_data.data.get("avatar", 0)) + delta) % count
            self.user_data.save()
            return True
        return False

    def _handle_achievement_key(self, key):
        if key == pygame.K_HOME:
            self.selected_achievement_game = None
            filtered = self._achievement_rows_for_filter()
            if filtered:
                self.selected_achievement = filtered[0][0]
            return True
        if key in (pygame.K_LEFT, pygame.K_a):
            self._change_achievement_filter(-1)
            return True
        if key in (pygame.K_RIGHT, pygame.K_d):
            self._change_achievement_filter(1)
            return True
        if key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self._feedback()
            return True
        filtered = self._achievement_rows_for_filter()
        if not filtered:
            return False
        indices = [index for index, _item in filtered]
        try:
            position = indices.index(self.selected_achievement)
        except ValueError:
            position = 0
        if key in (pygame.K_UP, pygame.K_w):
            self.selected_achievement = indices[(position - 1) % len(indices)]
            return True
        if key in (pygame.K_DOWN, pygame.K_s):
            self.selected_achievement = indices[(position + 1) % len(indices)]
            return True
        return False

    def _handle_settings_key(self, key):
        rows = self._settings_rows()
        if key in (pygame.K_UP, pygame.K_w):
            self.selected_setting = (self.selected_setting - 1) % len(rows)
            return True
        if key in (pygame.K_DOWN, pygame.K_s):
            self.selected_setting = (self.selected_setting + 1) % len(rows)
            return True
        if key in (pygame.K_LEFT, pygame.K_a):
            self._adjust_setting(-1)
            return True
        if key in (pygame.K_RIGHT, pygame.K_d, pygame.K_RETURN, pygame.K_SPACE):
            self._adjust_setting(1)
            return True
        if key == pygame.K_f:
            self.user_data.settings["fullscreen"] = not self.user_data.settings.get("fullscreen", False)
            self._apply_settings()
            return True
        return False

    def _adjust_setting(self, direction):
        key, _, _ = self._settings_rows()[self.selected_setting]
        settings = self.user_data.settings
        if key == "resolution":
            values = ["1280 x 720", "1600 x 900", "1920 x 1080"]
            try:
                index = values.index(settings.get(key, values[0]))
            except ValueError:
                index = 0
            settings[key] = values[(index + direction) % len(values)]
        elif key in {"fullscreen", "crt_filter", "vibration"}:
            settings[key] = not bool(settings.get(key, False))
        elif key == "network_enabled":
            settings[key] = False
            self.toast = "RED LOCAL NO CONFIGURADA"
            self.toast_until = time.monotonic() + 2.0
        elif key in {"crt_intensity", "volume_menu", "volume_game", "volume_fx", "sensitivity"}:
            settings[key] = max(0, min(100, int(settings.get(key, 50)) + direction * 5))
        self.user_data.save()
        if key in {"volume_menu", "volume_fx"}:
            self._feedback()
        if key in {"resolution", "fullscreen"}:
            self._apply_settings()
        elif key in {"volume_game", "volume_fx"} and pygame.mixer.get_init():
            if key == "volume_game":
                pygame.mixer.music.set_volume(int(settings[key]) / 100)
            else:
                for channel_id in range(pygame.mixer.get_num_channels()):
                    pygame.mixer.Channel(channel_id).set_volume(int(settings[key]) / 100)
        elif key == "sensitivity":
            try:
                pygame.key.set_repeat(350, max(30, 150 - int(settings[key])))
            except pygame.error:
                pass

    def _apply_settings(self):
        if self.apply_display:
            self.apply_display(self.user_data.settings)
        if self.page == "settings":
            self.scaled_size = None

    def _handle_click(self, pos):
        x, y = pos
        # Navegación lateral compartida por todas las pantallas.
        if x < SIDEBAR_W:
            destination = sidebar_destination(pos)
            if destination == "QUIT":
                pygame.event.post(pygame.event.Event(pygame.QUIT))
            elif destination:
                self.state_machine.change_state(destination)
            return
        if self.page == "library":
            for i, rect in enumerate(CATEGORY_RECTS):
                if rect.collidepoint(pos):
                    self.category = CATEGORIES[i]
                    self.library_page = 0
                    games = self._visible_games()
                    if games:
                        self.selected_game_id = games[0]["id"]
                    return
            games = self._visible_games()
            total_pages = max(1, (len(games) + LIBRARY_PAGE_SIZE - 1) // LIBRARY_PAGE_SIZE)
            if total_pages > 1:
                if LIBRARY_PREV_PAGE_RECT.collidepoint(pos):
                    if self.library_page > 0:
                        self.library_page -= 1
                        new_idx = self.library_page * LIBRARY_PAGE_SIZE
                        if new_idx < len(games):
                            self.selected_game_id = games[new_idx]["id"]
                        self._feedback()
                    return
                if LIBRARY_NEXT_PAGE_RECT.collidepoint(pos):
                    if self.library_page < total_pages - 1:
                        self.library_page += 1
                        new_idx = self.library_page * LIBRARY_PAGE_SIZE
                        if new_idx < len(games):
                            self.selected_game_id = games[new_idx]["id"]
                        self._feedback()
                    return
            start_slot = self.library_page * LIBRARY_PAGE_SIZE
            for slot, rect in enumerate(GRID_RECTS):
                if rect.collidepoint(pos):
                    game_idx = start_slot + slot
                    if game_idx < len(games):
                        self.selected_game_id = games[game_idx]["id"]
                        self._feedback()
                        if getattr(self, "last_clicked_slot", None) == game_idx and time.monotonic() - getattr(self, "last_click_time", 0) < 0.45:
                            self._launch_selected()
                        self.last_clicked_slot = game_idx
                        self.last_click_time = time.monotonic()
                    return
            if pygame.Rect(1082, 529, 150, 43).collidepoint(pos):
                self._launch_selected()
        elif self.page == "profile":
            if pygame.Rect(620, 178, 120, 24).collidepoint(pos):
                self.state_machine.change_state("USER_SELECT")
                return
            if pygame.Rect(742, 199, 38, 38).collidepoint(pos):
                self.text_input_active = True
                self.name_buffer = str(self.user_data.data.get("player_name", "CAMI"))
                pygame.key.start_text_input()
                return
            for i in range(len(self.avatar_surfaces)):
                col = i % 4
                row = i // 4
                rect = pygame.Rect(315 + col * 114, 415 + row * 92, 90, 80)
                if rect.collidepoint(pos):
                    self.user_data.data["avatar"] = i
                    self.user_data.save()
                    return
        elif self.page == "achievements":
            if ACHIEVEMENT_LEFT_ARROW_RECT.collidepoint(pos):
                self._change_achievement_filter(-1)
                self._feedback()
                return
            if ACHIEVEMENT_RIGHT_ARROW_RECT.collidepoint(pos):
                self._change_achievement_filter(1)
                self._feedback()
                return
            for rect, game in zip(ACHIEVEMENT_GAME_TILE_RECTS, self._achievement_game_tiles()):
                if rect.collidepoint(pos):
                    self.selected_achievement_game = game["id"]
                    self.achievement_game_offset = CATALOG.index(game)
                    filtered = self._achievement_rows_for_filter()
                    if filtered:
                        self.selected_achievement = filtered[0][0]
                    self._feedback()
                    return
            filtered = self._achievement_rows_for_filter()
            indices = [index for index, _item in filtered]
            try:
                selected_position = indices.index(self.selected_achievement)
            except ValueError:
                selected_position = 0
            visible_start = max(0, min(selected_position - 2, len(filtered) - 5))
            for slot, row_y in enumerate(ACHIEVEMENT_ROW_Y):
                row_rect = pygame.Rect(ACHIEVEMENT_ROW_RECT.x, row_y, ACHIEVEMENT_ROW_RECT.w, ACHIEVEMENT_ROW_RECT.h)
                if row_rect.collidepoint(pos):
                    entry_pos = visible_start + slot
                    if entry_pos < len(filtered):
                        self.selected_achievement = filtered[entry_pos][0]
                    return
        elif self.page == "settings":
            for i, (_, rect, _) in enumerate(self._settings_rows()):
                if rect.collidepoint(pos):
                    self.selected_setting = i
                    self._adjust_setting(1)
                    return
            if pygame.Rect(815, 574, 170, 40).collidepoint(pos):
                self.user_data.data["settings"] = _deep_default()["settings"]
                self.user_data.save()
                self._apply_settings()
                self.toast = "AJUSTES RESTABLECIDOS"
                self.toast_until = time.monotonic() + 1.8
            elif pygame.Rect(292, 584, 485, 29).collidepoint(pos):
                self.toast = "RED LOCAL NO CONFIGURADA"
                self.toast_until = time.monotonic() + 2.0
            elif pygame.Rect(1065, 574, 170, 40).collidepoint(pos):
                self.user_data.save()
                self.toast = "AJUSTES GUARDADOS"
                self.toast_until = time.monotonic() + 1.8

    def _handle_text_input(self, event):
        if self.text_input_active and event.type == pygame.TEXTINPUT:
            candidate = self.name_buffer + event.text
            if len(candidate) <= 18 and all(c.isprintable() for c in candidate):
                self.name_buffer = candidate

    def _draw_crt(self):
        alpha = int(8 + int(self.user_data.settings.get("crt_intensity", 50)) * 0.22)
        overlay = pygame.Surface((LOGICAL_W, LOGICAL_H), pygame.SRCALPHA)
        for y in range(0, LOGICAL_H, 4):
            pygame.draw.line(overlay, (0, 0, 0, alpha), (0, y), (LOGICAL_W, y))
        self.canvas.blit(overlay, (0, 0))

    def _draw_toast(self):
        if not self.toast:
            return
        rect = pygame.Rect(360, 614, 560, 38)
        pygame.draw.rect(self.canvas, (16, 17, 19), rect, border_radius=5)
        pygame.draw.rect(self.canvas, (165, 169, 175), rect, 1, border_radius=5)
        self._text(self.toast, rect.x + 14, rect.y + 11, 12, WHITE, max_width=530)

    def handle_events(self, events):
        # Text entry is handled before normal keys so F2/search work with SDL_TEXTINPUT.
        if self.search_active:
            self._handle_search(events)
            return
        if self.text_input_active:
            for event in events:
                if event.type == pygame.TEXTINPUT:
                    self._handle_text_input(event)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        self.user_data.data["player_name"] = self.name_buffer.strip()[:18] or "JUGADOR"
                        self.user_data.save()
                        self.text_input_active = False
                        pygame.key.stop_text_input()
                    elif event.key == pygame.K_ESCAPE:
                        self.text_input_active = False
                        pygame.key.stop_text_input()
                    elif event.key == pygame.K_BACKSPACE:
                        self.name_buffer = self.name_buffer[:-1]
            return
        if self.modal:
            for event in events:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.modal = ""
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        if self.modal == "quit":
                            pygame.event.post(pygame.event.Event(pygame.QUIT))
                        self.modal = ""
            return
        for event in events:
            if event.type == pygame.KEYDOWN:
                if self._handle_key(event.key):
                    continue
            elif event.type == pygame.TEXTINPUT and self.text_input_active:
                self._handle_text_input(event)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_click(self._logical_mouse(event.pos))
                return
            elif event.type == pygame.MOUSEWHEEL and self.page == "achievements":
                filtered = self._achievement_rows_for_filter()
                indices = [index for index, _item in filtered]
                if indices:
                    try:
                        position = indices.index(self.selected_achievement)
                    except ValueError:
                        position = 0
                    self.selected_achievement = indices[(position - event.y) % len(indices)]
                return

    def _draw_simple_modal(self):
        shade = pygame.Surface((LOGICAL_W, LOGICAL_H), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 190))
        self.canvas.blit(shade, (0, 0))
        rect = pygame.Rect(380, 260, 520, 180)
        pygame.draw.rect(self.canvas, (12, 13, 15), rect, border_radius=7)
        pygame.draw.rect(self.canvas, (205, 208, 213), rect, 2, border_radius=7)
        if self.modal == "quit":
            self._text("SALIR DE C.C.I. SYSTEM", 420, 296, 20, WHITE, True)
            self._text("ENTER: CONFIRMAR    ESC: CANCELAR", 420, 354, 14, LIGHT)
        elif self.modal == "controls":
            self._text("CONTROLES", 420, 292, 20, WHITE, True)
            self._text("↑↓←→ Navegar  ·  ENTER Jugar  ·  F Favorito", 420, 336, 12, LIGHT)
            self._text("F3 Buscar  ·  ESC Volver", 420, 362, 12, LIGHT)
        else:
            self._text("CONFIRMAR", 420, 296, 20, WHITE, True)
            self._text("ENTER: ACEPTAR    ESC: VOLVER", 420, 354, 14, LIGHT)

    def _draw_modal(self):
        if self.text_input_active:
            shade = pygame.Surface((LOGICAL_W, LOGICAL_H), pygame.SRCALPHA)
            shade.fill((0, 0, 0, 185))
            self.canvas.blit(shade, (0, 0))
            rect = pygame.Rect(380, 280, 520, 140)
            pygame.draw.rect(self.canvas, PANEL, rect, border_radius=7)
            pygame.draw.rect(self.canvas, LIGHT, rect, 2, border_radius=7)
            self._text("EDITAR NOMBRE", 420, 303, 18, WHITE, True)
            self._text(self.name_buffer + "_", 420, 344, 18, LIGHT, max_width=440)
            self._text("ENTER GUARDAR   ESC CANCELAR", 420, 383, 11, MUTED)
            return
        self._draw_simple_modal()
