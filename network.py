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
                        self.changeNickname(s,message)

                    # The user is requesting the server map
                    if(message.startswith("MAP")):
                        self.sendMap(s)

                else:
                    # Handle brutal disconnection
                    print(user+" has disconnected unexpectedly.")
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
        # Add it to the dictionnary with the UID as the key
        self.nicks[uid] = nick
        s.send("OK".encode())

        print(uid+" has a new nickname: "+nick)

    def sendMap(self,s):
        s.send((self.model.mappath).encode())


################################################################################
#                          NETWORK CLIENT CONTROLLER                           #
################################################################################

class NetworkClientController:

    def __init__(self, model, host, port, nickname):
        self.model = model
        self.host = host
        self.port = port
        self.nickname = nickname

        s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        s.connect((self.host,self.port))

        self.server = s

        self.server.send(("JOIN "+self.nickname).encode())
        data = self.server.recv(1500)



    # keyboard events

    def keyboard_quit(self):
        print("=> event \"quit\"")
        return False

    def keyboard_move_character(self, direction):
        print("=> event \"keyboard move direction\" {}".format(DIRECTIONS_STR[direction]))
        # ...
        return True

    def keyboard_drop_bomb(self):
        print("=> event \"keyboard drop bomb\"")
        # ...
        return True

    def load_map(self):
        self.server.send("MAP".encode())
        data = self.server.recv(1500)

        if data:
            self.model.load_map(data.decode())
        else:
            print("Failed to retrieve map from server.")

    # time event

    def tick(self, dt):
        # ...
        return True
