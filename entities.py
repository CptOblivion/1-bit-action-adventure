import os
import pygame
from pygame.math import Vector2
import sprite as s
import room as rm
import gameloop as g
import random
from math import atan2, degrees, ceil, floor

class Entity:
    #objects in scene
    def __init__(self, name, room, sprite, position=(100,100), origin=(0,0), parent=None):
        self.active=True
        self.children=[]
        self.name = name
        self._parent=None #TODO: why is this here?
        self.parent=None
        self.position=Vector2(position)
        if (type(sprite) == str):
            self.sprite=s.Sprite(sprite, (0,0,room.tileSize,room.tileSize))
        elif (type(sprite) == tuple or type(sprite)==list):
            self.sprite=s.Sprite(sprite[0],sprite[1])
        else:
            self.sprite=sprite
        self.origin=Vector2(origin)
        self.room = room
        if (self.room):
            self.room.entities.append(self)
        if (parent):
            self.setParent(parent)
        self.deathTimer=None
        self.visible=True
    @property
    def localPosition(self):
        return self._localPosition
    @localPosition.setter
    def localPosition(self, value):
        self._localPosition=value
        if (self.parent): self._globalPosition=value+self.parent._globalPosition
        else: self._globalPosition=value
        for child in self.children:
            child.localPosition=child._localPosition
    @property
    def position(self):
        return self._globalPosition
    @position.setter
    def position(self, value):
        if (self.parent): self.localPosition=value-self.parent._globalPosition
        else: self.localPosition=value
    def getCell(self, gridSize):
        #TODO: for optimization (get cell to cull collision tests, also to sort into rendering cells)
        pass
    def setActive(self, state):
        self.active=state
    def draw(self, **kwargs):
        if (self.active and self.visible and self.sprite):
            self.sprite.draw(self.position+self.origin, **kwargs)
    def update(self):
        if (self.deathTimer is not None):
            self.deathTimer -= g.deltaTime
            if (self.deathTimer <= 0):
                self.destroy()
        pass
    def setRoom(self, room):
        if (self.room):
            self.room.entities.remove(self)
        self.room=room
        room.entities.append(self)
        for child in self.children:
            child.setRoom(room)
    def destroy(self, time:float=None):
        if (time):
            self.deathTimer=time
            return
        self.room.entities.remove(self)
        if (self.parent): self.parent.children.remove(self)
        for child in self.children:
            child.destroy()
        del self
        #TODO: add self to garbage cleanup array in GameLoop,
        #   which will run actualDestroy right before the next frame starts
    def actualDestroy(self):
        del self
    def setParent(self, parent):
        #TODO: make parent into an @property so we can safely set it directly
        if (self.parent):
            self.parent.children.remove(self)
        parent.children.append(self)
        self.parent=self._parent = parent
        self.position=self._globalPosition
        
        #self.position -= parent.position
        #print('changed ', self.name, "'s parent to ", self.parent, '. New siblings (plus self): ', self.parent.children)

