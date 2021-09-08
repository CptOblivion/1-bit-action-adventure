import os
import pygame
from pygame.math import Vector2
import sprite as s
import room as rm
import gameloop as g
import random

class Entity:
    #objects in scene
    def __init__(self, name, room, sprite, position=(100,100), origin=(0,0)):
        self.name = name
        self.position=Vector2(position)
        if (type(sprite) == str):
            self.sprite=Sprite(sprite, s.Sprite.State(
                (s.Sprite.Frame(pygame.Rect(0,0,room.tileSize,room.tileSize)),))) #this is a mess
        else:
            self.sprite=sprite
        self.active=True
        self.origin=Vector2(origin)
        self.room = room
        if (self.room):
            self.room.entities.append(self)
    def getCell(self, gridSize):
        #TODO: for optimization (get cell to cull collision tests, also to sort into rendering cells)
        pass
    def setActive(self, state):
        self.active=state
    def draw(self):
        if (self.active and self.sprite):
            self.sprite.draw(self.position+self.origin)
    def update(self):
        None
    def setRoom(self, room):
        if (self.room):
            self.room.entities.remove(self)
        self.room=room
        room.entities.append(self)
    def destroy(self):
        self.room.entities.remove(self)
        #TODO: add self to garbage cleanup array in GameLoop,
        #   which will run actualDestroy right before the next frame starts
    def actualDestroy(self):
        del self

