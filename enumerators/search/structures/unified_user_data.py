import re

from utils.mashers.namemash import NameMasher


class UnifiedUserData:
    HEADERS = ["Name", "Role", "Location", "Summary", "Db", "Phone", "Password", "Hash", "Email", "Username", "Address"]

    def __init__(self, name="", role="", location="", text="", db="",
                 phone="", password="", phash="", email="", username="",
                 address=""):
        self.name = name
        self.role = role
        self.location = location
        self.text = text
        self.db = db
        self.phone = phone
        self.password = password
        self.phash = phash
        self.email = email
        self.username = username
        self.address = address

    def normalize(self, masher: NameMasher, domain: str):
        if self.name != "" and self.email == "":
            self.email = masher.handle_name(self.name) + "@" + domain
        if self.name != "" and re.search(r"^(x+)@", self.email, re.IGNORECASE):
            self.email = masher.handle_name(self.name) + "@" + self.email.split("@")[1]
        if self.username == "":
            self.username = masher.handle_name(self.name)
        if self.location == "" and self.address != "":
            self.location = self.address

    def to_csv(self):
        return f"\"{self.name}\",\"{self.role}\",\"{self.location}\",\"{self.text}\", \"{self.db}\", " \
               f"\"{self.phone}\", \"{self.password}\", \"{self.phash}\", \"{self.email}\", \"{self.username}\"," \
               f" \"{self.address}\""


class UnifiedUserDataList:
    def __init__(self):
        self.internal_list = []
        self.mode = "w"

    # adding two objects
    def __add__(self, o):
        if not hasattr(o, "internal_list"):
            return
        self.internal_list += o.internal_list
        return self

    def __len__(self):
        return len(self.internal_list)

    def __iter__(self):
        return self.internal_list.__iter__()

    @property
    def count(self):
        return len(self.internal_list)

    @property
    def is_empty(self):
        return len(self.internal_list) == 0

    def append(self, unified_user: UnifiedUserData):
        self.internal_list.append(unified_user)

    def to_csv(self):
        return "\n".join([uu.to_csv() for uu in self.internal_list])

    def save_csv(self, filename, reset=True):
        """
        This function saves the list using the following algorithm
        1st call: Writes header and overwrite the file
        2nd+ calls: Writes in append mode
        Every call to this function flushes the list of employees
        """
        if self.mode == "w":
            with open(filename, self.mode, encoding="latin-1", errors="replace") as save:
                save.write(",".join(UnifiedUserData.HEADERS) + "\n")
        self.mode = "a"
        with open(filename, self.mode, encoding="latin-1", errors="replace") as save:
            save.write(self.to_csv())
        if reset:
            self.internal_list = []

