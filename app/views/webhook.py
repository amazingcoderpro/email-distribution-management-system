from rest_framework.response import Response
import json
from rest_framework.views import APIView
from app import models


class EventCartUpdate(APIView):

    def post(self, request, *args, **kwargs):
        print("------------ cat update------------:")
        print(type(request.META))
        store_url = request.META["HTTP_X_SHOPIFY_SHOP_DOMAIN"]
        print(store_url)
        print(type(request.data))
        print(json.dumps(request.data))
        # print(type(request.META))

        return Response({"code": 200})


class EventCartCreate(APIView):

    def post(self, request, *args, **kwargs):
        print("------------ cat create ------------:")
        print(request.META, type(request.META))
        print(json.dumps(request.data))
        return Response({"code": 200})


class EventOrderUpdate(APIView):

    def post(self, request, *args, **kwargs):
        print("------------ order update------------:")
        print(request.META, type(request.META))
        print(json.dumps(request.data))
        return Response({"code": 200})


class EventOrderCreate(APIView):

    def post(self, request, *args, **kwargs):
        print("------------ order create ------------:")
        print(request.META, type(request.META))
        print(json.dumps(request.data))
        return Response({"code": 200})


class EventOrderPaid(APIView):

    def post(self, request, *args, **kwargs):
        print("------------ order paid ------------:")
        print(json.dumps(request.data))
        res = {}
        res["store_url"] = request.META["HTTP_X_SHOPIFY_SHOP_DOMAIN"]
        res["order_uuid"] = request.data["id"]
        res["status"] = 1
        res["customer_uuid"] = request.data["customer"]["id"]
        li = []
        for item in request.data["line_items"]:
            product_id = item["product_id"]
            title = item["title"]
            price = item["price"]
            quantity = item["quantity"]
            li.append({"product_id":product_id,"title":title,"price":"price","quantity":quantity})
        models.OrderEvent.objects.create(**res)
        return Response({"code": 200})