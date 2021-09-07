class Event:
    def __init__(self):
        self.subscribers = []
    def invoke(self):
        for subscriber in self.subscribers:
            subscriber()
    def add(self, subscriber):
        if not subscriber in self.subscribers:
            self.subscribers.append(subscriber)
    def remove(self, subscriber):
        if (subscriber in self.subscribers):
            self.subscribers.remove(subscriber)
class InputEvent(Event):
    def invoke(self, state):
        for subscriber in self.subscribers:
            subscriber(state)