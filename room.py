import os
import pygame
from pygame.math import Vector2
import configparser
import gameloop as g
import event as ev
import entities as e
#TODO: rename back to level.py, put Level class in here with Room
#   (it'll probably be long but they're pretty tightly coupled)

class RoomChangeEvent(ev.Event):
    #technically could just use InputEvent, but it's nice having a separate name to avoid confusion
    def invoke(self, room):
        for subscriber in self.subscribers:
            subscriber(room)

class Room:
    current=None
    init=False
    onRoomChange = RoomChangeEvent()
    def __init__(self, roomFile):
        self.onRoomChange = RoomChangeEvent()
        self.onRoomLeave = RoomChangeEvent()
        self.config = configparser.ConfigParser()
        self.config.read(os.path.join(os.getcwd(), 'Assets', 'Levels',roomFile+'.lvl'))
        self.mapImage=pygame.image.load(os.path.join(os.getcwd(), 'Assets', 'Levels', self.config['Main']['Image']))
        self.tileset=pygame.image.load(os.path.join(os.getcwd(), 'Assets', 'Tilesets', self.config['Main']['Tileset']))
        self.width = self.mapImage.get_width()
        self.height = self.mapImage.get_height()
        self.tileSize=int(self.config['Main']['Tilesize'])
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
        self.floorTiles={}
        self.wallTiles={}
        for iniIndex in self.config['Floors']:
            iniString=self.config['Floors'][iniIndex]
            name,x,y=iniString.split(',')
            x,y=(int(x), int(y))
            self.floorTiles[iniIndex]=Tile(name, pygame.Rect(x*self.tileSize,y*self.tileSize,
                                                            self.tileSize,self.tileSize), self.tileset)
        for iniIndex in self.config['Walls']:
            iniString=self.config['Walls'][iniIndex]
            name,x,y,height = iniString.split(',')
            x,y,height =(int(x), int(y), int(height))
            self.wallTiles[iniIndex]=WallTile(name, pygame.Rect(x*self.tileSize,y*self.tileSize,
                                                            self.tileSize,height), self.tileset, baseHeight=self.tileSize)

        for x in range(self.width):
            for y in range(self.height):
                pixel=self.mapImage.get_at((x,y))
                self.floors[x][y]=self.floorTiles[str(pixel[0])]
                if (pixel[1] > 0):
                    self.walls[x][y].setWall(self.wallTiles[str(pixel[1])])

        for doorName in self.config['Doors']:
            doorString=self.config['Doors'][doorName]
            left,top,width,height,dir,linkedRoom,linkedDoor = doorString.split(',')
            left,top,width,height=(int(left)*self.tileSize,int(top)*self.tileSize,int(width)*self.tileSize,int(height)*self.tileSize)
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
            if (entity.active):
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
    def getWall(self, position, oobReturn=None):
        if (position[0] < 0 or position[0] >= self.width or
            position[1] < 0 or position[1] >= self.height):
            return oobReturn #out of bounds return
        return self.walls[position[0]][position[1]]
    def changedRoom(self):
        self.updateTileCache()
        Room.onRoomChange.invoke(self)
        self.onRoomChange.invoke(self)
    def leavingRoom(self, newRoom):
        self.onRoomLeave.invoke(newRoom)

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
    def playerStart(self):
        self.collidingPlayerStart = True
        e.Player.current.position=self.position + self.playerOffset
        #TODO: get player position relative to self, place based on that
        #   make sure to push player away from colliding with self, though
    def onCollide(self, collision):
        super().onCollide(collision)
        if (collision.collider==e.Player.current): self.triggerLoad()
    def triggerLoad(self):
        g.GameLoop.changeRoom(self.linkedRoom, self.linkedDoor)
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
        self.cached=False
        self.rect = pygame.Rect(position[0]* room.tileSize, position[1]* room.tileSize,
                                room.tileSize, room.tileSize)
    def updateWall(self):
        if (self.wall):
            doCache=True
            cacheList=(2,3,7)
            for x in range(-1,2,2):
                for y in range(-1,2,2):
                    offsetIndex=0
                    if (self.room.getWall((self.position[0]+x, self.position[1]),self).wall == self.wall):
                        offsetIndex += 4
                    if (self.room.getWall((self.position[0], self.position[1]+y),self).wall == self.wall):
                        offsetIndex += 2
                    if (self.room.getWall((self.position[0]+x, self.position[1]+y),self).wall == self.wall):
                        offsetIndex += 1
                    self.corners[max(0,x)][max(0,y)] = offsetIndex
                    if (not offsetIndex in cacheList): doCache = False
            self.cached=doCache
            #don't forget to redraw cache after updating
            #maybe can get away with just drawing this tile and every one below it in the same column
            #maybe also just mark the tile's height in an array of all the columns (unless a higher tile is already marked)
            #   then just update marked columns from that height down
    def setWall(self, wall):
        self.wall=wall
        for x in range(-1,2):
            for y in range(-1,2):
                neighbor = self.room.getWall((self.position[0]+x,self.position[1]+y))
                if (neighbor): neighbor.updateWall()
    def draw(self, cache=None):
        if (self.wall):
            if (cache):
                if (self.cached):
                    self.wall.draw(self.position, self.corners, surface=cache)
            else:
                if (not self.cached):
                    self.wall.draw(self.position, self.corners)
    def collide(self, actor, applyForce = True):
        collisionBox=actor.collisionBounds.move(actor.position + actor.velocity*g.deltaTime)
        if (self.rect.colliderect(collisionBox)):
            normal=Vector2(collisionBox.center) - Vector2(self.rect.center)
            sign=[1,1]
            if (normal.x < 0): sign[0] = -1
            if (normal.y < 0): sign[1] = -1
            force=Vector2(self.rect.width/2*sign[0] + collisionBox.width/2*sign[0] - normal.x,
                            self.rect.height/2*sign[1] + collisionBox.height/2*sign[1] - normal.y)

            #TODO: use vel to bias result
            #   (goal: so if actor hits a corner, the are "nudged" sideways and can continue moving
            #   instead of being stopped because two squares overlapped by 2 pixels
            if (abs(force.x) > abs(force.y)):
                #normal is along the y axis
                force.x=0
                if (applyForce and not actor.ghost):
                    #TODO: there's gotta be a way to simplify this down
                    actor.position.y += force.y + actor.velocity.y * g.deltaTime
                    actor.velocity.y=0
            else:
                #normal is along the x axis
                force.y=0
                if (applyForce and not actor.ghost):
                    actor.position.x += force.x + actor.velocity.x * g.deltaTime
                    actor.velocity.x=0
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
        (0,1), #000, 0, outer corner
        (0,1), #001, 1, diagonal only (fallback to outer corner)
        (2,1), #010, 2, vertical wall
        (2,1), #011, 3, vertical wall fallback
        (2,0), #100, 4, horizontal wall
        (2,0), #101, 5, horizontal wall fallback
        (1,0), #110, 6, interior corner
        (1,1)  #111, 7, solid
        )
    def __init__(self, name, rect, tileset, baseHeight=None):
        Tile.__init__(self, name, rect, tileset)
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
    def draw(self, gridPosition, corners, surface=None):
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

