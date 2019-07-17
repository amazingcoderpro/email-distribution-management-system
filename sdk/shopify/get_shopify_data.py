# -*-coding:utf-8-*-
import requests
from config import logger
import json
from config import SHOPIFY_CONFIG


class ProductsApi:
    def __init__(self, access_token, shop_uri):
        """
        :param client_id: api key
        :param access_token: api password
        :param shop_URI: 店铺uri
        :param scopes: 权限
        :param callback_uri: callback url
        :param code: 1 状态正确， 2 状态错误， -1 出现异常
        """
        self.client_id = SHOPIFY_CONFIG.get("client_id")
        self.access_token = access_token
        self.shop_uri = shop_uri
        self.scopes = SHOPIFY_CONFIG.get("scopes")
        self.callback_uri = SHOPIFY_CONFIG.get("callback_uri")
        self.version_url = "/admin/api/2019-04/"
        self.headers = {'Content-Type': 'application/json'}
    
    def get_shop_info(self):
        """
        获取用户信息
        :return:
        """
        shop_url = f"https://{self.client_id}:{self.access_token}@{self.shop_uri}{self.version_url}shop.json"
        try:
            result = requests.get(shop_url)
            if result.status_code == 200:
                logger.info("get shopify info is success")
                return {"code": 1, "msg": "", "data": json.loads(result.text)}
            else:
                logger.info("get shopify info is failed")
                return {"code": 2, "msg": json.loads(result.text).get("errors", ""), "data": ""}
        except Exception as e:
            logger.error("get shopify info is failed info={}".format(str(e)))
            return {"code": -1, "msg": str(e), "data": ""}

    def get_all_collections(self):
        """
        获取collections_id的product
        # 接口  /admin/api/#{api_version}/products.json?collection_id=841564295
        # 连接地址 https://help.shopify.com/en/api/reference/products/product
        :return:
        """
        shop_url = f"https://{self.client_id}:{self.access_token}@{self.shop_uri}{self.version_url}custom_collections.json"
        shop_url2 = f"https://{self.client_id}:{self.access_token}@{self.shop_uri}{self.version_url}smart_collections.json"
        try:
            result = requests.get(shop_url)
            result2 = requests.get(shop_url2)

            if result.status_code and result2.status_code in [200, 201]:
                logger.info("get shopify all collections info is success")
                res_dict = json.loads(result.text)
                res_dict.update(json.loads(result2.text))
                print(res_dict)
                return {"code": 1, "msg": "", "data": res_dict}
            else:
                logger.info("get shopify all collections info is failed")
                return {"code": 2, "msg": json.loads(result.text).get("errors", ""), "data": ""}
        except Exception as e:
            logger.error("get shopify all collections info is failed info={}".format(str(e)))
            return {"code": -1, "msg": str(e), "data": ""}

    @classmethod
    def parse_collections(cls, data):
        all_collections = []
        for col in data["custom_collections"] + data["smart_collections"]:
            if "home" in col.get("title", "").lower():
                continue
            all_collections.append(
                {
                    "uuid": col.get("id", ""),
                    "meta_title": col.get("title", ""),
                    "address": "/collections/" + col.get("title", "").lower().replace("'", "").replace(" ", "-"),
                    "meta_description": col.get("body_html", ""),
                }
            )
        return all_collections

    def get_collections_products(self, collection_id, limit=250, since_id=""):
        """
        获取collections_id的product
        # 接口  /admin/api/2019-04/smart_collections.json
                /admin/api/2019-04/custom_collections.json
        # 连接地址 https://help.shopify.com/en/api/reference/products/product
        :return:
        """
        if not since_id:
            products_url = f"https://{self.client_id}:{self.access_token}@{self.shop_uri}{self.version_url}products.json?collection_id={collection_id}&limit={limit}"
        if since_id:
            products_url = f"https://{self.client_id}:{self.access_token}@{self.shop_uri}{self.version_url}products.json?collection_id={collection_id}&limit={limit}&since_id={since_id}"
        try:
            result = requests.get(products_url)
            if result.status_code == 200:
                logger.info("get shopify all products is success")
                return {"code": 1, "msg": "", "data": json.loads(result.text)}
            else:
                logger.info("get shopify all products is failed")
                return {"code": 2, "msg": json.loads(result.text).get("errors", ""), "data": ""}
        except Exception as e:
            logger.error("get shopify all products is failed info={}".format(str(e)))
            return {"code": -1, "msg": str(e), "data": ""}

    def get_all_customers(self, limit=250, since_id=""):
        """
        获取collections_id的product
        # 接口  /admin/api/2019-04/smart_collections.json
                  /admin/api/2019-04/custom_collections.json
        # 连接地址 https://help.shopify.com/en/api/reference/orders/order#index-2019-07
        :return:
          """
        if not since_id:
            shop_url = f"https://{self.client_id}:{self.access_token}@{self.shop_uri}{self.version_url}customers.json?limit={limit}"
        if since_id:
            shop_url = f"https://{self.client_id}:{self.access_token}@{self.shop_uri}{self.version_url}customers.json?limit={limit}&since_id={since_id}"
        result = requests.get(shop_url)
        try:
            if result.status_code == 200:
                logger.info("get shopify all customers info is success")
                res_dict = json.loads(result.text)
                return {"code": 1, "msg": "", "data": res_dict}
            else:
                logger.info("get shopify all customers info is failed")
                return {"code": 2, "msg": json.loads(result.text).get("errors", ""), "data": ""}
        except Exception as e:
            logger.error("get shopify all customers info is failed info={}".format(str(e)))
            return {"code": -1, "msg": str(e), "data": ""}

    def get_all_orders(self, limit=20, since_id="", created_at_min="",  financial_status="paid"):
        """
       获取collections_id的product
       # 接口  /admin/api/201 -07/orders.json
       # 连接地址 https://help.shopify.com/en/api/reference/orders/order#index-2019-07
       :return:
        """
        if not since_id:
            order_url = f"https://{self.client_id}:{self.access_token}@{self.shop_uri}{self.version_url}orders.json" \
                f"?limit={limit}&financial_status={financial_status}"
        if since_id:
            order_url = f"https://{self.client_id}:{self.access_token}@{self.shop_uri}{self.version_url}orders.json" \
                f"?limit={limit}&financial_status={financial_status}&since_id={since_id}"
        try:
            result = requests.get(order_url)
            if result.status_code == 200:
                logger.info("get shopify orders is success")
                return {"code": 1, "msg": "", "data": json.loads(result.text)}
            else:
                logger.info("get shopify orders is failed")
                return {"code": 2, "msg": json.loads(result.text).get("errors", ""), "data": ""}
        except Exception as e:
            logger.error("get shopify orders is failed info={}".format(str(e)))
            return {"code": -1, "msg": str(e), "data": ""}

    def get_orders_id(self, order_id):
        """
       获取collections_id的product
       # 接口  /admin/api/201 -07/orders.json
       # 连接地址 https://help.shopify.com/en/api/reference/orders/order#index-2019-07
       :return:
        """

        order_url = f"https://{self.client_id}:{self.access_token}@{self.shop_uri}{self.version_url}orders.json?ids={order_id}"
        try:
            result = requests.get(order_url)
            if result.status_code == 200:
                logger.info("get shopify orders is success")
                return {"code": 1, "msg": "", "data": json.loads(result.text)}
            else:
                logger.info("get shopify orders is failed")
                return {"code": 2, "msg": json.loads(result.text).get("errors", ""), "data": ""}
        except Exception as e:
            logger.error("get shopify orders is failed info={}".format(str(e)))
            return {"code": -1, "msg": str(e), "data": ""}

    def get_customer_count(self):
        shop_url = f"https://{self.client_id}:{self.access_token}@{self.shop_uri}{self.version_url}customers/count.json"
        result = requests.get(shop_url)
        try:
            if result.status_code == 200:
                logger.info("get shopify all customers info is success")
                res_dict = json.loads(result.text)
                return {"code": 1, "msg": "", "data": res_dict}
            else:
                logger.info("get shopify all customers info is failed")
                return {"code": 2, "msg": json.loads(result.text).get("errors", ""), "data": ""}
        except Exception as e:
            logger.error("get shopify all customers info is failed info={}".format(str(e)))
            return {"code": -1, "msg": str(e), "data": ""}


if __name__ == '__main__':
    access_token = "d1063808be79897450ee5030e1c163ef"
    shop = "mrbeauti.myshopify.com"
    id = "3583116148816"
    shop_uri = "charrcter.myshopify.com"
    products_api = ProductsApi(access_token=access_token, shop_uri=shop_uri)
    print(products_api.get_all_customers(since_id="1714880053321"))
    # since_id="1487712747593"
    # products_api.get_all_orders()
    # products_api.get_customer_count()
    # products_api.get_orders_id(order_id="503834869833")
