from multiprocessing.managers import BaseManager


class ShimManager(BaseManager):
    pass


class GroupManager:
    def __init__(self):
        ShimManager.register("dict", dict)
        self.selected_group = None
        self.shm = ShimManager()
        self.shm.start()
        self.groups = None
        self.create()

    def create(self):
        self.groups = self.shm.dict()

    def set(self, key, value):
        self.groups[key] = value

    def rm(self, key):
        self.groups.pop(key, None)

    def teardown(self):
        self.shm.shutdown()

    def get(self, key):
        return self.groups.get(key, None)