class Actor(Entity):
    collisionLayerNames={'default':1,'monsters':2,'player':3,'breakables':4,
                         'monsterAttack':5,'playerAttack':6,'iFrames':7,'unused':8}
    #reminder: the bits are in right-to-left order 
    #TODO: easier function to set masks (and make sure their complement is also set)
    collisionMask=[0,
                   0b01001111, #default
                   0b00101101, #monsters
                   0b00011111, #player
                   0b01111111, #breakables
                   0b00001100, #monsterAttack
                   0b00001010, #playerAttack
                   0b00001001, #iFrames
                   0b00000000] #unused
    class Collision:
        def __init__(self, collider, force, collidingObType):
            #collidingObTypes:'floor', 'wall', 'actor'
            self.collider = collider
            self.collidingObType=collidingObType
            self.force = force
    #has collision
    def __init__(self, name, room, collisionBounds, sprite, ghost=False,collisionLayer=1, health=1, **kwargs):
        self.collisionLayer=collisionLayer
        #weird fake initializations so the position and collisionBound setters won't complain later
        self._globalPosition=Vector2()
        self.collisionBounds=pygame.Rect(0,0,0,0)
        #TODO: add static tag (never check wall or floor collisions)
        #TODO: instead of bounds and origin, make it origin and size (w,h) and generate bounds from that
        #   (for easier definition down the line)
        #   (but of course include optional bounds input to override it)
        super().__init__(name, room, sprite, **kwargs)
        self.collisionBounds=collisionBounds
        if (self.room): self.room.actors.append(self)
        self.ghost=ghost #registers collisions, but doesn't receive physics
        self.static = False #isn't moved by forces
        self.skipDamage=True
        self.noCollideActors=False #skips collision tests with other actors
        self.noCollideWalls=False#skips collision test with walls
        self.noCollide=False #skips collision entirely
        self.velocity = pygame.Vector2(0,0)
        self.health=health
        self.damageITime=.5
        self.damageICounter=0
        self.collisionLayerLast=None
        self.isObstacle=False
        self.debugCollider=None
        self.damageFlicker=.03
        self.damageFlickerTimer=.02
        #TODO: map b key to toggle debug colliders
        #self.debugCollider = (0,255,0)
    @property
    def collisionBounds(self):
        return self._globalCollisionBounds
    @collisionBounds.setter
    def collisionBounds(self, value):
        self._localCollisionBounds = value
        self._globalCollisionBounds=value.move(self._globalPosition)
    @property
    def localPosition(self):
        #return super().position()
        return self._localPosition
    @localPosition.setter
    def localPosition(self, value):
        #TODO: there's probably a way to inherit the position setter/getter
        #   possibly by using property(fset=lambda self=self:self._setPosition(self)) on Entity
        #super().position(value)
        self._localPosition=value
        if (self.parent):
            self._globalPosition=value+self.parent._globalPosition
        else: self._globalPosition=value
        for child in self.children:
            child.localPosition=child._localPosition
        self.collisionBounds=self._localCollisionBounds
    def getBoundsAfterPhysics(self):
        """
        rect is quantized to pixels, so this function recreates the rect where it will be after velocity
            since applying the velocity to the stored global rect accumulates rounding errors   
        """
        return self._localCollisionBounds.move(self._globalPosition+self.velocity*g.deltaTime)
    def setCollisionLayer(self,layer):
        if (type(layer) == str): layer = Actor.collisionLayerNames[layer]
        if (not layer or layer == self.collisionLayer):
            return
        self.collisionLayerLast=self.collisionLayer
        self.collisionLayer=layer 
    def takeDamage(self, damage, fromActor, force):
        if (not self.skipDamage and self.damageICounter <=0):
            self.velocity = force
            self.health -= damage
            if self.health <= 0:
                self.onDeath()
                return True
            self.damageICounter=self.damageITime
            self.setCollisionLayer('iFrames')
            self.damageFlickerTimer=self.damageFlicker
    def returnFromDamage(self):
        self.setCollisionLayer(self.collisionLayerLast)
    def onDeath(self):
        pass
    def setRoom(self, room):
        if (self.room): self.room.actors.remove(self)
        super().setRoom(room)
        room.actors.append(self)
    def afterPhysics(self):
        if (self.active):
            self.position += self.velocity*g.deltaTime
    def drawDebug(self):
        if (self.debugCollider and not self.noCollide):
            tempBox = pygame.Surface((self.collisionBounds.width, self.collisionBounds.height))
            tempBox.fill(self.debugCollider)
            g.Window.current.screen.blit(tempBox, self.collisionBounds.topleft)
    def draw(self):
        super().draw()
        self.drawDebug()

    def destroy(self):
        super().destroy()
        self.room.actors.remove(self)
    def testCollision(self, actor):
        collisionMask=(Actor.collisionMask[actor.collisionLayer] >> (self.collisionLayer -1)) & 1
        if (actor.active and (not actor.noCollide) and collisionMask):
            #TODO: give Actor a worldBounds property, that gets updated any time position or velocity change
            #TODO: the original declaration will probably look like:
            #self.physicsBounds = property(getter_function, setter_function)
            #then use self._physicsBounds to store the bounds in local coordinates (and the getter returns that plus position)
            #we'll still have to do velocity in the physics checks manually but that's fine
            selfNewBounds=self.getBoundsAfterPhysics()
            actorNewBounds=actor.getBoundsAfterPhysics()
            if (selfNewBounds.colliderect(actorNewBounds)):
                force=Vector2(0,0)
                if (self.ghost == actor.ghost == False and (self.isObstacle or actor.isObstacle)):
                    force = Actor.__collideTest__(selfNewBounds, actor, True, skipTest=True)
                    #resolve physics
                    #store result in force on each sprite
                return(Actor.Collision(actor,force,'actor'))
        return None
    def gameloopCollision(self,actor):
        if (self.active):
            #make sure if one of them is an obstacle, it's the one performing the collision
            if (actor.isObstacle):
                bumper=actor
                bumpee=self
            else:
                bumper=self
                bumpee=actor
            collision = bumper.testCollision(bumpee)
            if (collision):
                bumpee.onCollide(Actor.Collision(bumper,collision.force,'actor'))
                bumper.onCollide(collision)
    def onCollide(self, collision):
        if (self.debugCollider):
            self.debugCollider = (255,0,0)
    def update(self):
        super().update()
        if (self.damageICounter>0):
            self.damageICounter-=g.deltaTime
            self.damageFlickerTimer -= g.deltaTime
            if (self.damageFlickerTimer <=0):
                self.damageFlickerTimer = self.damageFlicker
                self.visible = not self.visible
            if (self.damageICounter <=0):
                self.visible=True
                self.returnFromDamage()
        if (self.debugCollider): self.debugCollider=(0,255,0)
    def __collideTest__(ownBounds, actor, applyForce, skipTest=False):
        collisionBox=actor.getBoundsAfterPhysics()
        if (skipTest or ownBounds.colliderect(collisionBox)):
            normal=Vector2(collisionBox.center) - Vector2(ownBounds.center)
            sign=[1,1]
            if (normal.x < 0): sign[0] = -1
            if (normal.y < 0): sign[1] = -1
            force=Vector2(ownBounds.width/2*sign[0] + collisionBox.width/2*sign[0] - normal.x,
                            ownBounds.height/2*sign[1] + collisionBox.height/2*sign[1] - normal.y)

            #TODO: use vel to bias result
            #   (goal: so if actor hits a corner, the are "nudged" sideways and can continue moving
            #   instead of being stopped because two squares overlapped by 2 pixels
            #TODO: support for collision with diagonals (actually get the normal)
            if (abs(force.x) > abs(force.y)):
                #normal is along the y axis
                force.x=0
                if (applyForce and not actor.ghost):
                    #TODO: we're vibrating again for some reason
                    actor.position.y += force.y + actor.velocity.y * g.deltaTime
                    actor.velocity.y=0
            else:
                #normal is along the x axis
                force.y=0
                if (applyForce and not actor.ghost):
                    actor.position.x += force.x + actor.velocity.x * g.deltaTime
                    actor.velocity.x=0
            return force
        return None
        
