# -*- coding: utf-8 -*-
# Created by: Leemon7
# Created on: 2019/8/12
# Function:
import pymongo

from config import logger, MONGO_CONFIG, MYSQL_CONFIG
from task.db_util import MongoDBUtil, DBUtil


class ProductRecommend(MongoDBUtil, DBUtil):
    def __init__(self, mongo_config=MONGO_CONFIG, db_config=MYSQL_CONFIG):
        MongoDBUtil.__init__(self, mongo_config)
        DBUtil.__init__(self, **db_config)
        self.format_str = """<tr><td style="padding: 10px 0px;width: 50%;text-align: left;border-bottom: 1px solid #E8E8E8;margin: 10px 0;"><div style="width: calc(35% - 20px);display: inline-block;"><img src="{image_src}" style="width: 100%;"/></div><div style="width: calc(60% - 20px);display: inline-block;vertical-align: top;margin-left: 20px;line-height: 26px;"><div style="display: -webkit-box !important;overflow: hidden;text-overflow: ellipsis;word-break: break-all;-webkit-box-orient: vertical;-webkit-line-clamp: 2;"><a href="{product_url}" target="_blank" style="color: #000;text-decoration: none;">{title}</a></div><div style="background: #000;color: #fff;padding: 5px;display: inline-block;line-height: 10px;">Falsh Sale</div><div style="color: #666;width: 100%;">Color:{color}</div><div style="color: #666;width: 100%;">Size:{size}</div></div></td><td valign="top" style="padding: 10px 0px;border-bottom: 1px solid #E8E8E8;line-height: 26px;"><div>${price}</div><div style="text-decoration: line-through;color: #666;">${compare_at_price}</div></td><td valign="top" style="padding: 10px 0px;border-bottom: 1px solid #E8E8E8;">{quantity}</td><td valign="top" style="padding: 10px 0px;border-bottom: 1px solid #E8E8E8;">${line_price}</td></tr>"""

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
            product_str += self.format_str.format(**product)
        new_html = new_html.replace('<span style="display: none;">specialProduct</span>', product_str)
        return new_html

    def generate_snippets(self, product_list):
        """
        生成需要替换的snippet片段
        :param product_list: 产品信息列表
        :return: dict
        """
        store_info = product_list.pop(0)
        shop_name, firstname = store_info["shop_name"], store_info["firstname"]
        product_str = ""
        abandoned_checkout_url = "javascript:;"
        for product in product_list:
            abandoned_checkout_url = product["abandoned_checkout_url"]
            product_str += self.format_str.format(**product)
        snippet_dict = {"shop_name": shop_name,
                        "firstname": firstname,
                        "cart_products": product_str,
                        "abandoned_checkout_url": abandoned_checkout_url}
        return [{"name": name, "value": value} for name, value in snippet_dict.items()]

    def get_card_product_mongo(self, customer_email, store_name, length=3):
        """
        获取该用户购物车中的产品信息
        :param customer_email: 用户邮箱
        :param store_name: 店铺名称
        :param length: 返回结果产品数，默认为不超过6的产品
        :return: 产品信息列表
        """
        products = []
        try:
            # mdb = MongoDBUtil(mongo_config=self.mongo_config)
            db = MongoDBUtil.get_instance(self)
            # 通过ID获取firstname和shop_name
            res = db.shopify_customer.find_one({"email": customer_email, "site_name": store_name}, {"_id":0, "first_name": 1})
            firstname = res["first_name"]
            products.append({"shop_name": store_name, "firstname": firstname})
            # 获取购物车产品ID
            cart_products = db.shopify_unpaid_order.find({"customer.email": customer_email, "site_name": store_name}, {"_id":0, "line_items": 1, "abandoned_checkout_url": 1},
                                                         limit=1, sort=[("updated_at", pymongo.DESCENDING)])
            product_dict = {}
            for cart in cart_products:
                abandoned_checkout_url = cart["abandoned_checkout_url"]
                for pro in cart["line_items"]:
                    variant_title = pro["variant_title"]
                    color, size = variant_title.split("/") if "/" in variant_title else (variant_title, "")
                    product_dict.update({pro["product_id"]: {"title": pro["title"], "color": color.strip(), "size": size.strip(), "compare_at_price": pro["compare_at_price"],
                                                            "line_price": pro["line_price"], "price": pro["price"], "quantity": pro["quantity"],
                                                             "abandoned_checkout_url": abandoned_checkout_url}})
            if not product_dict:
                return products
            # 获取这些产品的信息
            product_infos= db.shopify_product.find({"id": {"$in": list(product_dict.keys())}},
                {"_id":0, "id":1, "handle":1, "site_name":1, "image.src":1, "title":1, "variants":1})
            for product in product_infos:
                if len(products) >= length+1:
                    break
                if product["id"] in product_dict:
                    product_dict[product["id"]].update({"product_url": "https://{}.myshopify.com/products/{}".format(product["site_name"], product["handle"]),
                                 "image_src": product["image"]["src"]})
            products += list(product_dict.values())
            return products
        except Exception as e:
            logger.exception("adapt_sign_up_time_mongo catch exception={}".format(e))
            return products
        finally:
            MongoDBUtil.close(self)

    # def get_template_by_condition(self):
    #     """
    #     获取需要符合条件的模板信息
    #     :return:
    #     """
    #     customers = []
    #     try:
    #         conn = DBUtil.get_instance(self)
    #         cursor = conn.cursor() if conn else None
    #         if not cursor:
    #             return customers
    #
    #
    #         cursor.execute("""select `uuid` from `customer` where store_id=%s""",)
    #
    #         res = cursor.fetchall()
    #         for uuid in res:
    #             customers.append(uuid[0])
    #         return customers
    #     except Exception as e:
    #         logger.exception("adapt_sign_up_time e={}".format(e))
    #         return customers
    #     finally:
    #         cursor.close() if cursor else 0
    #         conn.close() if conn else 0


if __name__ == '__main__':
    pr = ProductRecommend()
    # print(pr.get_card_product_mongo(326597345317))
    html = """
    Dear {firstname}:
        welcome to my shop {shop_name}!
        <span style="display: none;">specialProduct</span>
    """
    print(pr.generate_new_html_with_product_block(pr.get_card_product_mongo(326597345317), html=html))