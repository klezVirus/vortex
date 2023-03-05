import re
from enum import Enum

from db.enums.types import ExtendedEnum


class AadError(ExtendedEnum):
    UNKNOWN = -1
    LOCKED = 0
    WRONG_PASSWORD = 1
    EXPIRED_PASSWORD = 2
    NO_PASSWORD = 3
    AUTH_TIME_EXCEEDED = 4
    MFA_NEEDED = 5
    APP_NOT_FOUND = 6
    USER_NOT_FOUND = 7
    TENANT_NOT_FOUND = 8
    ACCOUNT_DISABLED = 9
    CONDITIONAL_ACCESS_POLICY = 10

    @staticmethod
    def from_str(label):
        if label.find("AADSTS50053") > -1:
            return AadError.LOCKED
        elif label.find("AADSTS50126") > -1:
            return AadError.WRONG_PASSWORD
        elif label.find("AADSTS50055") > -1:
            return AadError.EXPIRED_PASSWORD
        elif label.find("AADSTS50056") > -1:
            return AadError.NO_PASSWORD
        elif label.find("AADSTS50014") > -1:
            return AadError.AUTH_TIME_EXCEEDED
        elif label.find("AADSTS50076") > -1:
            return AadError.MFA_NEEDED
        elif label.find("AADSTS50057") > -1:
            return AadError.ACCOUNT_DISABLED
        elif label.find("AADSTS700016") > -1:
            return AadError.APP_NOT_FOUND
        elif label.find("AADSTS50034") > -1:
            return AadError.USER_NOT_FOUND
        elif label.find("AADSTS90002") > -1:
            return AadError.TENANT_NOT_FOUND
        elif label.find("AADSTS53003") or label.find("AADSTS50158") > -1:
            return AadError.CONDITIONAL_ACCESS_POLICY
        elif re.search(r"AADSTS\d{5}", label):
            return AadError.UNKNOWN
        else:
            return None


class IfExistsResult(ExtendedEnum):
    UNKNOWN_ERROR = -1
    VALID_USERNAME = 0
    UNKNOWN_USERNAME = 2
    THROTTLE = 3
    ERROR = 4
    VALID_USERNAME_DIFFERENT_IDP = 5
    VALID_USERNAME_2 = 6
