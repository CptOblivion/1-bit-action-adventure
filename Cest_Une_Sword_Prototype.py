import pygame
from pygame import locals
import os
import sys
from pygame.math import Vector2

class Window:
    current = None
    def __init__(self):
        self.width = 400
        self.height = 240
        self.screen = pygame.display.set_mode((self.width, self.height))
        Window.current=self

class GameLoop:
    def __init__(game):
        GameLoop.current=game
        pygame.init()
        pygame.display.set_caption("C'est Une Sword")
        pygame.display.set_icon(pygame.image.load(os.path.join(os.getcwd(), 'Assets','Icon.png')))
        game.window = Window()
        game.running = True
        GameLoop.inputEvents={
            'moveUp':Event(),
            'moveDown':Event(),
            'moveLeft':Event(),
            'moveRight':Event()}

        #debug startup stuff
        game.currentLevel = Level('TestLevel.png', 16, 'Testmap2.png')
        player=Player((100,100))

    def quit(game):
        print('quitting')
        game.running = False
    def update(game):
        for entity in Level.current.entities:
            if (entity.active):
                entity.update()
    def physics(game):
        #clone Level.current.actors
        testActors = []
        for actor in Level.current.actors:
            testActors.append(actor)
            cellIndex=actor.position//Level.current.tileSize #TODO: make sure floor division is what I think it is
            remainder=actor.position - cellIndex * Level.current.tileSize
            remainder -= Vector2(Level.current.tileSize/2,Level.current.tileSize/2)
            if (remainder.x > 0):remainder.x=1
            else: remainder.x=-1
            if (remainder.y > 0): remainder.y=1
            else: remainder.y=-1
            for x in range(0,2):
                for y in range(0,2):
                    wall = Level.current.getWall((int(cellIndex.x + remainder.x*x), int(cellIndex.y + remainder.y*y)))
                    if(wall.wall):
                        collisionBounds = actor.collisionBounds.move(actor.position)
                        collision = wall.collide(actor.collisionBounds)
                        if (collision):
                            actor.onCollide(collision)
                            actor.position += collision.force
                            #get normal

                            #move along normal until outside of rect

            

            #print(cell)
            #test collision against wall, floors
        while len(testActors) > 1:
            actor=testActors.pop(0)
            for actor2 in testActors:
                actor.testCollision(actor2)
        None
    def draw(game):
        game.window.screen.fill((255,255,255))
        tile = pygame.Surface((game.currentLevel.tileSize, game.currentLevel.tileSize))
        tile.fill((0,0,0))
        entityPositions=[]
        for i in range(game.currentLevel.height):
            entityPositions.append([])
        for entity in Level.current.entities:
            if (entity.active):
                gridCell = int(entity.position.y / Level.current.tileSize)
                if (0 <= gridCell < len(entityPositions)):
                    entityPositions[gridCell].append(entity)
        for y in range(game.currentLevel.height):
            for x in range(game.currentLevel.width):
                if (game.currentLevel.floors[x][y]):
                    game.currentLevel.floors[x][y].draw((x,y))
        for y in range(game.currentLevel.height):
            for x in range(game.currentLevel.width):
                if (game.currentLevel.walls[x][y]):
                    game.currentLevel.walls[x][y].draw()
            for entity in entityPositions[y]:
                entity.draw()
        pygame.display.flip()

    def main(game):
        while game.running:
            for event in pygame.event.get():
                if event.type== locals.KEYDOWN:
                    if event.key == locals.K_ESCAPE:
                        game.quit()
                elif event.type == locals.QUIT:
                    game.quit()
            pressed = pygame.key.get_pressed()
            if (pressed[pygame.locals.K_w]):
                GameLoop.inputEvents['moveUp'].invoke()
            if (pressed[locals.K_s]):
                GameLoop.inputEvents['moveDown'].invoke()
            if (pressed[locals.K_a]):
                GameLoop.inputEvents['moveLeft'].invoke()
            if (pressed[locals.K_d]):
                GameLoop.inputEvents['moveRight'].invoke()
            game.update()
            game.physics()
            game.draw()

