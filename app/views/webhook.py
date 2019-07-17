from rest_framework.response import Response
import json
from rest_framework.views import APIView
from app import models
import datetime


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
        store = models.Store.objects.filter(url=request.META["HTTP_X_SHOPIFY_SHOP_DOMAIN"]).first()
        res["store"] = store
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
        res["product_info"] = str(li)
        models.OrderEvent.objects.create(**res)
        customer_instance = models.Customer.objects.filter(uuid=request.data["customer"]["id"]).first()
        if not customer_instance:
            customer_res = {}
            customer_res["store"] = store
            customer_res["uuid"] = request.data["customer"]["id"]
            customer_res["customer_email"] = request.data["customer"]["email"]
            customer_res["first_name"] = request.data["customer"]["first_name"]
            customer_res["last_name"] = request.data["customer"]["last_name"]
            customer_res["accept_marketing_status"] = request.data["customer"]["accepts_marketing"]
            customer_res["subscribe_time"] = request.data["customer"]["created_at"]
            customer_res["last_order_status"] = 0
            customer_res["last_order_time"] = datetime.datetime.now()
            models.Customer.objects.create(**customer_res)
        else:
            customer_instance.last_order_status = 0
            customer_instance.last_order_time = datetime.datetime.now()
            customer_instance.save()
        return Response({"code": 200})