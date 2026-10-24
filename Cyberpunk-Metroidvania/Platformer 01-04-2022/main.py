from game import Game

g = Game()

while g.running:
	g.current_menu.display_menu()
	g.game_loop()
