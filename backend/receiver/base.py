from abc import ABC, abstractmethod

from backend.receiver.config import ReceiverConfig
from backend.signal.models import IQBlock


class Receiver(ABC):
    def __init__(self, config=None):
        self.config = config or ReceiverConfig()
        self.config.validate()

    @abstractmethod
    def open(self):
        raise NotImplementedError

    @abstractmethod
    def close(self):
        raise NotImplementedError

    @abstractmethod
    def read_block(self) -> IQBlock:
        raise NotImplementedError

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()
