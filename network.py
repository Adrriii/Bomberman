# -*- coding: Utf-8 -*
# Author: aurelien.esnard@u-bordeaux.fr

from model import *
import socket
import select
import random

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
        self.save_sock = {}

        # Socket creation
        sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM,0)
        try:
            sock.setsockopt(1,socket.SO_REUSEADDR,1024) # for testing
        except:
            print('Could not enable SO_REUSEADDR')
        sock.bind(('',self.port))
        sock.listen(1)

        self.sockets = [sock]

    def tick(self, dt):
        (read,e1,e2) = select.select(self.sockets,[],[], dt/1000)

        for s in read:
            if(s == self.sockets[0]):
                sockets = self.welcomeUser(s,self.sockets)
            else:
                message = self.receive_message(s)
                print("REC :", message)


                if message != None:
                    user = self.uid_from_socket(s)
                    # Handle user command
                    print(user+": "+message)

                    # The user is joining
                    if(message.startswith("JOIN ") or message.startswith("JOSP ")):
                        self.changeNickname(s,message)

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
                        self.kill_user(user, s)
                        continue

                else:
                    # Handle disconnection
                    print (self.save_sock)
                    if s in self.save_sock:
                        user = self.save_sock[s]
                        print(user+" has disconnected.")

                        self.kill_user(user,s)
                    else:
                        s.close()
                        self.sockets.remove(s)
                    continue


        if random.randint(0, 1000)%100 == 0:
            self.alea_bomb()

        return True

    def tell_clients(self,message,ignore=[]):
        print(message)
        for d in self.sockets:
            # Send encoded message to all peers excepted host and ignored
            if(d not in ignore and d != self.sockets[0]):
                self.send_message(message, d)

    def send_message(self, message, s):
        taille = "%5d "%(len(message) + 1)
        to_send = "BEGIN " + taille + message + "\n"
        s.send(to_send.encode())
        print("SENDING :", to_send)

    def receive_message(self, s):
        try:
            message = s.recv(6)
        except:
            print("Socket error: can't receive data from server.")
            return None

        if message.decode() == "BEGIN ":
            taille = s.recv(6)

            try:
                len = int(taille.decode())
            except ValueError:
                print("Value error, can't convert message's size")
                print(message.decode())
                return ""

            command = s.recv(len)
            return command.decode()

    def uid_from_socket(self,s):
        addr = s.getpeername()[0]
        port = s.getpeername()[1]
        return str(addr) + ":" + str(port)

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
        # The nickname should always be at the end
        splitted = message.split(" ")
        nick = splitted[(len(splitted)-1)].split("\n")[0]
        print("Join recv:")

        # Add it to the dictionnary with the UID as the key
        self.nicks[uid] = nick
        self.save_sock[s] = uid

        # Add to the model and respond positively
        self.model.add_character(nick)
        char = self.model.look(nick)

        # If the player comes in a special way
        if  message.startswith("JOSP "):
            char.health = int(splitted[1])
            char.kind = int(splitted[2])

        # Tell everyone else of the new player and its features
        char.immunity = 5000;
        #print("NICK:", nick[0:-1], "coucou")
        self.tell_clients("NEWP "+nick+" "+str(char.health)+" "+str(char.kind)+" "+str(char.pos[X])+" "+str(char.pos[Y])+"\n",[s])

        # Tell the new player its features and gives him the map
        self.send_message("WELC "+str(char.kind)+" "+str(char.health)+" "+str(char.pos[X])+" "+str(char.pos[Y])+" "+self.model.mappath+"\n", s)

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
                    self.send_message("NEWP "+p+" "+str(char.health)+" "+str(char.kind)+" "+str(char.pos[X])+" "+str(char.pos[Y])+"\n", s)

        # Tell about the fruits
        for f in self.model.fruits:
            # NEWF kind x y
            self.send_message("NEWF "+str(f.kind)+" "+str(f.pos[X])+" "+str(f.pos[Y])+"\n", s)

        # Don't tell about the bombs since we will give invincibility for a short time for newcomers

    def sendMap(self,s):
        self.send_message(self.model.mappath, s)

    def dropBomb(self,s):
        nick = self.nicks[self.uid_from_socket(s)]
        self.model.drop_bomb(nick)
        # DROP nick
        self.tell_clients("DROP "+nick+"\n",[s])

    def moveCharacter(self,s,message):
        nick = self.nicks[self.uid_from_socket(s)]
        direction = message[5:]
        self.model.move_character(nick,int(direction))

        character = self.model.look(nick)

        tile = self.model.map.get_tile(character.pos[X], character.pos[Y])
        if tile == "3":
            print(nick+' stepped on a teleporter!')
            self.teleport_user(s)
        else:
            # MOVP nick direction
            self.tell_clients("MOVP "+nick+" "+str(direction)+"\n",[s])

    def teleport_user(self,s):
        # We can change the server depending in the teleporter tile
        # This would require a teleporter object in the model
        if self.port == 7777:
            self.send_message("TPSP localhost 7778",s)
        elif self.port == 7778:
            self.send_message("TPSP localhost 7777",s)

    def kill_user(self,user,s):
        # Tell the model to remove the user
        if(self.model.quit(self.nicks[user])):
            # If it works, delete it and tell everyone
            self.tell_clients("QUIT "+self.nicks[user]+"\n",[s])
            del self.nicks[user]
            del self.save_sock[s]
            s.close()
            self.sockets.remove(s)

    def alea_bomb(self):
        print("Sever send BOMB !")
        random_pos = self.model.map.random()
        self.model.bombs.append(Bomb(self.model.map, random_pos))
        self.tell_clients("SERVDROP " + str(random_pos[0]) + " " + str(random_pos[1]))





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

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.host,self.port))

        self.server = s
        self.send_message("JOIN " + self.nickname)

    #####################################################
    # keyboard events and communication with the server #
    #####################################################

    def keyboard_quit(self):
        print("=> event \"quit\"")
        self.model.quit(self.nickname)
        self.send_message("QUIT")
        return False

    def keyboard_move_character(self, direction):
        print("=> event \"keyboard move direction\" {}".format(DIRECTIONS_STR[direction]))
        self.model.move_character(self.nickname,direction)
        self.send_message("MOVE "+str(direction))
        return True

    def keyboard_drop_bomb(self):
        print("=> event \"keyboard drop bomb\"")
        self.drop_bomb("DROP "+self.nickname)
        self.send_message("DROP")
        return True

    def send_message(self, message):
        taille = "%5d "%(len(message) + 1)
        to_send = "BEGIN " + taille + message + "\n"
        print("SENDING :", to_send)
        try:
            self.server.send(to_send.encode())
        except:
            print("Server unreachable")
            exit()

    def receive_message(self):
        try:
            message = self.server.recv(6)
        except:
            print("Caught socket error, can't receive data from sevrer.")
            return None

        if message.decode() == "BEGIN ":
            taille = self.server.recv(6)

            try:
                len = int(taille.decode())
            except ValueError:
                print("Value error, can't convert message's size")
                print(message.decode())
                return ""

            command = self.server.recv(len)
            return command.decode()

    ##############
    # time event #
    ##############

    def tick(self, dt=0):
        # Check if some data has been sent by the server
        ready = select.select([self.server], [], [], dt/1000)

        if ready[0]:
            message = self.receive_message()

            if message:
                print(message)

                orders = message.split("\n")

                for line in orders:

                    # New user is joining
                    if(line.startswith("NEWP ")):
                        self.add_character(line)

                    # New fruit to add
                    if(line.startswith("NEWF ")):
                        self.add_fruit(line)

                    # Another user is moving
                    if(line.startswith("MOVP")):
                        self.move_character(line)

                    #message = data.decode()# Another user drops a bomb
                    if(line.startswith("DROP ")):
                        self.drop_bomb(line)

                    # The server is welcoming with map and pos
                    if(line.startswith("WELC ")):
                        self.arrive(line)

                    # The server tells us of a quitting player
                    if(line.startswith("QUIT ")):
                        self.quit_player(line)

                    # The server drops a bomb
                    if line.startswith("SERVDROP"):
                        if self.ready:
                            self.server_bomb(line)

                    # The server tells us where the teleporter leads to
                    if line.startswith("TPSP"):
                        self.switch_server(line)
        else:
            return False

        return True

    def arrive(self,message):
        print("Arriving")
        parts = message.split(" ")
        path = parts[5]
        self.model.load_map(path)
        self.ready = True
        self.model.add_character(self.nickname, True, int(parts[1]),[int(parts[3]),int(parts[4])])
        char = self.model.look(self.nickname)
        char.health = int(parts[2])

    def add_fruit(self,message):
        # Split the message into arguments
        parts = message.split(" ")
        self.model.add_fruit(int(parts[1]),(int(parts[2]),int(parts[3])))

    def add_character(self,message):
        # Split the message into arguments
        print("IN ADD CHAR")
        print(message)
        parts = message.split(" ")
        print(parts)

        is_me = False
        if(self.nickname == parts[1]):
            is_me = True

        # Add the character to the model
        self.model.add_character(parts[1], is_me, int(parts[3]),[int(parts[4]),int(parts[5])])
        char = self.model.look(parts[1])
        char.immunity = 5000
        char.health = int(parts[2])

    def move_character(self,message):
        print("IN MOVE CHAR:", message)
        parts = message.split(" ")
        self.model.move_character(parts[1], int(parts[2]))

    def quit_player(self, message):
        nick = message.split(" ")[1].split("\n")[0]
        self.model.quit(nick)

    def drop_bomb(self,message):
        nick = message.split(" ")[1].split("\n")[0]
        self.model.drop_bomb(nick)

    def server_bomb(self, message):
        pos = message.split(" ")
        x = int(pos[1])
        y = int(pos[2])
        self.model.bombs.append(Bomb(self.model.map, (x, y)))

    def switch_server(self,message):
        address = message.split(" ")[1].split("\n")[0]
        port = message.split(" ")[2].split("\n")[0]

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((address, int(port)))
            s.close()
        except:
            print("TELEPORT ERROR: Second server unreachable...")
            return

        self.host = address
        self.port = int(port)
        self.join_special()

    def join_special(self):
        me = self.model.look(self.nickname)
        message = "JOSP "+str(me.health)+" "+str(me.kind)+ " " +self.nickname

        self.model.empty_model()
        self.server.close()

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.host,self.port))

        self.server = s
        self.send_message(message)
