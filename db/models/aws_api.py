from db.models.model import Model


class AwsApi(Model):
    def __init__(self, aid: int, api_id, region, url, proxy_url, created_at=None):
        super().__init__()
        self.aid = aid
        self.api_id = api_id
        self.region = region
        self.url = url
        self.proxy_url = proxy_url
        self.created_at = created_at

    def to_string(self):
        return f"({self.created_at})[{self.region}][{self.api_id}] {self.proxy_url} -> {self.url}"

    def to_dict(self):
        return {
            "aid": self.aid,
            "api_id": self.api_id,
            "region": self.region,
            "url": self.url,
            "proxy_url": self.proxy_url,
            "created_at": self.created_at
        }
