import datetime, json
from rest_framework.response import Response
from rest_framework.views import APIView

from app import models


# class EventOrderCreate(APIView):
#
#     def post(self, request, *args, **kwargs):
#         print("------------ order create ------------:")
#         print(json.dumps(request.data))
#         res = {}
#         store = models.Store.objects.filter(url=request.META["HTTP_X_SHOPIFY_SHOP_DOMAIN"]).first()
#         res["store"] = store
#         res["order_uuid"] = request.data["id"]
#         res["status"] = 0
#         res["total_price"] = request.data["total_price"]
#         create_time = request.data["created_at"].replace("T", " ")[:-6]
#         res["order_create_time"] = datetime.datetime.strptime(create_time, "%Y-%m-%d %H:%M:%S")
#         res["customer_uuid"] = request.data["customer"]["id"]
#         res["create_time"] = datetime.datetime.now()
#         order_instance = models.OrderEvent.objects.filter(store=store, order_uuid=request.data["id"]).first()
#         li = []
#         for item in request.data["line_items"]:
#             product_id = item["product_id"]
#             title = item["title"]
#             price = item["price"]
#             quantity = item["quantity"]
#             li.append({"product_id": product_id, "title": title, "price": price, "quantity": quantity})
#         res["product_info"] = json.dumps(li)
#         if order_instance:
#             order_instance.product_info = res["product_info"]
#             order_instance.total_price = res["total_price"]
#             order_instance.save()
#         else:
#             models.OrderEvent.objects.create(**res)
#         customer_instance = models.Customer.objects.filter(uuid=request.data["customer"]["id"]).first()
#         if not customer_instance:
#             customer_res = {}
#             customer_res["store"] = store
#             customer_res["uuid"] = request.data["customer"]["id"]
#             customer_res["customer_email"] = request.data["customer"]["email"]
#             customer_res["first_name"] = request.data["customer"]["first_name"]
#             customer_res["last_name"] = request.data["customer"]["last_name"]
#             customer_res["accept_marketing_status"] = request.data["customer"]["accepts_marketing"]
#             sign_up_time = request.data["customer"]["created_at"].replace("T"," ")[:-6]
#             customer_res["sign_up_time"] = datetime.datetime.strptime(sign_up_time, "%Y-%m-%d %H:%M:%S")
#             customer_res["last_order_status"] = 0
#             customer_res["last_order_id"] = request.data["customer"]["last_order_id"]
#             updated_at = request.data["customer"]["updated_at"].replace("T"," ")[:-6]
#             customer_res["last_order_time"] = datetime.datetime.strptime(updated_at, "%Y-%m-%d %H:%M:%S")
#             customer_res["create_time"] = datetime.datetime.now()
#             models.Customer.objects.create(**customer_res)
#         else:
#             customer_instance.last_order_status = 0
#             updated_at = request.data["customer"]["updated_at"].replace("T", " ")[:-6]
#             customer_instance.last_order_time = datetime.datetime.strptime(updated_at, "%Y-%m-%d %H:%M:%S")
#             customer_instance.save()
#         return Response({"code": 200})


class EventOrderPaid(APIView):

    def post(self, request, *args, **kwargs):
        print("------------ order paid ------------:")
        print(json.dumps(request.data))
        res = {}
        store = models.Store.objects.filter(url=request.META["HTTP_X_SHOPIFY_SHOP_DOMAIN"]).first()
        res["store"] = store
        res["order_uuid"] = request.data["id"]
        res["status"] = 1
        res["total_price"] = request.data["total_price"]
        res["checkout_id"] = request.data["checkout_id"]
        res["status_url"] = request.data.get("order_status_url", "")
        create_time = request.data["created_at"].replace("T", " ")[:-6]
        update_time = request.data["updated_at"].replace("T", " ")[:-6]
        res["order_create_time"] = datetime.datetime.strptime(create_time, "%Y-%m-%d %H:%M:%S")
        res["order_update_time"] = datetime.datetime.strptime(update_time, "%Y-%m-%d %H:%M:%S")
        res["customer_uuid"] = request.data["customer"]["id"]
        res["status_tag"] = "paid"
        res["create_time"] = datetime.datetime.now()
        order_instance = models.OrderEvent.objects.filter(store=store, order_uuid=request.data["id"]).first()
        li = []
        for item in request.data["line_items"]:
            product_id = item["product_id"]
            title = item["title"]
            price = item["price"]
            quantity = item["quantity"]
            li.append({"product_id": product_id, "title": title, "price": price, "quantity": quantity})
        res["product_info"] = li
        if order_instance:
            order_instance.product_info = res["product_info"]
            order_instance.total_price = res["total_price"]
            order_instance.checkout_id = res["checkout_id"]
            order_instance.save()
        else:
            models.OrderEvent.objects.create(**res)
        models.CheckoutEvent.objects.filter(store=store, checkout_id=request.data["checkout_id"]).update(status=1)
        customer_instance = models.Customer.objects.filter(uuid=request.data["customer"]["id"]).first()
        if not customer_instance:
            customer_res = {}
            customer_res["store"] = store
            customer_res["uuid"] = request.data["customer"]["id"]
            customer_res["customer_email"] = request.data["customer"]["email"]
            customer_res["first_name"] = request.data["customer"]["first_name"]
            customer_res["last_name"] = request.data["customer"]["last_name"]
            customer_res["accept_marketing_status"] = request.data["customer"]["accepts_marketing"]
            sign_up_time = request.data["customer"]["created_at"].replace("T"," ")[:-6]
            customer_res["sign_up_time"] = datetime.datetime.strptime(sign_up_time, "%Y-%m-%d %H:%M:%S")
            customer_res["last_order_status"] = 0
            customer_res["last_order_id"] = request.data["customer"]["last_order_id"]
            updated_at = request.data["customer"]["updated_at"].replace("T"," ")[:-6]
            customer_res["last_order_time"] = datetime.datetime.strptime(updated_at, "%Y-%m-%d %H:%M:%S")
            customer_res["create_time"] = datetime.datetime.now()
            models.Customer.objects.create(**customer_res)
        else:
            customer_instance.last_order_status = 0
            updated_at = request.data["customer"]["updated_at"].replace("T", " ")[:-6]
            customer_instance.last_order_time = datetime.datetime.strptime(updated_at, "%Y-%m-%d %H:%M:%S")
            customer_instance.save()
        return Response({"code": 200})


