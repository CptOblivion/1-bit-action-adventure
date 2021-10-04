class Event:
    def __init__(self):
        self.subscribers = []
    def invoke(self, *inputs):
        #subscriber may well delete self (or just unsubscribe) in the function that was subscribed
        #   so we'll iterate over a clone of the list, just to be safe
        for subscriber in self.subscribers[:]:
            subscriber(*inputs)
    def add(self, subscriber):
        if not subscriber in self.subscribers:
            self.subscribers.append(subscriber)
    def remove(self, subscriber):
        if (subscriber in self.subscribers):
            self.subscribers.remove(subscriber)
class InputEvent(Event):
    def invoke(self, value):
        super().invoke(value)