class Character(Actor):
    def __init__(self, name, room, collisionBounds, sprite, **kwargs):
        self.facing=Vector2(0,1)
        self.totalForce = Vector2(0,0)
        reqStates=('idle_-1-1', 'idle_0-1', 'idle_1-1', 'idle_-10', 'idle_10', 'idle_-11', 'idle_01', 'idle_11',
                  'walk_-1-1', 'walk_0-1', 'walk_1-1', 'walk_-10', 'walk_10', 'walk_-11', 'walk_01', 'walk_11')
        for state in reqStates:
            if (not state in sprite.states):
                raise AttributeError('required state ' + state + ' not in sprite!')
        super().__init__(name, room, collisionBounds, sprite, **kwargs)
    def go(self, vec, faceMovement=True, overrideAnimation=False):
        self.velocity.x= vec.x
        self.velocity.y = vec.y
        if faceMovement:
            if (vec.magnitude() > 0):
                self.facing = vec.normalize()
        if (not overrideAnimation):
            if (vec.magnitude() == 0): anim='idle'
            else: anim='walk'
            anim += self.getSpriteDirection()
            self.sprite.setState(anim)
    def getSpriteDirection(self):
        facing=[0,0]
        nor=self.facing.normalize()

        #.707 is the 45 degree angles on a vector, .487 is eighth-wedges between those and orthogonal
        if (nor.x > .487): facing[0] = 1
        elif (nor.x < -.487): facing[0] = -1
        if (nor.y > .487): facing[1] = 1
        elif (nor.y < -.487): facing[1] = -1
        return '_'+str(facing[0])+str(facing[1])
    def generateFacingSprites(baseName,columns,w,h,t):
        if (type(columns)==int):
            columns=(columns,)
        outDict={}
        suffixes=('01','11','10','1-1','0-1','-1-1','-10','-11')
        for i in range(8):
            line=[]
            for col in columns:
                line.append((col*w,h*i,w,h,t))
            outDict[baseName+'_'+suffixes[i]]=tuple(line)
        return outDict

class PlayerSpawn(Entity):
    def __init__(self, room, door, **kwargs):
        super().__init__('playerIntro', room, ('Guy',(112,32,8,16,100)), origin = (-4,-14), **kwargs)
        self.targetPosition=self.room.doors[door].getPlayerStartPosition()
        self.offset=250
        self.introTime=.5
        self.moveSpeed = 1/self.introTime * self.offset
        self.position=self.targetPosition - Vector2(0,self.offset)
        self.startDelay=1.5
        self.visible=False
        g.Window.current.shake(12,1,0,.05)
    def update(self):
        super().update()
        if (self.startDelay > 0):
            self.startDelay -= g.deltaTime
            if (self.startDelay <= 0):
                #g.Window.current.bump(0,2,.12)
                self.visible=True
        else:
            self.offset -= self.moveSpeed * g.deltaTime
            if (self.offset >= 0):
                self.position = self.targetPosition - Vector2(0,self.offset)
            else:
                g.Window.current.shake(6,1,0,.05)
                player = Player(self.room, position=self.targetPosition)
                impactSprite=Entity('impactEffect',self.room,('Guy',(
                    (0,0,0,0,1),(112,48,16,8,.3),(112,56,16,8),(112,64,16,8))),
                                    position=self.position, origin=(-8,-4))
                impactSprite.destroy(time=.9)
                player.spawnDust((-300,0), count=3)
                player.spawnDust((300,0), count=3)
                self.destroy()
