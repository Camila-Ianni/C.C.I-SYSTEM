# Jack Ryan, Max Walsh
# 4/29/16
# mario_kart_server.py

from twisted.internet.protocol import ClientFactory
from twisted.internet.protocol import Factory
from twisted.internet.protocol import Protocol
from twisted.internet import reactor
from twisted.internet.defer import DeferredQueue
from twisted.internet.task import LoopingCall
import json
# use import pickle to debug

###################    Globals   ######################
PLAYER1_PORT = 40028
PLAYER1_HOST = ""

PLAYER2_PORT = 40046
PLAYER2_HOST = ""

# Global deferred queue, handles input from both players
dq = DeferredQueue()

FPS = 30.0

class GameState:
    #def main(self):
    def __init__(self):
        self.mario_x = 474
        self.mario_y = 134
        self.yoshi_x = 474
        self.yoshi_y = 208
    
        self.boost1_taken = False
        self.boost2_taken = False
        self.boost3_taken = False
        self.boost4_taken = False
        self.banana1_taken = False
        self.banana2_taken = False
        self.banana3_taken = False
        self.mario_speed = 5
        self.yoshi_speed = 5
        self.mario_in_banana = False
        self.yoshi_in_banana = False
        #self.finishLineStart = (500, 900)
        #self.finishLineEnd = (500, 1000)

        self.mario_was_in_box = False
        self.yoshi_was_in_box = False
        self.mario_cross_finish_line = False
        self.yoshi_cross_finish_line = False

        self.mario_won = False
        self.yoshi_won = False

        self.finish_start_x = 433

    def getPlayer1_Connection(self, p1_conn):
        self.player1_Conn = p1_conn

    def getPlayer2_Connection(self, p2_conn):
        self.player2_Conn = p2_conn

    def checkWinner(self):
        #print 'mx:' + str(self.mario_x) + 'my:' +str(self.mario_y)
        self.mario_was_in_box = True
        self.yoshi_was_in_box = True
        if self.mario_x > self.finish_start_x and self.mario_x < self.finish_start_x + 15 and self.mario_y < 257:
            print 'mario in finish box'
            if self.mario_was_in_box and self.mario_cross_finish_line:
                self.mario_won = True
                print 'mario won'
        elif self.mario_x < self.finish_start_x and self.mario_y < 257:
            self.mario_cross_finish_line = True

        if self.yoshi_x > self.finish_start_x and self.yoshi_x < self.finish_start_x + 15 and self.yoshi_y < 257:
            print 'yoshi in finish box'
            if self.yoshi_was_in_box and self.yoshi_cross_finish_line:
                self.yoshi_won = True
                print 'yoshi won'
        elif self.yoshi_x < self.finish_start_x and self.yoshi_y < 257:
            self.yoshi_cross_finish_line = True

    def check_track_bound(self, x, y):
		# If out of bounds, return false. If safe, return true
        if x <= 110 or x >= 1070 or y <= 110 or y >= 774:
            return False
        if y >= 250 and y <= 670 and x >= 255 and x <= 920:
            return False
        return True

    def applyBoosts(self):
        if not self.boost1_taken:
            # boost1 is still open for the taking
            if self.mario_x >= 320 and self.mario_x <= 345 and self.mario_y >= 160 and self.mario_y <= 185:
                self.mario_speed += 1
                self.boost1_taken = True
            elif self.yoshi_x >= 320 and self.yoshi_x <= 345 and self.yoshi_y >= 160 and self.yoshi_y <= 185:
                self.yoshi_speed += 1
                self.boost1_taken = True

        if not self.boost2_taken:
            # boost2 is still open for the taking
            if self.mario_x >= 140 and self.mario_x <= 165 and self.mario_y >= 420 and self.mario_y <= 445:
                self.mario_speed += 2
                self.boost2_taken = True
            elif self.yoshi_x >= 140 and self.yoshi_x <= 165 and self.yoshi_y >= 420 and self.yoshi_y <= 445:
                self.yoshi_speed += 2
                self.boost2_taken = True
        
        if not self.boost3_taken:
            # boost4 is still open for the taking
            if self.mario_x >= 530 and self.mario_x <= 555 and self.mario_y >= 710 and self.mario_y <= 735:
                self.mario_speed += 3
                self.boost3_taken = True
            elif self.yoshi_x >= 530 and self.yoshi_x <= 555 and self.yoshi_y >= 710 and self.yoshi_y <= 735:
                self.yoshi_speed += 3
                self.boost3_taken = True
        
        if not self.boost4_taken:
            # boost3 is still open for the taking
            if self.mario_x >= 930 and self.mario_x <= 955 and self.mario_y >= 490 and self.mario_y <= 515:
                self.mario_speed += 4
                self.boost4_taken = True
            elif self.yoshi_x >= 930 and self.yoshi_x <= 955 and self.yoshi_y >= 490 and self.yoshi_y <= 515:
                self.yoshi_speed += 4
                self.boost4_taken = True

    def apply_banana(self):
        if not self.banana1_taken:
            if self.mario_x >= 160 and self.mario_x <= 185 and self.mario_y >= 216 and self.mario_y <= 245:
                self.mario_in_banana = True
                self.banana1_taken = True
            elif self.yoshi_x >= 160 and self.yoshi_x <= 185 and self.yoshi_y >= 216 and self.yoshi_y <= 245:
                self.yoshi_in_banana = True
                self.banana1_taken = True
        else:
            self.mario_in_banana = False
            self.yoshi_in_banana = False
        if not self.banana2_taken:
            if self.mario_x >= 356 and self.mario_x <= 381 and self.mario_y >= 755 and self.mario_y <= 780:
                self.mario_in_banana = True
                self.banana2_taken = True
            elif self.yoshi_x >= 356 and self.yoshi_x <= 381 and self.yoshi_y >= 755 and self.mario_y <= 780:
                self.yoshi_in_banana = True
                self.banana2_taken = True
        else:
            self.mario_in_banana = False
            self.yoshi_in_banana = False
        if not self.banana3_taken:
            if self.mario_x >= 620 and self.mario_x <= 645 and self.mario_y >= 174 and self.mario_y <= 199:
                self.mario_in_banana = True
                self.banana3_taken = True
            elif self.yoshi_x >= 620 and self.yoshi_x <= 645 and self.yoshi_y >= 174 and self.yoshi_y <= 199:
                self.yoshi_in_banana = True
                self.banana3_taken = True
        else:
            self.mario_in_banana = False
            self.yoshi_in_banana = False


    def decode_data(self, data):
        dataList = data.split(":")
        if dataList[1] == '-1':
            return
        self.apply_banana()
        if dataList[0] == '1':
            # MARIO
            print str(dataList[1])
            if not self.mario_in_banana:
                if dataList[1] == '273': # UP
                    self.mario_y -= self.mario_speed
                    self.mario_in_banana = False
                elif dataList[1] == '274': # DOWN
                    self.mario_y += self.mario_speed
                elif dataList[1] == '275': # RIGHT
                    self.mario_x += self.mario_speed
                elif dataList[1] == '276': # LEFT
                    self.mario_x -= self.mario_speed
                elif dataList[1] == "b":
                    pass
                if self.check_track_bound(self.mario_x, self.mario_y) == False:
                    # If mario goes out of bounds, send him back to start
                    self.mario_x = 474
                    self.mario_y = 134
                    self.mario_cross_finish_line = False
                    self.mario_won = False

        elif dataList[0] == '2':
			# YOSHI
            if dataList[1] == '273': # UP
                self.yoshi_y -= self.yoshi_speed
            elif dataList[1] == '274': # DOWN
                self.yoshi_y += self.yoshi_speed
            elif dataList[1] == '275': # RIGHT
                self.yoshi_x += self.yoshi_speed
            elif dataList[1] == '276': # LEFT
                self.yoshi_x -= self.yoshi_speed
            if self.check_track_bound(self.yoshi_x, self.yoshi_y) == False:
				# If yoshi goes out of bounds, send him back to start
                self.yoshi_x = 474
                self.yoshi_y = 208
                self.yoshi_cross_finish_line = False
                self.yoshi_won = False

        else:
            print "Error: unexpected data sent from Player"

        self.applyBoosts() # if either player ran over a boost, apply it
        self.checkWinner() # check at each tick if a player has won
		
        return_string = json.dumps({
                                    'mario_x':self.mario_x, 
                                    'mario_y':self.mario_y, 
                                    'mario_won':str(self.mario_won), 
                                    'mario_in_banana':str(self.mario_in_banana), 
                                    'yoshi_x':self.yoshi_x, 
                                    'yoshi_y':self.yoshi_y, 
                                    'yoshi_won':str(self.yoshi_won),
                                    'yoshi_in_banana':str(self.yoshi_in_banana) 
                                    })
        self.player1_Conn.sendData(return_string)
        self.player2_Conn.sendData(return_string)
        dq.get().addCallback(self.decode_data) # after decode data, reattach callback

