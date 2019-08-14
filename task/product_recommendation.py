# -*- coding: utf-8 -*-
# Created by: Leemon7
# Created on: 2019/8/12
# Function:
from config import logger, MONGO_CONFIG, MYSQL_CONFIG
from task.db_util import MongoDBUtil, DBUtil


class ProductRecommend(MongoDBUtil, DBUtil):
    def __init__(self, mongo_config=MONGO_CONFIG, db_config=MYSQL_CONFIG):
        MongoDBUtil.__init__(self, mongo_config)
        DBUtil.__init__(self, **db_config)
        self.format_str = """
        <div style="width: calc(50% - 24px);margin: 10px;vertical-align: top;border: 1px solid rgb(204, 204, 204);display: inline-block;">
            <a href="{product_url}">
                <img src="{image_src}" style="width: 100%;">
            </a>
            <h3 style="font-weight: 700;">{name}</h3>
            <h3>{price}</h3>
        </div>
        """

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

    def get_card_product_mongo(self, customer_id, length=6):
        """
        获取该用户购物车中的产品信息
        :param customer_id: 用户ID
        :param length: 返回结果产品数，默认为不超过6的产品
        :return: 产品信息列表
        """
        products = []
        try:
            # mdb = MongoDBUtil(mongo_config=self.mongo_config)
            db = MongoDBUtil.get_instance(self)
            # 通过ID获取firstname和shop_name
            res = db.shopify_customer.find_one({"id": customer_id}, {"_id":0, "site_name": 1, "first_name": 1})
            shop_name, firstname = res["site_name"], res["first_name"]
            products.append({"shop_name": shop_name, "firstname": firstname})
            # 获取购物车产品ID
            cart_products = db.shopify_unpaid_order.find({"customer.id": customer_id}, {"_id":0, "line_items": 1, "customer.first_name": 1})
            product_ids = []
            for cart in cart_products:
                for pro in cart["line_items"]:
                    product_ids.append(pro["product_id"])
            # 获取这些产品的信息
            product_infos= db.shopify_product.find({"id": {"$in": product_ids}}, {"_id":0, "id":1, "handle":1, "site_name":1, "image.src":1, "title":1, "variants":1})
            for product in product_infos:
                if len(products) >= 7:
                    break
                products.append({"product_url": "https://{}.myshopify.com/products/{}".format(product["site_name"], product["handle"]),
                                 "image_src": product["image"]["src"], "name": product["title"], "price": product["variants"][0]["price"]})
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