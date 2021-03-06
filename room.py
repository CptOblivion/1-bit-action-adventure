import os
import pygame
from pygame.math import Vector2
import configparser
import gameloop as g
import event as ev
import entities as e
#TODO: rename back to level.py, put Level class in here with Room
#   (it'll probably be long but they're pretty tightly coupled)

class Level:
    current=None
    def getProp(path, propName, default=None):
        if (propName in path): return path[propName]
        return default
    def loadRoom(self,roomName):
        #TODO: learn about how to trigger garbage collection (and ensure the previous room is properly flushed)
        self.rooms[roomName] = Room(roomName, self)
    def changeRoom(self, roomName, doorName, oldDoor=None):
        if (not roomName in self.rooms):
            self.loadRoom(roomName)
        newRoom=self.rooms[roomName]
        newDoor = newRoom.doors[doorName]
        details = RoomChangeDetails(Room.current, newRoom, oldDoor, newDoor)
        if (Room.current):
            Room.current.leavingRoom(details)
        Room.current=newRoom
        Room.onRoomChange.invoke(details)
        newRoom.enteredRoom(details)
    def __init__(self, levelName, startRoom, startDoor):
        Level.current=self
        self.rooms={}
        self.config = configparser.ConfigParser()
        self.config.read(os.path.join(os.getcwd(), 'Assets', 'Levels',levelName+'.lvl'))
        self.tileSize=int(Level.getProp(self.config['General'], 'tilesize', default=16))
        self.tileset = pygame.image.load(os.path.join(os.getcwd(), 'Assets', 'Tilesets',
                                                      Level.getProp(self.config['General'], 'tileset')))
        self.floorTiles={}
        self.wallTiles={}
        self.entities={}
        for floorString in self.config['General']['floors'].split('\n'):
            if (floorString != ''):
                rValue,name,x,y=floorString.split(',')
                x,y=(int(x), int(y))
                self.floorTiles[rValue]=Tile(name, pygame.Rect(x*self.tileSize,y*self.tileSize,
                                                                self.tileSize,self.tileSize), self.tileset)
        #for iniIndex in self.config['Walls']:
        for wallString in self.config['General']['walls'].split('\n'):
            if (wallString != ''):
                wallArray=wallString.split(',')
                bValue,name,x,y,height = wallArray[:5]
                x,y,height =(int(x), int(y), int(height))
                self.wallTiles[bValue]=WallTile(name, pygame.Rect(x*self.tileSize,y*self.tileSize,
                                                                self.tileSize,height), self.tileset,
                                                  baseHeight=self.tileSize)
                if (len(wallArray) > 5):
                    for arrayEntry in wallArray[5:]:
                        if (arrayEntry == 'diag'):
                            self.wallTiles[bValue].supportsDiagonals = True
                        elif (arrayEntry.startswith('tile:')):
                            self.wallTiles[bValue].tileGroup=arrayEntry[5:]
                        elif (arrayEntry == 'singleTile'): self.wallTiles[bValue].forceSingleTile=True
        for entityString in self.config['General']['entities'].split('\n'):
            if (entityString != ''):
                name,junkData=entityString.split(',')
        self.changeRoom(startRoom, startDoor)

class RoomChangeEvent(ev.Event):
    #technically could just use InputEvent, but it's nice having a separate name to avoid confusion
    def invoke(self, room):
        super().invoke(room)
class RoomChangeDetails:
    def __init__(self, oldRoom, newRoom, oldDoor, newDoor):
        #TODO: do we need oldRoom? (currently need oldDoor to get the player offset on that door
        #   when they left but there's probably a better way
        self.oldRoom=oldRoom
        self.newRoom=newRoom
        self.oldDoor=oldDoor
        self.newDoor = newDoor

