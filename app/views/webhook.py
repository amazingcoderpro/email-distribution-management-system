from rest_framework.response import Response
import json
from config import logger
from rest_framework.views import APIView


<<<<<<< HEAD
class Event_Trigger(APIView):
=======


class EventCartTrigger(APIView):
>>>>>>> 6c7788d2a0bf0d8da7d2830961417d5d6c3beae3

    def post(self, request, *args, **kwargs):
        print("------------ cat ------------:")
        print(json.dumps(request.data))
        return Response({"code": 200})


class EventCartTriggerCreate(APIView):

    def post(self, request, *args, **kwargs):
        print("------------ cat create ------------:")
        print(json.dumps(request.data))
        return Response({"code": 200})


class EventOrderTrigger(APIView):

    def post(self, request, *args, **kwargs):
        print("------------ order ------------:")
        print(json.dumps(request.data))
        return Response({"code": 200})


class EventOrderTriggerCreate(APIView):

    def post(self, request, *args, **kwargs):
        print("------------ order create ------------:")
        print(json.dumps(request.data))
        return Response({"code": 200})