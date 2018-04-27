# Bomber Man #
 
This is a simple "Bomber Man" game written in Python 3, based on the *PyGame* library.

![Bomber Man Snapshot](snap0.png?raw=true "snapshot")


## Download & Install ##

To install Python (root privilege required):

```
  $ sudo apt get install python3 pip3
```

To install the *PyGame* library (user privilege enough):

```
  $ pip3 install pygame
```

To start the server:

```
  $ ./bomber_server.py 7777 maps/map0
  $ ./bomber_server.py 7778 maps/map1
```


You can use teleportation only with a server on the port 7777, and another on 7778. If needed you can customize the ports and adresses in network.py
By default, the map "maps/map0" is used, but you can generate you own map (*mymap*) and use it as follows:

```
  $ ./bomber_server.py <port> maps/mymap
```

To start the game:

```
  $ ./bomber_client.py <server> <port> <username>
```


## Rules ##

This game is similar to a classic "Bomber Man". This is a multiplayer version of the game. In this version, every player starts the game with an initial amount of 50 health points. Each fruit brings a character with 10 extra health points, while each bomb blast removes 10 health points. A character is dead when its health points reach zero. A character gets immunity for a while after he's hit by a bomb blast, or he's join a server . After a character drops a bomb, he is disarmed for a while.

To play, just use the following keys:
  * use *arrows* to move the current character
  * press *space* to drop a bomb at current position, that will explode after a delay of 5 seconds
  * press *escape* to quit the game

The implementation of this game follows a simple MVC architecture (Model/View/Controller).

## Known Bugs ##

There is a [known bug](https://github.com/pygame/pygame/issues/331) in the *pygame.mixer* module, which causes high CPU usage, when calling *pygame.init()*. A workaround is to disable the mixer module, *pygame.mixer.quit()* or not to enable it, by using *pygame.display.init()* and *pygame.font.init()* instead. Consequently, there is no music, no sound :-(

## Documentation ##

  * https://www.pygame.org
  * https://openclassrooms.com/courses/interface-graphique-PyGame-pour-python/tp-dk-labyrinthe
  * http://ezide.com/games/writing-games.html