class EventDraftCustomersCreate(APIView):
    def post(self, request, *args, **kwargs):
        print("------------ Customer Create ------------:")
        # print(request.META, type(request.META))
        print(json.dumps(request.data))
        store = models.Store.objects.filter(url=request.META["HTTP_X_SHOPIFY_SHOP_DOMAIN"])
        if store.exists():
            store_id= store.first().id
        costomer_uuid = request.data["id"]
        # user = request.user
        # store_id  = user.store.id
        customer_email = request.data["email"]
        accept_marketing_status = request.data["accepts_marketing"]
        sign_up_time = request.data["created_at"].replace("T", " ")[:-6]
        first_name = request.data["first_name"]
        last_name = request.data["last_name"]
        orders_count = request.data["orders_count"]
        last_order_id = request.data["last_order_id"]
        payment_amount = request.data["total_spent"]
        create_time = request.data["created_at"].replace("T", " ")[:-6]
        update_time = request.data["updated_at"].replace("T", " ")[:-6]

        models.Customer.objects.create(
                                       store_id=store_id,
                                       uuid=costomer_uuid,
                                       customer_email= customer_email,
                                       accept_marketing_status= accept_marketing_status,
                                       sign_up_time=sign_up_time,
                                       first_name=first_name,
                                       last_name=last_name,
                                       orders_count=orders_count,
                                       last_order_id=last_order_id,
                                       payment_amount=payment_amount,
                                       create_time=create_time,
                                       update_time=update_time

        )

        return Response({"code": 200})


class EventDraftCustomersUpdate(APIView):
    def post(self, request, *args, **kwargs):
        print("------------ Customer Update ------------:")
        # print(request.META, type(request.META))
        print(json.dumps(request.data))
        store = models.Store.objects.filter(url=request.META["HTTP_X_SHOPIFY_SHOP_DOMAIN"])
        if store.exists():
            store_id = store.first().id
        event_uuid = request.data["id"]
        # user = request.user
        # store_id  = user.store.id
        costomer_instance = models.Customer.objects.get(store_id=store_id, uuid=event_uuid)
        if costomer_instance:
            costomer_instance.customer_email = request.data["email"]
            costomer_instance.accept_marketing_status = request.data["accepts_marketing"]
            costomer_instance.sign_up_time = request.data["created_at"].replace("T", " ")[:-6]
            costomer_instance.first_name = request.data["first_name"]
            costomer_instance.last_name = request.data["last_name"]
            costomer_instance.orders_count = request.data["orders_count"]
            costomer_instance.last_order_id = request.data["last_order_id"]
            costomer_instance.payment_amount = request.data["total_spent"]
            costomer_instance.create_time = request.data["created_at"].replace("T", " ")[:-6]
            costomer_instance.update_time = request.data["updated_at"].replace("T", " ")[:-6]
            costomer_instance.save()
        if not costomer_instance:
            models.Customer.objects.create(
                 store_id=store_id,
                 uuid=event_uuid,
                 customer_email=request.data["email"],
                 accept_marketing_status=request.data["accepts_marketing"],
                 sign_up_time=request.data["created_at"].replace("T", " ")[:-6],
                 first_name=request.data["first_name"],
                 last_name=request.data["last_name"],
                 orders_count=request.data["orders_count"],
                 last_order_id=request.data["last_order_id"],
                 payment_amount=request.data["total_spent"],
                 create_time=request.data["created_at"].replace("T", " ")[:-6],
                 update_time=request.data["updated_at"].replace("T", " ")[:-6]
            )
        return Response({"code": 200})


