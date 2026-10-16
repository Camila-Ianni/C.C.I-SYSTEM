"""
Synthesized 16-bit arcade sound effects for Metal Slug 1 weapons.
Provides crisp, punchy audio without external missing WAV dependencies.
"""
import numpy as np
import pygame

def generate_weapon_sfx():
    sfx = {}
    sr = 44100

    try:
        # 1. Pistol Gunshot (sharp transient crack + 160Hz punch)
        n = int(sr * 0.14)
        t = np.linspace(0, 0.14, n)
        noise = np.random.uniform(-1, 1, n) * np.exp(-t * 70)
        punch = np.sin(2 * np.pi * 210 * np.exp(-t * 45) * t) * np.exp(-t * 35)
        sig = 0.65 * noise + 0.35 * punch
        sig = (sig / np.max(np.abs(sig)) * 32767 * 0.95).astype(np.int16)
        sfx["gunshot"] = pygame.sndarray.make_sound(np.column_stack((sig, sig)))

        # 2. Heavy Machine Gun (rapid metallic percussive crack with high bite)
        n = int(sr * 0.09)
        t = np.linspace(0, 0.09, n)
        noise = np.random.uniform(-1, 1, n) * np.exp(-t * 90)
        metal = np.sin(2 * np.pi * 320 * np.exp(-t * 55) * t) * np.exp(-t * 50)
        click = np.sin(2 * np.pi * 1200 * t) * np.exp(-t * 120)
        sig = 0.5 * noise + 0.35 * metal + 0.15 * click
        sig = (sig / np.max(np.abs(sig)) * 32767 * 0.98).astype(np.int16)
        sfx["heavy_machine_gun_shot"] = pygame.sndarray.make_sound(np.column_stack((sig, sig)))

        # 3. Shotgun Blast (massive sub-bass thunder boom + expanding pressure cone)
        n = int(sr * 0.40)
        t = np.linspace(0, 0.40, n)
        noise = np.random.uniform(-1, 1, n) * np.exp(-t * 12)
        sub_bass = np.sin(2 * np.pi * 75 * np.exp(-t * 8) * t) * np.exp(-t * 10)
        rumble = np.sin(2 * np.pi * 45 * t) * np.exp(-t * 6)
        sig = 0.55 * noise + 0.30 * sub_bass + 0.15 * rumble
        sig = (sig / np.max(np.abs(sig)) * 32767 * 0.99).astype(np.int16)
        sfx["shotgun_blast"] = pygame.sndarray.make_sound(np.column_stack((sig, sig)))

        # 4. Rocket Missile Launch (whoosh whistle + roaring rocket propellant)
        n = int(sr * 0.32)
        t = np.linspace(0, 0.32, n)
        ignition = np.random.uniform(-1, 1, n) * (1 - np.exp(-t * 25)) * np.exp(-t * 7)
        whistle = np.sin(2 * np.pi * (280 + 450 * t) * t) * np.exp(-t * 9)
        sig = 0.65 * ignition + 0.35 * whistle
        sig = (sig / np.max(np.abs(sig)) * 32767 * 0.95).astype(np.int16)
        sfx["rocket_fire"] = pygame.sndarray.make_sound(np.column_stack((sig, sig)))

        # 5. Flame Shot (roaring combustion fireball ignition)
        n = int(sr * 0.38)
        t = np.linspace(0, 0.38, n)
        flame_noise = np.random.uniform(-1, 1, n) * np.exp(-t * 8)
        combustion = np.sin(2 * np.pi * 110 * np.exp(-t * 4) * t) * np.exp(-t * 6)
        sig = 0.75 * flame_noise + 0.25 * combustion
        sig = (sig / np.max(np.abs(sig)) * 32767 * 0.95).astype(np.int16)
        sfx["flame_fire"] = pygame.sndarray.make_sound(np.column_stack((sig, sig)))

        # 6. Knife Slash (crisp metallic razor slice whoosh)
        n = int(sr * 0.13)
        t = np.linspace(0, 0.13, n)
        slice_air = np.random.uniform(-1, 1, n) * np.exp(-t * 45)
        blade_ring = np.sin(2 * np.pi * 1650 * t) * np.exp(-t * 30)
        sig = 0.45 * slice_air + 0.55 * blade_ring
        sig = (sig / np.max(np.abs(sig)) * 32767 * 0.90).astype(np.int16)
        sfx["knife"] = pygame.sndarray.make_sound(np.column_stack((sig, sig)))

        # 7. Grenade Bounce (metallic impact tap)
        n = int(sr * 0.08)
        t = np.linspace(0, 0.08, n)
        ping = np.sin(2 * np.pi * 850 * np.exp(-t * 30) * t) * np.exp(-t * 50)
        sig = (ping / np.max(np.abs(ping)) * 32767 * 0.75).astype(np.int16)
        sfx["grenade_bounce"] = pygame.sndarray.make_sound(np.column_stack((sig, sig)))

    except Exception as e:
        print(f"[sfx_synth] Audio synthesis error: {e}")

    return sfx
