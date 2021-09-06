import os
import pygame
from pygame.math import Vector2
import Sprites as s
import Levels
import GameLoops

class Entity:
    #objects in scene
    def __init__(self, name, position, sprite, origin=(0,0)):
        self.name = name
        self.position=Vector2(position)
        if (type(sprite) == str):
            self.sprite=Sprite(sprite, s.Sprite.State(
                (s.Sprite.Frame(pygame.Rect(0,0,Levels.Level.current.tileSize,Levels.Level.current.tileSize)),))) #this is a mess
        else:
            self.sprite=sprite
        self.active=True
        self.origin=Vector2(origin)
        self.level = Levels.Level.current
        if (self.level):
            self.level.entities.append(self)
    def setActive(self, state):
        self.active=state
    def draw(self):
        if (self.active and self.sprite):
            self.sprite.draw(self.position+self.origin)
    def update(self):
        None
    def setLevel(self, level):
        if (self.level):
            self.level.entities.remove(self)
        self.level=level
        level.entities.append(self)
    def destroy(self):
        self.level.entities.remove(self)
        #TODO: add self to garbage cleanup array in GameLoop, which will properly finish up cleanup after render

class Actor(Entity):
    class Collision:
        def __init__(self, collider, force, collidingObType):
            #collidingObTypes:'floor', 'wall', 'actor'
            self.collider = collider
            self.collidingObType=collidingObType
            self.force = force
    #has collision
    def __init__(self, name, position, collisionBounds, sprite, origin=(0,0), ghost=False):
        #TODO: add static tag (never check wall or floor collisions)
        #TODO: add onlyCollidePlayer tag (for performance, self explanatory)

        Entity.__init__(self, name, position, sprite, origin=origin)
        self.collisionBounds=collisionBounds
        if (self.level): self.level.actors.append(self)
        self.ghost=ghost
        self.oldPosition = pygame.Vector2(position)
    def setLevel(self, level):
        if (self.level): self.level.actors.remove(self)
        super().setLevel(level)
        level.actors.append(self)

    def move(self, vect):
        newPos=self.position+vect
        self.position = newPos
    def destroy(self):
        Entity.destroy(self)
        self.level.actors.remove(self)
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
    def __init__(self, name, position, collisionBounds, sprite, origin=(0,0)):
        self.facing=Vector2(1,0)
        reqStates=('idle_-1-1', 'idle_0-1', 'idle_1-1', 'idle_-10', 'idle_10', 'idle_-11', 'idle_01', 'idle_11',
                  'walk_-1-1', 'walk_0-1', 'walk_1-1', 'walk_-10', 'walk_10', 'walk_-11', 'walk_01', 'walk_11')
        for state in reqStates:
            if (not state in sprite.states):
                raise AttributeError('required state ' + state + ' not in sprite!')
        Actor.__init__(self, name, position, collisionBounds, sprite, origin)
    def move(self, vec, faceMovement=True, overrideAnimation=False):
        Actor.move(self, vec)
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
    def __init__(self, position=(100,100)):
        Player.current=self
        self.walkSpeed = 1.3
        self.dodgeSpeed = 3
        self.dodgeTime=12
        self.backstepTime=5
        collisionBounds = pygame.Rect(-6,-4,12,8)
        #states: 'normal', 'dodge', 'damage'
        self.state='normal'
        sheetName='Guy'
        playerSheet=pygame.image.load(os.path.join(os.getcwd(), 'Assets','Sprites',sheetName+'.png'))
        #TODO: should we just encode all the sprite state data in pixels?
        dataPixel=playerSheet.get_at((0,playerSheet.get_height()-1))
        #w=16
        #h=16
        w=dataPixel[0]+1
        h=dataPixel[1]+1
        tIdle, tWalk,tDodge=(50,6,100)
        xIdle, xWalk1, xWalk2, xDodge = (0,w,w*2, w*3)
        ul, u, ur, l, r, dl, d, dr = (h*5,h*6,h*7,h*4,0,h*3,h*2,h)

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
        Character.__init__(self, 'player', position, collisionBounds,
                       s.Sprite(sheetName, 'idle_10', states = animDict, sheet=playerSheet),origin=(-8,-15))
        self.moveVec = Vector2(0,0)
        GameLoops.GameLoop.inputEvents['moveUp'].subscribers.append(self.moveUp)
        GameLoops.GameLoop.inputEvents['moveDown'].subscribers.append(self.moveDown)
        GameLoops.GameLoop.inputEvents['moveLeft'].subscribers.append(self.moveLeft)
        GameLoops.GameLoop.inputEvents['moveRight'].subscribers.append(self.moveRight)
        GameLoops.GameLoop.inputEvents['dodge'].subscribers.append(self.dodge)
        self.debugCollider=None

        #self.debugCollider = (0,255,0)
    def draw(self):
        Character.draw(self)
        if (self.debugCollider):
            tempBox = pygame.Surface((self.collisionBounds.width, self.collisionBounds.height))
            tempBox.fill(self.debugCollider)
            GameLoops.Window.current.screen.blit(tempBox, self.position+self.collisionBounds.topleft)
    def onCollide(self, collision):
        super().onCollide(collision)
        if (self.debugCollider):
            self.debugCollider = (255,0,0)
    def move(self, vect, faceMovement=True, overrideAnimation=False):
        Character.move(self, vect, faceMovement=faceMovement, overrideAnimation=overrideAnimation)
    def moveUp(self, state):
        if (state):
            self.moveVec += Vector2(0,-1)
        else:
            self.moveVec -= Vector2(0,-1)
    def moveDown(self, state):
        if (state):
            self.moveVec += Vector2(0,1)
        else:
            self.moveVec -= Vector2(0,1)
    def moveLeft(self, state):
        if (state):
            self.moveVec += Vector2(-1,0)
        else:
            self.moveVec -= Vector2(-1,0)
    def moveRight(self, state):
        if (state):
            self.moveVec += Vector2(1,0)
        else:
            self.moveVec -= Vector2(1,0)
    def dodge(self, state):
        if (state):
            if (self.state=='normal'):
                self.state='dodge'
                if self.moveVec.magnitude() > 0:
                    self.dodgeVec=Vector2(self.moveVec.normalize())
                    self.dodgeTimer=self.dodgeTime
                    self.sprite.changeState('dodge'+self.getSpriteDirection())
                else:
                    self.dodgeVec=Vector2(self.facing.normalize() * -1)
                    self.dodgeTimer=self.backstepTime
    def update(self):
        Character.update(self)
        if (self.state=='normal'):
            vec = self.moveVec
            if (vec.magnitude() > 0):
                vec=vec.normalize() * self.walkSpeed
            self.move(vec)
        elif self.state=='dodge':
            vec = self.dodgeVec * self.dodgeSpeed
            self.move(vec, faceMovement=False, overrideAnimation=True)
            self.dodgeTimer -= 1
            if (self.dodgeTimer <=0):
                self.state='normal'

        if (self.debugCollider): self.debugCollider=(0,255,0)