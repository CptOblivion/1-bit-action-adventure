import os
import pygame
from pygame.math import Vector2
import sprite as s
import room as rm
import gameloop as g
import random
from math import atan2, degrees

class Entity:
    #objects in scene
    def __init__(self, name, room, sprite, position=(100,100), origin=(0,0), parent=None):
        self.name = name
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
        self.children=[]
        self.parent=None
        if (parent):
            self.setParent(parent)
    def getCell(self, gridSize):
        #TODO: for optimization (get cell to cull collision tests, also to sort into rendering cells)
        pass
    def setActive(self, state):
        self.active=state
    def draw(self, **kwargs):
        if (self.active and self.sprite):
            self.sprite.draw(self.position+self.origin, **kwargs)
    def update(self):
        None
    def setRoom(self, room):
        if (self.room):
            self.room.entities.remove(self)
        self.room=room
        room.entities.append(self)
        for child in self.children:
            child.setRoom(room)
    def destroy(self):
        self.room.entities.remove(self)
        if (self.parent): self.parent.remove(self)
        for child in self.children:
            child.destroy()
        #TODO: add self to garbage cleanup array in GameLoop,
        #   which will run actualDestroy right before the next frame starts
    def actualDestroy(self):
        del self
    def setParent(self, parent):
        if (self.parent):
            self.parent.children.remove(self)
        parent.children.append(self)
        self.parent=parent
        #print('changed ', self.name, "'s parent to ", self.parent, '. New siblings (plus self): ', self.parent.children)

class Actor(Entity):
    collisionLayerNames={'default':1,'monsters':2,'player':3,'breakables':4,
                         'monsterAttack':5,'playerAttack':6,'hitStun':7,'unused':8}
    #reminder: the bits are in right-to-left order 
    collisionMask=[0,
                   0b01001111, #default
                   0b00101101, #monsters
                   0b00011111, #player
                   0b00111111, #breakables
                   0b00001100, #monsterAttack
                   0b00001010, #playerAttack
                   0b00000001, #hitstun
                   0b00000000] #unused
    class Collision:
        def __init__(self, collider, force, collidingObType):
            #collidingObTypes:'floor', 'wall', 'actor'
            self.collider = collider
            self.collidingObType=collidingObType
            self.force = force
    #has collision
    def __init__(self, name, room, collisionBounds, sprite, ghost=False, **kwargs):
        self.collisionLayer=1
        #TODO: add static tag (never check wall or floor collisions)
        #TODO: add onlyCollidePlayer tag (for performance, self explanatory)
        #TODO: add noCollideActors tag to only check walls for collision

        super().__init__(name, room, sprite, **kwargs)
        self.collisionBounds=collisionBounds
        if (self.room): self.room.actors.append(self)
        self.ghost=ghost #registers collisions, but doesn't receive physics
        self.skipDamage=True
        self.noCollideActors=False #skips collision tests with other actors
        self.noCollide=False #skips collision entirely
        self.velocity = pygame.Vector2(0,0)
        self.health=1
    def setCollisionLayer(self,layer):
        if (type(layer)==int): self.collisionLayer=layer
        else: self.collisionLayer = Actor.collisionLayerNames[layer]
    def takeDamage(self, damage, fromActor):
        if (not self.skipDamage):
            self.health -= damage
            if self.health <= 0: self.onDeath()
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
        newPos=self.position+vect
        self.position = newPos
        for child in self.children:
            child.position += vect
    def setPosition(self, pos):
        self.position=pos
        for child in self.children:
            pass
            #TODO: child should store local position (then get rid of the child for loop in move)
            #child.setPosition(self.position+child.localPosition)

    def destroy(self):
        super().destroy()
        self.room.actors.remove(self)
    def testCollision(self, actor):
        collisionMask=(Actor.collisionMask[actor.collisionLayer] >> (self.collisionLayer -1)) & 1
        if (actor.active and (not actor.noCollide) and collisionMask and (not actor.noCollideActors) and 
            self.collisionBounds.move(self.position).colliderect(actor.collisionBounds.move(actor.position))):
            force=Vector2(0,0)
            if (self.ghost == actor.ghost == False):
                None
                #resolve physics
                #store result in force on each sprite
            return(Actor.Collision(actor,force,'actor'))
        return None
    def gameloopCollision(self,actor):
        if (self.active):
            collision=self.testCollision(actor)
            if (collision):
                actor.onCollide(Actor.Collision(self,collision.force,'actor'))
                self.onCollide(collision)

    def onCollide(self, collision):
        None
        
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
            self.sprite.changeState(anim)
    def getSpriteDirection(self):
        facing=[0,0]
        if (self.facing.x > 0): facing[0] = 1
        elif (self.facing.x < 0): facing[0] = -1
        if (self.facing.y > 0): facing[1] = 1
        elif (self.facing.y < 0): facing[1] = -1
        return '_'+str(facing[0])+str(facing[1])

