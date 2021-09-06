import os
import pygame
from pygame.math import Vector2
import GameLoops
import Entities
import configparser
import LevelDoor
#from Cest_Une_Sword_Prototype import Window

class Level:
    current=None
    init=False
    #def __init__(self, mapImage, tileSize, tileset):
        #self.mapImage = pygame.image.load(os.path.join(os.getcwd(), 'Assets', 'Levels', mapImage))
        #self.width = self.mapImage.get_width()
        #self.height = self.mapImage.get_height()
        #self.tileSize = tileSize
        #self.tileset = pygame.image.load(os.path.join(os.getcwd(), 'Assets', 'Tilesets', tileset))

        #floor = Tile('NormalFloor',pygame.Rect(0,0,tileSize, tileSize), self.tileset)
        #wall= WallTile('NormalWall',pygame.Rect(96,0,16,32),self.tileset, baseHeight=16)
    def __init__(self, levelFile):
        Level.current=self
        self.config = configparser.ConfigParser()
        self.config.read(os.path.join(os.getcwd(), 'Assets', 'Levels',levelFile+'.lvl'))
        self.mapImage=pygame.image.load(os.path.join(os.getcwd(), 'Assets', 'Levels', self.config['Main']['Image']))
        self.tileset=pygame.image.load(os.path.join(os.getcwd(), 'Assets', 'Tilesets', self.config['Main']['Tileset']))
        self.width = self.mapImage.get_width()
        self.height = self.mapImage.get_height()
        self.tileSize=int(self.config['Main']['Tilesize'])

        self.floors = []
        self.walls = []
        self.entities=[]
        self.actors=[]
        self.doors={}

        for x in range(self.width):
            rowFloor = []
            rowWall = []
            for y in range(self.height):
                rowWall.append(WallEntry((x,y)))
                rowFloor.append(None)
            self.floors.append(rowFloor)
            self.walls.append(rowWall)
        self.floorTiles={}
        self.wallTiles={}
        for iniIndex in self.config['Floors']:
            iniString=self.config['Floors'][iniIndex]
            name,x,y=iniString.split(',')
            pixel = self.tileset.get_at((int(x),int(y)))
            self.floorTiles[iniIndex]=Tile(name, pygame.Rect(pixel[0]*self.tileSize,pixel[1]*self.tileSize,
                                                            self.tileSize,self.tileSize), self.tileset)
        for iniIndex in self.config['Walls']:
            iniString=self.config['Walls'][iniIndex]
            name,x,y = iniString.split(',')
            pixel=self.tileset.get_at((int(x),int(y)))
            #print(pixel)
            self.wallTiles[iniIndex]=WallTile(name, pygame.Rect(pixel[0]*self.tileSize,pixel[1]*self.tileSize,
                                                            self.tileSize,pixel[2]), self.tileset, baseHeight=self.tileSize)

        for x in range(self.width):
            for y in range(self.height):
                pixel=self.mapImage.get_at((x,y))
                self.floors[x][y]=self.floorTiles[str(pixel[0])]
                if (pixel[1] > 0):
                    self.walls[x][y].setWall(self.wallTiles[str(pixel[1])])
        for levelDoorName in self.config['Doors']:
            doorString=self.config['Doors'][levelDoorName]
            #print(doorString)
            x,y,exitDir,linkedLevel,linkedDoor = doorString.split(',')
            position = (int(x)*self.tileSize+self.tileSize/2,int(y)*self.tileSize+self.tileSize/2)
            bounds=pygame.Rect(-self.tileSize/2,-self.tileSize/2,self.tileSize,self.tileSize)
            levelDoor=LevelDoor.LevelDoor(levelDoorName,position,bounds,None,exitDir,linkedLevel,linkedDoor)


    def getWall(self, position, oobReturn=None):
        if (position[0] < 0 or position[0] >= self.width or
            position[1] < 0 or position[1] >= self.height):
            return oobReturn #out of bounds return
        return self.walls[position[0]][position[1]]
class WallEntry:
    def __init__(self, position):
        self.wall=None
        self.position=position
        self.corners=[[0,0],[0,0]]
        self.rect = pygame.Rect(position[0]* Level.current.tileSize, position[1]* Level.current.tileSize,
                                Level.current.tileSize, Level.current.tileSize)
    def updateWall(self):
        if (self.wall):
            for x in range(-1,2,2):
                for y in range(-1,2,2):
                    offsetIndex=0
                    if (Level.current.getWall((self.position[0]+x, self.position[1]),self).wall == self.wall):
                        offsetIndex += 4
                    if (Level.current.getWall((self.position[0], self.position[1]+y),self).wall == self.wall):
                        offsetIndex += 2
                    if (Level.current.getWall((self.position[0]+x, self.position[1]+y),self).wall == self.wall):
                        offsetIndex += 1
                    self.corners[max(0,x)][max(0,y)] = offsetIndex
    def setWall(self, wall):
        self.wall=wall
        for x in range(-1,2):
            for y in range(-1,2):
                neighbor = Level.current.getWall((self.position[0]+x,self.position[1]+y))
                if (neighbor): neighbor.updateWall()
    def draw(self):
        if (self.wall):
            self.wall.draw(self.position, self.corners)
    def collide(self, collisionBox):
        if (self.rect.colliderect(collisionBox)):
            normal=Vector2(collisionBox.center) - Vector2(self.rect.center)
            sign=[1,1]
            if (normal.x < 0): sign[0] = -1
            if (normal.y < 0): sign[1] = -1
            force=Vector2(self.rect.width/2*sign[0] + collisionBox.width/2*sign[0] - normal.x,
                            self.rect.height/2*sign[1] + collisionBox.height/2*sign[1] - normal.y)
            if (abs(force.x) > abs(force.y)): force.x=0
            else: force.y=0
            return(Entities.Actor.Collision(self, force,'wall'))

        return None

class Tile:
    def __init__(self, name, rect, tileset): #XY tuple, surface, XY tuple
        self.name=name
        self.surf = pygame.Surface((rect.width, rect.height))
        self.rect = rect
        self.surf.blit(tileset, (-rect.x,-rect.y))
        self.tileset = tileset
    def draw(self, position):
        GameLoops.Window.current.screen.blit(self.surf, (position[0]*Level.current.tileSize,
                                               position[1]*Level.current.tileSize))
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
    def draw(self, levelPosition, corners):
        tiles = Level.current.walls
        finalPos = (levelPosition[0]*Level.current.tileSize,
                    levelPosition[1]*Level.current.tileSize - self.rect.height + self.baseHeight)
        for x in range(2):
            for y in range(2):
                offset = WallTile.offsets[corners[x][y]]
                corner = self.corners[x][y]
                corner = corner.move(offset[0] * self.rect.width,
                                     offset[1] * self.rect.height)
                cornerOffset = (x * self.rect.width/2 + finalPos[0],
                                y * self.baseHeight/2 + finalPos[1])
                GameLoops.Window.current.screen.blit(self.tileset, cornerOffset, area=corner)