class Player(Character):
    #TODO: move to own file
    #controlled by player
    current=None
    def __init__(self, room, **kwargs):
        Player.current=self
        collisionBounds = pygame.Rect(-4,-3,8,6)
        #states: 'normal', 'attack', 'roll', 'backstep', 'damage', 'rollBounce'
        self.state='start'
        self.stateTimer = 1.5
        sheetName='Guy'
        playerSheet=pygame.image.load(os.path.join(os.getcwd(), 'Assets','Sprites',sheetName+'.png'))
        w=16
        h=16
        #TODO: in Character, make a function to generate this grid of values
        animDict = {**Character.generateFacingSprites('idle', 0, w,h,.25),
                    **Character.generateFacingSprites('walk',(1,0,2,0),w,h,.08),
                    **Character.generateFacingSprites('dodge',3,w,h,2),
                    **Character.generateFacingSprites('attack1',4,w,h,2),
                    **Character.generateFacingSprites('attack2',5,w,h,2),
                    #for some reason, the first frame (regardless of time) is skipped on spawn
                    'landing':((0,0,0,0,1),(112,0,16,16,1),(112,16,16,16,.3),(0,0,16,16,1)),
                    'dead':((112,0,16,16,.5),(112,80,16,16), 'noLoop')
                    }
        super().__init__('player', room, collisionBounds,
                       s.Sprite(sheetName, 'landing', states = animDict, sheet=playerSheet), origin=(-8,-15),
                       health=10, **kwargs)
        rm.Room.onRoomChange.add(self.roomChange)
        self.skipDamage=False
        self.damageStunTime=.15
        self.walkSpeed = 100
        self.dodgeSpeed = 350
        self.dodgeSteer = 15
        self.rollTime=.15
        self.backstepTime=.05
        self.dodgeCooldown=.1
        self.dodgeCooldownTimer=0
        self.attackStepSpeed = 40
        self.rollBounceTimeScale=5 #on rolling into an obstacle, stun for this factor of rmaining roll time
        self.rollBounceMinTime = .2 #roll bounce stun will always be at least this long
        self.rollBounceSpeed = 200 #start speed for roll bounce
        self.rollBounceFalloff = 25
        self.moveInputVec = Vector2(0,0)
        self.inputBufferAttack = .15
        self.inputBufferDodge = None
        self.inputBuffer=None
        self.stateTimer=1.5 #TODO: set the start state with this value via function, instead of using the default value
        self.nextState='normal'
        self.canMove=False
        self.attackString=0
        g.Input.actionSets['gameplay'].actions['moveX'].triggerAxis.add(self.inputMoveX)
        g.Input.actionSets['gameplay'].actions['moveY'].triggerAxis.add(self.inputMoveY)
        g.Input.actionSets['gameplay'].actions['dodge'].triggerButton.add(self.inputDodge)
        g.Input.actionSets['gameplay'].actions['attack'].triggerButton.add(self.inputAttack)
        g.Input.actionSets['gameplay'].actions['debugSpawn'].triggerButton.add(self.inputDebugSpawn)
        self.setCollisionLayer('player')
        bounds=pygame.Rect(-8,-8,16,16)
        center=(-8,-8)
        self.attackOb=DamageBox('playerAttack',self.room,bounds,
                                s.Sprite('Sword Slash2', 'Aortho',states={'Aortho':((0,0,16,16,.03),
                                                                                  (16,0,16,16,.02),
                                                                                  (32,0,16,16), 'noLoop'),
                                                                         'Adiag':((0,16,16,16,.03),
                                                                                  (16,16,16,16,.02),
                                                                                  (32,16,16,16), 'noLoop'),
                                                                         'Bortho':((0,32,16,16,.03),
                                                                                  (16,32,16,16,.02),
                                                                                  (32,32,16,16), 'noLoop'),
                                                                         'Bdiag':((0,48,16,16,.03),
                                                                                  (16,48,16,16,.02),
                                                                                  (32,48,16,16), 'noLoop')}),
                                1,.03,.1,.18,collisionLayer='playerAttack',
                              ghost=True, parent=self, origin=center)
    def draw(self):
        Character.draw(self)
    def inputDebugSpawn(self, state):
        if (state):
            Crate(self.room, self.position+self.facing*16)
    def onCollide(self, collision):
        super().onCollide(collision)
        if (self.state=='roll' and collision.force.magnitude()>0):
            #this bit is a bit jank, but we accumulate force over the course of the frame
            #   to check if we're in a corner (since each individual block push in a corner will be orthogonal,
            #   so diagonal rolling into a corner won't bounce
            self.totalForce += collision.force.normalize()
            if (self.totalForce.magnitude()>0):
                force=self.totalForce.normalize()
                if (self.dodgeVec.dot(force) < -.8):
                    self.setState('rollBounce')
                    g.Window.current.bump(int(force.x*-2),int(force.y*-2),.06)
                    #g.Window.current.shake(5,int(force.x*-1.5),int(force.y*-1.5), .03)
                    dustVec=Vector2(force.y,-force.x)
                    self.spawnDust(dustVec*200-force*15, count=2)
                    self.spawnDust(-dustVec*200-force*15, count=2)
                    self.facing = collision.force*-1
                    self.dodgeVec = force
                    self.stateTimer = max(self.stateTimer*self.rollBounceTimeScale,self.rollBounceMinTime)
                    #TODO: make 'stunned' state with 'hurt' sprites but no damage blink
                    self.sprite.setState('idle'+self.getSpriteDirection()) #placeholder sprite
    def inputMoveX(self, value):
        #TODO: this won't mix with button-based input movements at all
        self.moveInputVec.x = value
    def inputMoveY(self, value):
        self.moveInputVec.y = -value
    def inputAttack(self, buttonDown):
        if (buttonDown):
            self.queueState('attack')
    def takeDamage(self, damage, fromActor, force):
        if (super().takeDamage(damage, fromActor, force)):
            return True
        self.setState('damageStun')
        #TODO: actual hurt animation
    def returnFromDamage(self):
        super().returnFromDamage()
    def onDeath(self):
        print('you died to death')
        self.setState('dead')
        super().onDeath()
    def inputDodge(self, buttonDown):
        if (buttonDown):
            if (self.dodgeCooldownTimer <=0):
                if self.moveInputVec.magnitude() > 0:
                    self.queueState('roll')
                else:
                    self.queueState('backstep')

    def spawnDust(self, vel, count=5, randStr=1):
        vel = Vector2(vel)
        if not hasattr(self, 'dustSpriteSheet'):
            self.dustSpriteSheet=s.Sprite.loadSheet('Dust')
        #randStr=0
        rx,ry,ra = (.2*randStr,.7*randStr,.15*randStr)
        cross=Vector2(vel.y, -vel.x)
        spriteSize=8
        for i in range(count):
            rand=random.random()*2-1
            dust=Particle('dust',self.room,
                            pygame.Rect(-3,-1,6,2),
                            s.Sprite('Dust', ((0,0,spriteSize,spriteSize,.25+rand*ra),
                                              (spriteSize,0,spriteSize,spriteSize),
                                              (spriteSize*2,0,spriteSize,spriteSize)),
                                     sheet=self.dustSpriteSheet),
                            .75+rand*ra*3, position=self.position, origin=(-4,-6))
            dust.velocity=vel * (1-abs(rand)*ry) + cross*rand*rx
            dust.damping=8
    def update(self):
        super().update()
        updateDodgeDelay = True
        if (self.state=='normal'):
            vec = Vector2(self.moveInputVec)
            if (vec.magnitude() > 0):
                vec=vec.normalize() * self.walkSpeed
            self.go(vec)
        elif (self.state=='roll' or self.state == 'backstep'):
            updateDodgeDelay=False
            self.dodgeVec = (self.dodgeVec + (self.moveInputVec * self.dodgeSteer * g.deltaTime)).normalize()
            vec = self.dodgeVec * self.dodgeSpeed
            self.velocity=vec
            self.go(vec, faceMovement=False, overrideAnimation=True)
            self.advanceState()
        elif (self.state=='rollBounce'):
            updateDodgeDelay=False
            vec = self.dodgeVec * self.rollBounceSpeed
            self.dodgeVec *= 1-self.rollBounceFalloff*g.deltaTime
            self.go(vec, faceMovement=False, overrideAnimation=True)
            #self.velocity=vec
            self.advanceState()
        elif (self.state=='attack'):
            self.go(self.facing*self.attackStepSpeed, overrideAnimation=True)
            self.advanceState()
        elif (self.state=='start'):
            self.advanceState()
        elif (self.state=='damageStun'):
            self.advanceState()
        elif (self.state=='dead'):
            pass
        else:
            pass
        self.totalForce=Vector2()
        if (updateDodgeDelay):
            self.dodgeCooldownTimer -= g.deltaTime
    def roomChange(self, details):
        self.setRoom(details.newRoom)
        details.newDoor.playerStart()
    def advanceState(self, overrideNextState=None):
        self.stateTimer -= g.deltaTime
        if (self.stateTimer <=0):
            if (overrideNextState):
                self.setState(overrideNextState)
                return
            if (self.nextState):
                self.setState(self.nextState)
                return
            self.setState('normal') #fallback
            return
        if (self.inputBuffer is not None and self.stateTimer <= self.inputBuffer):
            self.canMove = True
            self.inputBuffer = None
    def queueState(self, state):
        if (self.canMove):
            if (self.state == 'normal'):
                self.setState(state)
                return
            self.nextState = state

    def setState(self, state):
        lastState=self.state
        if ((lastState == 'roll' or lastState == 'backstep') and self.damageICounter <=0):
            #after dodge, don't return from iFrames if we're still doing damage iFrames
            self.setCollisionLayer('player')
        self.state=state
        self.nextState='normal'
        if (state != 'attack'): self.attackString = 0
        if (state) == 'normal':
            self.canMove = True
            self.inputBuffer = None
        elif (state == 'attack'):
            self.canMove=False
            self.inputBuffer = self.inputBufferAttack
            self.state='attack'
            if (self.moveInputVec.magnitude()):
                #TODO: turn 45 degrees towards moveInputVec
                #   rather than allowing instant about-face between attacks
                self.facing=Vector2(self.moveInputVec)
            #TODO: quantize pos to 1 of 8 directions (to line up with facing sprites)
            pos = self.facing.normalize()*8 + Vector2(0,-8)
            if (self.attackString)==0:
                self.attackOb.attack(pos, self.facing, attackName='A')
                self.sprite.setState('attack1'+self.getSpriteDirection())
                self.attackString=1
                self.stateTimer=.3
            else:
                self.attackOb.attack(pos, self.facing, attackName='B')
                self.sprite.setState('attack2'+self.getSpriteDirection())
                self.attackString=0
                self.stateTimer=.3
        elif (state == 'roll'):
            if (self.moveInputVec.magnitude()>0):
                self.dodgeVec=Vector2(self.moveInputVec.normalize())
            else: 
                self.dodgeVec=Vector2(self.facing.normalize())
            self.stateTimer=self.rollTime
            self.sprite.setState('dodge'+self.getSpriteDirection())
            self.spawnDust(self.dodgeVec * 500 + Vector2(0,-50), count=3)
            self.canMove=False
            self.setCollisionLayer('iFrames')
            #TODO: combine all the common stuff in roll and backstep
            if (self.damageICounter<self.stateTimer):
                #make sure returning from damage iFrames won't prematurely end our dodge iFrames
                self.collisionLayerLast = None
            self.inputBuffer = self.inputBufferDodge
            self.dodgeCooldownTimer = self.dodgeCooldown
        elif (state == 'backstep'):
            self.dodgeVec=Vector2(self.facing.normalize() * -1)
            self.stateTimer=self.backstepTime
            self.sprite.setState('idle'+self.getSpriteDirection())
            self.spawnDust(self.dodgeVec*150,count=2)
            self.canMove=False
            self.inputBuffer = self.inputBufferDodge
            self.dodgeCooldownTimer = self.dodgeCooldown
            self.setCollisionLayer('iFrames')
            if (self.damageICounter<self.stateTimer):
                #make sure returning from damage iFrames won't prematurely end our dodge iFrames
                self.collisionLayerLast = None 
        elif (state == 'damageStun'):
            self.stateTimer = self.damageStunTime
            self.sprite.setState('idle'+self.getSpriteDirection()) #placeholder sprite
            self.attackOb.setActive(False)
        elif (state=='dead'):
            self.velocity = Vector2()
            self.sprite.setState('dead')
            self.noCollide=True
        else:
            #fallback
            self.canMove=False
            self.inputBuffer = None

