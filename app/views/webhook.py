from django.http import HttpResponse
import json
from config import logger


def event_trigger(request):
    if request.method == "POST":
        if request.POST:
            print(request.POST)
            logger.error("{}".format(request.POST))
    return HttpResponse(json.dumps({"code": 200}))