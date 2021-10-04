import os
#import time
from pygame import locals
import pygame
from pygame.math import Vector2
import room as rm
import entities as ent
import event as ev

deltaTime=100
timeScale=1

class ActionSet:
    def __init__(self, name, actions:list):
        self.name=name
        self.active=True
        self.actions=actions
        self.toggleState=None
        self.bindMap={
            'keyboard':{
                'keys':{}},
            'controllers':{
                'buttons':{},
                'axes':{},
                'hats':{}}}
        for actionName, action in actions.items():
            for binding in action.bindings:
                self.addToBindMap(binding)
    def addToBindMap(self, binding):
        self.bindMap[binding.address[0]][binding.address[1]][binding.address[2]] = binding

    def setActive(self,state):
        #if (self.active == state): return
        print('setting action set',self.name,'to',state)
        #self.toggleState=state
        self.active=state
        if (state):
            pressedKeys=pygame.key.get_pressed()
            for actionName, action in self.actions.items():
                for binding in action.bindings:
                    #recheck the state of the inputs when the action set is toggled on or off
                    binding.poll(pressedKeys)
    def processInputs(self, events):
        if (not self.active):
            return
        for event in events:
            if (event.type== locals.KEYDOWN and
                  event.key in self.bindMap['keyboard']['keys']):
                self.bindMap['keyboard']['keys'][event.key].trigger(True)
            elif (event.type== locals.KEYUP and
                  event.key in self.bindMap['keyboard']['keys']):
                self.bindMap['keyboard']['keys'][event.key].trigger(False)
            elif (event.type == locals.JOYBUTTONDOWN and
                  event.button in self.bindMap['controller']['buttons']):
                self.bindMap['controller']['buttons'][event.button].trigger(True)
            elif (event.type == locals.JOYBUTTONUP and
                  event.button in self.bindMap['controller']['buttons']):
                self.bindMap['controller']['buttons'][event.button].trigger(False)
            elif (event.type == locals.JOYHATMOTION):
                #split hats into two axes indexed sequentially, EG [hat0.x, hat0.y, hat1.x, hat1.y]
                for hatAxis in (0,1):
                    hatNum = event.hat+hatAxis
                    if (hatNum in self.bindMap['controller']['hats']):
                        self.bindMap['controller']['hats'][hatNum].trigger(event.value[hatAxis])
            elif (event.type ==  locals.JOYAXISMOTION):
                if (event.axis in self.bindMap['controller']['axes']):
                    self.bindMap[inputSet]['controller']['axes'][event.axis].trigger(event.value)



#TODO: move to own file
class Input:
    def init():
        pygame.joystick.init()
        Input.controllers=[]
        #TODO: put all this in an ini file (with a default one saved somewhere else)
        Input.actionSets={
            'menus':ActionSet('menus',{
                'cancel':Action('cancel',[
                    Binding(['keyboard','keys',locals.K_ESCAPE],'button')])
                }),
            'gameplay':ActionSet('gameplay',{
                'pause':Action('pause',[
                    Binding(['keyboard','keys',locals.K_ESCAPE],'button')]),
                'moveX':Action('moveX',[
                    Binding(['keyboard','keys',locals.K_d],'button'),
                    Binding(['keyboard','keys',locals.K_a],'button', invert=True),
                    Binding(['keyboard','keys',locals.K_RIGHT],'button'),
                    Binding(['keyboard','keys',locals.K_LEFT],'button', invert=True),
                    Binding(['controllers','axes',0],'analog'),
                    Binding(['controllers','hats',0],'analog')
                    ]),
                'moveY':Action('moveY',[
                    Binding(['keyboard','keys',locals.K_s],'button', invert=True),
                    Binding(['keyboard','keys',locals.K_w],'button'),
                    Binding(['keyboard','keys',locals.K_DOWN],'button', invert=True),
                    Binding(['keyboard','keys',locals.K_UP],'button'),
                    Binding(['controllers','axes',1],'analog', invert=True),
                    Binding(['controllers','hats',1],'analog')
                    ]),
                'dodge':Action('dodge',[
                    Binding(['keyboard','keys',locals.K_x],'button'),
                    Binding(['controllers','buttons',0],'button')
                    ]),
                'attack':Action('attack',[
                    Binding(['keyboard','keys',locals.K_z],'button'),
                    Binding(['controllers','buttons',1],'button')
                    ]),
                'debugDisplay':Action('debugDisplay',[
                    Binding(['keyboard', 'keys', locals.K_f],'button')]),
                'debugChart':Action('debugChart',[
                    Binding(['keyboard', 'keys', locals.K_r],'button')]),
                'debugSpawn':Action('debugSpawn',[
                    Binding(['keyboard', 'keys', locals.K_v],'button')])
                })}
        Input.actionSets['gameplay'].setActive(False)
    def addController(event):
        index=event.device_index
        print('controller ', index, ' connected: ')
        joystick = pygame.joystick.Joystick(index)
        if (len(Input.controllers) < index+1):
            Input.controllers.append(joystick)
        else:
            Input.controllers[index] = joystick
        #guid
    def removeController(event):
        index = event.instance_id
        print('controller ',index,' disconnected')
        Input.controllers[index].quit()
        Input.controllers[index] = None
    def processInputEvents():
        events=pygame.event.get()
        for event in events:
            if (event.type == locals.QUIT):
                game.quit()
            elif (event.type == locals.JOYDEVICEADDED):
                Input.addController(event)
            elif (event.type == locals.JOYDEVICEREMOVED):
                Input.removeController(event)
        for actionSetName, actionSet in Input.actionSets.items():
            actionSet.processInputs(events)
