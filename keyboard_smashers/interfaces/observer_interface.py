from abc import ABC, abstractmethod


# Observer Interface
class Observer(ABC):
    @abstractmethod
    def update(self, review, event_type, event_data):
        """Called when review is updated"""
        pass
