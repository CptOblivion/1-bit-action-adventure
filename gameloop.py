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

#TODO: move to own file
class Input:
    def init():
        actions = [
            'moveX',
            'moveY',
            'moveUp',
            'moveDown',
            'moveLeft',
            'moveRight',
            'dodge',
            'attack',
            'debugDisplay',
            'debugChart',
            'debugSpawn']
        Input.bindings={}
        for key in actions:
            Input.bindings[key] = Binding(key)
        Input.inputs={
            'keyboard':{
                'keys':{
                    pygame.locals.K_w:BindingInput('button','moveY'),
                    pygame.locals.K_s:BindingInput('button','moveY', invert=True),
                    pygame.locals.K_d:BindingInput('button','moveX'),
                    pygame.locals.K_a:BindingInput('button','moveX', invert=True),
                    pygame.locals.K_UP:BindingInput('button','moveY'),
                    pygame.locals.K_DOWN:BindingInput('button','moveY', invert=True),
                    pygame.locals.K_RIGHT:BindingInput('button','moveX'),
                    pygame.locals.K_LEFT:BindingInput('button','moveX', invert=True),
                    pygame.locals.K_x:BindingInput('button','dodge'),
                    pygame.locals.K_LSHIFT:BindingInput('button','dodge'),
                    pygame.locals.K_z:BindingInput('button','attack'),
                    pygame.locals.K_SPACE:BindingInput('button','attack'),
                    pygame.locals.K_f:BindingInput('button','debugDisplay'),
                    pygame.locals.K_c:BindingInput('button','debugChart'),
                    pygame.locals.K_v:BindingInput('button','debugSpawn')}},
            'controller':{ #TODO: support multiple controllers
                'buttons':{
                    0:BindingInput('button','dodge'),
                    2:BindingInput('button','attack')
                    },
                'axes':{
                    0:BindingInput('analog', 'moveX'),
                    1:BindingInput('analog', 'moveY', invert=True)
                    },
                'hats':{
                    0:(BindingInput('analog','moveX'),
                       BindingInput('analog','moveY'))
                    }}
            }
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
    def processInputEvents():
        for event in pygame.event.get():
            if (event.type == locals.QUIT):
                game.quit()
            elif (event.type== locals.KEYDOWN):
                if (event.key == locals.K_ESCAPE):
                    #TODO: esc shouldn't be rebindable, but it should bring up the menu
                    #also, in the menus arrows and enter should be locked in to what they do
                    game.quit()
                elif (event.key in Input.inputs['keyboard']['keys']):
                    Input.inputs['keyboard']['keys'][event.key].trigger(True)
            elif (event.type== locals.KEYUP):
                if (event.key in Input.inputs['keyboard']['keys']):
                    Input.inputs['keyboard']['keys'][event.key].trigger(False)
            elif (event.type == locals.JOYBUTTONDOWN):
                if (event.button in Input.inputs['controller']['buttons']):
                    Input.inputs['controller']['buttons'][event.button].trigger(True)
            elif (event.type == locals.JOYBUTTONUP):
                if (event.button in Input.inputs['controller']['buttons']):
                    Input.inputs['controller']['buttons'][event.button].trigger(False)
            elif (event.type == locals.JOYHATMOTION):
                if (event.hat in Input.inputs['controller']['hats']):
                    hat=Input.inputs['controller']['hats'][event.hat]
                    if (hat[0]): hat[0].trigger(event.value[0])
                    if (hat[1]): hat[1].trigger(event.value[1])
            elif (event.type ==  locals.JOYAXISMOTION):
                if (event.axis in Input.inputs['controller']['axes']):
                    Input.inputs['controller']['axes'][event.axis].trigger(event.value)
            elif (event.type == locals.JOYDEVICEADDED):
                Input.addController(event)
            elif (event.type == locals.JOYDEVICEREMOVED):
                Input.removeController(event)
class BindingInput:
    def __init__(self,
                 type,#'button' or 'axis'
                 binding, #actual binding, probably int (controller button or axis, keyboard constant, etc)
                 axisThreshold=.1, #deadzone for analog->analog, trigger threshold for analog->button
                 invert=False,#invert direction of output
                 debugPrint=False
                 ):
        
        #TODO: should we store the address (EG keyboard.key) in the binding? any use here?
        self.type = type
        self.value = 0
        self.binding=Input.bindings[binding]
        self.direction=1
        if (invert): self.direction=-1
        self.axisThreshold=axisThreshold
        self.binding.inputs.append(self)
        self.debugPrint=debugPrint
    def trigger(self, newValue):
        if (self.debugPrint): print(newValue)
        newValue *= self.direction
        self.binding.updateInput(self, newValue)
        self.value = newValue
class Binding:
    def __init__(self, name):
        #TODO: some way to extract hat values as separate buttons in one pass?
        #TODO: consider Vector2 support
        self.triggerButton=ev.InputEvent()
        self.triggerAxis = ev.InputEvent()
        self.inputs=[] #storing the inputs for later, to display in the config UI when that exists
        self.boolCount = 0
        self.boolValue=False
        self.floatValue = 0
    def updateInput(self, input, newValue):
        discardBool=False #for float values that don't cross the trigger threshold
        floatVal = 0
        if (input.type == 'button'):
            if (newValue):
                self.boolCount +=input.direction
            else:
                self.boolCount -= input.direction
            if (self.boolCount < 0): self.triggerAxis.invoke(-1)
            else: self.triggerAxis.invoke(min(1,self.boolCount))
        elif (input.type == 'analog'):
            if (abs(newValue) > input.axisThreshold):
                #TODO: forgot to check if axes are 0 to 1 or -1 to 1
                floatVal = (abs(newValue) - input.axisThreshold) * (1-input.axisThreshold)
                if (newValue < 0):
                    floatVal *= -1
                self.triggerAxis.invoke(floatVal)

                if (abs(input.value) < input.axisThreshold):
                    self.boolCount += 1
            elif (abs(newValue) < input.axisThreshold and abs(input.value) > input.axisThreshold):
                self.boolCount -= 1
                self.triggerAxis.invoke(0)
            #if both the previous and new value are on the same side of the threshold:
            else: discardBool=True
        if (not discardBool):
            if (self.boolValue and not self.boolCount):
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
        game.running = True
        pygame.init()
        Input.init()
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
    def main(game):
        while game.running:
            GameLoop.updateDeltaTime()
            Input.processInputEvents()

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

