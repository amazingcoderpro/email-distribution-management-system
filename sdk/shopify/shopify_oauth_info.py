# -*-coding:utf-8-*-
import requests
from urllib import parse
import json
from config import logger
from config import SHOPIFY_CONFIG


class ShopifyBase():
    """
    shopify授权的api
    """
    def __init__(self, shop_uri):
        """
        :param code: 1 状态正确， 2 状态错误， -1 出现异常
        :param shop_name: 店铺名称
        """
        self.client_id = SHOPIFY_CONFIG.get("client_id")
        self.client_secret = SHOPIFY_CONFIG.get("client_secret")
        self.redirect_uri = SHOPIFY_CONFIG.get("redirect_uri")
        self.shop_uri = shop_uri
        self.scopes = SHOPIFY_CONFIG.get("scopes")
        self.headers = {'Content-Type': 'application/json'}

    def ask_permission(self, nonce):
        """
        获取授权页面
        :param nonce: 标注
        :param redirect_uri: callback url
        :param scopes: 权限
        :return: status_code, text
        """
        redirect_uri = parse.quote(self.redirect_uri)
        scopes_info = ",".join(self.scopes)
        permission_url = f"https://{self.shop_uri}/admin/oauth/authorize" \
                         f"?client_id={self.client_id}" \
                         f"&scope={scopes_info}" \
                         f"&redirect_uri={redirect_uri}" \
                         f"&state={nonce}&grant_options[]="
        return permission_url

    def get_token(self, code):
        """
        获取shopify的永久性token
        :param client_secret:
        :param code:
        :return:
        """
        display = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code
        }
        url = f"https://{self.shop_uri}/admin/oauth/access_token"
        logger.info("url={}, display={}, shop_uri={}".format(url, display, self.shop_uri))
        try:
            result = requests.post(url, json.dumps(display), headers=self.headers)
            if result.status_code == 200:
                logger.info("get shopify token is successed, shopname={}".format(self.shop_uri))
                print(result.text)
                return {"code": 1, "msg": "", "data": json.loads(result.text).get("access_token")}
            else:
                logger.error("get shopify token is failed")
                return {"code": 2, "msg": "oauth failed", "data": ""}
        except Exception as e:
            logger.error("get shopify token is exception {}".format(str(e)))
            return {"code": -1, "msg": str(e), "data": ""}


if __name__ == '__main__':
    # ShopifyBase = ShopifyBase(shop_uri="ordersea.myshopify.com")

    # shopify 授权获取的url
    ShopifyBase = ShopifyBase(shop_uri="tiptopfree.myshopify.com")
    # ShopifyBase.get_token(code="d550a36479c1fd7daff5aa217a82dd07")
    url = ShopifyBase.ask_permission(nonce="tiptopfree")

    print(url)

    "https://partners.shopify.com/admin/oauth/authorize?client_id=14afd1038ae052d9f13604af3e5e3ce3&scope=read_content,write_content,read_themes,write_themes,read_products,write_products,read_product_listings,read_customers,write_customers,read_orders,write_orders,read_shipping,write_draft_orders,read_inventory,write_inventory,read_shopify_payments_payouts,read_draft_orders,read_locations,read_script_tags,write_script_tags,read_fulfillments,write_shipping,read_analytics,read_checkouts,write_resource_feedbacks,write_checkouts,read_reports,write_reports,read_price_rules,write_price_rules,read_marketing_events,write_marketing_events,read_resource_feedbacks,read_shopify_payments_disputes,write_fulfillments&redirect_uri=https%3A//smartsend.seamarketings.com/api/v1/auth/shopify/callback/&state=partners&grant_options[]="
