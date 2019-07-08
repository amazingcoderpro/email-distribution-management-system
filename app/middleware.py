from django.utils.deprecation import MiddlewareMixin
import json


class ResponseMiddleware(MiddlewareMixin):

    res = {
        'code': 1,
        'msg': "successful",
        'data': []
    }

    def process_response(self, request, response):
        if response.status_code == 400:
            response.status_code = 200
            self.res["code"] = 2
            self.res["msg"] = response.data
            self.res["data"] = []
            response._container = [bytes(json.dumps(self.res).encode("utf-8"))]
            return response

        if response.status_code == 401 or response.status_code == 403:
            self.res["code"] = 0
            self.res["msg"] = response.data
            self.res["data"] = []
            response._container = [bytes(json.dumps(self.res).encode("utf-8"))]
            return response

        if response.status_code == 200 or response.status_code == 201:
            response.status_code = 200
            self.res["code"] = 1
            self.res["msg"] = "successful"
            self.res["data"] = response.data
            response._container = [bytes(json.dumps(self.res).encode("utf-8"))]
            return response

        if response.status_code == 204:
            response.status_code = 200
            self.res["code"] = 1
            self.res["msg"] = "successful"
            self.res["data"] = []
            response._container = [bytes(json.dumps(self.res).encode("utf-8"))]
            return response

        if response.status_code == 404:
            response.status_code = 200
            self.res["code"] = 2
            self.res["msg"] = "The resource was not found"
            self.res["data"] = []
            response._container = [bytes(json.dumps(self.res).encode("utf-8"))]
            return response
        return response