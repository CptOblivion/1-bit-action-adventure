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
        self.children=[]
        self.name = name
        self._parent=None
        self.position=Vector2(position)
        if (type(sprite) == str):
            self.sprite=s.Sprite(sprite, (0,0,room.tileSize,room.tileSize))
        elif (type(sprite) == tuple or type(sprite)==list):
            self.sprite=s.Sprite(sprite[0],sprite[1])
        else:
            self.sprite=sprite
        self.active=True
        self.origin=Vector2(origin)
        self.room = room
        if (self.room):
            self.room.entities.append(self)
        self.parent=None
        if (parent):
            self.setParent(parent)
        self.deathTimer=None
    @property
    def position(self):
        return self._globalPosition
    @position.setter
    def position(self, value):
        #TODO: rework so set is also globalPosition, make new localPosition variable for setting local
        #(since += and whatnot doesn't work with parent/child this way)
        self._localPosition=value
        if (self._parent): self._globalPosition=value+self.parent._globalPosition
        else: self._globalPosition=value
        for child in self.children:
            child.position=child._localPosition #trigger the child to update its own position
            #child._globalPosition=self._globalPosition + child._localPosition
    def getCell(self, gridSize):
        #TODO: for optimization (get cell to cull collision tests, also to sort into rendering cells)
        pass
    def setActive(self, state):
        self.active=state
    def draw(self, **kwargs):
        if (self.active and self.sprite):
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
        
        print('setting ',self.name,'parent to ', parent.name,'. childlist:',parent.children)
        #self.position -= parent.position
        #print('changed ', self.name, "'s parent to ", self.parent, '. New siblings (plus self): ', self.parent.children)

