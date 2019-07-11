from django.http import HttpResponseRedirect

from rest_framework.views import APIView
from app import models
from app.utils import random_code
from rest_framework.response import Response
from sdk.shopify.shopify_oauth_info import ShopifyBase

from sdk.shopify.get_shopify_data import ProductsApi
from sdk.shopify import shopify_oauth_info
from edm.settings import WEB_URL


class ShopifyCallback(APIView):
    """shopify 回调接口"""
    def get(self, request):
        code = request.query_params.get("code", None)
        shop = request.query_params.get("shop", None)
        hmac = request.query_params.get("hmac", None)
        if not code or not shop or not hmac:
            return HttpResponseRedirect(redirect_to="{}aut_state?state=2".format(WEB_URL))
        shop_name = shop.split(".")[0]
        result = ShopifyBase(shop).get_token(code)
        if result["code"] != 1:
            return HttpResponseRedirect(redirect_to="{}aut_state?state=2".format(WEB_URL))
        instance = models.Store.objects.filter(url=shop).first()
        if instance:
            instance.token = result["data"]
            instance.hmac = hmac
            instance.save()
            user_instance = models.User.objects.filter(id=instance.user_id).first()
            user_instance.is_active = 0
            user_instance.password = ""
            user_instance.save()
            email = user_instance.email
        else:
            store_data = {"name": shop_name, "url": shop, "token": result["data"], "hmac":hmac}
            instance = models.Store.objects.create(**store_data)
            info = ProductsApi(access_token=result["data"], shop_uri=shop).get_shop_info()
            instance.name = info["data"]["shop"]["name"]
            instance.sender = info["data"]["shop"]["name"]
            instance.timezone = info["data"]["shop"]["timezone"]
            instance.customer_shop = info["data"]["shop"]["domain"]
            instance.customer_email = info["data"]["shop"]["customer_email"]
            email = info["data"]["shop"]["email"]
            user_data = {"username": shop, "email": email, "is_active": 0, "code": random_code.create_random_code(6, True)}
            user_instance = models.User.objects.create(**user_data)
            instance.user = user_instance
            instance.email = email
            instance.save()
        return HttpResponseRedirect(redirect_to="{}shopfy_regist?shop={}&email={}&id={}".format(WEB_URL,shop, email, user_instance.id))


class ShopifyAuthView(APIView):
    """shopify 授权页面"""
    # permission_classes = (IsAuthenticated,)
    # authentication_classes = (JSONWebTokenAuthentication,)

    def get(self, request, *args, **kwargs):
        # 获取get请求的参数
        shop_uri = request.query_params.get("shop", None)
        if not shop_uri:
            return Response({"message": "no shop"})
        # shop_uri = shop_name + ".myshopify.com"
        permission_url = shopify_oauth_info.ShopifyBase(shop_uri).ask_permission(shop_uri)
        return HttpResponseRedirect(redirect_to=permission_url)