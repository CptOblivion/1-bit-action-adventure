import os
from pygame import locals
import pygame
from pygame.math import Vector2
import datetime
import level as lv
import entities as ent
import event as ev

deltaTime=100
class GameLoop:
    lastTime=None
    levels={}
    def __init__(game):
        GameLoop.current=game
        pygame.init()
        pygame.display.set_caption("C'est Une Sword")
        pygame.display.set_icon(pygame.image.load(os.path.join(os.getcwd(), 'Assets','Icon.png')))
        game.window = Window()
        game.running = True
        GameLoop.inputEvents={
            'moveUp':ev.InputEvent(),
            'moveDown':ev.InputEvent(),
            'moveLeft':ev.InputEvent(),
            'moveRight':ev.InputEvent(),
            'dodge':ev.InputEvent()}

        player=ent.Player()
        GameLoop.changeLevel('TestLevel3', 'start')
        GameLoop.lastTime = datetime.datetime.now()
        
    def updateDeltaTime():
        global deltaTime
        time=datetime.datetime.now()
        deltaTime=(time-GameLoop.lastTime).microseconds / 1000000
        GameLoop.lastTime=time

    def loadLevel(levelName):
        print('loading level ',levelName)
        #TODO: learn about how to trigger garbage collection (and ensure the previous level is properly flushed)
        GameLoop.levels[levelName] = lv.Level(levelName)
    def changeLevel(levelName, doorName):
        print('moving to level ', levelName, ' at door ', doorName)
        if (not levelName in GameLoop.levels):
            GameLoop.loadLevel(levelName)
        newLevel=GameLoop.levels[levelName]
        if (lv.Level.current):
            lv.Level.current.leavingLevel(newLevel)
        lv.Level.current=newLevel
        ent.Player.current.setLevel(newLevel)
        ent.Player.current.position=newLevel.doors[doorName].position
        newLevel.changedLevel()

    def quit(game):
        print('quitting')
        game.running = False
    def update(game):
        for entity in lv.Level.current.entities:
            if (entity.active):
                entity.update()
    def physics(game):
        testActors = []
        for actor in lv.Level.current.actors:
            testActors.append(actor)
            cellIndex=actor.position//lv.Level.current.tileSize #TODO: make sure floor division is what I think it is
            remainder=actor.position - cellIndex * lv.Level.current.tileSize
            remainder -= Vector2(lv.Level.current.tileSize/2,lv.Level.current.tileSize/2)
            if (remainder.x > 0):remainder.x=1
            else: remainder.x=-1
            if (remainder.y > 0): remainder.y=1
            else: remainder.y=-1
            for x in range(0,2):
                for y in range(0,2):
                    wall = lv.Level.current.getWall((int(cellIndex.x + remainder.x*x), int(cellIndex.y + remainder.y*y)))
                    if(wall and wall.wall):
                        collisionBounds = actor.collisionBounds.move(actor.position)
                        collision = wall.collide(collisionBounds)
                        if (collision):
                            actor.onCollide(collision)
                            actor.position += collision.force
        while len(testActors) > 1:
            actor=testActors.pop(0)
            for actor2 in testActors:
                actor.gameloopCollision(actor2)
        None
    def main(game):
        while game.running:
            GameLoop.updateDeltaTime()
            for event in pygame.event.get():
                if event.type == locals.QUIT:
                    game.quit()
                elif event.type== locals.KEYDOWN:
                    if event.key == locals.K_ESCAPE:
                        game.quit()
                    elif event.key == locals.K_SPACE:
                        GameLoop.inputEvents['dodge'].invoke(True)
                    elif event.key == pygame.locals.K_w:
                        GameLoop.inputEvents['moveUp'].invoke(True)
                    elif event.key == locals.K_s:
                        GameLoop.inputEvents['moveDown'].invoke(True)
                    elif event.key == locals.K_a:
                        GameLoop.inputEvents['moveLeft'].invoke(True)
                    elif event.key == locals.K_d:
                        GameLoop.inputEvents['moveRight'].invoke(True)
                elif event.type== locals.KEYUP:
                    if event.key == locals.K_SPACE:
                        GameLoop.inputEvents['dodge'].invoke(False)
                    elif event.key == pygame.locals.K_w:
                        GameLoop.inputEvents['moveUp'].invoke(False)
                    elif event.key == locals.K_s:
                        GameLoop.inputEvents['moveDown'].invoke(False)
                    elif event.key == locals.K_a:
                        GameLoop.inputEvents['moveLeft'].invoke(False)
                    elif event.key == locals.K_d:
                        GameLoop.inputEvents['moveRight'].invoke(False)
            game.update()
            game.physics()
            lv.Level.current.draw()

class Window:
    current = None
    def __init__(self):
        self.width = 400
        self.height = 240
        self.screen = pygame.display.set_mode((self.width, self.height))
        Window.current=self
