from rest_framework.response import Response
import json
from config import logger
from rest_framework.views import APIView


class Event_Trigger(APIView):

    def post(self, request, *args, **kwargs):
        print("------------event_trigger:")
        print(json.dumps(request.data))
        return Response({"code": 200})


class EventTriggerCreate(APIView):

    def post(self, request, *args, **kwargs):
        print("------------event_trigger_create:")
        print(json.dumps(request.data))
        return Response({"code": 200})