class Actor(Entity):
    class Collision:
        def __init__(self, collider, force, collidingObType):
            #collidingObTypes:'floor', 'wall', 'actor'
            self.collider = collider
            self.collidingObType=collidingObType
            self.force = force
    #has collision
    def __init__(self, name, room, collisionBounds, sprite, ghost=False, **kwargs):
        #TODO: add static tag (never check wall or floor collisions)
        #TODO: add onlyCollidePlayer tag (for performance, self explanatory)
        #TODO: add noCollideActors tag to only check walls for collision

        super().__init__(name, room, sprite, **kwargs)
        self.collisionBounds=collisionBounds
        if (self.room): self.room.actors.append(self)
        self.ghost=ghost
        self.velocity = pygame.Vector2(0,0)
        self.collideActors=True
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
    def destroy(self):
        super().destroy()
        self.room.actors.remove(self)
    def testCollision(self, actor):
        if (actor.active and 
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
        self.facing=Vector2(1,0)
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
    #from GameLoops import GameLoop
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
        animDict={'idle_-1-1':s.Sprite.State(((xIdle,ul,w,h,tIdle),)),
                  'idle_0-1':s.Sprite.State(((xIdle,u,w,h,tIdle),)),
                  'idle_1-1':s.Sprite.State(((xIdle,ur,w,h,tIdle),)),
                  'idle_-10':s.Sprite.State(((xIdle,l,w,h,tIdle),)),
                  'idle_10':s.Sprite.State(((xIdle,r,w,h,tIdle),)),
                  'idle_-11':s.Sprite.State(((xIdle,dl,w,h,tIdle),)),
                  'idle_01':s.Sprite.State(((xIdle,d,w,h,tIdle),)),
                  'idle_11':s.Sprite.State(((xIdle,dr,w,h,tIdle),)),
                  'walk_-1-1':s.Sprite.State((
                      (xWalk1,ul,w,h,tWalk),
                      (xIdle,ul,w,h),
                      (xWalk2,ul,w,h),
                      (xIdle,ul,w,h))),
                  'walk_0-1':s.Sprite.State((
                      (xWalk1,u,w,h,tWalk),
                      (xIdle,u,w,h),
                      (xWalk2,u,w,h),
                      (xIdle,u,w,h))),
                  'walk_1-1':s.Sprite.State((
                      (xWalk1,ur,w,h,tWalk),
                      (xIdle,ur,w,h),
                      (xWalk2,ur,w,h),
                      (xIdle,ur,w,h))),
                  'walk_-10':s.Sprite.State((
                      (xWalk1,l,w,h,tWalk),
                      (xIdle,l,w,h),
                      (xWalk2,l,w,h),
                      (xIdle,l,w,h))),
                  'walk_10':s.Sprite.State((
                      (xWalk1,r,w,h,tWalk),
                      (xIdle,r,w,h),
                      (xWalk2,r,w,h),
                      (xIdle,r,w,h),)),
                  'walk_-11':s.Sprite.State((
                      (xWalk1,dl,w,h,tWalk),
                      (xIdle,dl,w,h),
                      (xWalk2,dl,w,h),
                      (xIdle,dl,w,h))),
                  'walk_01':s.Sprite.State((
                      (xWalk1,d,w,h,tWalk),
                      (xIdle,d,w,h),
                      (xWalk2,d,w,h),
                      (xIdle,d,w,h))),
                  'walk_11':s.Sprite.State((
                      (xWalk1,dr,w,h,tWalk),
                      (xIdle,dr,w,h),
                      (xWalk2,dr,w,h),
                      (xIdle,dr,w,h))),
                  'dodge_-1-1':s.Sprite.State(((xDodge,ul,w,h,tDodge),)),
                  'dodge_0-1':s.Sprite.State(((xDodge,u,w,h,tDodge),)),
                  'dodge_1-1':s.Sprite.State(((xDodge,ur,w,h,tDodge),)),
                  'dodge_-10':s.Sprite.State(((xDodge,l,w,h,tDodge),)),
                  'dodge_10':s.Sprite.State(((xDodge,r,w,h,tDodge),)),
                  'dodge_-11':s.Sprite.State(((xDodge,dl,w,h,tDodge),)),
                  'dodge_01':s.Sprite.State(((xDodge,d,w,h,tDodge),)),
                  'dodge_11':s.Sprite.State(((xDodge,dr,w,h,tDodge),)),
                  'dodge':s.Sprite.State(((xDodge,l,w,h,100),))}
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
        g.GameLoop.inputEvents['moveUp'].add(self.moveUp)
        g.GameLoop.inputEvents['moveDown'].add(self.moveDown)
        g.GameLoop.inputEvents['moveLeft'].add(self.moveLeft)
        g.GameLoop.inputEvents['moveRight'].add(self.moveRight)
        g.GameLoop.inputEvents['dodge'].add(self.dodge)
        self.debugCollider=None

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
    def moveUp(self, state):
        if (state):
            self.moveInputVec += Vector2(0,-1)
        else:
            self.moveInputVec -= Vector2(0,-1)
    def moveDown(self, state):
        if (state):
            self.moveInputVec += Vector2(0,1)
        else:
            self.moveInputVec -= Vector2(0,1)
    def moveLeft(self, state):
        if (state):
            self.moveInputVec += Vector2(-1,0)
        else:
            self.moveInputVec -= Vector2(-1,0)
    def moveRight(self, state):
        if (state):
            self.moveInputVec += Vector2(1,0)
        else:
            self.moveInputVec -= Vector2(1,0)
    def dodge(self, state):
        if (state):
            if (self.state=='normal'):
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
                            s.Sprite('Dust', s.Sprite.State(((0,0,spriteSize,spriteSize,.25+rand*ra),
                                                             (spriteSize,0,spriteSize,spriteSize),
                                                             (spriteSize*2,0,spriteSize,spriteSize))),
                                     sheet=self.dustSpriteSheet),
                            .75+rand*ra*3, position=self.position, origin=(-4,-6))
            dust.velocity=vel * (1-abs(rand)*ry) + cross*rand*rx
            dust.damping=8

    def update(self):
        Character.update(self)
        if (self.state=='normal'):
            vec = Vector2(self.moveInputVec)
            if (vec.magnitude() > 0):
                vec=vec.normalize() * self.walkSpeed# * g.deltaTime
            self.go(vec)
        elif self.state=='roll' or self.state == 'backstep':
            self.dodgeVec = (self.dodgeVec + (self.moveInputVec * self.dodgeSteer * g.deltaTime)).normalize()
            vec = self.dodgeVec * self.dodgeSpeed# * g.deltaTime
            self.velocity=vec
            self.go(vec, faceMovement=False, overrideAnimation=True)
            self.dodgeTimer -= g.deltaTime
            if (self.dodgeTimer <=0):
                self.state='normal'
        elif self.state=='rollBounce':
            vec = self.dodgeVec * self.rollBounceSpeed #* g.deltaTime
            self.dodgeVec *= 1-self.rollBounceFalloff*g.deltaTime
            self.go(vec, faceMovement=False, overrideAnimation=True)
            #self.velocity=vec
            self.dodgeTimer -= g.deltaTime
            if (self.dodgeTimer <= 0):
                self.state='normal'
                
        self.totalForce=Vector2()
        if (self.debugCollider): self.debugCollider=(0,255,0)

class Particle(Actor):
    def __init__(self, name, room, collisionBounds, sprite, life, **kwargs):
        super().__init__(name, room, collisionBounds, sprite, **kwargs)
        self.life=life
        self.damping = 0
        self.collideActors=False
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