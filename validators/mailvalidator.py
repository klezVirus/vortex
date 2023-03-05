import requests

from validators.validator import Validator


class EmailEnum(Validator):
    def __init__(self):
        super().__init__()
        self.urls = ["https://isitarealemail.com"]

    def execute(self, email) -> tuple:
        response = self.session.get(
            self.target + "/api/email/validate",
            params={'email': email})

        status = response.json()['status']
        if status == "valid":
            return True, email
        elif status == "invalid":
            return False, email
        else:
            return False, email