class Binding:
    def __init__(self,
                 address:list, #device, inputType, address (list, list, int)
                 type, #'button' or 'axis'
                 axisThreshold=.1, #deadzone for analog->analog, trigger threshold for analog->button
                 invert=False,#invert direction of output
                 debugPrint=False
                 ):
        self.address=address
        self.type = type
        self.value = 0
        self.action=None
        self.direction=1
        if (invert): self.direction=-1
        self.axisThreshold=axisThreshold
        self.debugPrint=debugPrint
    def trigger(self, newValue):
        if (self.debugPrint): print(newValue)
        newValue *= self.direction
        self.action.updateInput(self, newValue)
        self.value = newValue
    def poll(self, pressedKeys):
        if (self.address[0]=='keyboard'):
            pollValue=pressedKeys[self.address[2]]
        elif (self.address[0]) == 'controller':
            if (len(Input.controllers)==0): return
            """
            TODO: attach bindings to controllers as they connect and disconnect, to handle multiple
            controllers alternately, keep track of which controller is the active one (stored in Input),
            just poll that one and if it changes, update all the bindings. A button press, or
            a siginificant amount of axis movement can trigger an active controller change
            """
            if (self.address[1] == 'button'):
                pollValue=Input.controllers[0].get_button(self.address[2])
            elif (self.address[1] == 'axis'):
                pollValue=Input.controllers[0].get_axis(self.address[2])
            elif (self.address[1] == 'hat'):
                pollValue=Input.controllers[0].get_hat(int(self.address[2]/2))[self.address[2]%2]
            else: return #fallback, should never come up
        else: return
        if (pollValue != self.value): self.trigger(pollValue)
class Action:
    def __init__(self, name, bindings):
        #TODO: some way to extract hat values as separate buttons in one pass?
        #TODO: consider Vector2 support
        self.name=name
        self.triggerButton=ev.InputEvent()
        self.triggerAxis = ev.InputEvent()
        self.bindings=[]
        for binding in bindings:
            self.addBinding(binding)
        self.boolCount = 0
        self.boolValue=False
        self.floatValue = 0
    def addBinding(self, binding):
        self.bindings.append(binding)
        binding.action=self
    def updateInput(self, binding, newValue):
        discardBool=False #for float values that don't cross the trigger threshold
        floatVal = 0
        if (binding.type == 'button'):
            if (newValue):
                self.boolCount +=binding.direction
            else:
                self.boolCount -= binding.direction
            if (self.boolCount < 0): self.triggerAxis.invoke(-1)
            else: self.triggerAxis.invoke(min(1,self.boolCount))
        elif (binding.type == 'analog'):
            if (abs(newValue) > binding.axisThreshold):
                floatVal = (abs(newValue) - binding.axisThreshold) * (1-binding.axisThreshold)
                if (newValue < 0):
                    floatVal *= -1
                self.triggerAxis.invoke(floatVal)

                if (abs(binding.value) < binding.axisThreshold):
                    self.boolCount += 1
            elif (abs(newValue) < binding.axisThreshold and abs(binding.value) > binding.axisThreshold):
                self.boolCount -= 1
                self.triggerAxis.invoke(0)
            #if both the previous and new value are on the same side of the threshold:
            else: discardBool=True
        if (not discardBool):
            if (self.boolValue and not self.boolCount):
                #TODO: for axis to button, factor in direction
                #   (only trigger on positive input unless direction is negative)
                self.triggerButton.invoke(False)
                self.boolValue = False
            elif (self.boolCount and not self.boolValue):
                self.triggerButton.invoke(True)
                self.boolValue=True