class Room:
    current=False
    onRoomChange=RoomChangeEvent()
    init=False
    def __init__(self, name, level):
        self.level=level
        self.name=name
        self.onRoomEnter = RoomChangeEvent()
        self.onRoomLeave = RoomChangeEvent()
        roomDetails=self.level.config[name]
        self.tileSize = self.level.tileSize #TODO: maybe we should store this in just one place
        
        roomLayoutImage=Level.getProp(roomDetails, 'levelfile', name + '.png')
        self.mapImage=pygame.image.load(
            os.path.join(os.getcwd(), 'Assets', 'Levels', roomLayoutImage))
        self.width = self.mapImage.get_width()
        self.height = self.mapImage.get_height()
        self.tileCache = pygame.Surface((self.width *self.tileSize, self.height*self.tileSize))

        self.floors = []
        self.walls = []
        self.entities=[]
        self.actors=[]
        self.doors={}

        for x in range(self.width):
            rowFloor = []
            rowWall = []
            for y in range(self.height):
                rowWall.append(WallEntry((x,y), self))
                rowFloor.append(None)
            self.floors.append(rowFloor)
            self.walls.append(rowWall)

        for x in range(self.width):
            for y in range(self.height):
                pixel=self.mapImage.get_at((x,y))
                self.floors[x][y]=self.level.floorTiles[str(pixel[0])]
                if (pixel[1] > 0):
                    self.walls[x][y].setWall(self.level.wallTiles[str(pixel[1])])

        #for doorName in self.config['Doors']:
        for doorString in roomDetails['doors'].split('\n'):
            if (doorString != ''):
                #doorString=self.config['Doors'][doorName]
                doorName,left,top,width,height,dir,linkedRoom,linkedDoor = doorString.split(',')
                left,top,width,height=(int(left)*self.tileSize,int(top)*self.tileSize, int(width)*self.tileSize,
                                       int(height)*self.tileSize)
                position = (left+width/2,top+height/2)
                bounds=pygame.Rect(-width/2,-height/2,width, height)
                if(dir=='l' or dir=='L'):
                    offs=(-1,0)
                elif(dir=='r' or dir=='R'):
                    offs=(1,0)
                elif(dir=='u' or dir=='U' or dir=='t' or dir=='T'):
                    offs=(0,-1)
                elif(dir=='d' or dir=='D'or dir=='b' or dir=='B'):
                    offs=(0,1)
                playerOffset=Vector2((bounds.width)*offs[0],(bounds.height)*offs[1])

                roomDoor=Door(doorName,self,position,bounds,None,linkedRoom,linkedDoor,playerOffset)

        for entityString in roomDetails['entities'].split('\n'):
            if (entityString != ''):
                entityName, posX, posY=entityString.split(',')
                e.Spawn(entityName, self, Vector2(int(posX),int(posY)))

    def updateTileCache(self):
        for x in range(self.width):
            for y in range(self.height):
                if (self.floors[x][y]): self.floors[x][y].draw((x,y),surface=self.tileCache)
                if (self.walls[x][y]): self.walls[x][y].draw(cache=self.tileCache)
    def draw(self):
        entityPositions=[]
        for i in range(self.height):
            entityPositions.append([])
        for entity in self.entities:
            if (entity.active and entity.visible):
                gridCell = int(entity.position.y / self.tileSize)
                if (0 <= gridCell < len(entityPositions)):
                    entityPositions[gridCell].append(entity)

        g.Window.current.screen.blit(self.tileCache,(0,0))
        for y in range(self.height):
            for x in range(self.width):
                if (self.walls[x][y]):
                    self.walls[x][y].draw()
            #sort cell by y position first
            for entity in sorted(entityPositions[y], key=lambda entity: entity.position.y):
                entity.draw()
        g.Window.current.flip()
    def getWall(self, position:Vector2, oobReturn=None):
        if (position[0] < 0 or position[0] >= self.width or
            position[1] < 0 or position[1] >= self.height):
            return oobReturn #out of bounds return
        return self.walls[position[0]][position[1]]
    def enteredRoom(self, details):
        self.updateTileCache()
        self.onRoomEnter.invoke(details)
    def leavingRoom(self, details):
        self.onRoomLeave.invoke(details)

class Door(e.Actor):
    def __init__(self, name, room, position, collisionBounds, sprite,linkedRoom,linkedDoor,playerOffset):
        super().__init__(name, room, collisionBounds,sprite,ghost=True, position=position)
        #self.ghost=True
        self.linkedRoom=linkedRoom
        self.linkedDoor = linkedDoor
        self.playerOffset=playerOffset
        if (self.linkedRoom == 'None'):
            self.linkedRoom = None
            self.linkedDoor = None
            self.setActive(False)
        room.doors[self.name]=self
    def getPlayerStartPosition(self):
        #TODO: get player position relative to self, place based on that
        #   make sure to push player away from colliding with self, though
        return self.position + self.playerOffset
    def playerStart(self):
        self.collidingPlayerStart = True
        e.Player.current.position=self.getPlayerStartPosition()
    def onCollide(self, collision):
        super().onCollide(collision)
        if (collision.collider==e.Player.current): self.triggerLoad()
    def triggerLoad(self):
        Level.current.changeRoom(self.linkedRoom, self.linkedDoor, oldDoor=self)
    def update(self):
        super().update()
    def draw(self):
        return
        super().draw()
        if (self.active):
            tempBox=pygame.Surface((self.collisionBounds.width, self.collisionBounds.height))
            tempBox.fill((0,0,255))
            g.Window.current.screen.blit(tempBox,self.position+self.collisionBounds.topleft)

