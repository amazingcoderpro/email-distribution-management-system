# -*-coding:utf-8-*-
import requests
from config import logger
import json
from config import SHOPIFY_CONFIG
import six
from sdk.shopify.helpers import get_hmac


class ProductsApi:
    def __init__(self, shop_uri, access_token):
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
        self.version_url = "/admin/api/2019-07/"
        self.headers = {'Content-Type': 'application/json',
                        'X-Shopify-API-Version': '2019-07'}

    def create_webhook(self, topic, address, send_hmac=True):
        data = {
            "webhook": {
                "topic": topic,
                "address": address,
                "format": "json"
            }}
        if self.shop_uri:
            self.headers['X_Shopify_Shop_Domain'] = self.shop_uri
            self.headers['X_Shopify_Shop_Id'] = str(3)
        if topic:
            self.headers['X_Shopify_Topic'] = topic
        if send_hmac:
            self.headers['X_Shopify_Hmac_Sha256'] = six.text_type(get_hmac(six.b(json.dumps(data)), self.client_secret))

        shop_webhook_url = f"https://{self.client_id}:{self.access_token}@{self.shop_uri}{self.version_url}webhooks.json"

        try:
            result = requests.post(shop_webhook_url, data=json.dumps(data), headers=self.headers)

            if result.status_code in [200, 201]:
                logger.info("create shopify webhook info is success")
                res_dict = json.loads(result.text)
                print(res_dict)
                return {"code": 1, "msg": "", "data": res_dict}
            else:
                logger.info("create shopify webhook info is failed")
                return {"code": 2, "msg": json.loads(result.text).get("errors", ""), "data": ""}
        except Exception as e:
            logger.error("create shopify webhook info is failed info={}".format(str(e)))
            print(json.loads(result.text))
            return {"code": -1, "msg": str(e), "data": ""}

    def get_all_webhook(self):
        shop_webhook_url = f"https://{self.client_id}:{self.access_token}@{self.shop_uri}{self.version_url}webhooks.json"
        try:
            result = requests.get(shop_webhook_url)
            if result.status_code in [200, 201]:
                logger.info("get shopify webhook info is success")
                res_dict = json.loads(result.text)
                print(res_dict)
                return {"code": 1, "msg": "", "data": res_dict}
            else:
                logger.info("get shopify webhook info is failed")
                return {"code": 2, "msg": json.loads(result.text).get("errors", ""), "data": ""}
        except Exception as e:
            logger.error("get shopify webhook info is failed info={}".format(str(e)))
            return {"code": -1, "msg": str(e), "data": ""}

    def delete_webhook(self, webhook_id):
        shop_webhook_url = f"https://{self.client_id}:{self.access_token}@{self.shop_uri}{self.version_url}webhooks/{webhook_id}.json"
        try:
            result = requests.delete(shop_webhook_url)
            if result.status_code in [200, 201]:
                logger.info("delete shopify webhook info is success")
                res_dict = json.loads(result.text)
                print(res_dict)
                return {"code": 1, "msg": "", "data": res_dict}
            else:
                logger.info("delete shopify webhook info is failed")
                print(json.loads(result.text).get("errors", ""))
                return {"code": 2, "msg": json.loads(result.text).get("errors", ""), "data": ""}
        except Exception as e:
            logger.error("delete shopify webhook info is failed info={}".format(str(e)))
            return {"code": -1, "msg": str(e), "data": ""}


if __name__ == '__main__':
    access_token = "d1063808be79897450ee5030e1c163ef"
    id = "3583116148816"
    shop_uri = "tiptopfree.myshopify.com"
    address = "https://smartsend.seamarketings.com/api/v1/webhook/cart/update/"
    topic = "carts/update"
    products_api = ProductsApi(shop_uri=shop_uri, access_token=access_token)
    # 創建webhook
    products_api.create_webhook(topic=topic, address=address)
    # 查詢所有的webhook
    products_api.get_all_webhook()
    # 刪除對應ID的webhook
    # products_api.delete_webhook(webhook_id="504168251465")
    # 503916396617, 503834705993


