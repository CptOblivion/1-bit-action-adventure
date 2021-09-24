import os
from pygame import locals
import pygame
from pygame.math import Vector2
import datetime
import room as rm
import entities as ent
import event as ev

#TODO: use pygame.time instead of doing our own deltatime
deltaTime=100

class ActionSet:
    def __init__(self, name, actions:list):
        self.name=name
        self.active=True
        self.actions=actions
        self.bindMap={}
        for action in self.bindings:
            for binding in action.bindings:
                self.bindMap[binding.address[0]][binding.address[1]][binding.address[2]] = binding
    def setActive(self,state):
        if (self.active == state): return
        for action in self.actions:
            for binding in action.inputs:
                #recheck the state of the inputs when the action set is toggled on or off
                binding.poll()



#TODO: move to own file
class Input:
    def init():

        actions = [
            'pause',
            'moveX',
            'moveY',
            'dodge',
            'attack',
            'debugDisplay',
            'debugChart',
            'debugSpawn']
        Input.bindings={}
        for key in actions:
            Input.bindings[key] = Action(key)
        Input.actionSets={
            'menus':ActionSet('menus',{
                'cancel':Action('cancel',[
                    Binding(['keyboard','key',locals.K_ESCAPE],'button')])
                }),
            'gameplay':ActionSet('gameplay',{
                'pause':Action('pause',[
                    Binding(['keyboard','key',locals.K_ESCAPE],'button')]),
                'moveX':Action('moveX',[
                    Binding(['keyboard','key',locals.K_d],'button'),
                    Binding(['keyboard','key',locals.K_a],'button', invert=True),
                    Binding(['keyboard','key',locals.K_RIGHT],'button'),
                    Binding(['keyboard','key',locals.K_LEFT],'button', invert=True),
                    Binding(['controller','axis',0],'analog'),

                    ]),
                'moveY':Action('moveY',[
                    Binding(['keyboard','key',locals.K_s],'button'),
                    Binding(['keyboard','key',locals.K_w],'button', invert=True),
                    Binding(['keyboard','key',locals.K_DOWN],'button'),
                    Binding(['keyboard','key',locals.K_UP],'button', invert=True),
                    Binding(['controller','axis',1],'analog', invert=True)]),
                'dodge':Action('dodge',[]),
                'attack':Action('attack',[]),
                'debugDisplay':Action('debugDisplay',[]),
                'debugChart':Action('debugChart',[]),
                'debugSpawn':Action('debugSpawn',[])
                })}
        Input.inputs={
            'gameplay':{
                'keyboard':{
                    'keys':{
                        pygame.locals.K_ESCAPE:Binding('button','pause'),
                        pygame.locals.K_w:Binding('button','moveY'),
                        pygame.locals.K_s:Binding('button','moveY', invert=True),
                        pygame.locals.K_d:Binding('button','moveX'),
                        pygame.locals.K_a:Binding('button','moveX', invert=True),
                        pygame.locals.K_UP:Binding('button','moveY'),
                        pygame.locals.K_DOWN:Binding('button','moveY', invert=True),
                        pygame.locals.K_RIGHT:Binding('button','moveX'),
                        pygame.locals.K_LEFT:Binding('button','moveX', invert=True),
                        pygame.locals.K_x:Binding('button','dodge'),
                        pygame.locals.K_LSHIFT:Binding('button','dodge'),
                        pygame.locals.K_z:Binding('button','attack'),
                        pygame.locals.K_SPACE:Binding('button','attack'),
                        pygame.locals.K_f:Binding('button','debugDisplay'),
                        pygame.locals.K_c:Binding('button','debugChart'),
                        pygame.locals.K_v:Binding('button','debugSpawn')}},
                'controller':{ #TODO: support multiple controllers
                    'buttons':{
                        0:Binding('button','dodge'),
                        2:Binding('button','attack')
                        },
                    'axes':{
                        0:Binding('analog', 'moveX'),
                        1:Binding('analog', 'moveY', invert=True)
                        },
                    'hats':{
                        0:(Binding('analog','moveX'),
                           Binding('analog','moveY'))
                        }}
                },
            'menus':{
                'keyboard':{
                    'keys':{
                        pygame.locals.K_ESCAPE:Binding('button','pause')
                        }},
            'controller':{
                'buttons':{
                    },
                'axes':{
                    },
                'hats':{
                    }}
                }}
        pygame.joystick.init()
        Input.controllers=[]
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
    def processInputEvents(inputSet):
        for event in pygame.event.get():
            if (event.type == locals.QUIT):
                game.quit()
            elif (event.type== locals.KEYDOWN):
                if (event.key in Input.inputs[inputSet]['keyboard']['keys']):
                    Input.inputs[inputSet]['keyboard']['keys'][event.key].trigger(True)
            elif (event.type== locals.KEYUP):
                if (event.key in Input.inputs[inputSet]['keyboard']['keys']):
                    Input.inputs[inputSet]['keyboard']['keys'][event.key].trigger(False)
            elif (event.type == locals.JOYBUTTONDOWN):
                if (event.button in Input.inputs[inputSet]['controller']['buttons']):
                    Input.inputs[inputSet]['controller']['buttons'][event.button].trigger(True)
            elif (event.type == locals.JOYBUTTONUP):
                if (event.button in Input.inputs[inputSet]['controller']['buttons']):
                    Input.inputs[inputSet]['controller']['buttons'][event.button].trigger(False)
            elif (event.type == locals.JOYHATMOTION):
                #TODO: treat each hat as 2 axes (list them as such,
                #   eg hats[0] is hat==0 input[0], hats[1] is hat==0 input[1]
                #event.hat index is int(hatIndex/2), event.inputs index is hatIndex%2
                if (event.hat in Input.inputs[inputSet]['controller']['hats']):
                    hat=Input.inputs[inputSet]['controller']['hats'][event.hat]
                    if (hat[0]): hat[0].trigger(event.value[0])
                    if (hat[1]): hat[1].trigger(event.value[1])
            elif (event.type ==  locals.JOYAXISMOTION):
                if (event.axis in Input.inputs['controller']['axes']):
                    Input.inputs[inputSet]['controller']['axes'][event.axis].trigger(event.value)
            elif (event.type == locals.JOYDEVICEADDED):
                Input.addController(event)
            elif (event.type == locals.JOYDEVICEREMOVED):
                Input.removeController(event)
