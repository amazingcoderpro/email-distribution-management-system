# -*-coding:utf-8-*-
import requests
from config import logger
import json
from config import SHOPIFY_CONFIG
import six
# from helpers import get_hmac


class ProductsApi:
    def __init__(self):
        """
        :param client_id: api key
        :param access_token: api password
        :param shop_URI: 店铺uri
        :param scopes: 权限
        :param callback_uri: callback url
        :param code: 1 状态正确， 2 状态错误， -1 出现异常
        """
        self.client_id = SHOPIFY_CONFIG.get("client_id")
        self.client_secret = SHOPIFY_CONFIG.get("client_secret")
        self.access_token = access_token
        self.shop_uri = shop_uri
        self.scopes = SHOPIFY_CONFIG.get("scopes")
        self.callback_uri = SHOPIFY_CONFIG.get("callback_uri")
        self.version_url = "/admin/api/2019-04/"
        # self.headers = {'Content-Type': 'application/json',
        #                 "X-Shopify-Topic": "orders/create",
        #                 "X-Shopify-Hmac-Sha256": "590557930c793519038b795fbb0b157a8dbf40f42ecb29e58436c1dce0423a75",
        #                 "X-Shopify-Shop-Domain": shop_uri,
        #                 "X-Shopify-API-Version": "2019-04"}

    def create_webhook_order(self, topic=None, domain=None, data=None, headers=None, send_hmac=True):
        headers = {} if headers is None else headers
        headers['HTTP_X_SHOPIFY_TEST'] = 'true'
        headers['HTTP_X_SHOPIFY_SHOP_DOMAIN'] = domain

        # Add optional headers.
        if topic:
            headers['HTTP_X_SHOPIFY_TOPIC'] = topic
        if send_hmac:
            headers['HTTP_X_SHOPIFY_HMAC_SHA256'] = six.text_type(
                get_hmac(six.b(data), self.client_secret))

        shop_webhook_url = f"https://{self.client_id}:{self.access_token}@{self.shop_uri}{self.version_url}webhooks.json"
        body ={
                "webhook": {
                 "topic": "orders/create",
                 "address": "https://whatever.hostname.com/",
                 "format": "json"
                }}
        try:
            result = requests.post(shop_webhook_url, json.dumps(body), self.headers)
            if result.status_code == 200:
                logger.info("get shopify all collections info is success")
                res_dict = json.loads(result.text)
                return {"code": 1, "msg": "", "data": res_dict}
            else:
                logger.info("get shopify all collections info is failed")
                return {"code": 2, "msg": json.loads(result.text).get("errors", ""), "data": ""}
        except Exception as e:
            logger.error("get shopify all collections info is failed info={}".format(str(e)))
            return {"code": -1, "msg": str(e), "data": ""}


if __name__ == '__main__':
    access_token = "d1063808be79897450ee5030e1c163ef"
    callback_uri = "http://www.orderplus.com/index.html"
    id = "3583116148816"
    shop_uri = "charrcter.myshopify.com"
    products_api = ProductsApi()
    products_api.create_webhook_order()
