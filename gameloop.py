import os
from pygame import locals
import pygame
from pygame.math import Vector2
import datetime
import room as rm
import entities as ent
import event as ev

deltaTime=100
class GameLoop:
    lastTime=None
    rooms={}
    #TODO: make Level class to wrap a bunch of rooms together
    #gameloop can store  a list of levels, move this rooms dict into Level
    def __init__(game):
        GameLoop.current=game
        game.running = True
        pygame.init()
        pygame.display.set_caption("C'est Une Sword")
        pygame.display.set_icon(pygame.image.load(os.path.join(os.getcwd(), 'Assets','Icon.png')))
        #TODO: some system so multiple bindings to the same action don't trip the action multiple times
        #maybe a go-between class that uses 'or' on all the inputs, and triggers on edges
        GameLoop.mapping ={
            pygame.locals.K_w:'moveUp',
            pygame.locals.K_UP:'moveUp',
            pygame.locals.K_s:'moveDown',
            pygame.locals.K_DOWN:'moveDown',
            pygame.locals.K_a:'moveLeft',
            pygame.locals.K_LEFT:'moveLeft',
            pygame.locals.K_d:'moveRight',
            pygame.locals.K_RIGHT:'moveRight',
            pygame.locals.K_x:'dodge',
            pygame.locals.K_LSHIFT:'dodge',
            pygame.locals.K_z:'attack',
            pygame.locals.K_SPACE:'attack',
            pygame.locals.K_f:'debugDisplay',
            pygame.locals.K_c:'debugChart',
            pygame.locals.K_v:'debugSpawn'}
        GameLoop.inputEvents={}
        for key in GameLoop.mapping:
            val=GameLoop.mapping[key]
            if (not val in GameLoop.inputEvents):
                GameLoop.inputEvents[val] = ev.InputEvent()
        
        game.window = Window()
        player=ent.Player()
        GameLoop.changeRoom('StartRoom', 'start')
        player.spawnLandingImpact()
        GameLoop.lastTime = datetime.datetime.now()
        
    def updateDeltaTime():
        global deltaTime
        time=datetime.datetime.now()
        deltaTime=(time-GameLoop.lastTime).microseconds / 1000000
        GameLoop.lastTime=time

    def loadRoom(roomName):
        print('loading room ',roomName)
        #TODO: learn about how to trigger garbage collection (and ensure the previous room is properly flushed)
        GameLoop.rooms[roomName] = rm.Room(roomName)
    def changeRoom(roomName, doorName):
        #print('moving to room ', roomName, ' at door ', doorName)
        if (not roomName in GameLoop.rooms):
            GameLoop.loadRoom(roomName)
        newRoom=GameLoop.rooms[roomName]
        if (rm.Room.current):
            rm.Room.current.leavingRoom(newRoom)
        rm.Room.current=newRoom
        ent.Player.current.setRoom(newRoom)
        newRoom.doors[doorName].playerStart()
        newRoom.changedRoom()

    def quit(game):
        print('quitting')
        game.running = False
    def update(game):
        for entity in rm.Room.current.entities:
            if (entity.active):
                entity.update()
    def physics(game):
        testActors = []
        for actor in rm.Room.current.actors:
            if (actor.active and not actor.noCollide):
                if (not actor.noCollideActors): testActors.append(actor)
                if (not actor.noCollideWalls):
                    cellIndex=actor.position//rm.Room.current.tileSize
                    remainder=actor.position - cellIndex * rm.Room.current.tileSize
                    remainder -= Vector2(rm.Room.current.tileSize/2,rm.Room.current.tileSize/2)
                    if (remainder.x > 0):remainder.x=1
                    else: remainder.x=-1
                    if (remainder.y > 0): remainder.y=1
                    else: remainder.y=-1
                    for x in range(0,2):
                        for y in range(0,2):
                            wall = rm.Room.current.getWall((int(cellIndex.x + remainder.x*x), int(cellIndex.y + remainder.y*y)))
                            if(wall and wall.wall): wall.collide(actor)
        while len(testActors) > 1:
            actor=testActors.pop(0)
            for actor2 in testActors:
                actor.gameloopCollision(actor2)
        for actor in rm.Room.current.actors:
            actor.afterPhysics()
    def main(game):
        while game.running:
            GameLoop.updateDeltaTime()
            for event in pygame.event.get():
                if event.type == locals.QUIT:
                    game.quit()
                elif event.type== locals.KEYDOWN:
                    if event.key == locals.K_ESCAPE:
                        game.quit()
                    elif event.key in GameLoop.mapping:
                        GameLoop.inputEvents[GameLoop.mapping[event.key]].invoke(True)
                elif event.type== locals.KEYUP:
                    if event.key in GameLoop.mapping:
                        GameLoop.inputEvents[GameLoop.mapping[event.key]].invoke(False)
            game.update()
            game.physics()
            rm.Room.current.draw()

