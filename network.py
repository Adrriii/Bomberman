# -*- coding: Utf-8 -*
# Author: aurelien.esnard@u-bordeaux.fr

from model import *
import socket
import select

################################################################################
#                          NETWORK SERVER CONTROLLER                           #
################################################################################

class NetworkServerController:

    def __init__(self, model, port):
        self.model = model
        self.port = port

        # Nicks -> key:"remote_addr+remote_port" -> nickname string
        # Dictionnary with all users' nicknames
        self.nicks = {}

        # Socket creation
        sock = socket.socket(socket.AF_INET6,socket.SOCK_STREAM,0)
        sock.setsockopt(1,socket.SO_REUSEADDR,1024) # for testing
        sock.bind(('',self.port))
        sock.listen(1)

        self.sockets = [sock]

    def uid_from_socket(self,s):
        addr = s.getpeername()[0]
        port = s.getpeername()[1]
        return str(addr) + ":" + str(port)

    def validate_receive(self, s):
        s.send(b"OK ")
        data = s.recv(10)
        data_decode = data.decode()
        return data_decode.startswith("OK ")


    def tick(self, dt):
        (read,e1,e2) = select.select(self.sockets,[],[])

        for s in read:
            if(s == self.sockets[0]):
                sockets = self.welcomeUser(s,self.sockets)
            else:
                data = s.recv(1500) # Get the data with a buffer of 1500
                user = self.uid_from_socket(s)

                if data:
                    # Handle user command
                    message = data.decode()
                    print(user+": "+message)

                    # The user is joining
                    if(message.startswith("JOIN ")):
                        self.validate_receive(s)
                        self.changeNickname(s,message)

                    # The user is requesting the server map
                    if(message.startswith("MAP")):
                        self.sendMap(s)

                    # The user is requesting to move
                    if(message.startswith("MOVE")):
                        self.moveCharacter(s, message)

                    # The user is requesting to drop a bomb
                    if(message.startswith("DROP")):
                        self.dropBomb(s)

                    # The user is leaving the game
                    if(message.startswith("QUIT")):
                        # Will be handled by socket disconnection, but if we want
                        # To do something about it we can do it here
                        i = None # dummy

                else:
                    # Handle disconnection
                    print(user+" has disconnected.")

                    self.kill_user(user,s)

                    s.close()
                    self.sockets.remove(s)

        return True

    # Handles a new connection
    def welcomeUser(self,s,sockets):
        # Add a new peer to the socket list
        remote = s.accept()
        sockets.append(remote[0])

        print("A new player has connected.")

        return sockets

    def changeNickname(self,s,message):
        uid = self.uid_from_socket(s)

        # Only take the decoded string data without JOIN
        nick = message[5:]
        print("Join recv:")

        # Add it to the dictionnary with the UID as the key
        self.nicks[uid] = nick

        # Add to the model and respond positively
        self.model.add_character(nick)


        # Tell everyone else of the new player and its features
        char = self.model.look(nick)
        self.tell_clients("NEWP "+nick+" "+str(char.kind)+" "+str(char.pos[X])+" "+str(char.pos[Y])+"\n",[s])

        # Tell the new player its features and gives him the map
        s.send(("WELC "+str(char.kind)+" "+str(char.pos[X])+" "+str(char.pos[Y])+" "+self.model.mappath+"\n").encode())

        # Send to the new player all the info to catch up with the others
        self.update_state(s)

        print(uid+" has joined the game with the nickname "+nick)

    def update_state(self,s):
        uid = self.uid_from_socket(s)
        nick = self.nicks[uid]

        # Tell about other players
        for p in self.nicks.values():
            if(p != nick):
                char = self.model.look(p)
                if char:
                    # NEWP nick kind x y
                    s.send(("NEWP "+p+" "+str(char.kind)+" "+str(char.pos[X])+" "+str(char.pos[Y])+"\n").encode())

        # Tell about the fruits
        for f in self.model.fruits:
            # NEWF kind x y
            s.send(("NEWF "+str(f.kind)+" "+str(f.pos[X])+" "+str(f.pos[Y])+"\n").encode())

        # Don't tell about the bombs since we will give invincibility for a short time for newcomers

    def sendMap(self,s):
        s.send((self.model.mappath).encode())

    def dropBomb(self,s):
        nick = self.nicks[self.uid_from_socket(s)]
        self.model.drop_bomb(nick)
        # DROP nick
        self.tell_clients("DROP "+nick+"\n",[s])

    def moveCharacter(self,s,message):
        nick = self.nicks[self.uid_from_socket(s)]
        direction = message[5:]
        self.model.move_character(nick,int(direction))

        # MOVP nick direction
        self.tell_clients("MOVP "+nick+" "+str(direction)+"\n",[s])

    def tell_clients(self,message,ignore=[]):
        print(message)
        for d in self.sockets:
            # Send encoded message to all peers excepted host and ignored
            if(d not in ignore and d != self.sockets[0]):
                d.send(message.encode())

    def kill_user(self,user,s):
        # Tell the model to remove the user
        if(self.model.quit(self.nicks[user])):
            # If it works, delete it and tell everyone
            self.tell_clients("QUIT "+self.nicks[user]+"\n",[s])
            del self.nicks[user]



