from attack import Attack

# Catálogo completo de los 5 profesores de Da Vinci
CHARACTERS = {
    "carloni": {
        "id": "carloni",
        "name": "Juan Bautista Carloni",
        "subjects": ["Base de Datos", "HTML", "CSS", "JavaScript"],
        "health": 110,
        "speed": 5.5,
        "color": (40, 140, 220),
        "quote": "DATABASE MASTER - DROP TABLE ENEMY;",
        "attacks": {
            "punch_light": Attack("DIV Punch", damage=8, knockback=4.0, hitbox_offset=(50, 20), hitbox_size=(45, 30), startup=3, active_time=8, recovery=6, stun=10),
            "punch_heavy": Attack("CSS Flexbox", damage=18, knockback=9.0, hitbox_offset=(55, 15), hitbox_size=(60, 35), startup=7, active_time=12, recovery=12, stun=20),
            "kick_light": Attack("JS Event", damage=10, knockback=5.0, hitbox_offset=(50, 60), hitbox_size=(50, 35), startup=4, active_time=9, recovery=8, stun=12),
            "kick_heavy": Attack("SQL Query", damage=22, knockback=11.0, hitbox_offset=(60, 50), hitbox_size=(65, 40), startup=9, active_time=14, recovery=15, stun=25),
            "special": Attack("SELECT * FROM ENEMY", damage=25, knockback=12.0, hitbox_offset=(70, 30), hitbox_size=(80, 50), startup=12, active_time=15, recovery=20, stun=30, effects=["sql_beam"]),
            "ultimate": Attack("DROP TABLE", damage=45, knockback=16.0, hitbox_offset=(60, 10), hitbox_size=(100, 100), startup=20, active_time=25, recovery=30, stun=45, effects=["drop_table"])
        }
    },

    "cavasso": {
        "id": "cavasso",
        "name": "Gabriel Ernesto Cavasso",
        "subjects": ["Aplicaciones Móviles", "Python", "Ciberseguridad"],
        "health": 100,
        "speed": 6.5,
        "color": (50, 200, 100),
        "quote": "SYSTEM BREACH - ACCESS GRANTED",
        "attacks": {
            "punch_light": Attack("Python Touch", damage=7, knockback=3.5, hitbox_offset=(45, 20), hitbox_size=(40, 30), startup=3, active_time=7, recovery=5, stun=9),
            "punch_heavy": Attack("Debug Strike", damage=16, knockback=7.5, hitbox_offset=(50, 15), hitbox_size=(50, 35), startup=6, active_time=11, recovery=11, stun=18),
            "kick_light": Attack("Scan Sweep", damage=9, knockback=4.5, hitbox_offset=(45, 60), hitbox_size=(45, 35), startup=4, active_time=8, recovery=7, stun=11),
            "kick_heavy": Attack("Brute Force", damage=24, knockback=10.0, hitbox_offset=(55, 50), hitbox_size=(60, 40), startup=8, active_time=13, recovery=14, stun=24),
            "special": Attack("PYTHON SNAKE", damage=22, knockback=8.0, hitbox_offset=(80, 40), hitbox_size=(75, 45), startup=10, active_time=16, recovery=18, stun=25, effects=["snake"]),
            "ultimate": Attack("SYSTEM BREACH", damage=42, knockback=14.0, hitbox_offset=(60, 10), hitbox_size=(95, 95), startup=18, active_time=24, recovery=28, stun=40, effects=["breach"])
        }
    },

    "romero": {
        "id": "romero",
        "name": "Facundo Iván Romero",
        "subjects": ["Organización Empresarial", "Telecomunicaciones"],
        "health": 105,
        "speed": 6.0,
        "color": (220, 120, 40),
        "quote": "REUNIÓN DE 10 AM - AGENDA COMPLETA",
        "attacks": {
            "punch_light": Attack("Signal Packet", damage=8, knockback=4.0, hitbox_offset=(50, 20), hitbox_size=(45, 30), startup=3, active_time=8, recovery=6, stun=10),
            "punch_heavy": Attack("Radio Wave", damage=17, knockback=8.0, hitbox_offset=(55, 15), hitbox_size=(55, 35), startup=7, active_time=12, recovery=12, stun=19),
            "kick_light": Attack("Cable Hook", damage=10, knockback=5.0, hitbox_offset=(50, 60), hitbox_size=(50, 35), startup=4, active_time=9, recovery=8, stun=12),
            "kick_heavy": Attack("Congestion", damage=21, knockback=9.5, hitbox_offset=(60, 50), hitbox_size=(60, 40), startup=9, active_time=14, recovery=15, stun=23),
            "special": Attack("REUNIÓN 10:00 AM", damage=20, knockback=6.0, hitbox_offset=(65, 30), hitbox_size=(70, 50), startup=11, active_time=18, recovery=22, stun=35, effects=["meeting"]),
            "ultimate": Attack("CORPORATE NETWORK", damage=40, knockback=15.0, hitbox_offset=(60, 10), hitbox_size=(90, 90), startup=19, active_time=25, recovery=29, stun=42, effects=["network"])
        }
    },

    "gamaliel": {
        "id": "gamaliel",
        "name": "Gamaliel Natanael",
        "subjects": ["Java", "Programación Orientada a Objetos"],
        "health": 115,
        "speed": 5.0,
        "color": (200, 50, 50),
        "quote": "OBJECT ORIENTED SYSTEM INHERITED",
        "attacks": {
            "punch_light": Attack("Java Method", damage=9, knockback=4.5, hitbox_offset=(50, 20), hitbox_size=(45, 30), startup=4, active_time=8, recovery=7, stun=11),
            "punch_heavy": Attack("Class Instantiation", damage=20, knockback=10.0, hitbox_offset=(55, 15), hitbox_size=(60, 35), startup=8, active_time=13, recovery=13, stun=22),
            "kick_light": Attack("Encapsulation", damage=11, knockback=5.5, hitbox_offset=(50, 60), hitbox_size=(50, 35), startup=5, active_time=9, recovery=9, stun=13),
            "kick_heavy": Attack("Inheritance Kick", damage=23, knockback=11.5, hitbox_offset=(60, 50), hitbox_size=(65, 40), startup=10, active_time=15, recovery=16, stun=26),
            "special": Attack("EXCEPTION ERROR", damage=24, knockback=7.0, hitbox_offset=(70, 30), hitbox_size=(75, 50), startup=12, active_time=16, recovery=20, stun=38, effects=["exception"]),
            "ultimate": Attack("OBJECT ORIENTED SYSTEM", damage=48, knockback=18.0, hitbox_offset=(60, 10), hitbox_size=(105, 105), startup=22, active_time=26, recovery=32, stun=45, effects=["oop"])
        }
    },

    "sellanes": {
        "id": "sellanes",
        "name": "Sellanes Luca",
        "subjects": ["Ingeniería de Requerimientos"],
        "health": 95,
        "speed": 7.0,
        "color": (180, 80, 220),
        "quote": "EL CLIENTE CAMBIÓ LOS REQUISITOS",
        "attacks": {
            "punch_light": Attack("Requisito Strike", damage=7, knockback=3.5, hitbox_offset=(45, 20), hitbox_size=(40, 30), startup=2, active_time=6, recovery=5, stun=8),
            "punch_heavy": Attack("Relevamiento", damage=15, knockback=7.0, hitbox_offset=(50, 15), hitbox_size=(50, 35), startup=5, active_time=10, recovery=10, stun=17),
            "kick_light": Attack("Validation Kick", damage=9, knockback=4.0, hitbox_offset=(45, 60), hitbox_size=(45, 35), startup=3, active_time=8, recovery=6, stun=10),
            "kick_heavy": Attack("Specification", damage=20, knockback=9.0, hitbox_offset=(55, 50), hitbox_size=(55, 40), startup=7, active_time=12, recovery=13, stun=21),
            "special": Attack("CAMBIO DE REQUISITOS", damage=23, knockback=9.0, hitbox_offset=(75, 30), hitbox_size=(80, 45), startup=9, active_time=15, recovery=17, stun=30, effects=["req_change"]),
            "ultimate": Attack("CLIENTE CAMBIÓ REQUISITOS", damage=44, knockback=15.0, hitbox_offset=(60, 10), hitbox_size=(95, 95), startup=17, active_time=25, recovery=27, stun=42, effects=["req_final"])
        }
    },

    "cami": {
        "id": "cami",
        "name": "Camila Ianni",
        "subjects": ["C.C.I. System Master", "Arquitectura FSM", "Cyber Combat"],
        "health": 120,
        "speed": 6.8,
        "width": 160,
        "height": 260,
        "color": (160, 40, 240),
        "quote": "C.C.I. SYSTEM ONLINE - PREPARE TO FIGHT",
        "attacks": {
            "punch_light": Attack("Cyber Palm", damage=9, knockback=4.0, hitbox_offset=(80, 50), hitbox_size=(80, 50), startup=8, active_time=14, recovery=12, stun=16),
            "punch_heavy": Attack("Ki Burst Strike", damage=19, knockback=8.5, hitbox_offset=(90, 40), hitbox_size=(95, 60), startup=12, active_time=18, recovery=18, stun=26),
            "kick_light": Attack("Low Cyber Kick", damage=10, knockback=4.5, hitbox_offset=(80, 140), hitbox_size=(85, 60), startup=9, active_time=14, recovery=13, stun=18),
            "kick_heavy": Attack("Timed Axe Kick", damage=24, knockback=10.5, hitbox_offset=(95, 100), hitbox_size=(105, 75), startup=14, active_time=20, recovery=20, stun=30),
            "special": Attack("PURPLE MULTI-STRIKE", damage=26, knockback=11.0, hitbox_offset=(110, 60), hitbox_size=(130, 85), startup=15, active_time=24, recovery=22, stun=36, effects=["purple_flame"]),
            "ultimate": Attack("MAX KI OVERDRIVE", damage=48, knockback=17.0, hitbox_offset=(90, 20), hitbox_size=(160, 160), startup=22, active_time=30, recovery=30, stun=48, effects=["overdrive"])
        }
    },

    "enith": {
        "id": "enith",
        "name": "Enith Mendoza",
        "subjects": ["Fuerza Andina", "Invocación Ancestral", "Poder Solar"],
        "health": 125,
        "speed": 6.5,
        "width": 160,
        "height": 260,
        "color": (230, 140, 40),
        "quote": "EL PODER ANDINO Y LOS CUYS GUÍAN MI PUÑO",
        "attacks": {
            "punch_light": Attack("Jab de Boxeadora", damage=10, knockback=4.2, hitbox_offset=(80, 50), hitbox_size=(80, 50), startup=8, active_time=14, recovery=12, stun=16),
            "punch_heavy": Attack("Directo Andino", damage=20, knockback=9.0, hitbox_offset=(90, 40), hitbox_size=(95, 60), startup=12, active_time=18, recovery=18, stun=26),
            "kick_light": Attack("Patada Baja Solar", damage=11, knockback=4.8, hitbox_offset=(80, 140), hitbox_size=(85, 60), startup=9, active_time=14, recovery=13, stun=18),
            "kick_heavy": Attack("Patada Alta Andina", damage=25, knockback=11.0, hitbox_offset=(95, 80), hitbox_size=(105, 75), startup=14, active_time=20, recovery=20, stun=30),
            "special": Attack("ATAQUE DE CUYS", damage=27, knockback=11.5, hitbox_offset=(110, 60), hitbox_size=(130, 85), startup=15, active_time=24, recovery=22, stun=36, effects=["cuy_swarm"]),
            "ultimate": Attack("FURIA SOLAR ANDINA", damage=50, knockback=18.0, hitbox_offset=(90, 20), hitbox_size=(160, 160), startup=22, active_time=30, recovery=30, stun=48, effects=["solar_flare"])
        }
    },

    "martin": {
        "id": "martin",
        "name": "Martín",
        "subjects": ["Fisicoquímica Láctea", "Óptica Prismática", "Lucha Retro"],
        "health": 120,
        "speed": 6.7,
        "width": 160,
        "height": 260,
        "color": (60, 160, 240),
        "quote": "TODO TIENE SOLUCIÓN CON UN BUEN SACHET",
        "attacks": {
            "punch_light": Attack("Puño Retro", damage=10, knockback=4.0, hitbox_offset=(80, 50), hitbox_size=(80, 50), startup=8, active_time=14, recovery=12, stun=16),
            "punch_heavy": Attack("Puño Lácteo Directo", damage=20, knockback=9.0, hitbox_offset=(90, 40), hitbox_size=(95, 60), startup=12, active_time=18, recovery=18, stun=26),
            "kick_light": Attack("Lanzamiento de Sachet", damage=11, knockback=4.5, hitbox_offset=(80, 100), hitbox_size=(85, 60), startup=9, active_time=14, recovery=13, stun=18),
            "kick_heavy": Attack("Patada Rompedora", damage=24, knockback=10.5, hitbox_offset=(95, 90), hitbox_size=(105, 75), startup=13, active_time=19, recovery=19, stun=28),
            "special": Attack("LLUVIA DE LECHE", damage=28, knockback=11.5, hitbox_offset=(110, 60), hitbox_size=(130, 85), startup=15, active_time=24, recovery=22, stun=36, effects=["milk_splash"]),
            "ultimate": Attack("PRISMAS ARCOÍRIS", damage=49, knockback=18.0, hitbox_offset=(90, 20), hitbox_size=(160, 160), startup=22, active_time=30, recovery=30, stun=48, effects=["rainbow_prism"])
        }
    }
}


def get_character_data(char_id):
    """Retorna los datos y ataques de un personaje por su ID (ej. 'carloni')."""
    return CHARACTERS.get(char_id, CHARACTERS["carloni"])
