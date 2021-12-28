from db.handler import DBHandler
from db.models.profile import Profile
from db.models.endpoint import Endpoint


class EndpointDao:
    def __init__(self, handler: DBHandler):
        self.dbh = handler

    def list_all(self):
        endpoints = []
        sql = "SELECT * FROM endpoints"
        with self.dbh.create_cursor() as cursor:
            cursor.execute(sql)
            for data in cursor:
                endpoint = Endpoint(
                    eid=data[0],
                    target=data[1],
                    endpoint_type=data[2],
                    is_o365=data[3]
                )
                endpoints.append(endpoint)
        return endpoints

    def delete(self, endpoint: Endpoint):
        sql = "DELETE FROM endpoints where eid = ?"
        args = (endpoint.eid,)
        with self.dbh.create_cursor() as cursor:
            cursor.execute(sql, args)

    def save(self, endpoint: Endpoint):
        # See if there is already
        endpoints = self.list_all()
        for p in endpoints:
            if p.target == endpoint.target and p.endpoint_type == endpoint.endpoint_type:
                return
        sql = "INSERT OR IGNORE INTO endpoints (target, endpoint_type, is_o365) VALUES (?, ?, ?)"
        args = (endpoint.target, endpoint.endpoint_type, endpoint.is_o365)
        with self.dbh.create_cursor() as cursor:
            cursor.execute(sql, args)