class DamageBox(Actor):
    def __init__(self, name, room, collisionBounds, sprite, damage,
                 windupTime,damageTime,remainTime, collisionLayer='monsterAttack', **kwargs):
        super().__init__(name, room, collisionBounds,sprite, **kwargs)
        self.ghost=True
        self.noCollideWalls = True
        self.setActive(False)
        self.skipDamage=True
        self.damage=damage
        self.setCollisionLayer(collisionLayer)
        self.windupTime=windupTime
        self.damageTime=damageTime
        self.remainTime=remainTime
        self.state='notYetActivated'
        self.surface=pygame.Surface((self.sprite.currentSprite.width,self.sprite.currentSprite.height),
                                   flags=pygame.SRCALPHA)
        #self.debugCollider = (0,255,0)
    def attack(self, position, facingVec, attackName=''):
        self.setActive(True)
        self.localPosition=position
        self.rotation=degrees(atan2(facingVec[0],facingVec[1]))+180
        self.rotation=int(self.rotation/45)
        self.facingVec=facingVec
        if (self.rotation%2): self.sprite.setState(attackName+'diag', restart=True)
        else: self.sprite.setState(attackName+'ortho', restart=True)
        self.rotation=int(self.rotation/2)*90
        if (self.windupTime):
            self.timer=self.windupTime
            self.noCollide=True
            self.state='windup'
        else:
            self.tier=self.damageTime
            self.noCollide=False
            self.state='damage'
        #we'll draw rotated, but collision uses orthogonal squares
    def update(self):
        super().update()
        self.timer -= g.deltaTime
        if (self.timer <= 0):
            if (self.state=='windup'):
                self.noCollide=False
                self.timer = self.damageTime
                self.state='damage'
            elif (self.state=='damage'):
                self.noCollide=True
                self.timer=self.remainTime
                self.state='remain'
            else:
                self.setActive(False)
    def draw(self):
        #TODO: only need to do fill, blit, rotate when sprite image updates (IE on state or frame change)
        self.surface.fill((255,255,255,0))
        self.surface.blit(self.sprite.sheet, (0,0), area=self.sprite.currentSprite)
        self.sprite.draw(None)
        #TODO: build rotation library on sprite creation?
        g.Window.current.screen.blit(pygame.transform.rotate(self.surface, self.rotation),
                                     self.position+self.origin)
        self.drawDebug()
    def onCollide(self, collision):
        super().onCollide(collision)
        col=collision.collider
        if hasattr(col,'takeDamage'):
            vec=self.facingVec
            col.takeDamage(1,self,vec.normalize()*50)

