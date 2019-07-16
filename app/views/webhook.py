from rest_framework.response import Response
import json
from config import logger
from rest_framework.views import APIView


class EventCartUpdate(APIView):

    def post(self, request, *args, **kwargs):
        print("------------ cat ------------:")
        print(json.dumps(request.data))
        return Response({"code": 200})


class EventCartTriggerCreate(APIView):

    def post(self, request, *args, **kwargs):
        print("------------ cat create ------------:")
        print(json.dumps(request.data))
        return Response({"code": 200})


class EventCartCreate(APIView):

    def post(self, request, *args, **kwargs):
        print("------------ order ------------:")
        print(json.dumps(request.data))
        return Response({"code": 200})


class EventOrderCreate(APIView):

    def post(self, request, *args, **kwargs):
        print("------------ order create ------------:")
        print(json.dumps(request.data))
        return Response({"code": 200})