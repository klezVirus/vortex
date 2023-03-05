from db.handler import DBHandler
from db.interfaces.dao import Dao
from db.models.attempt import Attempt
from db.models.aws_api import AwsApi
from db.models.login import Login


class AwsApiDao(Dao):
    def __init__(self, handler: DBHandler):
        super().__init__(handler, "aws_api")

    def dao_create_object(self, data):
        return AwsApi(
                    aid=data[0],
                    api_id=data[1],
                    region=data[2],
                    url=data[3],
                    proxy_url=data[4],
                    created_at=data[5]
                )

    def exists(self, **kwargs):
        pass

    def find_by_url(self, url):
        sql = "SELECT * FROM aws_api WHERE url = ?"
        args = (url,)
        return self.dao_collect(sql, args)

    def find_by_region(self, region):
        sql = "SELECT * FROM aws_api WHERE region = ?"
        args = (region,)
        return self.dao_collect(sql, args)

    def delete_by_url(self, url):
        sql = "DELETE FROM aws_api where url = ?"
        args = (url,)
        self.dao_execute(sql, args)

    def delete_by_id(self, api_id):
        sql = "DELETE FROM aws_api where aid = ?"
        args = (api_id,)
        self.dao_execute(sql, args)

    def delete(self, obj: AwsApi):
        self.delete_by_id(obj.api_id)

    def save_new(self, **kwargs):
        url = kwargs.get("url")
        proxy_url = kwargs.get("proxy_url")
        region = kwargs.get("region")
        api_gateway_id = kwargs.get("api_gateway_id")
        self.save(AwsApi(aid=0, api_id=api_gateway_id, url=url, proxy_url=proxy_url, region=region))

    def save(self, obj: AwsApi):
        sql = "INSERT OR IGNORE INTO aws_api (api_id, region, url, proxy_url) VALUES (?, ?, ?, ?)"
        args = (obj.api_id, obj.region, obj.url, obj.proxy_url)
        self.dao_execute(sql, args)