class Particle(Actor):
    def __init__(self, name, room, collisionBounds, sprite, life, **kwargs):
        super().__init__(name, room, collisionBounds, sprite, **kwargs)
        self.life=life
        self.damping = 0
        self.noCollideActors=False
        self.room.onRoomLeave.add(self.roomLeave)
        #TODO: some sort of flag (in Entity, probably) to destroy on room change
        #   maybe just subscribe to on room change (don't forget to unsubscribe on destroy)
    def update(self):
        super().update()
        self.velocity *= 1-self.damping*g.deltaTime
        if (self.life <= 0):
            self.destroy()
        self.life -= g.deltaTime
    def draw(self):
        super().draw()
    def roomLeave(self, room):
        self.destroy()
    def destroy(self):
        self.room.onRoomLeave.remove(self.roomLeave)
        super().destroy()
class EffectTrigger(Actor):
    #TODO: make Trigger base class
    def quickAdd(name, position, effect, effectValues):
        trigger = EffectTrigger(name, rm.Room.current,
                                pygame.Rect(0, 0, rm.Level.tileSize, rm.Level.tileSize),
                                None, position=position)
        trigger.effect=effect
        trigger.effectValues = effectValues
        return trigger
    def __init__(self, name, level, collisionBounds,sprite,**kwargs):
        self.effect=None
        self.effectValues=None
        self.ghost=True
    def onTrigger(self):
        if (self.effect == 'bump'):
            #TODO: test if this actually works
            g.Window.current.bump(*self.effectValues)
        elif (self.effect == 'shake'):
            g.Window.current.shake(*self.effectValues)
        self.destroy()

    def onCollide(self, collision):
        super().onCollide(collision)
        if (collision.collider == Player.current):
            self.onTrigger()
