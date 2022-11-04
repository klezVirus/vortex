from enum import Enum


class AadError(Enum):
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
        if label == "AADSTS50053":
            return AadError.LOCKED
        elif label == "AADSTS50126":
            return AadError.WRONG_PASSWORD
        elif label == "AADSTS50055":
            return AadError.EXPIRED_PASSWORD
        elif label == "AADSTS50056":
            return AadError.NO_PASSWORD
        elif label == "AADSTS50014":
            return AadError.AUTH_TIME_EXCEEDED
        elif label == "AADSTS50076":
            return AadError.MFA_NEEDED
        elif label == "AADSTS50057":
            return AadError.ACCOUNT_DISABLED
        elif label == "AADSTS700016":
            return AadError.APP_NOT_FOUND
        elif label == "AADSTS50034":
            return AadError.USER_NOT_FOUND
        elif label == "AADSTS90002":
            return AadError.TENANT_NOT_FOUND
        elif label == "AADSTS53003":
            return AadError.CONDITIONAL_ACCESS_POLICY
        else:
            return AadError.UNKNOWN