class GameLoop:
    lastTime=None
    #TODO: make separate time file
    #   (use globals in the file, so it can be accessed like deltatime.safe and deltatime.raw)
    def __init__(game):
        game.frameCap=60
        global controllers
        game.idleTime=0
        game.togglePause=None
        GameLoop.current=game
        game.paused=True
        pygame.init()
        Input.init()
        Input.actionSets['gameplay'].actions['pause'].triggerButton.add(game.inputPause)
        Input.actionSets['menus'].actions['cancel'].triggerButton.add(game.inputUnpause)
        pygame.display.set_caption("C'est Une Sword")
        pygame.display.set_icon(pygame.image.load(os.path.join(os.getcwd(), 'Assets','Icon.png')))
        game.clock=pygame.time.Clock()
        
        game.window = Window()
        rm.Level('TestZone', 'StartRoom', 'Start')
        ent.PlayerSpawn(rm.Room.current, 'Start')
        #TODO: make a third action set that accepts start, A, X, space, enter, esc, lots of things
        #   then change the prompt to "press start to begin"
        game.window.screen.blit(game.window.font16.render('Press ESC to begin', False, (255,255,255)),
                                (30,190))
        game.window.flip()
        
    def updateDeltaTime(game):
        global deltaTime
        game.clock.tick(game.frameCap)
        deltaTime=game.clock.get_time()/1000*timeScale

    def quit(game):
        print('quitting')
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
                    cellIndex=actor.position//rm.Level.current.tileSize
                    remainder=actor.position - cellIndex * rm.Level.current.tileSize
                    remainder -= Vector2(rm.Level.current.tileSize/2,rm.Level.current.tileSize/2)
                    if (remainder.x > 0):remainder.x=1
                    else: remainder.x=-1
                    if (remainder.y > 0): remainder.y=1
                    else: remainder.y=-1
                    for x in range(0,2):
                        for y in range(0,2):
                            wall = rm.Room.current.getWall((int(cellIndex.x + remainder.x*x),
                                                            int(cellIndex.y + remainder.y*y)))
                            if(wall and wall.wall): wall.collide(actor)
        while len(testActors) > 1:
            actor=testActors.pop(0)
            for actor2 in testActors:
                actor.gameloopCollision(actor2)
        for actor in rm.Room.current.actors:
            actor.afterPhysics()
    
    def controllerAxisMotion(event):
        key = 'controllerAxis' + str(event.axis)
        if (key in GameLoop.mappingAnalog):
            GameLoop.inputEvents[GameLoop.mappingAnalog[key]].invoke(event.value)
    def controllerHatMotion(event):
        if ('controllerHatX' in GameLoop.mappingAnalog):
            GameLoop.inputEvents[GameLoop.mappingAnalog['controllerHatX']].invoke(event.value[0])
        if ('controllerHatY' in GameLoop.mappingAnalog):
            GameLoop.inputEvents[GameLoop.mappingAnalog['controllerHatY']].invoke(event.value[1])
    def pause(game):
        print('pause', deltaTime)
        Input.actionSets['menus'].setActive(True)
        Input.actionSets['gameplay'].setActive(False)
        game.paused= True
    def unpause(game):
        print('unpause', deltaTime)
        Input.actionSets['menus'].setActive(False)
        Input.actionSets['gameplay'].setActive(True)
        game.paused=False
    def inputPause(game, value):
        if (value): game.togglePause=True #game.pause()
    def inputUnpause(game,value):
        if (value): game.togglePause=True #game.unpause()
    def main(game):
        while True:
            game.updateDeltaTime()
            Input.processInputEvents()
            
            if (not game.paused):
                game.update()
                game.physics()
                rm.Room.current.draw()
            if (game.togglePause):
                if game.paused: game.unpause()
                else: game.pause()
                game.togglePause=False

class Window:
    current = None
    framerates=[]
    def __init__(self):
        pygame.font.init()
        self.width = 400
        self.height = 240
        self.mult=3
        self.screenSize=(self.width*self.mult, self.height*self.mult)
        self.debugFont=pygame.font.Font(pygame.font.match_font('arial'), 16*self.mult)
        self.font16=pygame.font.Font(pygame.font.match_font('arial'), 16)
        self.screen=pygame.Surface((self.width, self.height))
        self.actualScreen = pygame.display.set_mode((self.width*self.mult, self.height*self.mult))
        self.frameChart = pygame.Surface((600,300), pygame.SRCALPHA, 32)
        self.drawFramerate=False
        self.drawChart = False
        Input.actionSets['gameplay'].actions['debugDisplay'].triggerButton.add(self.toggleDrawFramerate)
        Input.actionSets['gameplay'].actions['debugChart'].triggerButton.add(self.toggleDrawFramechart)
        Window.current=self

        #effects (placeholder variables, mostly)
        #bump the screen over some amount of pixels
        self.bumpVec=None
        self.bumpTime=0
        self.shakeCount=0
        self.shakeTime=0
        #TODO: screenflash removed because epillepsy,
        #   but check if it's bad on a tiny not-backlithandheld later
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
            #TODO: start with an empty list, just overwrite when at length
            #   (average won't creep up from 0 at start, that way)
            #TODO: maybe just track a position and overwrite that index, instead of deleting and appending
            if (self.drawChart):
                #costs a few frames on its own
                self.frameChart.scroll(1,0)
                h = self.frameChart.get_height()
                self.frameChart.fill((0,0,0,0),pygame.Rect(0,0,1,h))
                self.frameChart.fill((0,255,0,128), pygame.Rect(0,h-f, 1, f))
                self.frameChart.fill((0,0,255,128), pygame.Rect(0,h-framerate+2, 1, 4))
                self.actualScreen.blit(self.frameChart, (0,0))
            self.actualScreen.blit(self.debugFont.render(str(int(framerate)), False, (0,255,0)),
                                   (5*self.mult,5*self.mult))
    def flip(self, doEffects=True):
        if (doEffects): self.doEffects()
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