class Actor(Entity):
    collisionLayerNames={'default':1,'monsters':2,'player':3,'breakables':4,
                         'monsterAttack':5,'playerAttack':6,'hitStun':7,'dodgeroll':8}
    #reminder: the bits are in right-to-left order 
    #TODO: easier function to set masks (and make sure their complement is also set)
    collisionMask=[0,
                   0b11001111, #default
                   0b01101101, #monsters
                   0b01011111, #player
                   0b11111111, #breakables
                   0b00001100, #monsterAttack
                   0b00001010, #playerAttack
                   0b10001111, #hitstun
                   0b01001001] #dodgeroll
    class Collision:
        def __init__(self, collider, force, collidingObType):
            #collidingObTypes:'floor', 'wall', 'actor'
            self.collider = collider
            self.collidingObType=collidingObType
            self.force = force
    #has collision
    def __init__(self, name, room, collisionBounds, sprite, ghost=False, **kwargs):
        self.collisionLayer=1
        #weird fake initializations so the position and collisionBound setters won't complain later
        self._globalPosition=Vector2()
        self.collisionBounds=pygame.Rect(0,0,0,0)
        #TODO: add static tag (never check wall or floor collisions)
        #TODO: add noCollideActors tag to only check walls for collision
        #TODO: instead of bounds and origin, make it origin and size (w,h) and generate bounds from that
        #   (for easier definition down the line)
        #   (but of course include optional bounds input to override it)
        super().__init__(name, room, sprite, **kwargs)
        self.collisionBounds=collisionBounds
        if (self.room): self.room.actors.append(self)
        self.ghost=ghost #registers collisions, but doesn't receive physics
        self.skipDamage=True
        self.noCollideActors=False #skips collision tests with other actors
        self.noCollideWalls=False#skips collision test with walls
        self.noCollide=False #skips collision entirely
        self.velocity = pygame.Vector2(0,0)
        self.health=1
        self.damageITime=.5
        self.damageICounter=0
        self.collisionLayerLast=None
        self.isObstacle=False
        self.debugCollider=None
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
    def position(self):
        #return super().position()
        return self._globalPosition
    @position.setter
    def position(self, value):
        #TODO: there's probably a way to inherit the position setter/getter
        #   possibly by using property(fset=lambda self=self:self._setPosition(self)) on Entity
        #super().position(value)
        self._localPosition=value
        if (self._parent): self._globalPosition=value+self.parent._globalPosition
        else: self._globalPosition=value
        for child in self.children:
            child.position=child._localPosition #trigger the child to update its own position
        self.collisionBounds=self._localCollisionBounds
    def getBoundsAfterPhysics(self):
        """
        rect is quantized to pixels, so this function recreates the rect where it will be after velocity
            since applying the velocity to the stored global rect accumulates rounding errors   
        """
        return self._localCollisionBounds.move(self._globalPosition+self.velocity*g.deltaTime)
    def setCollisionLayer(self,layer):
        self.collisionLayerLast=self.collisionLayer
        if (type(layer)==int): self.collisionLayer=layer
        else: self.collisionLayer = Actor.collisionLayerNames[layer]
    def takeDamage(self, damage, fromActor):
        if (not self.skipDamage and self.damageICounter <=0):
            self.damageICounter=self.damageITime
            self.health -= damage
            if self.health <= 0: self.onDeath()
            self.damageICounter=self.damageITime
            self.setCollisionLayer('hitStun')
    def onDeath(self):
        pass
    def setRoom(self, room):
        if (self.room): self.room.actors.remove(self)
        super().setRoom(room)
        room.actors.append(self)
    def afterPhysics(self):
        if (self.active):
            self.move(self.velocity*g.deltaTime)
    def move(self, vect):
        #probably doesn't need to be a separate function, really
        if (self.parent):
            newPos=self._localPosition+vect
        else:
            newPos=self.position+vect
        self.position = newPos
    def setPosition(self, pos):
        self.position=pos
    def draw(self):
        super().draw()
        if (self.debugCollider):
            tempBox = pygame.Surface((self.collisionBounds.width, self.collisionBounds.height))
            tempBox.fill(self.debugCollider)
            g.Window.current.screen.blit(tempBox, self.collisionBounds.topleft)

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
            #we'll still have to do velocity in the physics checks manually but that's finb
            #selfNewBounds=self.collisionBounds.move(self.velocity*g.deltaTime)
            #actorNewBounds=actor.collisionBounds.move(actor.velocity*g.deltaTime)
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
    def returnFromDamage(self):
        pass
    def update(self):
        super().update()
        if (self.damageICounter>0):
            self.damageICounter-=g.deltaTime
            if (self.damageICounter <=0):
                self.returnFromDamage()
                self.setCollisionLayer(self.collisionLayerLast)
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
        room=rm.Room.current
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
        if (self.facing.x > 0): facing[0] = 1
        elif (self.facing.x < 0): facing[0] = -1
        if (self.facing.y > 0): facing[1] = 1
        elif (self.facing.y < 0): facing[1] = -1
        return '_'+str(facing[0])+str(facing[1])
    def generateFacingSprites(baseName,columns,w,h,t):
        if (type(columns)==int):
            columns=(columns,)
        outDict={}
        suffixes=('10','11','01','-11','-10','-1-1','0-1','1-1')
        for i in range(8):
            line=[]
            for col in columns:
                line.append((col*w,h*i,w,h,t))
            outDict[baseName+'_'+suffixes[i]]=tuple(line)
        return outDict

