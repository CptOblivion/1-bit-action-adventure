import Entities as e
import pygame
import Levels
import GameLoops

class LevelDoor(e.Actor):
	def __init__(self, name, position, collisionBounds, sprite, exitDirection,linkedLevel,linkedDoor):
		super().__init__(name, position,collisionBounds,sprite,ghost=True)
		#TODO: maybe this should be a floor or a wall tile, actually
		#	collision is implemented for entities tho
		self.exitDirection=exitDirection
		self.linkedLevel=linkedLevel
		self.linkedDoor = linkedDoor
		if (self.linkedLevel=='None'):
			self.linkedLevel = None
			self.linkedDoor = None
			self.setActive(False)
		self.colliding=False
		Levels.Level.current.doors[self.name]=self
		#print(self.name)
	def onCollide(self, collision):
		super().onCollide(collision)
		if (collision.collider==e.Player.current):
			if (self.collisionBounds.move(self.position).collidepoint(e.Player.current.position)):
				self.colliding=True
	def update(self):
		super().update()
		if (self.colliding):
			collision=self.testCollision(e.Player.current)
			if(not collision):
				self.colliding=False
				#TODO: not totally robust, should be checking if player position plus half of each bound on the appropriate axis
				if (self.exitDirection =='T' and e.Player.current.position.y < self.position.y):
					self.triggerLoad()
				if (self.exitDirection =='B' and e.Player.current.position.y > self.position.y):
					self.triggerLoad()
				if (self.exitDirection =='L' and e.Player.current.position.x < self.position.x):
					self.triggerLoad()
				if (self.exitDirection =='R' and e.Player.current.position.x > self.position.x):
					self.triggerLoad()
	def triggerLoad(self):
		GameLoops.GameLoop.current.loadLevel(self.linkedLevel, self.linkedDoor)
		#print(self.linkedLevel,self.linkedDoor)
		#self.setActive(False)
	def draw(self):
		return
		super().draw()
		if (self.active):
			tempBox=pygame.Surface((self.collisionBounds.width, self.collisionBounds.height))
			tempBox.fill((0,0,255))
			GameLoops.Window.current.screen.blit(tempBox,self.position+self.collisionBounds.topleft)