class WallEntry:
    #TODO: move to own file
    def __init__(self, position, room):
        self.room=room
        self.wall=None
        self.position=position
        self.corners=[[0,0],[0,0]]
        self.cached=True
        self.rect = pygame.Rect(position[0]* room.tileSize, position[1]* room.tileSize,
                                room.tileSize, room.tileSize)
        self.singleTile=None
        self.forceSingleTile=False
    def updateWall(self):
        if (self.wall and self.wall.tileGroup):
            for x in range(-1,2,2):
                for y in range(-1,2,2):
                    offsetIndex=0
                    wall=self.room.getWall((self.position[0]+x, self.position[1]),self)
                    if (wall.wall and wall.wall.tileGroup == self.wall.tileGroup):
                        offsetIndex += 4
                    wall = self.room.getWall((self.position[0], self.position[1]+y),self)
                    if (wall.wall and wall.wall.tileGroup == self.wall.tileGroup):
                        offsetIndex += 2
                    wall=self.room.getWall((self.position[0]+x, self.position[1]+y),self)
                    if (wall.wall and wall.wall.tileGroup == self.wall.tileGroup):
                        offsetIndex += 1
                    #trim fallbacks
                    if (offsetIndex == 1 or offsetIndex == 3 or offsetIndex==5): offsetIndex -=1
                    self.corners[max(0,x)][max(0,y)] = offsetIndex
            self.checkDiagonal()
            #TODO: these caching rules need to propagate downwards,
            #   so when changing a tile we should:
            #       update ourself 
            #       update neighbors (inc. check diagonals for them)
            #       check diagonals on ourself
            #       then, if the neighbor directly below changed its cached state,
            #           or turned to or from fully solid, update the block below that
            #           (and iterate until the chain breaks)
            #TODO: add a flag when setting self, where we only update neighbors in the row above,
            #   and the one to the left
            #   (for when we know we're updating the whole map left to right top to bottom)
            #TODO: if we're only drawing tiles that overlap sprites, we can probably just skip all this
            #   selective caching nonsense
            #   then just use a liveDraw function which is called on any tile colliding with a sprite,
            #       (check if the extra collisions are worth the cost, or if we should just redraw
            #           tiles which contain a sprite plus left and right neighbors)
            #   which calls redraw on the tile below it (adding the tile to a draw queue,
            #       and calling redraw on the one below until culling rules break the chain)
            #   then on draw, just draw the tiles in the queue
            neighbor=self.room.getWall((self.position[0],self.position[1]-1), self)
            self.cached = (neighbor.wall and (neighbor.cached or neighbor.corners==[[7,7],[7,7]]))
            #don't forget to redraw cache after updating
            #maybe can get away with just drawing this tile and every one below it in the same column
            #maybe also just mark the tile's height in an array of all the columns
            #   (unless a higher tile is already marked)
            #   then just update marked columns from that height down
    def setWall(self, wall):
        self.wall=wall
        self.updateWall()
        for x in range(-1,2):
            for y in range(-1,2):
                neighbor = self.room.getWall((self.position[0]+x,self.position[1]+y))
                if (neighbor and neighbor != self): neighbor.updateWall()
        #TODO: checkDiagonal on neighbors after we've updated
    def checkDiagonal(self):
        if (not self.wall.supportsDiagonals): return
        self.singleTile=None
        #TODO: test the relevant corner in the relevant neighbors
        if  (self.corners == [[2,0],[7,4]]):
            #lower left
            #TODO: condense
            #   EG if corner[0] == corner[1] we can use ((-1,1),(1,-1)) else use ((-1,-1,),(1,1))
            #   or maybe even just use the same X coordinate and flip the Y
            neighbors=((-1,-1),(1,1))
            self.singleTile=(0,1)
        elif (self.corners == [[7,4],[2,0]]):
            #lower right
            neighbors=((-1,1),(1,-1))
            self.singleTile=(1,1)
        elif (self.corners == [[0,2],[4,7]]):
            #upper left
            neighbors=((-1,1),(1,-1))
            self.singleTile=(2,1)
        elif (self.corners == [[4,7],[0,2]]):
            #upper right
            neighbors=((-1,-1),(1,1))
            self.singleTile=(3,1)
        if (self.singleTile):
            for coords in neighbors:
                coords=(self.position[0]+coords[0], self.position[1]+coords[1])
                neighbor = self.room.getWall(coords, None)
                if (not (neighbor and neighbor.wall)):
                    self.singleTile=None
                    return

    def draw(self, cache=None):
        #TODO: should be able to condense this down a bit
        draw=(cache and self.cached) or (not cache and not self.cached)
        if (self.wall and draw):
            if (self.wall.forceSingleTile):
                self.wall.drawSingle(self.position,(0,0), surface=cache)
            elif (self.singleTile):
                self.wall.drawSingle(self.position,self.singleTile, surface=cache)
            else:
                self.wall.draw(self.position, self.corners, surface=cache)
    def collide(self, actor, applyForce = True):
        force=e.Actor.__collideTest__(self.rect, actor, applyForce)
        if (force):
            actor.onCollide(e.Actor.Collision(self, force,'wall'))