class Binding:
    def __init__(self,
                 address:list[str,str,int], #device, inputType, address (list, list, int)
                 type,#'button' or 'axis'
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
    def poll(self):
        #TODO: check the current state of the bound input,
        #   self.trigger(value) if it's different from self.value
        pass
class Action:
    def __init__(self, name, bindings):
        #TODO: some way to extract hat values as separate buttons in one pass?
        #TODO: consider Vector2 support
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
                #TODO: forgot to check if axes are 0 to 1 or -1 to 1
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
    rooms={}
    #TODO: make Level class to wrap a bunch of rooms together
    #gameloop can store  a list of levels, move this rooms dict into Level
    def __init__(game):
        global controllers
        GameLoop.current=game
        game.paused=True
        pygame.init()
        Input.init()
        Input.bindings['pause'].triggerButton.add(game.inputPause)
        pygame.display.set_caption("C'est Une Sword")
        pygame.display.set_icon(pygame.image.load(os.path.join(os.getcwd(), 'Assets','Icon.png')))
        
        game.window = Window()
        rm.Level('TestZone', 'StartRoom', 'Start')
        ent.PlayerSpawn(rm.Room.current, 'Start')
        GameLoop.lastTime = datetime.datetime.now()
        
    def updateDeltaTime():
        global deltaTime
        time=datetime.datetime.now()
        deltaTime=(time-GameLoop.lastTime).microseconds / 1000000
        GameLoop.lastTime=time


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
        game.paused= not game.paused
    def inputPause(game, value):
        if (value): game.pause()
    def main(game):
        while True:
            GameLoop.updateDeltaTime()
            if (game.paused): Input.processInputEvents('menus')
            else: Input.processInputEvents('gameplay')
            
            if (not game.paused):
                game.update()
                game.physics()
                rm.Room.current.draw()

class Window:
    current = None
    framerates=[]
    def __init__(self):
        pygame.font.init()
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
        Input.bindings['debugDisplay'].triggerButton.add(self.toggleDrawFramerate)
        Input.bindings['debugChart'].triggerButton.add(self.toggleDrawFramechart)
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
            self.actualScreen.blit(self.font.render(str(int(framerate)), False, (0,255,0)),
                                   (5*self.mult,5*self.mult))
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