class Tile:
    def __init__(self, rect, tileMap): #XY tuple, surface, XY tuple
        self.surf = pygame.Surface((rect.width, rect.height))
        self.rect = rect
        self.surf.blit(tileMap, (-rect.x*rect.width,-rect.y * rect.height))
        self.tileMap = tileMap
    def draw(self, position):
        Window.current.screen.blit(self.surf, (position[0]*Level.current.tileSize,
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
    def __init__(self, rect, tileMap, baseHeight=None):
        Tile.__init__(self, rect, tileMap)
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
                Window.current.screen.blit(self.tileMap, cornerOffset, area=corner)


class Level:
    class WallEntry:
            def __init__(self, position):
                self.wall=None
                self.position=position
                self.corners=[[0,0],[0,0]]
                self.rect = pygame.Rect(position[0]* Level.current.tileSize, position[1]* Level.current.tileSize,
                                        Level.current.tileSize, Level.current.tileSize)
                self.edges = ()
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
                print(self.rect.midleft, self.rect.topleft, self.rect.bottomleft)
                return False
    current=None
    def __init__(self, mapImage, tileSize, tileMap):
        self.mapImage = pygame.image.load(os.path.join(os.getcwd(), 'Assets', 'Levels', mapImage))
        self.width = self.mapImage.get_width()
        self.height = self.mapImage.get_height()
        self.tileSize = tileSize
        self.tileMap = pygame.image.load(os.path.join(os.getcwd(), 'Assets', 'Tilemaps', tileMap))
        self.floors = []
        self.walls = []
        
        self.entities=[]
        self.actors=[]
        Level.current=self

        #TODO: move tile definitions to level metadata file
        #TODO: separate tile height and level grid height (since tiles can stick out the top of their grid cell)
        
        floor = Tile(pygame.Rect(0,0,tileSize, tileSize), self.tileMap)
        wall= WallTile(pygame.Rect(96,0,16,32),self.tileMap, baseHeight=16)

        for x in range(self.width):
            rowFloor = []
            rowWall = []
            for y in range(self.height):
                rowWall.append(Level.WallEntry((x,y)))
                rowFloor.append(floor)
            self.floors.append(rowFloor)
            self.walls.append(rowWall)

        #debug level population
        for x in range(self.width):
            for y in range(self.height):
                if (self.mapImage.get_at((x,y)).g == 0):
                    self.walls[x][y].setWall(wall)
        #levels are saved as a data file, and an image
        #data file points to a tileMap, an image layout file, and indices for entities and such
        #the image is the level layout, where each pixel represents a tile
        #the color of the pixel is the four layers of objects on that point in the level
        #R = floor, G = wall, B and A are entities (maybe B is entities, A is logic?
        #   EG level triggers, etc- or maybe those are just entities also)
    def getWall(self, position, oobReturn=None):
        if (position[0] < 0 or position[0] >= self.width or
            position[1] < 0 or position[1] >= self.height):
            return oobReturn #out of bounds return
        return self.walls[position[0]][position[1]]

class Event:
    def __init__(self):
        self.subscribers = []
    def invoke(self):
        for subscriber in self.subscribers:
            subscriber()

class Sprite:
    class State:
        def __init__(self, frames):
            if (not (type(frames) == list or type(frames) == tuple)):
                raise TypeError('wrong type:', type(frames))
            self.frames = frames
            self.currentFrame=0
        def getCurrentFrame(self):
            return self.frames[self.currentFrame]
        def advanceFrame(self):
            if (self.currentFrame == len(self.frames)-1):
                self.currentFrame=0
            else:
                self.currentFrame+=1
            return self.frames[self.currentFrame].rect
        def activate(self):
            self.currentFrame = 0
            return self.frames[0]
    class Frame:
        def __init__(self, rect, time=None):
            self.rect=rect
            self.time=time
    def __init__(self, sheetName, startState, states={}):
        self.sheetName=sheetName
        self.sheet=pygame.image.load(os.path.join(os.getcwd(), 'Assets','Sprites',sheetName+'.png'))
        #self.startState = startState
        #self.currentState=startState
        self.animTimer=0
        #TODO: option to put a name in for startState, and pull the name out of states (throw an error if state not in states)
        if (type(startState) == str and states):
            self.states=states
            if (not startState in states):
                raise IndexError('startState '+startState+' not in states!')
            self.currentState = states[startState]
        elif (type(startState) == Sprite.State):
            self.states=states
            self.states['start'] = startState
            self.currentState=startState
        else:
            raise TypeError('states not defined! startState: ' + type(startState) + ', states: ' + type(states))
        
        self.currentSprite=self.currentState.activate().rect
    def draw(self, position):
        if (len(self.currentState.frames)>1):
            self.animTimer+=1 #TODO: implement deltatime
            if (self.animTimer >= self.currentState.getCurrentFrame().time):
                self.animTimer = 0
                self.currentSprite=self.currentState.advanceFrame()
        Window.current.screen.blit(self.sheet, position, area=self.currentSprite)
    def changeState(self, state):
        if (state in self.states and self.states[state] != self.currentState):
            self.animTimer=0
            self.currentState=self.states[state]
            self.currentSprite=self.currentState.activate()

class Entity:
    #objects in scene
    def __init__(self, name, position, sprite, origin=(0,0)):
        self.name = name
        self.position=Vector2(position)
        if (type(sprite) == str):
            self.sprite=Sprite(sprite, Sprite.State(
                (Sprite.Frame(pygame.Rect(0,0,Level.current.tileSize,Level.current.tileSize)),))) #this is a mess
        else:
            self.sprite=sprite
        self.active=True
        self.origin=Vector2(origin)
        self.level = Level.current
        self.level.entities.append(self)
    def setActive(self, state):
        self.active=state
    def draw(self):
        if (self.active):
            self.sprite.draw(self.position+self.origin)
    def update(self):
        None
    def destroy(self):
        self.level.entities.remove(self.level.entities.index(self))
        #TODO: add self to garbage cleanup array in GameLoop, which will properly finish up cleanup after render

class Actor(Entity):
    class Collision:
        def __init__(self, collider, force, collidingObType):
            #collidingObTypes:'floor', 'wall', 'actor'
            self.collider = collider
            self.collidingObType=collidingObType
            self.force = force
    #has collision
    def __init__(self, name, position, collisionBounds, sprite, origin=(0,0), ghost=False):
        Entity.__init__(self, name, position, sprite, origin=origin)
        self.collisionBounds=collisionBounds
        self.level.actors.append(self)
        self.ghost=ghost
        self.oldPosition = pygame.Vector2(position)
    def move(self, vect):
        newPos=self.position+vect

        #TODO: collision
        #actors' physics interaction should have a priority system:
        #heavy actors aren't moved
        #medium actors are stopped/pushed by heavy actors
        #light actors are stopped/pushed by all actors
        #check bounds against level grid
        #check bounds against other actors (filter by grid position?)
        self.position = newPos
    def destroy(self):
        Entity.destroy(self)
        self.level.actors.remove(self.level.actors.index(self))
    def testCollision(self, actor):
        colliding = False
        if colliding:
            force=Vector2(0,0)
            if (self.ghost == actor.ghost == False):
                None
                #resolve physics
                #store result in force on each sprite
            #call onCollide for self and actor

    def onCollide(self, collision):
        None
        
class Character(Actor):
    def __init__(self, name, position, collisionBounds, sprite, origin=(0,0)):
        self.facing=Vector2(1,0)
        reqStates=('idleL', 'idleR', 'walkL', 'walkR')
        for state in reqStates:
            if (not state in sprite.states):
                raise AttributeError('required state ' + state + ' not in sprite!')
        Actor.__init__(self, name, position, collisionBounds, sprite, origin)
    def move(self, vec):
        Actor.move(self, vec)
        if (vec.magnitude() > 0):
            if (vec.x ==0): self.facing.y=vec.y
            else: self.facing = vec.normalize()
            if (self.facing.x > 0): self.sprite.changeState('walkL')
            else: self.sprite.changeState('walkR')
        else:
            if (self.facing.x > 0): self.sprite.changeState('idleL')
            else: self.sprite.changeState('idleR')
class Player(Character):
    #controlled by player
    def __init__(self, position):
        collisionBounds = pygame.Rect(-7,-4,14,8)
        Character.__init__(self, 'player', position, collisionBounds,
                       Sprite('Guy', 'idleL', states = {
                           'idleL':Sprite.State((
                               Sprite.Frame(pygame.Rect(0,0,16,16), time=50),
                               Sprite.Frame(pygame.Rect(0,16,16,16), time=50))),
                           'idleR': Sprite.State((
                               Sprite.Frame(pygame.Rect(16,0,16,16), time=50),
                               Sprite.Frame(pygame.Rect(16,16,16,16), time=50))),
                           'walkL':Sprite.State((
                               Sprite.Frame(pygame.Rect(0,0,16,16), time=7),
                               Sprite.Frame(pygame.Rect(0,16,16,16), time=7))),
                           'walkR':Sprite.State((
                               Sprite.Frame(pygame.Rect(16,0,16,16), time=7),
                               Sprite.Frame(pygame.Rect(16,16,16,16), time=7)))})
                       ,origin=(-8,-15))
        self.moveVec = Vector2(0,0)
        GameLoop.inputEvents['moveUp'].subscribers.append(self.moveUp)
        GameLoop.inputEvents['moveDown'].subscribers.append(self.moveDown)
        GameLoop.inputEvents['moveLeft'].subscribers.append(self.moveLeft)
        GameLoop.inputEvents['moveRight'].subscribers.append(self.moveRight)
        self.debugCollider = (0,255,0)
    def draw(self):
        Character.draw(self)
        if (self.debugCollider):
            tempBox = pygame.Surface((self.collisionBounds.width, self.collisionBounds.height))
            tempBox.fill(self.debugCollider)
            Window.current.screen.blit(tempBox, self.position+self.collisionBounds.topleft)
    def onCollide(self, collision):
        super().onCollide(collision)
        self.debugCollider = (255,0,0)
    def move(self, vect):
        Character.move(self, vect)
    def moveUp(self):
        self.moveVec += Vector2(0,-1)
    def moveDown(self):
        self.moveVec += Vector2(0,1)
    def moveLeft(self):
        self.moveVec += Vector2(-1,0)
    def moveRight(self):
        self.moveVec += Vector2(1,0)
    def update(self):
        Character.update(self)
        self.move(self.moveVec)
        self.moveVec = Vector2(0,0)
        if (self.debugCollider): self.debugCollider=(0,255,0)


gameLoop = GameLoop()
gameLoop.main()