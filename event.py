class Event:
    def __init__(self):
        self.subscribers = []
    def invoke(self):
        for subscriber in self.subscribers:
            subscriber()
class InputEvent(Event):
    def invoke(self, state):
        for subscriber in self.subscribers:
            subscriber(state)