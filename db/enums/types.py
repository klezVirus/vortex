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
    def from_value(cls, value):
        _types = dict(map(lambda c: (c.value, c), cls))
        return _types[value] if value in _types.keys() else None

    @classmethod
    def value_list(cls):
        return list(map(lambda c: c.value, cls))

    @classmethod
    def key_list(cls):
        return list(map(lambda c: c.name.lower(), cls))


class EndpointType(ExtendedEnum):
    UNKNOWN = 1
    CISCO = 2
    CITRIX = 3
    CITRIXLEGACY = 4
    PULSE = 5
    SONICWALL = 6
    F5 = 7
    FORTINET = 8
    OPENVPN = 9
    OWA = 10
    LYNC = 11
    ADFS = 12
    IMAP = 13
    O365 = 14


class ProfileType(ExtendedEnum):
    LinedIn = 0
    Facebook = 1
    Instagram = 2