gs = GameState()


class Player1_ConnFactory(Factory):
    def buildProtocol(self, addr):
        return Player1_Connection(addr)

class Player1_Connection(Protocol):
    def __init__(self, addr):
        self.addr = addr
        PLAYER1_HOST = addr.host
        #self.player2_conn = ""

    def dataReceived(self, data):
        # data received from player 1
        dq.put(data)
        #print str(data)

    def connectionMade(self):
        print "Connection receieved from player 1"
        # listen for player 2
        gs.getPlayer1_Connection(self)
        reactor.listenTCP(PLAYER2_PORT, Player2_ConnFactory(self))
 
    def connectionLost(self, reason):
        print "Lost connection from player 1:", str(reason)

    def startForwarding(self):
        # start forwarding the player 1 data
        print "sendData"
        dq.get().addCallback(gs.decode_data)

    def sendData(self, data):
        self.transport.write(data + '\r\n')        

    def getPlayer2_Connection(self, player2_conn):
        self.player2_conn = player2_conn

class Player2_ConnFactory(Factory):
    def __init__(self, player1_conn):
        self.player1_conn = player1_conn

    def buildProtocol(self, addr):
        return Player2_Connection(addr, self.player1_conn)

class Player2_Connection(Protocol):
    def __init__(self, addr, player1_conn):
        self.addr = addr
        print addr
        PLAYER2_HOST = addr.host
        self.player1_conn = player1_conn

    def dataReceived(self, data):
        # data received from player 2
        dq.put(data)

    def connectionMade(self):
        print "Connection receieved from player 2"
        print "ready to begin game"
        self.player1_conn.getPlayer2_Connection(self)
        gs.getPlayer2_Connection(self)
        self.startForwarding()

    def connectionLost(self, reason):
        print "Lost connection from player 2:", str(reason)

    def startForwarding(self):
        # start forwarding the player 2 data
        #dq.get().addCallback(gs.decode_data)
        dq.get().addCallback(gs.decode_data)

    def sendData(self, data):
        self.transport.write(data + '\r\n')


if __name__ == "__main__":
    # http://stackoverflow.com/questions/8381850/combining-pygame-and-twisted
    #gs = GameState()
    #tick = LoopingCall(gs.game_tick)
    #tick.start(1.0 / FPS)
    reactor.listenTCP(PLAYER1_PORT, Player1_ConnFactory())
    reactor.run()
