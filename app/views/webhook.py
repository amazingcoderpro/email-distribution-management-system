from django.http import HttpResponse
import json
from config import logger


def event_trigger(request):
    if request.method == "POST":
        if request.POST:
            print("------------event_trigger:")
            print(request.POST)
            logger.error("---------event_trigger:{}".format(request.POST))
    return HttpResponse(json.dumps({"code": 200}))