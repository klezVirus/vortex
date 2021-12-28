from abc import ABC, abstractmethod


class Model(ABC):
    def __init__(self):
        pass
        # self.dbh = DBHandler(workspace=workspace)

    @abstractmethod
    def to_string(self):
        pass