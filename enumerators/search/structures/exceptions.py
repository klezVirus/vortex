class LinkedInSessionExpired(Exception):
    pass


class LinkedInInvalidSessionFileError(Exception):
    pass


class LinkedInInitFailed(Exception):
    pass


class LinkedInCaptchaError(Exception):
    pass


class LinkedInLiteVersionError(Exception):
    pass


class LinkedInCommercialSearchLimitError(Exception):
    pass


class LinkedInFetchError(Exception):
    def __init__(self, msg=""):
        super().__init__(msg)