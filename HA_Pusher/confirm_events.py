from .const import *
import datetime

class EventConfirmation:
    install_id: str
    context_id: str
    timestamp: int

    def __init__(self, install_id: str, context_id: str, timestamp: int):
        self.install_id = install_id
        self.context_id = context_id
        self.timestamp = timestamp

    def __repr__(self):
        return f"({self.install_id}, {self.context_id}, {self.timestamp})"

    def __str__(self):
        return self.__repr__()


class EventConfirmer:
    confirmations: [EventConfirmation]

    def __init__(self):
        self.confirmations = []

    def __repr__(self):
        return f"confirmations: {self.confirmations}"

    def __str__(self):
        return self.__repr__()

    def _current_timestamp(self) -> int:
        return int(datetime.datetime.now().timestamp() * 1e6)

    def remove_expired(self):
        self.confirmations = list(
            filter(lambda conf: self._current_timestamp() - conf.timestamp < EVENT_CONFIRMATION_EXPIRATION_TIME,
                   self.confirmations))

    def add_confirmation(self, install_id: str, context_id: str):
        self.remove_expired()
        self.confirmations.append(EventConfirmation(install_id, context_id, self._current_timestamp()))

    def found_confirmation(self, install_id, context_id) -> bool:
        res = [conf for conf in self.confirmations if conf.install_id == install_id and conf.context_id == context_id]
        return len(res) > 0
