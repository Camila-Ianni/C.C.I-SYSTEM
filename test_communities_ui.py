"""
test_communities_ui.py - Pruebas unitarias de las interfaces gráficas de Grupos y Comunidades.

Cubre:
1. 'GRUPOS' presente en las entradas del sidebar y sidebar_destination retorna 'GROUPS'.
2. Inicialización y ciclo de vida de GroupsHubState ('GROUPS').
3. Navegación en cuadrícula de comunidades (W/S/A/D y flechas).
4. Inicialización y ciclo de vida de CommunityViewState ('COMMUNITY').
5. Envío y renderizado interactivo de mensajes en el chat de la comunidad.
"""

import os
import tempfile
import unittest
import pygame

from sidebar_ui import ENTRIES, sidebar_destination, NAV_ROW_TOP, NAV_ROW_STEP
from states import StateMachine
from groups_ui import GroupsHubState, CommunityViewState, COMMUNITIES_CATALOG


class TestCommunitiesUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.init()
        pygame.font.init()
        pygame.display.set_mode((1280, 720))

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_ui.sqlite3")
        screen = pygame.display.get_surface()
        self.sm = StateMachine(screen)
        self.hub_state = GroupsHubState(self.sm, db_path=self.db_path)
        self.comm_state = CommunityViewState(self.sm, db_path=self.db_path)
        self.sm.register_state("GROUPS", self.hub_state)
        self.sm.register_state("COMMUNITY", self.comm_state)

    def tearDown(self):
        self.hub_state.bridge.repo.close()
        self.comm_state.bridge.repo.close()
        self.temp_dir.cleanup()

    def test_01_sidebar_entries_and_destination(self):
        """Verifica que GRUPOS esté en el sidebar y sidebar_destination resuelva a GROUPS."""
        labels = [e[0] for e in ENTRIES]
        destinations = [e[2] for e in ENTRIES]
        self.assertIn("GRUPOS", labels)
        self.assertIn("GROUPS", destinations)

        # La posición Y de GRUPOS es index 2: NAV_ROW_TOP + 2 * NAV_ROW_STEP
        groups_y = NAV_ROW_TOP + 2 * NAV_ROW_STEP + 10
        dest = sidebar_destination((80, groups_y))
        self.assertEqual(dest, "GROUPS")

    def test_02_groups_hub_initialization_and_enter(self):
        """Verifica inicialización de GroupsHubState y catálogo de comunidades."""
        self.assertEqual(len(COMMUNITIES_CATALOG), 6)
        self.sm.change_state("GROUPS")
        self.assertEqual(self.sm.current_state_name, "GROUPS")
        self.assertEqual(self.hub_state.selected_index, 0)
        self.assertEqual(self.hub_state.active_tab, 0)

    def test_03_groups_hub_navigation_keys(self):
        """Verifica navegación con W/S/A/D en la cuadrícula 2x3 de comunidades."""
        self.sm.change_state("GROUPS")
        self.assertEqual(self.hub_state.selected_index, 0)

        # Mover a la derecha (D)
        ev_right = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d, unicode="d")
        self.hub_state.handle_events([ev_right])
        self.assertEqual(self.hub_state.selected_index, 1)

        # Mover hacia abajo (S)
        ev_down = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_s, unicode="s")
        self.hub_state.handle_events([ev_down])
        self.assertEqual(self.hub_state.selected_index, 3)

        # Mover a la izquierda (A)
        ev_left = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, unicode="a")
        self.hub_state.handle_events([ev_left])
        self.assertEqual(self.hub_state.selected_index, 2)

        # Mover hacia arriba (W)
        ev_up = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_w, unicode="w")
        self.hub_state.handle_events([ev_up])
        self.assertEqual(self.hub_state.selected_index, 0)

    def test_04_community_view_initialization_and_enter(self):
        """Verifica inicialización de CommunityViewState y canales por defecto."""
        self.sm.change_state("COMMUNITY", community_id="night_raid")
        self.assertEqual(self.sm.current_state_name, "COMMUNITY")
        self.assertEqual(self.comm_state.community_id, "night_raid")
        self.assertEqual(self.comm_state.current_channel, "general")
        self.assertGreaterEqual(len(self.comm_state.chat_messages), 6)

    def test_05_community_view_chat_message_sending(self):
        """Verifica agregado y envío interactivo de mensajes en el chat de la comunidad."""
        self.sm.change_state("COMMUNITY")
        initial_count = len(self.comm_state.chat_messages)

        self.comm_state.input_text = "¡Nos vemos en la sala de Gaming!"
        ev_enter = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, unicode="\r")
        self.comm_state.handle_events([ev_enter])

        self.assertEqual(len(self.comm_state.chat_messages), initial_count + 1)
        last_msg = self.comm_state.chat_messages[-1]
        self.assertEqual(last_msg["text"], "¡Nos vemos en la sala de Gaming!")
        self.assertEqual(self.comm_state.input_text, "")

    def test_06_draw_rendering_without_exceptions(self):
        """Verifica que el método draw de ambos estados ejecute sin excepciones en el display."""
        screen = pygame.display.get_surface()
        self.sm.change_state("GROUPS")
        self.hub_state.update(0.016)
        self.hub_state.draw(screen)

        self.sm.change_state("COMMUNITY")
        self.comm_state.update(0.016)
        self.comm_state.draw(screen)

    def test_07_dynamic_discord_groups_channels_and_invite_links(self):
        """Verifica canales independientes por grupo, creación de canales [+] y compartición por código/link."""
        screen = pygame.display.get_surface()
        self.sm.change_state("GROUPS")

        # 1. Crear un grupo nuevo personalizado con descripción y privacidad
        self.hub_state.modal_mode = "create"
        self.hub_state.modal_input = "CLAN CYBERPUNK"
        self.hub_state.modal_desc_input = "Servidor competitivo de speedruns y torneos."
        self.hub_state.modal_privacy = "private"
        self.hub_state._confirm_modal()

        created_grp = self.hub_state.groups[0]
        self.assertEqual(created_grp["name"], "CLAN CYBERPUNK")
        self.assertTrue(created_grp.get("invite_code"))
        self.assertTrue(created_grp.get("invite_link", "").startswith("https://"))
        self.assertTrue(created_grp.get("invite_uri", "").startswith("cci://invite/"))

        # Renderizar tarjeta procedural y modal de compartir código/link
        self.hub_state.modal_mode = "share"
        self.hub_state.draw(screen)
        self.hub_state.modal_mode = None

        # 2. Verificar que Sakura Club, Da Vinci Team y Clan Cyberpunk tienen canales distintos
        self.sm.change_state("COMMUNITY", community_id="sakura_club")
        sakura_text_names = [c[0] for c in self.comm_state.text_channels]
        self.assertIn("galeria-pixel", sakura_text_names)
        self.assertNotIn("dev-log", sakura_text_names)
        self.comm_state.draw(screen)

        self.sm.change_state("COMMUNITY", community_id="da_vinci_team")
        davinci_text_names = [c[0] for c in self.comm_state.text_channels]
        self.assertIn("dev-log", davinci_text_names)
        self.assertNotIn("galeria-pixel", davinci_text_names)
        self.comm_state.draw(screen)

        # 3. Entrar al grupo creado por el usuario y crear un canal de texto y una sala de voz propios con [+]
        self.sm.change_state("COMMUNITY", community_id=created_grp["id"])
        self.comm_state.modal_mode = "create_text_channel"
        self.comm_state.modal_input = "estrategias-boss"
        self.comm_state.modal_topic_input = "Guías para vencer jefes finales"
        self.comm_state._confirm_modal()

        custom_text_names = [c[0] for c in self.comm_state.text_channels]
        self.assertIn("estrategias-boss", custom_text_names)
        self.assertEqual(self.comm_state.current_channel, "estrategias-boss")

        self.comm_state.modal_mode = "create_voice_channel"
        self.comm_state.modal_input = "Raid Nocturno"
        self.comm_state._confirm_modal()
        custom_voice_names = [c[0] for c in self.comm_state.voice_channels]
        self.assertIn("Raid Nocturno", custom_voice_names)

        # El canal creado en Clan Cyberpunk NO debe aparecer en Sakura Club
        self.sm.change_state("COMMUNITY", community_id="sakura_club")
        self.assertNotIn("estrategias-boss", [c[0] for c in self.comm_state.text_channels])

        # 4. Unirse mediante un link completo de invitación (https://.../invite/CODIGO)
        self.sm.change_state("GROUPS")
        self.hub_state.modal_mode = "join"
        self.hub_state.modal_input = created_grp["invite_link"]
        self.hub_state._confirm_modal()
        self.assertEqual(self.hub_state.groups[0]["name"], "CLAN CYBERPUNK")


if __name__ == "__main__":
    unittest.main()