class Crate(Actor):
    def __init__(self, room, position):
        super().__init__('crate',room, pygame.Rect(-8,-13,16,16), ('Crate',(0,0,16,16)),
                         position=position, origin=(-8,-13))
        self.skipDamage=False
        self.setCollisionLayer('breakables')
        self.health=3
        self.isObstacle=True
    def takeDamage(self, damage, fromActor, force):
        super().takeDamage(damage, fromActor,force)
        self.sprite.setState('hurt')
    def onDeath(self):
        super().onDeath()
        self.destroy()
class NPC(Character):
    def __init__(self, name, room, collisionBounds, sprite, behaviorIdle, behaviorAwake, behaviorAction,
                 leaveRoomFunc = 'reset', **kwargs):
        super().__init__(name, room, collisionBounds, sprite, **kwargs)
        self.startPosition=Vector2(self.position)
        self.startHealth=self.health
        #idle behaviors: patrol, wander, None
        #awake behaviors: follow, guard, None
        #behaviors when in range: charge, lurk (keep distance and occasionally attack), scatter, None
        self.behaviorIdle=behaviorIdle
        self.behaviorAwake=behaviorAwake
        self.behaviorAction=behaviorAction
        self.AIState='sleep'
        self.wakeupTime = 0
        self.wakeupTimer=0
        self.wakeupRange=100
        self.wakeupRangeBuffer=20
        self.actionRange=16
        self.actionRangeBuffer=16
        self.collisionLayerAlive=self.collisionLayer
        if (leaveRoomFunc == 'reset'): self.onRoomChange=self.reset
        elif (leaveRoomFunc == 'sleep'): self.onRoomChange=self.sleep
        elif (leaveRoomFunc == 'respawn'): self.onRoomChange=self.respawn
        self.room.onRoomLeave.add(self.onRoomChange)

        self.moveSpeed=20

    def reset(self, roomChangeDetails):
        if (self.active and self.AIState!='dead'):
            self.position=Vector2(self.startPosition)
            self.health=self.startHealth
            self.setAIState('sleep')
            self.sprite.setState('default')
            self.facing = Vector2(0,1)
            #self.sprite.resetState()
    def respawn(self, roomChangeDetails):
        self.active=True
        self.setAIState('alive') #placeholder state to make sure we're not set as dead
        self.reset(roomChangeDetails)
        self.setCollisionLayer(self.collisionLayerAlive)
        self.noCollide=False
    def sleep(self, roomChangeDetails):
        self.setAIState('sleep')
        self.sprite.setState('default')
    def destroy(self):
        self.room.onRoomLeave.remove(self.onRoomChange)
        super().destroy()
    def setAIState(self, state):
        self.AIState=state
        if (state == 'sleep'):

            self.velocity=Vector2()
            self.sprite.setState('sleep')
        elif (state == 'wakeup'):
            self.wakeupTimer = self.wakeupTime
            self.sprite.setState('wakeup')
    def getVectTo(self, actor):
        return (actor.position - self.position)
    def onDeath(self):
        super().onDeath()
        self.velocity=Vector2()
        self.noCollide=True
        self.setAIState('dead')
        self.sprite.setState('dead')
    def onCollide(self, collision):
        super().onCollide(collision)
        if (self.AIState != 'hurt' and collision.collider == Player.current):
            vec = collision.collider.position - self.position
            collision.collider.takeDamage(1,self,vec.normalize() * 50)
    def returnFromDamage(self):
        super().returnFromDamage()
        self.setAIState('awake')
    def takeDamage(self, damage, fromActor, force):
        if (super().takeDamage(damage, fromActor, force)):
            return True
        self.setAIState('hurt')
    def update(self):
        super().update()
        if (not Player.current): pass
        if (self.AIState != 'dead'):
            if (Player.current.state=='dead'):
                if (self.AIState != 'sleep'):
                    print(self.AIState)
                    self.setAIState('sleep')
                return
            vec = self.getVectTo(Player.current)
            dist=vec.magnitude()
        if (self.AIState=='sleep'):
            if (dist < self.wakeupRange):
                self.setAIState('wakeup')
                return
            #self.go(Vector2())
        elif (self.AIState == 'wakeup'):
            self.wakeupTimer -= g.deltaTime
            if (self.wakeupTimer <= 0):
                self.setAIState('awake')
        elif (self.AIState == 'awake'):
            if (dist <=self.actionRange):
                self.setAIState('act')
                return
            if (dist > self.wakeupRange + self.wakeupRangeBuffer):
                self.setAIState('sleep')
                return
            if (self.behaviorAwake == 'follow'):
                self.go(vec.normalize()*self.moveSpeed)
                return
            self.go(Vector2())
        elif (self.AIState == 'act'):
            if (dist > self.wakeupRange + self.wakeupRangeBuffer):
                self.setAIState('sleep')
                return
            if (dist > self.actionRange + self.actionRangeBuffer):
                self.setAIState('awake')
                return
            self.go(Vector2())
        else:
            #fallback
            pass

def Spawn(entityName, room, position):
    #TODO: placeholder until I have an actual spawning system
    if (entityName=='Slime'):
        #TODO: move default sprite generation into init for NPC (with some settings)
        w=16
        h=16
        animDict={**Character.generateFacingSprites('idle', 0, w,h,.25),
                  **Character.generateFacingSprites('walk', 0, w,h,.25),
                  'sleep':((0,64,16,16,.3),(48,16,16,16),(48,0,16,16),'noLoop'),
                  'wakeup':((48,16,16,16,.3),(0,64,16,16),(0,0,16,16),'noLoop'),
                  'default':(48,0,16,16),
                  'dead':((48,32,16,16,.5),(48,48,16,16),'noLoop')}

        slime=NPC('slime', room, pygame.Rect(-8,-12,16,16), s.Sprite('Slime', 'default', states=animDict),
                 None, 'follow', None, leaveRoomFunc='respawn', position=position, origin=(-8,-12),
                 health=5, collisionLayer=2)
        slime.skipDamage=False
        slime.damageITime = .3
        slime.actionRange=0
        slime.wakeupTime=1
    else:
        print('no entity', entityName,'!')
