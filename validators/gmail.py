from validators.validator import Validator


class GmailEnum(Validator):
    def __init__(self):
        super().__init__()
        self.urls = ["https://mail.google.com"]

    def execute(self, email) -> tuple:
        url = self.target + "/mail/gxlu"
        res = self.session.get(url, params={"email": email})
        if res and len(res.history) > 0:
            return True, email
        return False, email

