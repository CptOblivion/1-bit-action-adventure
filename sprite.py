import os
import pygame
from pygame.math import Vector2
import gameloop as g

class Sprite:
    def loadSheet(sheetName):
        return pygame.image.load(os.path.join(os.getcwd(), 'Assets','Sprites',sheetName+'.png'))
    class State:
        #TODO: move state.currentFrame into Sprite, so we can reuse states between multiple sprite instances
        #TODO: automatic caching of state instances in multiple copies of the same object
        def __init__(self, frames):
            self.frames=[]
            if ((not (type(frames) == list or type(frames) == tuple)) or type(frames[0])==int):
                frames=(frames,) #single frames can be passed, nest it in an empty tuple for simple processing
            for frame in frames:
                if (type(frame) == Sprite.Frame):
                    self.frames.append(frame)
                else:
                    if (len(frame) == 5):time=frame[4]
                    else: time=None
                    self.frames.append(Sprite.Frame(frame[0],frame[1],frame[2],frame[3], time=time))

            self.frames = tuple(self.frames)
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
        def __init__(self, *args, time=None):
            if (type(args[0])==pygame.Rect):
                rect = args[0]
            else:
                rect = pygame.Rect(args[0],args[1],args[2],args[3])
                if (len(args)==5): time=args[4]
            self.rect=rect
            self.time=time
    def __init__(self, sheetName, startState, states={}, sheet=None):
        self.sheetName=sheetName
        if (sheet):
            #TODO: cache sheets (dict in Sprite that tracks sheet names)
            #   watch memory bloat though, might need to clear the cache periodically
            self.sheet=sheet
        else:
            self.sheet=Sprite.loadSheet(sheetName)
        self.animTimer=0
        self.nextFrameTime=0
        self.states=states
        for stateName in self.states:
            self.states[stateName]=Sprite.initState(self.states[stateName])
        if (type(startState) == str and states):
            if (not startState in states):
                raise IndexError('startState '+startState+' not in states!')
            self.currentState = states[startState]
            self.startState=startState
        else:
            self.states['start'] = self.currentState = Sprite.initState(startState)
            self.startState='start'
        
        self.currentSprite=self.currentState.activate().rect
    def resetState(self):
        self.setState(self.startState, restart=True)

    def initState(state):
        if (type(state)==list or type(state)==tuple):
            return Sprite.State(state)
        return state

    def draw(self, position, target=None):
        #pass None to position to update timers without drawing
        if (len(self.currentState.frames)>1):
            self.animTimer+=g.deltaTime
            #TODO: maybe move timer into update (if draw isn't called, eg while offscreen, anim won't play)
            if (self.animTimer >= self.nextFrameTime):
                self.animTimer = 0
                self.currentSprite=self.currentState.advanceFrame()
                time=self.currentState.frames[self.currentState.currentFrame].time
                if (time):
                    self.nextFrameTime=time
        if (position is not None):
            if (target == None): target=g.Window.current.screen
            #TODO: return this sprite stuff
            target.blit(self.sheet, position, area=self.currentSprite)
    def setState(self, state, restart=False):
        if ((state in self.states and self.states[state] != self.currentState) or restart):
            self.animTimer=0
            self.currentState=self.states[state]
            self.currentSprite=self.currentState.activate()
            self.nextFrameTime = self.currentState.frames[0].time