class Player(Character):
    #TODO: move to own file
    #controlled by player
    current=None
    def __init__(self, **kwargs):
        Player.current=self
        collisionBounds = pygame.Rect(-4,-3,8,6)
        #states: 'normal', 'roll', 'backstep', 'damage', 'rollBounce'
        self.state='start'
        self.dodgeTimer = 2.5
        sheetName='Guy'
        playerSheet=pygame.image.load(os.path.join(os.getcwd(), 'Assets','Sprites',sheetName+'.png'))
        w=16
        h=16
        #TODO: in Character, make a function to generate this grid of values
        animDict = {**Character.generateFacingSprites('idle', 0, w,h,.25),
                    **Character.generateFacingSprites('walk',(1,0,2,0),w,h,.08),
                    **Character.generateFacingSprites('dodge',3,w,h,2),
                    **Character.generateFacingSprites('attack',4,w,h,2),
                    #for some reason, the first frame (regardless of time) is skipped on spawn
                    'landing':((0,0,0,0,1),(0,0,0,0,1.5),(96,0,16,16,1),(112,0,16,16,.3),(0,32,16,16,1))
                    }
        super().__init__('player', None, collisionBounds,
                       s.Sprite(sheetName, 'landing', states = animDict, sheet=playerSheet),origin=(-8,-15),**kwargs)
        self.walkSpeed = 100
        self.dodgeSpeed = 350
        self.dodgeSteer = 15
        self.dodgeTime=.15
        self.backstepTime=.05
        self.rollBounceTimeScale=5 #on rolling into an obstacle, stun for this factor of rmaining roll time
        self.rollBounceMinTime = .2 #roll bounce stun will always be at least this long
        self.rollBounceSpeed = 200 #start speed for roll bounce
        self.rollBounceFalloff = 25
        self.moveInputVec = Vector2(0,0)
        g.GameLoop.inputEvents['moveUp'].add(self.inputMoveUp)
        g.GameLoop.inputEvents['moveDown'].add(self.inputMoveDown)
        g.GameLoop.inputEvents['moveLeft'].add(self.inputMoveLeft)
        g.GameLoop.inputEvents['moveRight'].add(self.inputMoveRight)
        g.GameLoop.inputEvents['dodge'].add(self.dodge)
        g.GameLoop.inputEvents['attack'].add(self.inputAttack)
        g.GameLoop.inputEvents['debugSpawn'].add(self.inputDebugSpawn)
        self.setCollisionLayer('player')
        bounds=pygame.Rect(-8,-8,16,16)
        center=(-8,-8)
        self.attackOb=DamageBox('playerAttack',self.room,bounds,
                                s.Sprite('Sword Slash2', 'ortho',states={'ortho':((0,0,16,16,.03),
                                                                                  (16,0,16,16,.02),
                                                                                  (32,0,16,16,100)),
                                                                         'diag':((0,16,16,16,.03),
                                                                                  (16,16,16,16,.02),
                                                                                  (32,16,16,16,100))}),
                                1,.03,.02,.25,collisionLayer='playerAttack',
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
                    self.state='rollBounce'
                    g.Window.current.bump(int(force.x*-2),int(force.y*-2),.06)
                    #g.Window.current.shake(5,int(force.x*-1.5),int(force.y*-1.5), .03)
                    dustVec=Vector2(force.y,-force.x)
                    self.spawnDust(dustVec*200-force*15, count=2)
                    self.spawnDust(-dustVec*200-force*15, count=2)
                    self.facing = collision.force*-1
                    self.dodgeVec = force
                    self.dodgeTimer = max(self.dodgeTimer*self.rollBounceTimeScale,self.rollBounceMinTime)
                    #TODO: make 'stunned' state with 'hurt' sprites but no damage blink
                    self.sprite.setState('idle'+self.getSpriteDirection()) #placeholder sprite
    def move(self, vect, faceMovement=True, overrideAnimation=False):
        Character.move(self, vect)
    def inputMoveUp(self, state):
        if (state):
            self.moveInputVec += Vector2(0,-1)
        else:
            self.moveInputVec -= Vector2(0,-1)
    def inputMoveDown(self, state):
        if (state):
            self.moveInputVec += Vector2(0,1)
        else:
            self.moveInputVec -= Vector2(0,1)
    def inputMoveLeft(self, state):
        if (state):
            self.moveInputVec += Vector2(-1,0)
        else:
            self.moveInputVec -= Vector2(-1,0)
    def inputMoveRight(self, state):
        if (state):
            self.moveInputVec += Vector2(1,0)
        else:
            self.moveInputVec -= Vector2(1,0)
    def inputAttack(self, state):
        if state:
            if (self.state=='normal' and not self.attackOb.active):
                #pos = self.position + self.facing.normalize()*8 + Vector2(0,-8)
                pos = self.facing.normalize()*8 + Vector2(0,-8)
                self.attackOb.attack(pos, self.facing)
                self.sprite.setState('attack'+self.getSpriteDirection())
    def dodge(self, state):
        if (state):
            if (self.state=='normal' and not self.attackOb.active):
                if self.moveInputVec.magnitude() > 0:
                    self.state='roll'
                    self.dodgeVec=Vector2(self.moveInputVec.normalize())
                    self.dodgeTimer=self.dodgeTime
                    self.sprite.setState('dodge'+self.getSpriteDirection())
                    self.spawnDust(self.dodgeVec * 500 + Vector2(0,-50), count=3)
                else:
                    self.state='backstep'
                    self.dodgeVec=Vector2(self.facing.normalize() * -1)
                    self.dodgeTimer=self.backstepTime
                    self.spawnDust(self.dodgeVec*150,count=2)
    def spawnDust(self, vel, count=5, randStr=1):
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
    def spawnLandingImpact(self):
        impactSprite=Entity('impactEffect',self.room,('Guy',((0,0,0,0,1),(0,0,0,0,1.5),(96,16,16,8,.3),(112,16,16,8),(96,24,16,8))),
                            position=self.position, origin=(-8,-4))
        impactSprite.destroy(time=2.4)


    def update(self):
        Character.update(self)
        if (self.state=='normal'):
            vec = Vector2(self.moveInputVec)
            if (vec.magnitude() > 0):
                vec=vec.normalize() * self.walkSpeed
            lockSprite=(self.attackOb.active)
            self.go(vec, faceMovement=(not lockSprite), overrideAnimation=lockSprite)
        elif self.state=='roll' or self.state == 'backstep':
            self.dodgeVec = (self.dodgeVec + (self.moveInputVec * self.dodgeSteer * g.deltaTime)).normalize()
            vec = self.dodgeVec * self.dodgeSpeed
            self.velocity=vec
            self.go(vec, faceMovement=False, overrideAnimation=True)
            self.dodgeTimer -= g.deltaTime
            if (self.dodgeTimer <=0):
                self.state='normal'
        elif self.state=='rollBounce':
            vec = self.dodgeVec * self.rollBounceSpeed
            self.dodgeVec *= 1-self.rollBounceFalloff*g.deltaTime
            self.go(vec, faceMovement=False, overrideAnimation=True)
            #self.velocity=vec
            self.dodgeTimer -= g.deltaTime
            if (self.dodgeTimer <= 0):
                self.state='normal'
        elif (self.state=='start'):
                self.dodgeTimer -= g.deltaTime
                if (self.dodgeTimer <= 0):
                    self.state='normal'
        self.totalForce=Vector2()

class DamageBox(Actor):
    def __init__(self, name, room, collisionBounds, sprite, damage,
                 windupTime,damageTime,remainTime, collisionLayer='monsterAttack', **kwargs):
        super().__init__(name, room, collisionBounds,sprite, **kwargs)
        print('damage box added, but not yet implemented')
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
        print(self.sprite.currentSprite)
        self.surface=pygame.Surface((self.sprite.currentSprite.width,self.sprite.currentSprite.height),
                                   flags=pygame.SRCALPHA)
        #TODO: collision mask
    def attack(self, position, facingVec):
        self.setActive(True)
        self.position=position
        self.rotation=degrees(atan2(facingVec[0],facingVec[1]))+180
        self.rotation=int(self.rotation/45)
        #self.diag=self.rotation%2
        if (self.rotation%2): self.sprite.setState('diag', restart=True)
        else: self.sprite.setState('ortho', restart=True)
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
        #g.Window.current.screen.blit(self.surface,self.position+self.origin)
    def onCollide(self, collision):
        super().onCollide(collision)
        col=collision.collider
        if hasattr(col,'takeDamage'):
            col.takeDamage(1,self)

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
        trigger = EffectTrigger(name, rm.Level.current,
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
        super().__init__('crate',room, pygame.Rect(-8,-13,16,16),
                         s.Sprite('Crate','normal',states={'normal':(0,0,16,16),
                                                           'hurt':((0,0,1,1,.03),(0,0,16,16))}),
                         position=position, origin=(-8,-13))
        self.skipDamage=False
        self.setCollisionLayer('breakables')
        self.health=3
        self.isObstacle=True
    def takeDamage(self, damage, fromActor):
        super().takeDamage(damage, fromActor)
        #TODO: use something other than a custom-defined sprite for flicker
        #   maybe an invisible flag that we can toggle on and off while hurt
        #TODO: add that invisible flag
        self.sprite.setState('hurt')
    def onDeath(self):
        super().onDeath()
        self.destroy()
    def returnFromDamage(self):
        super().returnFromDamage()
        self.sprite.setState('normal')