class Player(Character):
    #controlled by player
    current=None
    def __init__(self, **kwargs):
        Player.current=self
        collisionBounds = pygame.Rect(-6,-4,12,8)
        #states: 'normal', 'roll', 'backstep', 'damage', 'rollBounce'
        self.state='normal'
        sheetName='Guy'
        playerSheet=pygame.image.load(os.path.join(os.getcwd(), 'Assets','Sprites',sheetName+'.png'))
        w=16
        h=16
        tIdle, tWalk,tDodge=(.25,.08,10)
        xIdle, xWalk1, xWalk2, xDodge = (0,w,w*2, w*3)
        ul, u, ur, l, r, dl, d, dr = (h*5,h*6,h*7,h*4,0,h*3,h*2,h)
        #TODO: in Character, make a function to generate this grid of values
        animDict={'idle_-1-1':(xIdle,ul,w,h,tIdle),
                  'idle_0-1':(xIdle,u,w,h,tIdle),
                  'idle_1-1':(xIdle,ur,w,h,tIdle),
                  'idle_-10':(xIdle,l,w,h,tIdle),
                  'idle_10':(xIdle,r,w,h,tIdle),
                  'idle_-11':(xIdle,dl,w,h,tIdle),
                  'idle_01':(xIdle,d,w,h,tIdle),
                  'idle_11':(xIdle,dr,w,h,tIdle),
                  'walk_-1-1':(
                      (xWalk1,ul,w,h,tWalk),
                      (xIdle,ul,w,h),
                      (xWalk2,ul,w,h),
                      (xIdle,ul,w,h)),
                  'walk_0-1':(
                      (xWalk1,u,w,h,tWalk),
                      (xIdle,u,w,h),
                      (xWalk2,u,w,h),
                      (xIdle,u,w,h)),
                  'walk_1-1':(
                      (xWalk1,ur,w,h,tWalk),
                      (xIdle,ur,w,h),
                      (xWalk2,ur,w,h),
                      (xIdle,ur,w,h)),
                  'walk_-10':(
                      (xWalk1,l,w,h,tWalk),
                      (xIdle,l,w,h),
                      (xWalk2,l,w,h),
                      (xIdle,l,w,h)),
                  'walk_10':(
                      (xWalk1,r,w,h,tWalk),
                      (xIdle,r,w,h),
                      (xWalk2,r,w,h),
                      (xIdle,r,w,h)),
                  'walk_-11':(
                      (xWalk1,dl,w,h,tWalk),
                      (xIdle,dl,w,h),
                      (xWalk2,dl,w,h),
                      (xIdle,dl,w,h)),
                  'walk_01':((
                      (xWalk1,d,w,h,tWalk),
                      (xIdle,d,w,h),
                      (xWalk2,d,w,h),
                      (xIdle,d,w,h))),
                  'walk_11':(
                      (xWalk1,dr,w,h,tWalk),
                      (xIdle,dr,w,h),
                      (xWalk2,dr,w,h),
                      (xIdle,dr,w,h)),
                  'dodge_-1-1':(xDodge,ul,w,h,tDodge),
                  'dodge_0-1':(xDodge,u,w,h,tDodge),
                  'dodge_1-1':(xDodge,ur,w,h,tDodge),
                  'dodge_-10':(xDodge,l,w,h,tDodge),
                  'dodge_10':(xDodge,r,w,h,tDodge),
                  'dodge_-11':(xDodge,dl,w,h,tDodge),
                  'dodge_01':(xDodge,d,w,h,tDodge),
                  'dodge_11':(xDodge,dr,w,h,tDodge),
                  'dodge':(xDodge,l,w,h,100)}
        super().__init__('player', None, collisionBounds,
                       s.Sprite(sheetName, 'idle_10', states = animDict, sheet=playerSheet),origin=(-8,-15),**kwargs)
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
        self.setCollisionLayer('player')
        self.debugCollider=None
        bounds=pygame.Rect(-8,-8,16,16)
        center=(-8,-8)
        self.attackOb=DamageBox('playerAttack',self.room,bounds,
                                s.Sprite('Sword Slash2', 'ortho',states={'ortho':(0,0,16,16,100),
                                                                         'diag':(0,16,16,16,100)}),
                                1,.03,.02,.25,collisionLayer='playerAttack',
                              ghost=True, parent=self, origin=center)
        #self.debugCollider = (0,255,0)
    def draw(self):
        Character.draw(self)
        if (self.debugCollider):
            tempBox = pygame.Surface((self.collisionBounds.width, self.collisionBounds.height))
            tempBox.fill(self.debugCollider)
            g.Window.current.screen.blit(tempBox, self.position+self.collisionBounds.topleft)
    def onCollide(self, collision):
        super().onCollide(collision)
        if (self.state=='roll' and collision.collidingObType == 'wall'):
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
                    self.sprite.changeState('idle'+self.getSpriteDirection()) #placeholder sprite
        if (self.debugCollider):
            self.debugCollider = (255,0,0)
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
                pos = self.position + self.facing.normalize()*8 + Vector2(0,-8)
                self.attackOb.attack(pos, self.facing)
    def dodge(self, state):
        if (state):
            if (self.state=='normal' and not self.attackOb.active):
                if self.moveInputVec.magnitude() > 0:
                    self.state='roll'
                    self.dodgeVec=Vector2(self.moveInputVec.normalize())
                    self.dodgeTimer=self.dodgeTime
                    self.sprite.changeState('dodge'+self.getSpriteDirection())
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

    def update(self):
        Character.update(self)
        if (self.state=='normal'):
            vec = Vector2(self.moveInputVec)
            if (vec.magnitude() > 0):
                vec=vec.normalize() * self.walkSpeed
            self.go(vec, faceMovement=(not self.attackOb.active))
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
                
        self.totalForce=Vector2()

        #TODO: move hitbox debug drawing to Actor
        if (self.debugCollider): self.debugCollider=(0,255,0)
class DamageBox(Actor):
    def __init__(self, name, room, collisionBounds, sprite, damage,
                 windupTime,damageTime,remainTime, collisionLayer='monsterAttack', **kwargs):
        super().__init__(name, room, collisionBounds,sprite, **kwargs)
        print('damage box added, but not yet implemented')
        self.ghost=True
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
        if (self.rotation%2): self.sprite.changeState('diag')
        else: self.sprite.changeState('ortho')
        self.rotation=int(self.rotation/2)*90
        self.sprite.animTimer=0
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
        #TODO: build rotation library on sprite creation?
        g.Window.current.screen.blit(pygame.transform.rotate(self.surface, self.rotation),
                                     self.position+self.origin)
        #g.Window.current.screen.blit(self.surface,self.position+self.origin)
    def onCollide(self, collision):
        super().onCollide(collision)
        col=collision.collider
        print('hit ', col)

class Particle(Actor):
    def __init__(self, name, room, collisionBounds, sprite, life, **kwargs):
        super().__init__(name, room, collisionBounds, sprite, **kwargs)
        self.life=life
        self.damping = 0
        self.noCollideActors=False
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