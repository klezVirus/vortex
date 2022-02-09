from enum import Enum


class ExtendedEnum(Enum):
    @classmethod
    def get_name(cls, value):
        if isinstance(value, str):
            value = int(value)
        _types = dict(map(lambda c: (c.value, c.name.lower()), cls))
        return _types[value] if value in _types.keys() else None

    @classmethod
    def from_name(cls, name):
        _types = dict(map(lambda c: (c.name.lower(), c.value), cls))
        return _types[name] if name in _types.keys() else None

    @classmethod
    def value_list(cls):
        return list(map(lambda c: c.value, cls))

    @classmethod
    def key_list(cls):
        return list(map(lambda c: c.name.lower(), cls))


class EndpointType(ExtendedEnum):
    CISCO = 0
    CITRIX = 1
    CITRIXLEGACY = 2
    PULSE = 3
    SONICWALL = 4
    FORTINET = 5
    OWA = 6
    LYNC = 7
    ADFS = 8
    IMAP = 9
    O365 = 10
    UNKNOWN = 11
    F5 = 12


class ProfileType(ExtendedEnum):
    LinedIn = 0
    Facebook = 1
    Instagram = 2
