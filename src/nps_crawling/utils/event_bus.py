from collections import defaultdict
from typing import Callable

class EventBus:
    def __init__(self):
        self._listeners = defaultdict(list)

    def subscribe(self, event_name: str, callback: Callable):
        """Subscribe a callback function to an event."""
        self._listeners[event_name].append(callback)

    def unsubscribe(self, event_name: str, callback: Callable):
        """Unsubscribe a callback function from an event."""
        if callback in self._listeners[event_name]:
            self._listeners[event_name].remove(callback)

    def publish(self, event_name: str, *args, **kwargs):
        """Publish an event and call all subscribed callbacks."""
        for callback in self._listeners[event_name]:
            callback(*args, **kwargs)

bus: EventBus = EventBus()