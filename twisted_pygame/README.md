# Pygame Parkway

Gameplay: 

On student02 run mario_kart_server.py:
$ python mario_kart_server.py

Then run Player.py on another machine with the argument host:
$ python Player.py host

Then run Player.py on another machine with the argument join:
$ python Player.py join

Once both players have joined the game begins. Player 1 (host) plays as Mario, player 2 (join) plays
as Yoshi. Both players move using the arrow keys. 

There is a power up indicated by a red arrow, running over the arrow will increase the players speed. Each arrow can only be used once. There is also an obstacle indicated by the yellow bananas. 
Running over a banana will stop the player from moving and cause it to spin once in a circle and then
the player can begin to move again. Again each banana can be used only once. If a player moves off the track
by moving into the green portion of the track they will be resest and must begin again from the start
of the race.

A large image of the winner will be displayed when they cross the finish line. 

The game can be quit using the exit button on each players window and by using ctrl + C to stop the 
server.
