# -*- coding: utf-8 -*-
# Created by: Leemon7
# Created on: 2019/8/12
# Function:
import copy

import pymongo
import pymysql
import json
from config import logger, MONGO_CONFIG, MYSQL_CONFIG
from task.db_util import MongoDBUtil, DBUtil


class ProductRecommend:
    def __init__(self):
        self.cart_str = """<tr><td style="padding: 10px 0px;width: 50%;text-align: left;border-bottom: 1px solid #E8E8E8;margin: 10px 0;"><div style="width: 35%;display: inline-block;"><a href="{product_url}" target="_blank"><img src="{image_src}" style="width: 100%;"/></a></div><div style="width: 58%;display: inline-block;vertical-align: top;margin-left: 20px;line-height: 26px;"><div style="display: -webkit-box !important;overflow: hidden;text-overflow: ellipsis;word-break: break-all;-webkit-box-orient: vertical;-webkit-line-clamp: 2;"><a href="{product_url}" target="_blank" style="color: #000;text-decoration: none;">{title}</a></div><div style="color: #666;width: 100%;">Color:{color}</div><div style="color: #666;width: 100%;">Size:{size}</div></div></td><td valign="top" style="padding: 10px 0px;border-bottom: 1px solid #E8E8E8;line-height: 26px;"><div>{price}</div><div style="text-decoration: line-through;color: #666;">{compare_at_price}</div></td><td valign="top" style="padding: 10px 0px;border-bottom: 1px solid #E8E8E8;">{quantity}</td><td valign="top" style="padding: 10px 0px;border-bottom: 1px solid #E8E8E8;">{line_price}</td></tr>"""
        self.top_str = """<div style="width:46%;margin:10px;display:inline-block;vertical-align: top;"><a href="{url}"><img src="{image_url}" style="width:100%;"/></a><h3 style="font-weight:700;white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 14px;">{name}</h3></div>"""

    def generate_new_html_with_product_block(self, product_list, html):
        """
        生成HTML中产品信息块，
        :param product_list: 产品信息列表
        :param html: 模板字符串
        :return: 替换后的html字符串
        """
        new_html = html.format(**product_list.pop(0))
        if not product_list:
            logger.warning("no product list")
            return new_html
        product_str = ""
        for product in product_list:
            product_str += self.cart_str.format(**product)
        new_html = new_html.replace('<span style="display: none;">specialProduct</span>', product_str)
        return new_html

    def generate_snippets(self, cart_product_list, top_product_list, flow=True):
        """
        生成需要替换的snippet片段
        :param product_list: 购物车产品信息列表
        :param product_list: top产品信息列表
        :return: snippet_list
        """
        store_info = cart_product_list.pop(0)
        shop_name, firstname = store_info["shop_name"], store_info["firstname"]
        # 拼接购物车产品html
        cart_product_str = ""
        abandoned_checkout_url = "javascript:;"
        for product in cart_product_list:
            logger.info("cart product info is %s" % str(product))
            abandoned_checkout_url = product["abandoned_checkout_url"]
            cart_product_str += self.cart_str.format(**product)
        # 拼接top产品html
        top_product_str = ""
        product_title = {"products_title": "hide"}
        if top_product_list:
            product_title = top_product_list.pop(-1)
            for product in top_product_list:
                top_product_str += self.top_str.format(**product)

        snippet_dict = {"shop_name": shop_name,
                        "firstname": firstname,
                        "domain": store_info["domain"],
                        "service_email": store_info["service_email"],
                        "about_us_url": store_info["about_us_url"],
                        "store_url": store_info["store_url"],
                        "privacy_policy_url": store_info["privacy_policy_url"],
                        "help_center_url": store_info["help_center_url"],
                        "cart_products": cart_product_str,
                        "abandoned_checkout_url": abandoned_checkout_url,
                        "top_products": top_product_str}
        snippet_dict.update(product_title)
        if not flow:
            return snippet_dict
        return [{"name": name, "value": value} for name, value in snippet_dict.items()]

    def get_card_product_mongo(self, customer_email, store_name, flow_title, template_id, domain, service_email, length=3, utm_medium="flow"):
        """
        获取该用户购物车中的产品信息
        :param customer_email: 用户邮箱
        :param store_name: 店铺名称
        :param length: 返回结果产品数，默认为不超过6的产品
        :return: 产品信息列表
        """
        products = []
        try:
            mdb = MongoDBUtil(mongo_config=MONGO_CONFIG)
            db = mdb.get_instance()
            # 通过store_name获取money_in_emails_format
            money_format = db.shopify_shop_info.find_one({"site_name": store_name}, {"_id": 0, "money_in_emails_format": 1, "name": 1})
            try:
                money_in_emails_format = money_format["money_in_emails_format"].split("{{")[0][-1]
            except Exception as e:
                logger.exception("get store's(store_name: %s) money_in_emails_format exception, use default '$'." % store_name)
                money_in_emails_format = "$"
            # 通过ID获取firstname和shop_name
            firstname = ""
            if customer_email:
                res = db.shopify_customer.find_one({"email": customer_email, "site_name": store_name},
                                                   {"_id": 0, "first_name": 1})
                firstname = res.get("first_name", "")
            products.append({"shop_name": money_format["name"],
                             "firstname": firstname,
                             "domain": domain,
                             "service_email": service_email,
                             "about_us_url": "https://{}/pages/about-us".format(
                                 domain) + f"?utm_source=smartsend&utm_medium={utm_medium}&utm_campaign={flow_title}&utm_term={template_id}",
                             "store_url": "https://{}".format(
                                 domain) + f"?utm_source=smartsend&utm_medium={utm_medium}&utm_campaign={flow_title}&utm_term={template_id}",
                             "privacy_policy_url": "https://{}/pages/privacy-policy".format(
                                 domain) + f"?utm_source=smartsend&utm_medium={utm_medium}&utm_campaign={flow_title}&utm_term={template_id}",
                             "help_center_url": "https://{}/pages/faq".format(
                                 domain) + f"?utm_source=smartsend&utm_medium={utm_medium}&utm_campaign={flow_title}&utm_term={template_id}"})
            # 获取购物车产品ID
            if length == 0:
                return products
            cart_products = db.shopify_unpaid_order.find({"customer.email": customer_email, "site_name": store_name},
                                                         {"_id": 0, "line_items": 1, "abandoned_checkout_url": 1},
                                                         limit=1, sort=[("updated_at", pymongo.DESCENDING)])
            product_dict = {}
            for cart in cart_products:
                abandoned_checkout_url = cart[
                                             "abandoned_checkout_url"] + f"&utm_source=smartsend&utm_medium=flow&utm_campaign={flow_title}&utm_term={template_id}"
                for pro in cart["line_items"]:
                    variant_title = pro["variant_title"]
                    color, size = variant_title.split("/") if "/" in variant_title else (variant_title, "")
                    product_dict.update({pro["product_id"]: {"title": pro.get("title", ""), "color": color.strip(),
                                                             "size": size.strip(),
                                                             "compare_at_price": money_in_emails_format + pro.get("compare_at_price", 0),
                                                             "line_price": money_in_emails_format + pro.get("line_price", 0),
                                                             "price": money_in_emails_format+pro.get("price", 0),
                                                             "quantity": pro.get("quantity"),
                                                             "abandoned_checkout_url": abandoned_checkout_url}})
            if not product_dict:
                return products
            # 获取这些产品的信息
            product_infos = db.shopify_product.find({"id": {"$in": list(product_dict.keys())}},
                                                    {"_id": 0, "id": 1, "handle": 1, "site_name": 1, "image.src": 1,
                                                     "title": 1, "variants": 1})
            for product in product_infos:
                if product["id"] in product_dict:
                    product_uuid_template_id = "{}_{}".format(product["id"], template_id)
                    product_url = "https://{}.myshopify.com/products/{}".format(product["site_name"],
                                                                                product["handle"]) + \
                                  f"?utm_source=smartsend&utm_medium=flow&utm_campaign={flow_title}&utm_term={product_uuid_template_id}"
                    product_dict[product["id"]].update(
                        {"product_url": product_url, "image_src": product["image"]["src"]})

            # 过滤掉product_info没有product_url 和 image_src的item,
            # 即过滤掉产品表中查找不到购物车产品id的产品
            product_dict_copy = copy.deepcopy(product_dict)
            for p_id, val in product_dict_copy.items():
                if val.get("product_url", None) is None or val.get("image_src", None) is None:
                    del product_dict[p_id]

            products += list(product_dict.values())
            if len(product_dict) > length:
                products = products[0:length+1]
            return products
        except Exception as e:
            logger.exception("get_card_product_mongo catch exception={}".format(e))
            return products
        finally:
            mdb.close()

    def get_top_product_by_condition(self, condition, store_id, flow_title, template_id, length=4, utm_medium="flow"):
        """
        获取店铺下top_products信息
        :param condition: 条件字符串
        :param store_id: 店铺ID
        :param flow_title: flow的标题
        :param template_id: 模板ID
        :param length: 返回的最大产品数
        :return: 符合条件的偶数个产品信息列表
        """
        products_list = []
        try:
            conn = DBUtil(**MYSQL_CONFIG).get_instance()
            cursor = conn.cursor(pymysql.cursors.DictCursor) if conn else None
            if not cursor:
                return products_list
            sql_str = "select `{condition}` from top_product where store_id={store_id}".format(condition=condition, store_id=store_id)
            cursor.execute(sql_str)
            res = cursor.fetchone()
            # 对URL进行构建并控制返回数量

            if res:
                products = json.loads(res.get(condition, ""))
                if products:
                    products = products[0:4]
                    for product in products:
                        product_uuid_template_id = "{}_{}".format(product["uuid"], template_id)
                        product["url"] += f"?utm_source=smartsend&utm_medium={utm_medium}&utm_campaign={flow_title}&utm_term={product_uuid_template_id}"
                        products_list.append(product)
                    if len(products_list) % 2 == 1:
                        products_list.pop(-1)
            if len(products_list):
                products_title = ""
            else:
                products_title = "hide"
            products_list.append({"products_title": products_title})
            return products_list
        except Exception as e:
            logger.exception("get_top_product_by_condition e={}".format(e))
            return products
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0


if __name__ == '__main__':
    pr = ProductRecommend()
    # print(pr.get_card_product_mongo(326597345317))
    # html = """
    # Dear {firstname}:
    #     welcome to my shop {shop_name}!
    #     <span style="display: none;">specialProduct</span>
    # """
    # print(pr.generate_new_html_with_product_block(pr.get_card_product_mongo(326597345317), html=html))
    pr.get_card_product_mongo(customer_email="twoben.meng@orderplus.com", store_name="charrcter", flow_title="2019-08-15T18:08:45+08:00", template_id=20, domain="charrcter.myshopify.com", length=3)
    # pr.get_top_product_by_condition("top_fifteen", 3, "cd", 3)
