from abc import ABC, abstractmethod
from nio.events.room_events import RoomMessageText
class Observable(ABC):
    
    @abstractmethod
    def subscribe(self, observer: Observer):
        pass

    @abstractmethod
    def unsubscribe(self, observer: Observer):
        pass

    @abstractmethod
    def notify(self, message: str):
        pass

class Observer(ABC):

    @abstractmethod
    def notify(self, event:RoomMessageText):
        pass

    @abstractmethod
    def prefix(self:str)
        pass