class Tile:
    def __init__(self, name, rect, tileset): #XY tuple, surface, XY tuple
        self.name=name
        self.surf = pygame.Surface((rect.width, rect.height))
        self.rect = rect
        self.surf.blit(tileset, (-rect.x,-rect.y))
        self.tileset = tileset
    def draw(self, position, surface=None):
        if (not surface): surface=g.Window.current.screen
        surface.blit(self.surf, (position[0]*Room.current.tileSize,
                                               position[1]*Room.current.tileSize))
class WallTile(Tile):
    offsets = (#HVD
        (0,0), #000, 0, outer corner
        (0,0), #001, 1, diagonal only (fallback to outer corner)
        (2,0), #010, 2, vertical wall
        (2,0), #011, 3, vertical wall fallback
        (3,0), #100, 4, horizontal wall
        (3,0), #101, 5, horizontal wall fallback
        (4,0), #110, 6, interior corner
        (1,0)  #111, 7, solid
        )
    def __init__(self, name, rect, tileset, baseHeight=None):
        Tile.__init__(self, name, rect, tileset)
        self.tileGroup=None
        self.supportsDiagonals=False
        self.forceSingleTile=False

        if (baseHeight==None):
            self.baseHeight = rect.height
        else: self.baseHeight = baseHeight
        self.corners = ((pygame.Rect(rect.left, rect.top,
                                     rect.width/2, self.baseHeight/2),
                         pygame.Rect(rect.left, rect.top+self.baseHeight/2,
                                     rect.width/2, rect.height-self.baseHeight/2)),
                        (pygame.Rect(rect.left + rect.width/2, rect.top,
                                     rect.width/2, self.baseHeight),
                         pygame.Rect(rect.left + rect.width/2, rect.top+self.baseHeight/2,
                                     rect.width/2, rect.height-self.baseHeight/2)))
    def draw(self, gridPosition:tuple, corners:tuple, surface=None):
        if (not surface):
            surface=g.Window.current.screen
        tiles = Room.current.walls
        finalPos = (gridPosition[0]*self.rect.width,
                    gridPosition[1]*self.baseHeight - self.rect.height + self.baseHeight)
        for x in range(2):
            for y in range(2):
                offset = WallTile.offsets[corners[x][y]]
                corner = self.corners[x][y]
                corner = corner.move(offset[0] * self.rect.width,
                                     offset[1] * self.rect.height)
                cornerOffset = (x * self.rect.width/2 + finalPos[0],
                                y * self.baseHeight/2 + finalPos[1])
                surface.blit(self.tileset, cornerOffset, area=corner)
    def drawSingle(self, gridPosition, offset, surface=None):
        if (not surface):
            surface=g.Window.current.screen
        rect=self.rect.move((offset[0]*self.rect.width, offset[1]*self.rect.height))
        drawPos=(gridPosition[0]*self.rect.width,
                 gridPosition[1]*self.baseHeight - self.rect.height +self.baseHeight)
        surface.blit(self.tileset, drawPos, area=rect)