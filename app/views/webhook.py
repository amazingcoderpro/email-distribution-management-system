from rest_framework.response import Response
import json
from config import logger
from rest_framework.views import APIView




class Event_Trigger(APIView):

    def post(self, request, *args, **kwargs):
        print("------------event_trigger:")
        print(request.POST)
        logger.error("---------event_trigger:{}".format(request.POST))
        return Response({"code": 200})