################################################################################
#                          NETWORK CLIENT CONTROLLER                           #
################################################################################

class NetworkClientController:

    def __init__(self, model, host, port, nickname):
        self.model = model
        self.host = host
        self.port = port
        self.nickname = nickname
        self.ready = False

        s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        s.connect((self.host,self.port))

        self.server = s
        connected = False

        while not connected:

            self.server.send(("JOIN "+self.nickname).encode())
            connected = self.check_receive()

    # keyboard events and communication with the server

    def check_receive(self):
        data = self.server.recv(10)
        data_decode = data.decode()

        if data_decode.startswith("OK "):
            self.server.send(b"OK ")
            return True
        return False

    def keyboard_quit(self):
        print("=> event \"quit\"")
        self.model.quit(self.nickname)
        self.send_action("QUIT")
        return False

    def keyboard_move_character(self, direction):
        print("=> event \"keyboard move direction\" {}".format(DIRECTIONS_STR[direction]))
        self.model.move_character(self.nickname,direction)
        self.send_action("MOVE "+str(direction))
        return True

    def keyboard_drop_bomb(self):
        print("=> event \"keyboard drop bomb\"")
        self.drop_bomb("DROP "+self.nickname)
        self.send_action("DROP")
        return True

    def send_action(self,action):
        self.server.send(action.encode())

    # time event

    def tick(self, dt=0):
        # Check if some data has been sent by the server
        ready = select.select([self.server], [], [], dt/1000)

        if ready[0]:
            data = self.server.recv(1500)

            if data:
                message = data.decode()
                print(message)

                orders = message.split("\n")

                for line in orders:
                    print("read: "+line)
                    # New user is joining
                    if(line.startswith("NEWP ")):
                        self.add_character(line)

                    # New fruit to add
                    if(line.startswith("NEWF ")):
                        self.add_fruit(line)

                    # Another user is moving
                    if(line.startswith("MOVP")):
                        self.move_character(line)

                    # Another user drops a bomb
                    if(line.startswith("DROP ")):
                        self.drop_bomb(line)

                    # The server is welcoming with map and pos
                    if(line.startswith("WELC ")):
                        self.arrive(line)

                    # The server tells us of a quitting player
                    if(line.startswith("QUIT ")):
                        self.quit_player(line)
        else:
            return False

        return True

    def arrive(self,message):
        print("Arriving")
        parts = message.split(" ")
        path = parts[4]
        self.model.load_map(path)
        self.ready = True
        self.model.add_character(self.nickname, True, int(parts[1]),[int(parts[2]),int(parts[3])])


    def add_fruit(self,message):
        # Split the message into arguments
        parts = message.split(" ")

        self.model.add_fruit(int(parts[1]),(int(parts[2]),int(parts[3])))

    def add_character(self,message):
        # Split the message into arguments
        parts = message.split(" ")

        is_me = False
        if(self.nickname == parts[1]):
            is_me = True

        y = parts[4].split("\n")[0]
        # Add the character to the model
        self.model.add_character(parts[1], is_me, int(parts[2]),[int(parts[3]),int(y)])

    def move_character(self,message):
        parts = message.split(" ")
        self.model.move_character(parts[1], int(parts[2]))

    def quit_player(self, message):
        nick = message.split(" ")[1].split("\n")[0]
        self.model.quit(nick)

    def drop_bomb(self,message):
        nick = message.split(" ")[1].split("\n")[0]
        self.model.drop_bomb(nick)
