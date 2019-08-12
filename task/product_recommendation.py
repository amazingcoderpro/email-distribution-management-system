# -*- coding: utf-8 -*-
# Created by: Leemon7
# Created on: 2019/8/12
# Function:
from config import logger
from task.db_util import MongoDBUtil, DBUtil


class ProductRecommend(MongoDBUtil, DBUtil):
    def __init__(self):
        super(ProductRecommend, self).__init__(MongoDBUtil)
        super(ProductRecommend, self).__init__(DBUtil)

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
            # 获取购物车产品信息
            customers_res = db.shopify_customer.find({}, {"_id": 0, "id": 1})
            for cus in customers_res:
                products.append(cus["id"])
            return products
        except Exception as e:
            logger.exception("adapt_sign_up_time_mongo catch exception={}".format(e))
            return products
        finally:
            MongoDBUtil.close(self)

    def get_template_by_condition(self):
        """
        获取需要符合条件的模板信息
        :return:
        """
        customers = []
        try:
            conn = DBUtil.get_instance(self)
            cursor = conn.cursor() if conn else None
            if not cursor:
                return customers


            cursor.execute("""select `uuid` from `customer` where store_id=%s""",)

            res = cursor.fetchall()
            for uuid in res:
                customers.append(uuid[0])
            return customers
        except Exception as e:
            logger.exception("adapt_sign_up_time e={}".format(e))
            return customers
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0