class Window:
    current = None
    framerates=[]
    def __init__(self):
        pygame.font.init()
        #print(pygame.font.get_fonts())
        self.width = 400
        self.height = 240
        self.mult=3
        self.screenSize=(self.width*self.mult, self.height*self.mult)
        self.font=pygame.font.Font(pygame.font.match_font('arial'), 16*self.mult)
        self.screen=pygame.Surface((self.width, self.height))
        self.actualScreen = pygame.display.set_mode((self.width*self.mult, self.height*self.mult))
        self.frameChart = pygame.Surface((600,300), pygame.SRCALPHA, 32)
        self.drawFramerate=False
        self.drawChart = False
        GameLoop.inputEvents['debugDisplay'].add(self.toggleDrawFramerate)
        GameLoop.inputEvents['debugChart'].add(self.toggleDrawFramechart)
        Window.current=self

        #effects (placeholder variables, mostly)
        #bump the screen over some amount of pixels
        self.bumpVec=None
        self.bumpTime=0
        self.shakeCount=0
        self.shakeTime=0
        #TODO: screenflash removed because epillepsy, but check if it's bad on a tiny not-backlit handheld later
    def initializeFramerates(self):
        self.weightedFramerateCount=100
        framerates=[]
        for i in range(self.weightedFramerateCount):
            framerates.append(0)
        Window.framerates=framerates
    def initializeFramechart(self):
        self.frameChart.fill((0,0,0,0))
    def framerateCounter(self):
        if(self.drawFramerate and deltaTime != 0):
            del Window.framerates[0]
            f = 1/deltaTime
            Window.framerates.append(f)
            framerate = 0
            for f in Window.framerates:
                framerate += f
            framerate /= self.weightedFramerateCount
            #TODO: start with an empty list, just overwrite when at length (average won't creep up from 0 at start, that way)
            #TODO: maybe just track a position and overwrite that index, instead of deleting and appending
            if (self.drawChart):
                #costs a few frames on its own
                self.frameChart.scroll(1,0)
                h = self.frameChart.get_height()
                self.frameChart.fill((0,0,0,0),pygame.Rect(0,0,1,h))
                self.frameChart.fill((0,255,0,128), pygame.Rect(0,h-f, 1, f))
                self.frameChart.fill((0,0,255,128), pygame.Rect(0,h-framerate+2, 1, 4))
                self.actualScreen.blit(self.frameChart, (0,0))
            self.actualScreen.blit(self.font.render(str(int(framerate)), False, (0,255,0)), (5*self.mult,5*self.mult))
    def flip(self):
        self.doEffects()
        pygame.transform.scale(self.screen,self.screenSize,self.actualScreen)
        self.framerateCounter()
        pygame.display.flip()
    def bump(self, x,y,time):
        self.bumpTime=time
        self.bumpVec=(x,y)
    def shake(self, count, x,y, time):
        self.shakeCount=count
        self.shakeTime=time
        self.bump(x,y,time)
    def doEffects(self):
        #TODO: add abortEffects() command, to cease all effects
        if (self.bumpTime > 0):
            self.screen.scroll(self.bumpVec[0],self.bumpVec[1])
            self.bumpTime-= deltaTime
            if (self.bumpTime <=0 and self.shakeCount>0):
                self.shakeCount-=1
                self.bump(-self.bumpVec[0],-self.bumpVec[1], self.shakeTime)
    def toggleDrawFramerate(self, state):
        if (state):
            self.drawFramerate = not self.drawFramerate
            if (self.drawFramerate):
                self.initializeFramerates()
                if (self.drawChart):
                    self.initializeFramechart()

    def toggleDrawFramechart(self, state):
        if (state):
            self.drawChart = not self.drawChart
            if (self.drawChart and self.drawFramerate):
                self.initializeFramechart()