class CheckoutsCreate(APIView):

    def post(self, request, *args, **kwargs):
        print("------------ Checkouts Create ------------:")
        # print(request.META, type(request.META))
        print(json.dumps(request.data))

        result = request.data
        if not result.get("customer", ""):
            return Response({"code": 200})
        store_id = models.Store.objects.filter(url=request.META["HTTP_X_SHOPIFY_SHOP_DOMAIN"]).first().id
        checkout_id = result.get("id")
        customer_info = result.get("customer", "")
        product_info = []
        for product in result["line_items"]:
            product_dict = {"product": product.get("product_id", ""), "sales": product.get("quantity", ""),
                            "price": product.get("variant_price", "")}
            product_info.append(product_dict)
        customer_uuid = customer_info.get("id")
        total_price = customer_info.get("total_spent", 0.0)
        cart_token = request.data["cart_token"]
        if not cart_token:
            cart_token = ""
        checkout_create_time = result["created_at"].replace("T", " ")[:-6]
        checkout_update_time = result["updated_at"].replace("T", " ")[:-6]
        abandoned_checkout_url = result["abandoned_checkout_url"]
        create_time = datetime.datetime.now()
        update_time = datetime.datetime.now()
        cart_instance = models.CheckoutEvent.objects.create(
                        store_id=store_id,
                        customer_uuid=customer_uuid,
                        checkout_id=checkout_id,
                        total_price=total_price,
                        status=0,
                        cart_token=cart_token,
                        product_info=product_info,
                        abandoned_checkout_url=abandoned_checkout_url,
                        checkout_create_time=checkout_create_time,
                        checkout_update_time=checkout_update_time,
                        create_time=create_time,
                        update_time=update_time
        )
        cart_instance.save()
        return Response({"code": 200})


class CheckoutsUpdate(APIView):

    def post(self, request, *args, **kwargs):
        print("------------ Checkouts Update ------------:")
        # print(request.META, type(request.META))
        print(json.dumps(request.data))
        if not request.data.get("customer"):
            return Response({"code": 200})
        store = models.Store.objects.filter(url=request.META["HTTP_X_SHOPIFY_SHOP_DOMAIN"]).first()
        store_id = store.id
        product_info = []
        for product in request.data["line_items"]:
            product_dict = {"product": product.get("product_id", ""), "sales": product.get("quantity", ""),
                            "price": product.get("variant_price", "")}
            product_info.append(product_dict)
        checkout_create_time = request.data["created_at"].replace("T", " ")[:-6]
        checkout_update_time = request.data["updated_at"].replace("T", " ")[:-6]
        abandoned_checkout_url = request.data["abandoned_checkout_url"]
        cart_token = request.data["cart_token"]
        if not cart_token:
            cart_token = ""
        checkout_id = request.data["id"]
        customer_info = request.data.get("customer", "")
        customer_uuid = customer_info.get("id")
        total_price = request.data["total_price"]
        checkout_instance = models.CheckoutEvent.objects.filter(store=store, checkout_id=request.data["id"]).first()
        if not checkout_instance:
            models.CheckoutEvent.objects.create(
                store_id=store_id,
                status=0,
                customer_uuid=customer_uuid,
                checkout_id=checkout_id,
                total_price=total_price,
                product_info=product_info,
                cart_token=cart_token,
                abandoned_checkout_url=abandoned_checkout_url,
                checkout_create_time=checkout_create_time,
                checkout_update_time=checkout_update_time
            )
        else:
            checkout_instance.product_info = product_info
            checkout_instance.total_price = total_price
            checkout_instance.cart_token = cart_token
            checkout_instance.checkout_create_time = checkout_create_time
            checkout_instance.checkout_update_time = checkout_update_time
            checkout_instance.abandoned_checkout_url = abandoned_checkout_url
            checkout_instance.update_time = datetime.datetime.now()
            checkout_instance.save()
        return Response({"code": 200})


class CheckoutsDelete(APIView):

    def post(self, request, *args, **kwargs):
        print("------------ Checkouts Delete ------------:")
        # print(request.META, type(request.META))
        print(json.dumps(request.data))
        result = request.data
        if not result.get("id"):
            return Response({"code": 200})
        store = models.Store.objects.filter(url=request.META["HTTP_X_SHOPIFY_SHOP_DOMAIN"]).first()
        models.CheckoutEvent.objects.filter(store=store, checkout_id=request.data["id"]).update(status=2)
        return Response({"code": 200})


class CartsUpdate(APIView):
    def post(self, request, *args, **kwargs):
        print("------------ cart update ------------:")
        # print(request.META, type(request.META))
        print(json.dumps(request.data))
        store = models.Store.objects.filter(url=request.META["HTTP_X_SHOPIFY_SHOP_DOMAIN"]).first()
        store_id = store.id
        product_info = []
        for product in request.data["line_items"]:
            product_dict = {"product": product.get("product_id", ""), "sales": product.get("quantity", ""),
                            "price": product.get("variant_price", "")}
            product_info.append(product_dict)
        token = request.data.get("token", "")
        checkout_instance = models.CheckoutEvent.objects.filter(store=store, cart_token=token).first()
        if checkout_instance:
            checkout_instance.product_info = product_info
            checkout_instance.update_time = datetime.datetime.now()
            checkout_instance.save()
        return Response({"code": 200})


