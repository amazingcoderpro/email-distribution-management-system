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
        store_url = request.META["HTTP_X_SHOPIFY_SHOP_DOMAIN"]
        event_uuid = request.data["id"]
        order_uuid = request.data[""]

        print(request.META, type(request.META))
        print(json.dumps(request.data))
        return Response({"code": 200})


    # event_uuid = models.CharField(max_length=255, verbose_name="事件的唯一标识符")
    # order_uuid = models.CharField(max_length=255, verbose_name="订单的唯一标识符")
    # status = models.IntegerField(default=0, verbose_name="订单事件类型, 0-创建(未支付)，1-支付")
    # store_url = models.CharField(max_length=255, verbose_name="订单对应的店铺的url")
    # customer = models.CharField(max_length=255, db_index=True, verbose_name="订单对应客户id")
    #
    # # [{"product": "123456", "sales": 2, "amount": 45.22}, {"product": "123456", "sales": 1, "amount": 49.22}]
    # products = models.TextField(blank=True, null=True, verbose_name="订单所涉及到的产品及其销量信息")
    # create_time = models.DateTimeField(auto_now=True, db_index=True, verbose_name="订单创建时间")