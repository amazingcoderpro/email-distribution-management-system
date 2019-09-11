#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Created by charles on 2019-07-19
# Function:
import time

import pymysql
import datetime
import json
from dateutil.relativedelta import relativedelta
from pytz import timezone

from config import logger, MONGO_CONFIG, MYSQL_CONFIG, ENABLE_SUBSCRIBE
from task.db_util import DBUtil, MongoDBUtil
from sdk.ems import ems_api
from task.product_recommendation import ProductRecommend


def count_time(func):
    def wrapper(*args, **kwargs):
        tn = datetime.datetime.now()
        logger.info("----start call {} at {}".format(func.__name__, tn))
        ret = func(*args, **kwargs)
        logger.info("----call {} end, spend time={}".format(
            func.__name__, round((datetime.datetime.now()-tn).microseconds/1000, 6)
        ))
        return ret
    return wrapper

class AnalyzeCondition:
    def __init__(self, mysql_config, mongo_config):
        self.db_host = mysql_config.get("host", "")
        self.db_port = mysql_config.get("port", 3306)
        self.db_name = mysql_config.get("db", "")
        self.db_user = mysql_config.get("user", "")
        self.db_password = mysql_config.get("password", "")
        self.condition_dict = {"Customer sign up time": "adapt_sign_up_time",  # 已完成
                              "Customer last order created time": "adapt_last_order_created_time",  # 已完成
                              "Customer last opened email time": "adapt_last_opened_email_time",  # 已完成
                              "Customer last click email time": "adapt_last_click_email_time",  # 已完成
                              "Customer placed order": "adapt_placed_order",  # 已完成
                              "Customer paid order": "adapt_paid_order",  # 已完成
                              "Customer order number": "adapt_all_order",  # 已完成
                              "Customer opened email": "adapt_opened_email",  # 已完成
                              "Customer clicked email": "adapt_clicked_email",  # 已完成
                              "Customer last order status": "adapt_last_order_status",  # 已完成
                              "Customer who accept marketing": "adapt_is_accept_marketing",  # 已完成
                              "Customer Email": "adapt_customer_email",  # 已完成
                              "Customer total order payment amount": "adapt_total_order_amount",  # 已完成
                              "Customer subscribe time": "adapt_subscribe_time", # 只实现了mongo方法
                            }
        self.note_dict = {"customer makes a purchase": self.filter_purchase_customer,  # 已完成
                          "customer received an email from this campaign in the last 7 days": self.filter_received_customer,  # 已完成
                        }
        self.mongo_config = mongo_config

    def common_adapter(self, condition, store_id, relations):
        from_type, store_name = self.get_store_source(store_id)
        function_name = self.condition_dict.get(condition, "")
        if not function_name:
            logger.warning("Condition have no adapter, condition name={}".format(condition))
            return None

        if from_type == 0:
            # 来自opstores
            function_name += "_mongo"

        adapter = getattr(self, function_name, None)
        if not adapter:
            logger.warning("Adapter have not implement, condition name={}, adapter name={}".format(condition, function_name))
            return None

        if from_type == 0:
            return adapter(store_id, relations, store_name)
        else:
            return adapter(store_id, relations)

    def adapt_subscribe_time_mongo(self, store_id, relations, store_name):
        """
        适配出订阅时间所有符合条件的customer
        :param store_id:
        :param relations:
        :param store_name:
        :return:
        """
        min_time, max_time = self.date_relation_convert_mongo(relations[0]["relation"], relations[0]["values"],
                                                              store_name,
                                                              relations[0].get("unit", "days"))
        customers = []
        try:
            mdb = MongoDBUtil(mongo_config=self.mongo_config)
            db = mdb.get_instance()
            # TODO
            if min_time and max_time:
                filter_dict = {"$lte": max_time, "$gte": min_time}
            elif min_time:
                filter_dict = {"$gte": min_time}
            elif max_time:
                filter_dict = {"$lte": max_time}
            else:
                filter_dict = {"$lte": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")}
            customers_res = db.shopify_customer.find({"site_name": store_name, "accepts_marketing_updated_at": filter_dict},
                                                     {"_id": 0, "id": 1})
            for cus in customers_res:
                customers.append(cus["id"])
            return customers
        except Exception as e:
            logger.exception("adapt_subscribe_time_mongo catch exception={}".format(e))
            return customers
        finally:
            mdb.close()

    # def unpaid_order_customers_mongo(self, store_name, min_time=None, max_time=None):
    #     """
    #     获取未支付的customers
    #     :param store_id: 店铺ID
    #     :param store_name: 店铺名称
    #     :param min_time:
    #     :param max_time:
    #     :return: 符合条件的id{customer_id:[checkout_id1,checkout_id2], }
    #     """
    #     logger.info("unpaid_order_customers_mongo start")
    #     result_dict = {}
    #     try:
    #         mdb = MongoDBUtil(mongo_config=self.mongo_config)
    #         db = mdb.get_instance()
    #         if min_time and max_time:
    #             filter_dict = {"$lte": max_time, "$gte": min_time}
    #         elif min_time:
    #             filter_dict = {"$gte": min_time}
    #         elif max_time:
    #             filter_dict = {"$lte": max_time}
    #         else:
    #             filter_dict = {"$lte": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")}
    #         unpaid_order = db.shopify_unpaid_order.find({"site_name": store_name, "updated_at": filter_dict, "customer.email": {"$exists": 1}}, {"_id": 0, "id": 1, "token": 1, "customer.id": 1})
    #         paid_order = [item["checkout_token"] for item in db.shopify_order.find({"site_name": store_name}, {"_id": 0, "checkout_token": 1})]
    #         for unpaid in unpaid_order:
    #             if unpaid["token"] in paid_order:
    #                 continue
    #             if unpaid["customer"]["id"] not in result_dict:
    #                 result_dict[unpaid["customer"]["id"]] = [unpaid["id"],]
    #             else:
    #                 result_dict[unpaid["customer"]["id"]].append(unpaid["id"])
    #         return result_dict
    #     except Exception as e:
    #         logger.exception("unpaid_order_customers_mongo catch exception={}".format(e))
    #         return result_dict
    #     finally:
    #         mdb.close()

    def get_store_source(self, store_id):
        """
        获取某一店铺的from_type和name
        :param store_id: 店铺id
        :return: 元组(from_type, site_name) from_type:0--来自opstores, 1--来自edm
        """
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user, password=self.db_password).get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return 0, None
            cursor.execute("select `source`, `site_name` from `store` where id=%s", (store_id, ))
            store = cursor.fetchone()
            if not store:
                return 0, None

            return store
        except Exception as e:
            logger.exception("get_store_source exception={}".format(e))
            return 0, None
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0

    def paid_order_filter(self, store_id, min_time=None, max_time=None):
        """
        从MYSQL数据库中筛选出某一店铺中所有有过支付订单的客户id
        :param store_id:
        :param min_time:
        :param max_time:
        :return:
        """
        customers = []
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user, password=self.db_password).get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return customers

            if min_time and max_time:
                cursor.execute(
                    "select customer_uuid from order_event where store_id=%s and status=1 and order_update_time>=%s and order_update_time<=%s",
                    (store_id, min_time, max_time))
            elif min_time:
                cursor.execute(
                    "select customer_uuid from order_event where store_id=%s and status=1 and order_update_time>=%s",
                    (store_id, min_time))
            elif max_time:
                cursor.execute(
                    "select customer_uuid from order_event where store_id=%s and status=1 and order_update_time<=%s",
                    (store_id, max_time))
            else:
                cursor.execute(
                    "select customer_uuid from order_event where store_id=%s and status=1",
                    (store_id,))

            res = cursor.fetchall()
            for r in res:
                customers.append(r[0])
            return customers
        except Exception as e:
            logger.exception("paid_order_filter e={}".format(e))
            return customers
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0

    def unpaid_order_filter(self, store_id, min_time=None, max_time=None):
        """
        从MYSQL数据库中筛选出某一店铺中所有有未支付订单的客户id
        :param store_id:
        :param min_time:
        :param max_time:
        :return:
        """
        customers = []
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user,
                          password=self.db_password).get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return customers

            if min_time and max_time:
                cursor.execute(
                    "select customer_uuid, checkout_id from checkout_event where store_id=%s and checkout_update_time>=%s and checkout_update_time<=%s",
                    (store_id, min_time, max_time))
            elif min_time:
                cursor.execute(
                    "select customer_uuid, checkout_id from checkout_event where store_id=%s and checkout_update_time>=%s",
                    (store_id, min_time))
            elif max_time:
                cursor.execute(
                    "select customer_uuid, checkout_id from checkout_event where store_id=%s and checkout_update_time<=%s",
                    (store_id, max_time))
            else:
                cursor.execute(
                    "select customer_uuid, checkout_id from checkout_event where store_id=%s",
                    (store_id, ))

            res = cursor.fetchall()
            checkout_ids = []
            for r in res:
                customers.append(r[0])
                checkout_ids.append(r[1])

            # 再排除掉那些已经付款的checkout
            if customers:
                cursor.execute("select customer_uuid from order_event where store_id=%s and status=1 and checkout_id in %s", (store_id, checkout_ids))
                paid_customers = cursor.fetchall()
                for pc in paid_customers:
                    if pc[0] in customers:
                        customers.remove(pc[0])

            return customers
        except Exception as e:
            logger.exception("unpaid_order_filter e={}".format(e))
            return customers
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0

    def order_filter(self, store_id, status, relation, value, min_time=None, max_time=None):
        """
        筛选满足订单条件的客户id
        :param store_id: 店铺id
        :param status: 订单状态0－未支付，　１－支付　, 2 - all
        :param relation: 订单条件关系，　大于，小于，等于
        :param value: 订单条件值
        :param min_time: 时间筛选范围起点
        :param max_time: 时间筛选范围终点
        :return: list 满足条件的客户列表
        """
        customers = []
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user, password=self.db_password).get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return customers

            unpaid_customers = {}
            paid_customers = {}
            if status == 1 or status == 2:
                # between date
                if min_time and max_time:
                    cursor.execute(
                        """select `customer_uuid`, count(1) from `order_event` where store_id=%s and status=1 and `order_update_time`>=%s and `order_update_time`<=%s group by `customer_uuid`""", (store_id, min_time, max_time))

                # after, in the past
                elif min_time:
                    cursor.execute(
                        """select `customer_uuid`, count(1) from `order_event` where store_id=%s and status=1 and `order_update_time`>=%s group by `customer_uuid`""", (store_id, min_time))

                # before
                elif max_time:
                    cursor.execute(
                        """select `customer_uuid`, count(1) from `order_event` where store_id=%s and status=1 and `order_update_time`<=%s group by `customer_uuid`""", (store_id, max_time))

                # over all time
                else:
                    cursor.execute(
                        """select `customer_uuid`, count(1) from `order_event` where store_id=%s and status=1 group by `customer_uuid`""", (store_id, ))

                res = cursor.fetchall()
                for uuid, count in res:
                    paid_customers[uuid] = count

            if status == 0 or status == 2:
                # between date
                if min_time and max_time:
                    cursor.execute(
                        """select `customer_uuid`, count(1) from `checkout_event` where store_id=%s and `checkout_update_time`>=%s and `checkout_update_time`<=%s group by `customer_uuid`""", (store_id, min_time, max_time))

                    checkouts = cursor.fetchall()
                    if checkouts:
                        count = 0
                        for c in checkouts:
                            customer_uuid = c[0]
                            count = c[1]
                            if count>0:
                                cursor.execute("select checkout_id from checkout_event where store_id=%s and customer_uuid=%s and `checkout_update_time`>=%s and `checkout_update_time`<=%s", (store_id, customer_uuid, min_time, max_time))
                                checkout_ids = cursor.fetchall()
                                if checkout_ids:
                                    paid_orders = cursor.execute("select checkout_id from order_event where store_id=%s and status=1 and checkout_id in %s and `order_update_time`>=%s and `order_update_time`<=%s", (store_id, checkout_ids, min_time, max_time))
                                    for pd in paid_orders:
                                        count -= 1
                                else:
                                    count = 0

                        count = 0 if count < 0 else count
                        unpaid_customers[customer_uuid] = count

                # after, in the past
                elif min_time:
                    cursor.execute(
                        """select `customer_uuid`, count(1) from `checkout_event` where store_id=%s and `checkout_update_time`>=%s group by `customer_uuid`""", (store_id, min_time))

                    count = 0
                    checkouts = cursor.fetchall()
                    if checkouts:
                        for c in checkouts:
                            customer_uuid = c[0]
                            count = c[1]
                            if count > 0:
                                cursor.execute(
                                    "select checkout_id from checkout_event where store_id=%s and customer_uuid=%s and `checkout_update_time`>=%s",
                                    (store_id, customer_uuid, min_time))
                                checkout_ids = cursor.fetchall()
                                if checkout_ids:
                                    paid_orders = cursor.execute(
                                        "select checkout_id from order_event where store_id=%s and status=1 and checkout_id in %s and `order_update_time`>=%s",
                                        (store_id, checkout_ids, min_time))
                                    for pd in paid_orders:
                                        count -= 1
                                else:
                                    count = 0

                        count = 0 if count < 0 else count
                        unpaid_customers[customer_uuid] = count

                    # before
                elif max_time:
                    cursor.execute(
                        """select `customer_uuid`, count(1) from `checkout_event` where store_id=%s and `checkout_update_time`<=%s group by `customer_uuid`""", (store_id, max_time))

                    checkouts = cursor.fetchall()
                    if checkouts:
                        count = 0
                        for c in checkouts:
                            customer_uuid = c[0]
                            count = c[1]
                            if count > 0:
                                cursor.execute(
                                    "select checkout_id from checkout_event where store_id=%s and customer_uuid=%s and `checkout_update_time`<=%s",
                                    (store_id, customer_uuid, max_time))
                                checkout_ids = cursor.fetchall()
                                if checkout_ids:
                                    paid_orders = cursor.execute(
                                        "select checkout_id from order_event where store_id=%s and status=1 and checkout_id in %s and `order_update_time`<=%s",
                                        (store_id, checkout_ids, max_time))
                                    for pd in paid_orders:
                                        count -= 1
                                else:
                                    count = 0

                        count = 0 if count < 0 else count
                        unpaid_customers[customer_uuid] = count

                    # over all time
                else:
                    cursor.execute(
                        """select `customer_uuid`, count(1) from `checkout_event` where store_id=%s group by `customer_uuid`""", (store_id, ))
                    checkouts = cursor.fetchall()
                    if checkouts:
                        count = 0
                        for c in checkouts:
                            customer_uuid = c[0]
                            count = c[1]
                            if count > 0:
                                cursor.execute(
                                    "select checkout_id from checkout_event where store_id=%s and customer_uuid=%s",
                                    (store_id, customer_uuid))
                                checkout_ids = cursor.fetchall()
                                if checkout_ids:
                                    paid_orders = cursor.execute(
                                        "select checkout_id from order_event where store_id=%s and status=1 and checkout_id in %s",
                                        (store_id, checkout_ids))
                                    for pd in paid_orders:
                                        count -= 1
                                else:
                                    count = 0

                            count = 0 if count < 0 else count
                            unpaid_customers[customer_uuid] = count

            relation_dict = {"equals": "==", "more than": ">", "less than": "<"}
            if status == 1:
                for uuid, count in paid_customers.items():
                    just_str = "{} {} {}".format(count, relation_dict.get(relation), value)
                    if eval(just_str):
                        customers.append(uuid)
            if status == 0:
                for uuid, count in unpaid_customers.items():
                    just_str = "{} {} {}".format(count, relation_dict.get(relation), value)
                    if eval(just_str):
                        customers.append(uuid)

            if status == 2:
                for uuid, count in paid_customers.items():
                    if uuid in unpaid_customers.keys():
                        paid_customers[uuid] += unpaid_customers[uuid]
                    else:
                        unpaid_customers.pop(uuid)

                paid_customers.update(unpaid_customers)

                for uuid, count in paid_customers.items():
                    just_str = "{} {} {}".format(count, relation_dict.get(relation), value)
                    if eval(just_str):
                        customers.append(uuid)
            return customers
        except Exception as e:
            logger.exception("order_filter e={}".format(e))
            return customers
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0

    def order_filter_mongo(self, store_id, status, store_name, relation, value, min_time=None, max_time=None):
        """
        筛选满足订单条件的客户id
        :param store_id: 店铺id
        :param status: 订单状态0－未支付，　１－支付　, 2 - all
        :param relation: 订单条件关系，　大于，小于，等于
        :param value: 订单条件值
        :param min_time: 时间筛选范围起点
        :param max_time: 时间筛选范围终点
        :return: list 满足条件的客户列表
        """
        try:
            customers = []
            mdb = MongoDBUtil(mongo_config=self.mongo_config)
            db = mdb.get_instance()
            paid_results = db["shopify_order"]
            relation_dict = {"equals": "==", "more than": ">", "less than": "<"}
            if status == 0 or status == 2:  # 状态为0或者2的时候需要筛选的用户
                if int(value) <= 0:
                    unpaid_res = self.unpaid_order_customers_mongo(store_name, min_time, max_time)
                    unpaid_customer_list = unpaid_res.keys()

                    shopify_customer = db["shopify_customer"]

                    customer_res = shopify_customer.find({"site_name": store_name}, {"id": 1, "_id": 0})
                    # zero_order_customer = []
                    for cust in customer_res:
                        if cust["id"] not in unpaid_customer_list:
                            customers.append(cust["id"])
                else:
                    # 查询未支付的customer_uuid
                    unpaid_res = self.unpaid_order_customers_mongo(store_name, min_time, max_time)
                    for uuid, count_list in unpaid_res.items():
                        just_str = "{} {} {}".format(len(set(count_list)), relation_dict.get(relation), value)
                        if eval(just_str):
                            customers.append(uuid)
            if status == 1 or status == 2:  # 状态为1或者2的时候需要筛选的用户
                if min_time and max_time:
                    filter_dict = {"$lte": max_time, "$gte": min_time}
                elif min_time:
                    filter_dict = {"$gte": min_time}
                elif max_time:
                    filter_dict = {"$lte": max_time}
                else:
                    filter_dict = {"$lte": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")}

                if int(value) <= 0:
                    # 订单数为零
                    paid_res = paid_results.find({"updated_at": filter_dict, "site_name": store_name}, {"customer.id": 1, "_id": 0})
                    order_customer_list = []
                    for cus in paid_res:
                        order_customer_list.append(cus["customer"]["id"])

                    shopify_customer = db["shopify_customer"]
                    customer_res = shopify_customer.find({"site_name": store_name}, {"id": 1, "_id": 0})
                    for cus in customer_res:
                        if cus["id"] not in order_customer_list:
                            customers.append(cus["id"])
                else:
                    group = {
                        '_id': "$customer.id",
                        'count': {'$sum': 1}
                    }
                    paid_res = paid_results.aggregate(
                        [{"$match": {"updated_at": filter_dict, "site_name": store_name}}, {"$group": group}],
                        allowDiskUse=True)

                    for item in paid_res:
                        just_str = "{} {} {}".format(item["count"], relation_dict.get(relation), value)
                        if eval(just_str):
                            customers.append(item["_id"])
            return customers
        except Exception as e:
            logger.exception("order_filter_mongo catch exception={}".format(e))
            return customers
        finally:
            mdb.close()

    def adapt_sign_up_time_mongo(self, store_id, relations, store_name):
        """
        适配出所有符合注册条件的客户id
        :param store_id: 店铺id
        :param relations: 筛选条件
        :param store_name: 店铺名称
        :return: 客户ids
        """
        min_time, max_time = self.date_relation_convert_mongo(relations[0]["relation"], relations[0]["values"], store_name,
                                                        relations[0].get("unit", "days"))
        customers = []
        try:
            mdb = MongoDBUtil(mongo_config=self.mongo_config)
            db = mdb.get_instance()
            #TODO
            if min_time and max_time:
                filter_dict = {"$lte": max_time, "$gte": min_time}
            elif min_time:
                filter_dict = {"$gte": min_time}
            elif max_time:
                filter_dict = {"$lte": max_time}
            else:
                filter_dict = {"$lte": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")}
            customers_res = db.shopify_customer.find({"site_name": store_name, "created_at": filter_dict}, {"_id": 0, "id": 1})
            for cus in customers_res:
                customers.append(cus["id"])
            return customers
        except Exception as e:
            logger.exception("adapt_sign_up_time_mongo catch exception={}".format(e))
            return customers
        finally:
            mdb.close()

    def adapt_sign_up_time(self, store_id, relations):
        """
        适配出所有符合注册条件的客户id
        :param store_id: 店铺id
        :param relations: 筛选条件　
        :return: 客户ids
        """
        min_time, max_time = self.date_relation_convert(relations[0]["relation"], relations[0]["values"],
                                                   relations[0].get("unit", "days"))
        customers = []
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user, password=self.db_password).get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return customers

            # between date
            if min_time and max_time:
                cursor.execute(
                    """select `uuid` from `customer` where store_id=%s and `sign_up_time`>=%s and `sign_up_time`<=%s""",
                    (store_id, min_time, max_time))
            # after, in the past
            elif min_time:
                cursor.execute(
                    """select `uuid` from `customer` where store_id=%s and `sign_up_time`>=%s""", (store_id, min_time))
            # before
            elif max_time:
                cursor.execute("""select `uuid` from `customer` where store_id=%s and `sign_up_time`<=%s""", (store_id, max_time))
            # over all time
            else:
                cursor.execute("""select `uuid` from `customer` where store_id=%s""", (store_id, ))

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

    def adapt_last_order_created_time(self, store_id, relations):
        """
        适配出所有上次订单时间符合条件的客户id(这里的订单包括已支付的（order_event)和未支付的(checkout_event))
        :param store_id: 店铺id
        :param relations: 筛选条件　
        :return: 客户ids
        """
        min_time, max_time = self.date_relation_convert(relations[0]["relation"], relations[0]["values"],
                                                   relations[0].get("unit", "days"))
        customers = []
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user, password=self.db_password).get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return customers

            # between date
            if min_time and max_time:
                cursor.execute(
                    """select `customer_uuid` from `order_event` where store_id=%s and `order_update_time`>=%s and `order_update_time`<=%s""",
                    (store_id, min_time, max_time))

                res = cursor.fetchall()
                for uuid in res:
                    customers.append(uuid[0])

                cursor.execute(
                    """select `customer_uuid` from `checkout_event` where store_id=%s and `checkout_update_time`>=%s and `checkout_update_time`<=%s""",
                    (store_id, min_time, max_time))

                res = cursor.fetchall()
                for uuid in res:
                    customers.append(uuid[0])

            # after, in the past
            elif min_time:
                cursor.execute(
                    """select `customer_uuid` from `order_event` where store_id=%s and `order_update_time`>=%s""",
                    (store_id, min_time))

                res = cursor.fetchall()
                for uuid in res:
                    customers.append(uuid[0])

                cursor.execute(
                    """select `customer_uuid` from `checkout_event` where store_id=%s and `checkout_update_time`>=%s""",
                    (store_id, min_time))

                res = cursor.fetchall()
                for uuid in res:
                    customers.append(uuid[0])
            # before
            elif max_time:
                cursor.execute(
                    """select `customer_uuid` from `order_event` where store_id=%s and `order_update_time`<=%s""",
                    (store_id, max_time))

                res = cursor.fetchall()
                for uuid in res:
                    customers.append(uuid[0])

                cursor.execute(
                    """select `customer_uuid` from `checkout_event` where store_id=%s and `checkout_update_time`<=%s""",
                    (store_id, max_time))

                res = cursor.fetchall()
                for uuid in res:
                    customers.append(uuid[0])

            # over all time
            else:
                cursor.execute(
                    """select `customer_uuid` from `order_event` where store_id=%s""",
                    (store_id,))

                res = cursor.fetchall()
                for uuid in res:
                    customers.append(uuid[0])

                cursor.execute(
                    """select `customer_uuid` from `checkout_event` where store_id=%s""",
                    (store_id,))

                res = cursor.fetchall()
                for uuid in res:
                    customers.append(uuid[0])

            # 去重后返回
            return list(set(customers))
        except Exception as e:
            logger.exception("adapt_last_order_created_time e={}".format(e))
            return customers
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0

    def adapt_last_order_created_time_mongo(self, store_id, relations, store_name):
        """
        适配出所有上次订单时间符合条件的客户id
        :param store_id: 店铺ID
        :param relations: 筛选条件
        :param store_name: 店铺名称
        :return: 客户ids
        """
        min_time, max_time = self.date_relation_convert_mongo(relations[0]["relation"], relations[0]["values"],
                                                              store_name,
                                                              relations[0].get("unit", "days"))
        customers = []
        try:
            mdb = MongoDBUtil(mongo_config=self.mongo_config)
            db = mdb.get_instance()
            # TODO
            if min_time and max_time:
                filter_dict = {"$lte": max_time, "$gte": min_time}
            elif min_time:
                filter_dict = {"$gte": min_time}
            elif max_time:
                filter_dict = {"$lte": max_time}
            else:
                filter_dict = {"$lte": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")}
            order_customers = [item["customer"]["id"] for item in db.shopify_order.find({"site_name": store_name, "updated_at": filter_dict}, {"_id": 0, "id": 1, "customer.id": 1})]
            unpaid_customers = [item["customer"]["id"] for item in db.shopify_unpaid_order.find({"site_name": store_name, "updated_at": filter_dict, "customer": {"$exists": 1}}, {"_id": 0, "id": 1, "customer.id": 1})]
            customers = list(set(order_customers + unpaid_customers))
            return customers
        except Exception as e:
            logger.exception("adapt_last_order_created_time_mongo catch exception={}".format(e))
            return customers
        finally:
            mdb.close()

    def adapt_last_opened_email_time(self, store_id, relations):
        """
        适配出所有打开过邮件的时间符合条件的客户ids
        :param store_id: 店铺id
        :param relations: 时间范围条件
        :return: 客户ids
        """
        customers = []
        customer_emails = []
        opt_type = 0
        min_time, max_time = self.date_relation_convert(relations[0]["relation"], relations[0]["values"],
                                                   relations[0].get("unit", "days"))
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user, password=self.db_password).get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return customers

            # between date
            if min_time and max_time:
                cursor.execute(
                    """select `email` from `subscriber_activity` where store_id=%s and type=%s 
                    and `opt_time`>=%s and `opt_time`<=%s""",
                    (store_id, opt_type, min_time, max_time))
            # after, in the past
            elif min_time:
                cursor.execute(
                    """select `email` from `subscriber_activity` where store_id=%s and type=%s 
                    and `opt_time`>=%s""", (store_id, opt_type, min_time))
            # before
            elif max_time:
                cursor.execute(
                    """select `email`　from `subscriber_activity` where store_id=%s and type=%s 
                    and `opt_time`<=%s""", (store_id, opt_type, max_time))
            # over all time
            else:
                cursor.execute(
                    """select `email`, count from `subscriber_activity` where store_id=%s and type=%s""",
                    (store_id, opt_type))

            res = cursor.fetchall()
            for email in res:
                customer_emails.append(email[0])

            # 去重
            customer_emails = list(set(customer_emails))
            if customer_emails:
                # 通过邮箱查出所有的uuid
                cursor.execute("""select `uuid` from customer where store_id=%s and customer_email in %s""", (store_id, customer_emails))
                res = cursor.fetchall()
                if res:
                    for uuid in res:
                        customers.append(uuid[0])
            return customers
        except Exception as e:
            logger.exception("adapt_last_opened_email_time e={}".format(e))
            return customers
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0

    def adapt_last_opened_email_time_mongo(self, store_id, relations, store_name):
        """
        适配出所有打开过邮件的时间符合条件的客户ids
        :param store_id: 店铺id
        :param relations: 时间范围条件
        :param store_name: 店铺名称
        :return: 客户ids
        """
        customers = []
        customer_emails = []
        opt_type = 0
        min_time, max_time = self.date_relation_convert(relations[0]["relation"], relations[0]["values"],
                                                        relations[0].get("unit", "days"))
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user,
                          password=self.db_password).get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return customers

            # between date
            if min_time and max_time:
                cursor.execute(
                    """select `email` from `subscriber_activity` where store_id=%s and type=%s 
                    and `opt_time`>=%s and `opt_time`<=%s""",
                    (store_id, opt_type, min_time, max_time))
            # after, in the past
            elif min_time:
                cursor.execute(
                    """select `email` from `subscriber_activity` where store_id=%s and type=%s 
                    and `opt_time`>=%s""", (store_id, opt_type, min_time))
            # before
            elif max_time:
                cursor.execute(
                    """select `email`　from `subscriber_activity` where store_id=%s and type=%s 
                    and `opt_time`<=%s""", (store_id, opt_type, max_time))
            # over all time
            else:
                cursor.execute(
                    """select `email`, count from `subscriber_activity` where store_id=%s and type=%s""",
                    (store_id, opt_type))

            res = cursor.fetchall()
            for email in res:
                customer_emails.append(email[0])

            # 去重
            customer_emails = list(set(customer_emails))
            if customer_emails:
                # 通过邮箱查出所有的uuid
                customers = self.customer_email_to_uuid_mongo(customer_emails, store_name)
            return customers
        except Exception as e:
            logger.exception("adapt_last_opened_email_time_mongo exception e={}".format(e))
            return customers
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0


    def adapt_last_click_email_time(self, store_id, relations):
        """
        适配出所有打开过邮件的时间符合条件的客户ids
        :param store_id: 店铺id
        :param relations: 时间范围条件
        :return: 客户ids
        """
        customers = []
        customer_emails = []
        opt_type = 1
        min_time, max_time = self.date_relation_convert(relations[0]["relation"], relations[0]["values"],
                                                   relations[0].get("unit", "days"))
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user, password=self.db_password).get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return customers

            # between date
            if min_time and max_time:
                cursor.execute(
                    """select `email` from `subscriber_activity` where store_id=%s and type=%s 
                    and `opt_time`>=%s and `opt_time`<=%s""",
                    (store_id, opt_type, min_time, max_time))
            # after, in the past
            elif min_time:
                cursor.execute(
                    """select `email` from `subscriber_activity` where store_id=%s and type=%s 
                    and `opt_time`>=%s""", (store_id, opt_type, min_time))
            # before
            elif max_time:
                cursor.execute(
                    """select `email`　from `subscriber_activity` where store_id=%s and type=%s 
                    and `opt_time`<=%s""", (store_id, opt_type, max_time))
            # over all time
            else:
                cursor.execute(
                    """select `email` from `subscriber_activity` where store_id=%s and type=%s""",
                    (store_id, opt_type))

            res = cursor.fetchall()
            for email in res:
                customer_emails.append(email[0])

            # 去重
            customer_emails = list(set(customer_emails))
            if customer_emails:
                # 通过邮箱查出所有的uuid
                cursor.execute("""select `uuid` from customer where store_id=%s and customer_email in %s""",
                              (store_id, customer_emails))
                res = cursor.fetchall()
                if res:
                    for uuid in res:
                        customers.append(uuid[0])
            return customers
        except Exception as e:
            logger.exception("adapt_last_click_email_time e={}".format(e))
            return customers
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0

    def adapt_last_click_email_time_mongo(self, store_id, relations, store_name):
        """
        适配出所有打开过邮件的时间符合条件的客户ids
        :param store_id: 店铺id
        :param relations: 时间范围条件
        :return: 客户ids
        """
        customers = []
        customer_emails = []
        opt_type = 1
        min_time, max_time = self.date_relation_convert(relations[0]["relation"], relations[0]["values"],
                                                   relations[0].get("unit", "days"))
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user, password=self.db_password).get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return customers

            # between date
            if min_time and max_time:
                cursor.execute(
                    """select `email` from `subscriber_activity` where store_id=%s and type=%s 
                    and `opt_time`>=%s and `opt_time`<=%s""",
                    (store_id, opt_type, min_time, max_time))
            # after, in the past
            elif min_time:
                cursor.execute(
                    """select `email` from `subscriber_activity` where store_id=%s and type=%s 
                    and `opt_time`>=%s""", (store_id, opt_type, min_time))
            # before
            elif max_time:
                cursor.execute(
                    """select `email`　from `subscriber_activity` where store_id=%s and type=%s 
                    and `opt_time`<=%s""", (store_id, opt_type, max_time))
            # over all time
            else:
                cursor.execute(
                    """select `email` from `subscriber_activity` where store_id=%s and type=%s""",
                    (store_id, opt_type))

            res = cursor.fetchall()
            for email in res:
                customer_emails.append(email[0])

            # 去重
            customer_emails = list(set(customer_emails))
            if customer_emails:
                # 通过邮箱查出所有的uuid
                customers = self.customer_email_to_uuid_mongo(customer_emails, store_name)
            return customers
        except Exception as e:
            logger.exception("adapt_last_click_email_time e={}".format(e))
            return customers
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0

    def adapt_placed_order(self, store_id, relations):
        """
        适配出所有待支付的订单符合条件的客户id
        :param store_id: 店铺id
        :param relations: 筛选条件
        :return: 客户id列表
        """
        # relations 两个, 第一个是数量，第二个是时间范围
        min_time, max_time = self.date_relation_convert(relations[1]["relation"], relations[1]["values"],
                                                   relations[1].get("unit", "days"))
        adapt_customers = self.order_filter(store_id=store_id, status=0, relation=relations[0]["relation"],
                                       value=relations[0]["values"][0], min_time=min_time, max_time=max_time)
        return adapt_customers

    def adapt_paid_order(self, store_id, relations):
        """
        适配出所有已支付的订单符合条件的客户id
        :param store_id: 店铺id
        :param relations: 筛选条件
        :return: 客户id列表
        """
        # relations 两个, 第一个是数量，第二个是时间范围
        min_time, max_time = self.date_relation_convert(relations[1]["relation"], relations[1]["values"],
                                                   relations[1].get("unit", "days"))
        adapt_customers = self.order_filter(store_id=store_id, status=1, relation=relations[0]["relation"],
                                       value=relations[0]["values"][0], min_time=min_time, max_time=max_time)
        return adapt_customers

    def adapt_all_order(self, store_id, relations):
        """
        适配出所有的订单符合条件的客户id
        :param store_id: 店铺id
        :param relations: 筛选条件
        :return: 客户id列表
        """
        # relations 两个, 第一个是数量，第二个是时间范围
        min_time, max_time = self.date_relation_convert(relations[1]["relation"], relations[1]["values"],
                                                        relations[1].get("unit", "days"))
        adapt_customers = self.order_filter(store_id=store_id, status=2, relation=relations[0]["relation"],
                                            value=relations[0]["values"][0], min_time=min_time, max_time=max_time)
        return adapt_customers

    def adapt_placed_order_mongo(self, store_id, relations, store_name):
        """
        适配出所有待支付的订单符合条件的客户id
        :param store_id: 店铺id
        :param relations: 筛选条件
        :return: 客户id列表
        """
        # relations 两个, 第一个是数量，第二个是时间范围
        min_time, max_time = self.date_relation_convert_mongo(relations[1]["relation"], relations[1]["values"], store_name,
                                                   relations[1].get("unit", "days"))
        adapt_customers = self.order_filter_mongo(store_id=store_id, status=0, store_name=store_name, relation=relations[0]["relation"],
                                       value=relations[0]["values"][0], min_time=min_time, max_time=max_time)
        return adapt_customers

    def adapt_paid_order_mongo(self, store_id, relations, store_name):
        """
        适配出所有已支付的订单符合条件的客户id
        :param store_id: 店铺id
        :param relations: 筛选条件
        :return: 客户id列表
        """
        # relations 两个, 第一个是数量，第二个是时间范围
        min_time, max_time = self.date_relation_convert_mongo(relations[1]["relation"], relations[1]["values"], store_name,
                                                   relations[1].get("unit", "days"))
        adapt_customers = self.order_filter_mongo(store_id=store_id, status=1, store_name=store_name, relation=relations[0]["relation"],
                                       value=relations[0]["values"][0], min_time=min_time, max_time=max_time)
        return adapt_customers

    def adapt_all_order_mongo(self, store_id, relations, store_name):
        """
        适配出所有的订单符合条件的客户id
        :param store_id: 店铺id
        :param relations: 筛选条件
        :return: 客户id列表
        """
        # relations 两个, 第一个是数量，第二个是时间范围
        try:
            min_time, max_time = self.date_relation_convert_mongo(relations[1]["relation"], relations[1]["values"], store_name,
                                                            relations[1].get("unit", "days"))
            adapt_customers = self.order_filter_mongo(store_id=store_id, status=2, store_name= store_name, relation=relations[0]["relation"],
                                                value=relations[0]["values"][0], min_time=min_time, max_time=max_time)
            return adapt_customers
        except Exception as e:
            logger.exception("adapt_all_order_mongo catch exception={}, relations={}".format(e, relations))
            return []

    def email_opt_filter(self, store_id, opt_type, relation, value, min_time, max_time):
        """
        筛选满足邮件操作条件的客户的id
        :param store_id: 店铺id
        :param opt_type: 邮件的操作类型, open－0，　click－1, send-3
        :param relation: 条件关系，　大于，小于，等于
        :param value: 条件值
        :param min_time: 时间筛选范围起点
        :param max_time: 时间筛选范围终点
        :return: list 满足条件的客户列表
        """
        customer_emails = []
        customers = []
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user, password=self.db_password).get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return customers

            # between date
            if min_time and max_time:
                cursor.execute(
                    """select `email`, count(1) from `subscriber_activity` where store_id=%s and type=%s 
                    and `opt_time`>=%s and `opt_time`<=%s group by `email`""",
                    (store_id, opt_type, min_time, max_time))
            # after, in the past
            elif min_time:
                cursor.execute(
                    """select `email`, count(1) from `subscriber_activity` where store_id=%s and type=%s 
                    and `opt_time`>=%s group by `email`""", (store_id, opt_type, min_time))
            # before
            elif max_time:
                cursor.execute(
                    """select `email`, count(1) from `subscriber_activity` where store_id=%s and type=%s 
                    and `opt_time`<=%s group by `email`""", (store_id, opt_type, max_time))
            # over all time
            else:
                cursor.execute(
                    """select `email`, count(1) from `subscriber_activity` where store_id=%s and type=%s 
                    group by `email`""", (store_id, opt_type))

            res = cursor.fetchall()
            relation_dict = {"equals": "==", "more than": ">", "less than": "<"}

            for email, count in res:
                just_str = "{} {} {}".format(count, relation_dict.get(relation), value)
                if eval(just_str):
                    customer_emails.append(email[0])

            # 去重
            customer_emails = list(set(customer_emails))
            if customer_emails:
                # 通过邮箱查出所有的uuid
                cursor.execute("""select `uuid` from customer where store_id=%s and customer_email in %s""", (store_id, customer_emails))
                res = cursor.fetchall()
                if res:
                    for uuid in res:
                        customers.append(uuid[0])
            return customers
        except Exception as e:
            logger.exception("email_opt_filter e={}".format(e))
            return customers
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0

    def email_opt_filter_mongo(self, store_id, opt_type, relation, value, min_time, max_time, site_name):
        """
        筛选满足邮件操作条件的客户的id
        :param store_id: 店铺id
        :param opt_type: 邮件的操作类型, open－0，　click－1, send-3
        :param relation: 条件关系，　大于，小于，等于
        :param value: 条件值
        :param min_time: 时间筛选范围起点
        :param max_time: 时间筛选范围终点
        :return: list 满足条件的客户列表
        """
        customer_emails = []
        customers = []
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user, password=self.db_password).get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return customers
            if min_time:
                min_time = datetime.datetime.strptime(min_time, "%Y-%m-%dT%H:%M:%S")
            if max_time:
                max_time = datetime.datetime.strptime(max_time, "%Y-%m-%dT%H:%M:%S")
            # between date
            if min_time and max_time:
                cursor.execute(
                    """select `email`, count(1) from `subscriber_activity` where store_id=%s and type=%s 
                    and `opt_time`>=%s and `opt_time`<=%s group by `email`""",
                    (store_id, opt_type, min_time, max_time))
            # after, in the past
            elif min_time:
                cursor.execute(
                    """select `email`, count(1) from `subscriber_activity` where store_id=%s and type=%s 
                    and `opt_time`>=%s group by `email`""", (store_id, opt_type, min_time))
            # before
            elif max_time:
                cursor.execute(
                    """select `email`, count(1) from `subscriber_activity` where store_id=%s and type=%s 
                    and `opt_time`<=%s group by `email`""", (store_id, opt_type, max_time))
            # over all time
            else:
                cursor.execute(
                    """select `email`, count(1) from `subscriber_activity` where store_id=%s and type=%s 
                    group by `email`""", (store_id, opt_type))

            res = cursor.fetchall()
            relation_dict = {"equals": "==", "more than": ">", "less than": "<"}

            for email, count in res:
                just_str = "{} {} {}".format(count, relation_dict.get(relation), value)
                if eval(just_str):
                    customer_emails.append(email[0])

            # 去重
            customer_emails = list(set(customer_emails))
            if customer_emails:
                # 通过邮箱查出所有的uuid
                customers = self.customer_email_to_uuid_mongo(customer_emails, site_name)
            return customers
        except Exception as e:
            logger.exception("email_opt_filter e={}".format(e))
            return customers
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0

    def adapt_opened_email(self, store_id, relations):
        """
        适配出所有符合邮件打开筛选条件的customer uuids
        :param store_id: 店铺id
        :param relations: 筛选条件列表
        :return: 客户的id列表
        """
        # relations 两个, 第一个是数量，第二个是时间范围
        min_time, max_time = self.date_relation_convert(relation=relations[1]["relation"], values=relations[1]["values"],
                                                   unit=relations[1].get("unit", "days"))
        customers = self.email_opt_filter(store_id=store_id, opt_type=0, relation=relations[0]["relation"], value=relations[0]["values"][0],
                         min_time=min_time, max_time=max_time)
        return customers

    def adapt_opened_email_mongo(self, store_id, relations, store_name):
        """
        适配出所有符合邮件打开筛选条件的customer uuids
        :param store_id: 店铺id
        :param relations: 筛选条件列表
        :return: 客户的id列表
        """
        # relations 两个, 第一个是数量，第二个是时间范围
        min_time, max_time = self.date_relation_convert_mongo(relation=relations[1]["relation"], values=relations[1]["values"],
                                                   unit=relations[1].get("unit", "days"), store_name=store_name)
        customers = self.email_opt_filter_mongo(store_id=store_id, opt_type=0, relation=relations[0]["relation"], value=relations[0]["values"][0],
                         min_time=min_time, max_time=max_time, site_name=store_name)
        return customers

    def adapt_clicked_email(self, store_id, relations):
        """
        适配出所有符合邮件点击筛选条件的customer uuids
        :param store_id: 店铺id
        :param relations: 筛选条件列表
        :return: 客户的id列表
        """
        # relations 两个, 第一个是数量，第二个是时间范围
        min_time, max_time = self.date_relation_convert(relation=relations[1]["relation"], values=relations[1]["values"],
                                                   unit=relations[1].get("unit", "days"))
        customers = self.email_opt_filter(store_id=store_id, opt_type=1, relation=relations[0]["relation"], value=relations[0]["values"][0],
                         min_time=min_time, max_time=max_time)
        return customers

    def adapt_clicked_email_mongo(self, store_id, relations, store_name):
        """
        适配出所有符合邮件点击筛选条件的customer uuids
        :param store_id: 店铺id
        :param relations: 筛选条件列表
        :return: 客户的id列表
        """
        # relations 两个, 第一个是数量，第二个是时间范围
        min_time, max_time = self.date_relation_convert_mongo(relation=relations[1]["relation"], values=relations[1]["values"],
                                                   unit=relations[1].get("unit", "days"), store_name=store_name)
        customers = self.email_opt_filter_mongo(store_id=store_id, opt_type=1, relation=relations[0]["relation"], value=relations[0]["values"][0],
                         min_time=min_time, max_time=max_time, site_name=store_name)
        return customers

    def adapt_last_order_status(self, store_id, relations):
        """
        适配出所有最后一次订单状态符合条件的客户id
        :param store_id: 店铺id
        :param relations: 筛选条件　
        :return: 客户ids
        """
        status = 0
        if relations[0]["relation"] == "is paid":
            status = 1

        customers = []
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user, password=self.db_password).get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return customers

            cursor.execute("""select `uuid` from `customer` where store_id=%s and last_order_status=%s""", (store_id, status))
            res = cursor.fetchall()
            for uuid in res:
                customers.append(uuid[0])

            return customers
        except Exception as e:
            logger.exception("adapt_last_order_status e={}".format(e))
            return customers
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0

    def unpaid_order_customers_mongo(self, store_name, min_time=None, max_time=None):
        """
        获取未支付的customers
        :param store_id: 店铺ID
        :param store_name: 店铺名称
        :param min_time:
        :param max_time:
        :return: 符合条件的id{customer_id:[checkout_id1,checkout_id2], }
        """
        logger.info("unpaid_order_customers_mongo start")
        result_dict = {}
        try:
            mdb = MongoDBUtil(mongo_config=self.mongo_config)
            db = mdb.get_instance()
            if min_time and max_time:
                filter_dict = {"$lte": max_time, "$gte": min_time}
            elif min_time:
                filter_dict = {"$gte": min_time}
            elif max_time:
                filter_dict = {"$lte": max_time}
            else:
                filter_dict = {"$lte": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")}
            unpaid_order = db.shopify_unpaid_order.find({"site_name": store_name, "updated_at": filter_dict, "customer.email": {"$ne": None}}, {"_id": 0, "id": 1, "token": 1, "customer.id": 1})
            paid_order = [item["checkout_token"] for item in db.shopify_order.find({"site_name": store_name, "updated_at": {"$gte": min_time}}, {"_id": 0, "checkout_token": 1})]
            for unpaid in unpaid_order:
                if unpaid["token"] in paid_order:
                    continue
                if "customer" in unpaid.keys():
                    if unpaid["customer"]["id"] not in result_dict:
                        result_dict[unpaid["customer"]["id"]] = [unpaid["id"],]
                    else:
                        result_dict[unpaid["customer"]["id"]].append(unpaid["id"])
            return result_dict
        except Exception as e:
            logger.exception("unpaid_order_customers_mongo catch exception={}".format(e))
            return result_dict
        finally:
            mdb.close()

    def adapt_last_order_status_mongo(self, store_id, relations, store_name):
        """
        适配出所有最后一次订单状态符合条件的客户id
        :param store_id:
        :param relations:
        :param store_name:
        :return: 符合条件的ids
        """
        logger.info("adapt_last_order_status_mongo start")
        try:
            mdb = MongoDBUtil(mongo_config=self.mongo_config)
            db = mdb.get_instance()
            # 从customer表中查找对应的uuid
            # customer = db["shopify_customer"]
            if relations[0]["relation"] == "is paid":  # 最后一笔订单已支付
                customers = [item["customer"]["id"] for item in db.shopify_order.find({"financial_status": "paid", "site_name": store_name},
                                           {"_id": 0, "id": 1, "customer.id": 1})]
                return list(set(customers))
            elif relations[0]["relation"] == "is unpaid":
                result_dict = self.unpaid_order_customers_mongo(store_name,
                                                                min_time=(datetime.datetime.now()-datetime.timedelta(days=120)).strftime("%Y-%m-%dT%H:%M:%S"),
                                                                max_time=datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))
                return list(result_dict.keys())
        except Exception as e:
            logger.exception("adapt_last_order_status_mongo catch exception={}".format(e))
            return []
        finally:
            mdb.close()

    def adapt_is_accept_marketing(self, store_id, relations):
        """
        适配出是否接受市场推销符合条件的客户id
        :param store_id: 店铺id
        :param relations: 筛选条件　
        :return: 客户ids
        """
        status = 0
        if relations[0]["relation"] == "is true":
            status = 1

        customers = []
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user, password=self.db_password).get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return customers

            cursor.execute("""select `uuid` from `customer` where store_id=%s and accept_marketing_status=%s""",
                           (store_id, status))
            res = cursor.fetchall()
            for uuid in res:
                customers.append(uuid[0])
            return customers
        except Exception as e:
            logger.exception("adapt_is_accept_marketing e={}".format(e))
            return customers
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0

    def adapt_is_accept_marketing_mongo(self, store_id, relations, store_name):
        """
        适配出是否接受市场推销符合条件的客户id
        :param store_id:
        :param relations:
        :param store_name:
        :return:
        """
        status = False
        if 'true' in relations[0]["relation"]:
            status = True
        customer_list = []
        try:
            mdb = MongoDBUtil(mongo_config=self.mongo_config)
            db = mdb.get_instance()
            # 从customer表中查找对应的uuid
            customer = db["shopify_customer"]
            customers = customer.find({"accepts_marketing": status, "site_name": store_name}, {"_id": 0, "id": 1, "accepts_marketing": 1})
            for cus in customers:
                customer_list.append(cus["id"])
            return customer_list
        except Exception as e:
            logger.exception("adapt_is_accept_marketing_mongo catch exception={}".format(e))
            return customer_list
        finally:
            mdb.close()

    def adapt_customer_email(self, store_id, relations):
        """
        适配出邮件地址符合条件的客户id
        :param store_id: 店铺id
        :param relations: 筛选条件　
        :return: 客户ids
        """
        customers = []
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user, password=self.db_password).get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return customers

            if relations[0]["relation"] == "contains":
                cursor.execute("""select `uuid` from `customer` where store_id=%s and customer_email like \"%{}%\"""".
                               format(relations[0]["values"][0]), (store_id, ))
            elif relations[0]["relation"] == "is started with":
                cursor.execute("""select `uuid` from `customer` where store_id=%s and customer_email start with \"{}%\"""".
                               format(relations[0]["values"][0]), (store_id, ))
            elif relations[0]["relation"] == "is end with":
                cursor.execute("""select `uuid` from `customer` where store_id=%s and customer_email start with \"%{}\"""".
                               format(relations[0]["values"][0]), (store_id, ))
            res = cursor.fetchall()
            for uuid in res:
                customers.append(uuid[0])
            return customers
        except Exception as e:
            logger.exception("adapt_customer_email e={}".format(e))
            return customers
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0

    def adapt_customer_email_mongo(self, store_id, relations, store_name):
        """
        适配出邮件地址符合条件的客户id
        :param store_id:
        :param relations:
        :param store_name:
        :return:
        """
        customer_list = []
        try:
            mdb = MongoDBUtil(mongo_config=self.mongo_config)
            db = mdb.get_instance()
            # 从customer表中查找对应的uuid
            customer = db["shopify_customer"]
            if relations[0]["relation"] == "contains":
                customers = customer.find({"email": {"$regex": relations[0]["values"][0]}, "site_name": store_name},
                                          {"_id": 0, "id": 1, "email":1})
            elif relations[0]["relation"] == "is started with":
                customers = customer.find({"email": {"$regex": "^" + relations[0]["values"][0]}, "site_name": store_name},
                                          {"_id": 0, "id": 1, "email":1})
            elif relations[0]["relation"] == "is end with":
                customers = customer.find({"email": {"$regex": relations[0]["values"][0] + "$"}, "site_name": store_name},
                                          {"_id": 0, "id": 1, "email":1})
            for cus in customers:
                customer_list.append(cus["id"])
            return customer_list
        except Exception as e:
            logger.exception("adapt_customer_email_mongo catch exception={}".format(e))
            return customer_list
        finally:
            mdb.close()

    def adapt_total_order_amount(self, store_id, relations):
        """
        适配出总订单金额符合条件的客户id
        :param store_id: 店铺id
        :param relations: 筛选条件　
        :return: 客户ids
        """
        customers = []
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user, password=self.db_password).get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return customers

            if relations[0]["relation"] == "is":
                cursor.execute("""select `uuid` from `customer` where store_id=%s and payment_amount=%s""", (store_id, relations[0]["values"][0]))
            elif relations[0]["relation"] == "is more than":
                cursor.execute("""select `uuid` from `customer` where store_id=%s and payment_amount>%s""", (store_id, relations[0]["values"][0]))
            elif relations[0]["relation"] == "is less than":
                cursor.execute("""select `uuid` from `customer` where store_id=%s and payment_amount<%s""", (store_id, relations[0]["values"][0]))
            res = cursor.fetchall()
            for uuid in res:
                customers.append(uuid[0])
            return customers
        except Exception as e:
            logger.exception("adapt_total_order_amount e={}".format(e))
            return customers
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0

    def adapt_total_order_amount_mongo(self, store_id, relations, store_name):
        """
        适配出总订单金额符合条件的客户id
        :param store_id:
        :param relations: 条件
        :param store_name: 店铺名称
        :return: 符合条件的uuid列表
        """
        customer_list = []
        try:
            mdb = MongoDBUtil(mongo_config=self.mongo_config)
            db = mdb.get_instance()
            # 从customer表中查找对应的uuid
            customer = db["shopify_customer"]
            if relations[0]["relation"] == "is":
                customers = customer.find({"total_spent": relations[0]["values"][0], "site_name": store_name}, {"_id": 0, "id": 1})
            elif relations[0]["relation"] == "is more than":
                customers = customer.find({"total_spent": {"$gt": relations[0]["values"][0]}, "site_name": store_name}, {"_id": 0, "id": 1})
            elif relations[0]["relation"] == "is less than":
                customers = customer.find({"total_spent": {"$lt": relations[0]["values"][0]}, "site_name": store_name}, {"_id": 0, "id": 1})
            for cus in customers:
                customer_list.append(cus["id"])
            return customer_list
        except Exception as e:
            logger.exception("adapt_total_order_amount_mongo catch exception={}".format(e))
            return customer_list
        finally:
            mdb.close()

    def date_relation_convert(self, relation, values, unit="days"):
        """
        转换日期条件为起\止时间点
        :param relation: 日期条件，如before, in the past...
        :param values: 条件值列表
        :param unit: 日期单位
        :return: 起＼止时间点，datetime类型
        """
        def unit_convert(unit_, value):
            if unit_ in ["days", 'weeks']:
                str_delta = "datetime.timedelta({}={})".format(unit_, value)
            else:
                str_delta = "relativedelta({}={})".format(unit_, value)

            return eval(str_delta)

        try:
            min_time = None
            max_time = None
            format_str_0 = format_str_1 = "%Y-%m-%d %H:%M:%S"
            # 兼容一下时间格式
            if isinstance(values[0], str):
                if len(values[0]) <= 10:
                    format_str_0 = format_str_1 = "%Y-%m-%d"

            time_now = datetime.datetime.now()
            if relation.lower() in "is in the past":
                min_time = time_now - unit_convert(unit_=unit, value=values[0])
            elif relation.lower() in "is before":
                max_time = datetime.datetime.strptime(values[0], format_str_0)
            elif relation.lower() in "is after":
                min_time = datetime.datetime.strptime(values[0], format_str_0)
            elif relation.lower() == "is between date" or relation.lower() == "between date":
                min_time = datetime.datetime.strptime(values[0], format_str_0)
                max_time = datetime.datetime.strptime(values[1], format_str_1)
            elif relation.lower() == "is between" or relation.lower() == "between":
                max_time = time_now - unit_convert(unit_=unit, value=values[0])
                min_time = time_now - unit_convert(unit_=unit, value=values[1])
            elif relation.lower() == "is more than":
                max_time = time_now - unit_convert(unit_=unit, value=values[0])
            else:
                # over all time
                min_time = None
                max_time = None
        except Exception as e:
            logger.exception("date_relation_convert catch exception: {}".format(e))

        return min_time, max_time

    def get_shop_timezone_mongo(self, store_name):
        """
        获取当前店铺的时区
        :param store_name: 店铺名称
        :return: 时区名称，eg:'Asia/Shanghai'
        """
        logger.info("get_shop_timezone_mongo start, store name is %s" % store_name)
        timezone_str = "Asia/Shanghai"
        try:
            mdb = MongoDBUtil(mongo_config=self.mongo_config)
            db = mdb.get_instance()
            # 从shop_info表中查找对应的时区
            shop_info = db["shopify_shop_info"]

            timezone = shop_info.find_one({"site_name": store_name}, {"_id": 0, "iana_timezone": 1})
            if timezone and timezone["iana_timezone"]:
                timezone_str = timezone["iana_timezone"]
            return timezone_str
        except Exception as e:
            logger.exception("get_shop_timezone_mongo catch exception={}".format(e))
            return timezone
        finally:
            mdb.close()

    def date_relation_convert_mongo(self, relation, values, store_name, unit="days"):
        """
        转换日期条件为起\止时间点
        :param relation: 日期条件，如before, in the past...
        :param values: 条件值列表
        :param unit: 日期单位
        :return: 起＼止时间点，时间字符串类型
        """
        def unit_convert(unit_, value):
            if unit_ in ["days", 'weeks']:
                str_delta = "datetime.timedelta({}={})".format(unit_, value)
            else:
                str_delta = "relativedelta({}={})".format(unit_, value)
            return eval(str_delta)

        min_time = None
        max_time = None
        try:
            format_str_0 = format_str_1 = "%Y-%m-%d %H:%M:%S"
            # 兼容一下时间格式
            if isinstance(values[0], str):
                if len(values[0]) <= 10:
                    format_str_0 = format_str_1 = "%Y-%m-%d"

            time_now = datetime.datetime.now()
            if relation.lower() in "is in the past":
                min_time = time_now - unit_convert(unit_=unit, value=values[0])
            elif relation.lower() in "is before":
                max_time = datetime.datetime.strptime(values[0], format_str_0)
            elif relation.lower() in "is after":
                min_time = datetime.datetime.strptime(values[0], format_str_0)
            elif relation.lower() == "is between date" or relation.lower() == "between date":
                min_time = datetime.datetime.strptime(values[0], format_str_0)
                max_time = datetime.datetime.strptime(values[1], format_str_1)
            elif relation.lower() == "is between" or relation.lower() == "between":
                max_time = time_now - unit_convert(unit_=unit, value=values[0])
                min_time = time_now - unit_convert(unit_=unit, value=values[1])
            else:
                # over all time
                min_time = None
                max_time = None
            # 按照store的时区转换
            iana_timezone = self.get_shop_timezone_mongo(store_name)
            if min_time:
                min_time = self.timezone_transform(min_time, 'Asia/Shanghai', iana_timezone)
            if max_time:
                max_time = self.timezone_transform(max_time, 'Asia/Shanghai', iana_timezone)
        except Exception as e:
            logger.exception("date_relation_convert catch exception: {}".format(e))
            # return min_time, max_time
        return min_time, max_time

    def timezone_transform(self, date_time, src_timezone, dst_timezone):
        """
        将date_time从src_timezone时区转换成dst_timezone时区的时间
        :param date_time: datetime时间类型or时间字符串，格式为："%Y-%m-%d %H:%M:%S"
        :param src_timezone: 源时区名称，eg:'Asia/Shanghai'
        :param dst_timezone: 目标时区名称，同src_timezone
        :return: 转换后的datetine时间类型 or 时间字符串，格式为："%Y-%m-%d %H:%M:%S";
        转换后的时间有6分钟的时间精度调整
        """
        try:
            if isinstance(date_time, str):
                date_time = datetime.datetime.strptime(date_time[0:19], "%Y-%m-%d %H:%M:%S")
            result_time = date_time.replace(tzinfo=timezone(src_timezone)).astimezone(timezone(dst_timezone))
            if dst_timezone != 'Asia/Shanghai':
                result_time += datetime.timedelta(0, 360)
            return result_time.strftime("%Y-%m-%d %H:%M:%S").replace(" ", "T")
        except Exception as e:
            logger.error("timezone_transform exception e: %s" % e)

    def get_customers_by_condition(self, condition, store_id):
        """
        根据综合条件，筛选出符合的顾客列表
        :param condition: 条件　字典
        :param store_id: 店铺id
        :return: 顾客uuid列表
        """
        group_conditions = condition.get("group_condition", [])
        group_customers = []
        final_customers = None
        try:
            for gc in group_conditions:
                children = gc.get("children", [])
                children_final_customers = None
                child_relation = gc.get("relation", "&&")
                for child in children:
                    condition_name = child.get("condition", "")
                    customers = self.common_adapter(condition=condition_name, store_id=store_id, relations=child.get("relations", []))
                    if customers is not None:
                        # 当条件为且时，　任一条件的结果为空时，则break, 且置总结果为空
                        if child_relation == "&&":
                            if not customers:
                                children_final_customers = []
                                break

                            if children_final_customers is None:
                                children_final_customers = customers
                            else:
                                children_final_customers = list(set(children_final_customers).intersection(set(customers)))
                        else:
                            if children_final_customers is None:
                                children_final_customers = customers
                            else:
                                children_final_customers = list(set(children_final_customers).union(set(customers)))

                    else:
                        # 如果某个条件的处理还未实现，则跳过
                        logger.error("This condition have no processor!! condition name={}".format(condition_name))
                        continue

                # logger.info("adapt group condition, name={}, relation={}, children={}, customers={}".format(
                #     gc.get("group_name", "unknown"), gc.get("relation", "unknown"), gc.get("children", []), children_final_customers))
                group_customers.append(children_final_customers)

            gp_relations = condition.get("relation", "").split(",")

            i = 0
            for child_customers in group_customers:
                if final_customers is None:
                    final_customers = child_customers
                    continue

                if child_customers is not None:
                    if gp_relations[i] == "&&":
                        final_customers = list(set(final_customers).intersection(set(child_customers)))
                    else:
                        final_customers = list(set(final_customers).union(set(child_customers)))
                i += 1
        except Exception as e:
            logger.exception("get_customers_by_condition catch exception: {}, condition={}".format(e, condition))

        logger.debug("get_customers_by_condition succeed: \nstore_id={}, \ncondition={}, \nfinal_customers={}".format(store_id, condition, final_customers))
        return final_customers

    def get_conditions(self, store_id=None, condition_id=None, only_new=False):
        """
        批量获取customer group中的condition
        :param store_id:
        :param condition_id:
        :return:
        """
        result = []
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user, password=self.db_password).get_instance()
            cursor = conn.cursor(cursor=pymysql.cursors.DictCursor) if conn else None
            if not cursor:
                return result

            # between date
            if store_id and condition_id:
                cursor.execute(
                    """select `store_id`, `id`, `title`, `relation_info` from `customer_group` where store_id=%s and id=%s""",
                    (store_id, condition_id))
            elif store_id:
                if only_new == True:
                    cursor.execute(
                        """select `store_id`, `id`, `title`, `relation_info` from `customer_group` where store_id=%s and state=0""",
                        (store_id,))
                else:
                    cursor.execute(
                        """select `store_id`, `id`, `title`, `relation_info` from `customer_group` where store_id=%s and state!=2""",
                        (store_id, ))
            elif condition_id:
                cursor.execute(
                    """select `store_id`, `id`, `title`, `relation_info` from `customer_group` where id=%s""",
                    (condition_id, ))
            else:
                # 未删除的才取出来
                # 剔除amdin
                if only_new:
                    cursor.execute(
                        """select `store_id`, `id`, `title`, `relation_info` from `customer_group` where store_id>1 and state=0""")
                else:
                    cursor.execute(
                        """select `store_id`, `id`, `title`, `relation_info` from `customer_group` where store_id>1 and state!=2""")

            res = cursor.fetchall()
            if res:
                for ret in res:
                    result.append(ret)
        except Exception as e:
            logger.exception("adapt_last_order_created_time e={}".format(e))
            return result
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0
        return result

    def parse_new_customer_group_list(self):
        self.update_customer_group_list(only_new=True)

    def update_customer_group_list(self, store_id=None, only_new=False):
        """
        更新所有待解析的customer group, 同时创建email group id
        :param store_id:
        :return:
        """
        logger.info("update_customer_group_list trigger, store_id={}, only_new={}".format(store_id, only_new))
        conditions = self.get_conditions(store_id=store_id, only_new=only_new)
        values = []
        for cond in conditions:
            customer_list = self.get_customers_by_condition(condition=json.loads(cond["relation_info"]), store_id=cond["store_id"])
            # values.append((str(customer_list), datetime.datetime.now(), cond["id"]))
            values.append({"customer_list": customer_list, "group_id": cond["id"], "store_id": cond["store_id"], "group_title": cond["title"]})

        if not values:
            logger.warning("there have not customer group need update customer list")
            return True

        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user, password=self.db_password).get_instance()
            cursor = conn.cursor(cursor=pymysql.cursors.DictCursor) if conn else None
            if not cursor:
                return False

            for value in values:
                group_id = value["group_id"]
                store_id = value["store_id"]
                group_title = value["group_title"]
                source, store_site_name = self.get_store_source(store_id)
                # 新的顾客列表，转成邮件
                new_customer_list = value["customer_list"]
                dt_now = datetime.datetime.now()

                # 获取这个店铺所有处于退订状态的客户邮箱
                cursor.execute("select `email` from customer_unsubscribe where store_id=%s and (`unsubscribe_status`=1 or (`unsubscribe_status`=2 and `unsubscribe_date`<%s))", (store_id, dt_now))
                unsub_email = cursor.fetchall()
                unsub_email_list = []
                should_delete_unsub_email_list = []
                if unsub_email:
                    unsub_email_list = [ue["email"] for ue in unsub_email]

                if new_customer_list:
                    if source == 0:
                        new_customer_email_list = self.customer_uuid_to_email_mongo(new_customer_list, store_site_name)
                    else:
                        new_customer_email_list = self.customer_uuid_to_email(new_customer_list)

                    # 从需要新增的客户中，排除那些取消订阅的或者处于休眠期的客户
                    if ENABLE_SUBSCRIBE and unsub_email_list:
                        new_customer_email_list = list(set(new_customer_email_list).difference(set(unsub_email_list)))
                else:
                    new_customer_email_list = []
                logger.info("update group id={}, new customer list length={}".format(group_id, len(new_customer_list)))

                # 获取这个group, 看看他有没有已经创建过email group id
                cursor.execute("select `uuid`, `customer_list` from `customer_group` where id=%s", (value["group_id"], ))
                customer_group = cursor.fetchone()
                if customer_group:
                    old_uuid = customer_group["uuid"]
                    if customer_group["customer_list"]:
                        old_customer_list = eval(customer_group["customer_list"])
                        if old_customer_list:
                            if source == 0:
                                old_email_list = self.customer_uuid_to_email_mongo(old_customer_list, store_site_name)
                            else:
                                old_email_list = self.customer_uuid_to_email(old_customer_list)

                            # 从现有的收件人中排除那些取消订阅的或者处于休眠期的客户,同时出现在旧用户列表和取消列表中的用户才是需要删除的
                            if unsub_email_list and old_email_list:
                                should_delete_unsub_email_list = list(set(old_email_list).intersection(set(unsub_email_list)))
                        else:
                            old_email_list = []
                    else:
                        old_customer_list = []
                else:
                    old_uuid = ""
                    old_customer_list = []

                cursor.execute("select `name`, `sender`, `sender_address` from `store` where id=%s", (store_id,))
                store = cursor.fetchone()
                if not store:
                    logger.warning("store is not found, store id={}".format(store_id))
                    continue

                exp = ems_api.ExpertSender(from_name=store["sender"], from_email=store["sender_address"])

                # 判断这个group是不是已经被解析过且创建了邮件组id
                if old_uuid:
                    logger.info("customer group have been analyzed, old uuid={}, need update".format(old_uuid))
                    new_add_customers = list(set(new_customer_list) - set(old_customer_list))   #新增加的客户id
                    delete_customers = list(set(old_customer_list) - set(new_customer_list))     #需要删除的客户id
                    if new_add_customers:
                        if source == 0:
                            new_add_customers_email_list = self.customer_uuid_to_email_mongo(new_add_customers, store_site_name)
                        else:
                            new_add_customers_email_list = self.customer_uuid_to_email(new_add_customers)

                        while new_add_customers_email_list:
                            if len(new_add_customers_email_list) >= 100:
                                front_99 = new_add_customers_email_list[0:99]
                                new_add_customers_email_list = new_add_customers_email_list[99:]
                            else:
                                front_99 = new_add_customers_email_list
                                new_add_customers_email_list = []

                            diff_add_result = exp.add_subscriber(old_uuid, front_99)
                            if diff_add_result["code"] == 1:
                                logger.info("add_subscriber succeed, uuid={}".format(old_uuid))
                            elif diff_add_result["code"] == 3:
                                logger.warning("add_subscriber partly succeed, uuid={}, invalid email={}".format(old_uuid, diff_add_result.get("invalid_email", [])))
                            else:
                                logger.error("update_customer_group_list add_subscriber failed, diff_add_result={}, "
                                             "group id={}, uuid={}, add emails={}".format(diff_add_result, group_id, uuid, front_99))

                    if delete_customers:
                        if source == 0:
                            delete_customers_email_list = self.customer_uuid_to_email_mongo(delete_customers, store_site_name)
                        else:
                            delete_customers_email_list = self.customer_uuid_to_email(delete_customers)

                        if delete_customers_email_list:
                            for email in delete_customers_email_list:
                                diff_delete_result = exp.delete_subscriber(email, old_uuid)
                                if diff_delete_result["code"] != 1:
                                    logger.error("update_customer_group_list delete_subscriber failed, diff_delete_result={}"
                                                ", group id={}, uuid={}, delete email={}".format(diff_delete_result, group_id, old_uuid, email))
                    # 删除那些取消订阅的
                    if ENABLE_SUBSCRIBE and should_delete_unsub_email_list:
                        for ue in should_delete_unsub_email_list:
                            try:
                                # 从所有人中删除那些取消订阅的
                                exp.delete_subscriber(ue, old_uuid)
                            except:
                                pass

                    cursor.execute(
                        "update `customer_group` set customer_list=%s, members=%s, update_time=%s, state=1 where id=%s",
                        (str(new_customer_list), len(new_customer_list), datetime.datetime.now(), group_id))
                    conn.commit()
                else:
                    # 还没有创建过email group id
                    logger.info("customer group have not been analyzed, need analyze")
                    # 如果customer list为空，则暂时不创建email group
                    # if not new_customer_email_list:
                    #     continue

                    email_group_name = f"{store['name']}_{group_title}_{datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S')}".replace(" ", "_")
                    create_result = exp.create_subscribers_list(name=email_group_name)

                    if create_result["code"] == 1:
                        uuid = create_result["data"]
                        logger.info("customer group analyze and create email group id={}".format(uuid))
                        while new_customer_email_list:
                            if len(new_customer_email_list) >= 100:
                                front_99 = new_customer_email_list[0:99]
                                new_customer_email_list = new_customer_email_list[99:]
                            else:
                                front_99 = new_customer_email_list
                                new_customer_email_list = []

                            add_result = exp.add_subscriber(str(uuid), front_99)
                            if add_result["code"] != 1 and add_result["code"] != 3:
                                logger.error("update_customer_group_list add_subscriber failed, group id={}, uuid={}, result={}".format(group_id, uuid, add_result))
                        cursor.execute(
                            "update `customer_group` set uuid=%s, customer_list=%s, members=%s, update_time=%s, state=1 where id=%s",
                            (str(uuid), str(new_customer_list), len(new_customer_list), datetime.datetime.now(), group_id))
                        conn.commit()
                    else:
                        logger.error("update_customer_group_list create_subscribers_list failed, group id={}, result={}".format(group_id, create_result))
        except Exception as e:
            logger.exception("update_customer_group_list e={}".format(e))
            return False
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0
        return True

    def filter_purchase_customer(self, store_id, start_time, end_time=datetime.datetime.now()):

        """
        搜索在flow过程中完成了一次购买的用户(发第一封邮件时不需要筛选，以后每次发邮件前都需要)
        :param store_id: 用户所属的店铺
        :param start_time:  flow的创建时间
        :param end_time:  截止到目前为止，发邮件前的时间
        :return: 满足条件的用户id列表
        """
        logger.info("customers by makes a purchase, store_id={}".format(store_id))
        adapt_customers = self.order_filter(store_id=store_id, status=1, relation="more than",
                                            value=0, min_time=start_time, max_time=end_time)
        return adapt_customers

    def filter_purchase_customer_mongo(self, store_id, start_time, store_name, end_time=datetime.datetime.now()):

        """
        搜索在flow过程中完成了一次购买的用户(发第一封邮件时不需要筛选，以后每次发邮件前都需要)
        :param store_id: 用户所属的店铺
        :param start_time:  flow的创建时间
        :param end_time:  截止到目前为止，发邮件前的时间
        :return: 满足条件的用户id列表
        """
        logger.info("customers by makes a purchase, store_id={}".format(store_id))
        adapt_customers = self.order_filter_mongo(store_id=store_id, status=1, store_name=store_name, relation="more than",
                                            value=0, min_time=start_time, max_time=end_time)
        return adapt_customers

    def filter_unsubscribed_and_snoozed_in_the_customer_list(self, store_id):
        """
        获取当前店铺取消订阅或正在休眠的收件人
        :param store_id: 店铺ID
        :return: 满足条件的收件人email列表
        """
        logger.info(
            "get unsubscribed and snoozed in the customer unsubscribe table, store_id={}".format(store_id))
        result = []
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user,
                          password=self.db_password).get_instance()
            cursor = conn.cursor(cursor=pymysql.cursors.DictCursor) if conn else None
            if not cursor:
                return result
            # 更新休眠收件人的状态
            cursor.execute(
                """select id,unsubscribe_date from `customer_unsubscribe` where store_id=%s and unsubscribe_status=2""", (store_id,))
            snoozed = cursor.fetchall()
            if snoozed:
                update_ids = []
                for customer in snoozed:
                    if customer["unsubscribe_date"] < datetime.datetime.now():
                        update_ids.append(customer["id"])
                if update_ids:
                    cursor.execute(
                        """update `customer_unsubscribe` set unsubscribe_date=null, unsubscribe_status=0, update_time=%s where id in %s""",
                        (datetime.datetime.now(), tuple(update_ids)))
                    conn.commit()
                    logger.info("update snoozed customers status success.")
            cursor.execute(
                """select `email` from `customer_unsubscribe` where store_id=%s and unsubscribe_status in (1,2)""", (store_id,))
            res = cursor.fetchall()
            if res:
                for ret in res:
                    result.append(ret.get('email'))
        except Exception as e:
            logger.exception("get unsubscribed and snoozed exception: e = {}".format(e))
            return result
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0
        return result

    def filter_received_customer(self, store_id, email_id):

        """
        7天之内收到过此邮件的用户
        :param store_id: 用户所属的店铺
        :return: 满足条件的用户uuid列表
        """
        logger.info(" the customer received an email from this campaign in the last 7 days, store_id={}".format(store_id))
        result = []
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user,
                          password=self.db_password).get_instance()
            cursor = conn.cursor(cursor=pymysql.cursors.DictCursor) if conn else None
            if not cursor:
                return result

            cursor.execute(
                """select c.uuid from `subscriber_activity`as s join `customer` as c on s.email=c.customer_email 
                where s.store_id=%s and s.message_uuid=%s and s.type=2 and s.opt_time > %s""",
                (store_id, email_id, datetime.datetime.now()-datetime.timedelta(days=7)))
            res = cursor.fetchall()
            if res:
                for ret in res:
                    result.append(ret.get('uuid'))
        except Exception as e:
            logger.exception("the customer received an email from this campaign in the last 7 days exceptions: e = {}".format(e))
            return result
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0
        return result

    def get_site_name_by_sotre_id(self, store_id):
        """
        通过store_id获取店铺名称
        :param store_id:
        :return: 对应的店铺名称
        """
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user,
                          password=self.db_password).get_instance()
            cursor = conn.cursor(cursor=pymysql.cursors.DictCursor) if conn else None
            if not cursor:
                return None
            cursor.execute("select name from `store` where id=%s", (store_id,))
            res = cursor.fetchone()
            if res:
                return res["name"]
        except Exception as e:
            logger.exception("the customer received an email from this campaign in the last 7 days exceptions: e = {}".format(e))
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0

    def filter_received_customer_mongo(self, store_id, email_id, store_name):

        """
        7天之内收到过此邮件的用户
        :param store_id: 用户所属的店铺
        :param email_id: 发送邮件后返回的邮件ID
        :param store_name: 店铺名称
        :return: 满足条件的用户uuid列表
        """
        logger.info("the customer received an email from this campaign in the last 7 days, store_id={}".format(store_id))
        result = []
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user,
                          password=self.db_password).get_instance()
            cursor = conn.cursor(cursor=pymysql.cursors.DictCursor) if conn else None
            if not cursor:
                return result
            # 先查出符合条件的email
            cursor.execute(
                """select email from `subscriber_activity` where store_id=%s and message_uuid=%s and type=2 and opt_time > %s""",
                (store_id, email_id, datetime.datetime.now() - datetime.timedelta(days=7)))
            res = cursor.fetchall()
            if res:
                for ret in res:
                    result.append(ret.get('email'))
            # site_name = self.get_site_name_by_sotre_id(store_id)
            # if not site_name:
            #     logger.warning("site name exception.site name is %s" % site_name)
            # 转换成uuid列表
            result = self.customer_email_to_uuid_mongo(result, store_name)
        except Exception as e:
            logger.exception("the customer received an email from this campaign in the last 7 days catch exception={}".format(e))
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0
        return result

    def customer_email_to_uuid_mongo(self, email_list, site_name):
        """
        customer 的 email 转化成对应的 uuid
        :param email_list:
        :return: uuid 列表
        """
        uuid_list = []
        try:
            mdb = MongoDBUtil(mongo_config=self.mongo_config)
            db = mdb.get_instance()
            # 从customer表中查找对应的uuid
            customer = db["shopify_customer"]
            customers = customer.find({"email": {"$in": email_list}, "site_name": site_name}, {"_id":0, "id":1})
            for cus in customers:
                uuid_list.append(cus["id"])
        except Exception as e:
            logger.exception("customer_email_to_uuid_mongo catch exception={}".format(e))
            return uuid_list
        finally:
            mdb.close()
        return uuid_list

    def get_trigger_conditions(self, store_id=None, condition_id=None):
        """
        批量获取email trigger中的condition(启用的flow)
        :param store_id: 可选，店铺ID
        :param condition_id: 可选，email_trigger_id
        :return:
        """
        result = []
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user,
                          password=self.db_password).get_instance()
            cursor = conn.cursor(cursor=pymysql.cursors.DictCursor) if conn else None
            if not cursor:
                return result

            # between date
            if store_id and condition_id:
                cursor.execute(
                    """select `store_id`, `id`, `title`, `relation_info`, `email_delay`, `note`, `customer_list`, `customer_list_id` from `email_trigger` where store_id=%s and id=%s""",
                    (store_id, condition_id))
            elif store_id:
                # 未删除的才取出来
                cursor.execute(
                    """select `store_id`, `id`, `title`, `relation_info`, `email_delay`, `note`, `customer_list`, `customer_list_id` from `email_trigger` where store_id=%s and status=1 and draft=0""",
                    (store_id,))
            elif condition_id:
                cursor.execute(
                    """select `store_id`, `id`, `title`, `relation_info`, `email_delay`, `note`, `customer_list`, `customer_list_id` from `email_trigger` where id=%s""",
                    (condition_id,))
            else:
                # 未删除的才取出来
                # 把admin剔除
                cursor.execute(
                    """select `store_id`, `id`, `title`, `relation_info`, `email_delay`, `note`, `customer_list`, `customer_list_id` from `email_trigger` where status=1 and store_id!=1 and draft=0""")

            res = cursor.fetchall()
            if res:
                for ret in res:
                    result.append(ret)
        except Exception as e:
            logger.exception("get trigger conditions exception: {}".format(e))
            return result
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0
        return result

    def store_sender_and_email_by_id(self,store_id):
        """
        获取商店发送者和email
        :param store_id: 店铺ID
        :return: `name`, `sender`, `sender_address`
        """
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user,
                          password=self.db_password).get_instance()
            cursor = conn.cursor(cursor=pymysql.cursors.DictCursor) if conn else None
            if not cursor:
                return None
            cursor.execute("select `name`, `sender`, `sender_address`, `domain`, `service_email` from `store` where id=%s", (store_id,))
            store = cursor.fetchone()
            if not store:
                logger.warning("store is not found, store id={}".format(store_id))
                return None
        except Exception as e:
            logger.exception("update customer list from email_trigger exception: {}".format(e))
            return None
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0
        return store

    def customer_uuid_to_email(self, customer_uuid_list):
        """
        将customer_uuid转换成email
        :param customer_uuid_list: customer uuid列表
        :return: email 列表
        """
        email_list = []
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user,
                          password=self.db_password).get_instance()
            cursor = conn.cursor(cursor=pymysql.cursors.DictCursor) if conn else None
            if not cursor:
                return None
            cursor.execute("select `customer_email` from `customer` where uuid in %s", (customer_uuid_list,))
            store = cursor.fetchall()
            if not store:
                logger.warning("not found any data")
                return email_list

            email_list = list(set([s["customer_email"] for s in store if s["customer_email"]]))
        except Exception as e:
            logger.exception("customer uuid to customer email exception: {}".format(e))
            return email_list
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0
        return email_list

    def customer_email_to_uuid(self, email_list, store_id):
        """
        将emial 转换成 uuid
        :param email_list: email 列表
        :param store_id: 所属店铺
        :return: uuid 列表
        """
        uuid_list = []
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user,
                          password=self.db_password).get_instance()
            cursor = conn.cursor(cursor=pymysql.cursors.DictCursor) if conn else None
            if not cursor:
                return None
            cursor.execute("select `uuid` from `customer` where customer_email in %s and store_id=%s", (email_list, store_id))
            store = cursor.fetchall()
            if not store:
                logger.warning("not found any data")
                return uuid_list

            uuid_list = list(set([s["uuid"] for s in store if s["uuid"]]))
        except Exception as e:
            logger.exception("customer_email_to_uuid exception: {}".format(e))
            return uuid_list
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0
        return uuid_list

    @count_time
    def customer_uuid_to_email_mongo(self, customer_uuid_list, store_name):
        """
        将customer_uuid转换成email
        :param customer_uuid_list: customer uuid列表
        :param store_name: email 列表
        :return:
        """
        email_list = []
        try:
            mdb = MongoDBUtil(mongo_config=self.mongo_config)
            db = mdb.get_instance()
            # 从customer表中查找对应的email
            customer = db["shopify_customer"]
            customers = customer.find({"id": {"$in": customer_uuid_list}, "site_name": store_name}, {"_id": 0, "id": 1, "email": 1})
            for cus in customers:
                if cus.get("email", ""):
                    email_list.append(cus["email"])
            email_list = [em for em in email_list if em]  # 只要不为空的邮箱
            return list(set(email_list))
        except Exception as e:
            logger.exception("customer_uuid_to_email_mongo catch exception={}".format(e))
            return email_list
        finally:
            mdb.close()

    def insert_customer_list_id_from_email_trigger(self, customer_list_id, trigger_id):
        """
        插入为此flow创建的ListId
        :param customer_list_id: ListId
        :param trigger_id: flow ID
        :return:
        """
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user,
                          password=self.db_password).get_instance()
            cursor = conn.cursor(cursor=pymysql.cursors.DictCursor) if conn else None
            if not cursor:
                return False
            cursor.execute("update `email_trigger` set customer_list_id=%s where id=%s", (customer_list_id, trigger_id))
            conn.commit()
        except Exception as e:
            logger.exception("customer uuid to customer email exception: {}".format(e))
            return False
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0
        return True

    def parse_trigger_tasks(self, trigger_id=None, email_id_list=None, test_email=False):
        """
        解析触发邮件任务, 定时获取符合触发信息的新用户，并且创建定时任务
        :param trigger_id: 若为测试邮件时的triggerID
        :param email_id_list: 若为测试邮件时，需要发送邮件的email地址列表
        :param test_email: 是否为测试邮件
        :return:
        """
        # 获取所有trigger条件
        return_res_email_list = email_id_list
        trigger_conditions = self.get_trigger_conditions(condition_id=trigger_id)  # 可以直接通过triggerID获取trigger信息
        for cond in trigger_conditions:
            update_list = []
            insert_list = []
            store_id, t_id, title, relation_info, email_delay, note, old_customer_list, customer_list_id = cond.values()
            if email_id_list is None:
                customer_list = self.get_customers_by_condition(condition=json.loads(cond["relation_info"]),
                                                              store_id=cond["store_id"])
            else:
                customer_list = email_id_list
            logger.info("search customers by trigger conditions success. trigger_id = %s" % t_id)
            if not customer_list:
                # 无符合触发条件的用户
                logger.warning("Not found customers matching the search relation_info: %s"% json.loads(cond["relation_info"]))
                continue
            # 计算新增用户，创建新的任务，第一次应全是新增用户
            if not old_customer_list:
                old_customer_list = []
            elif not eval(str(old_customer_list)):
                old_customer_list = []
            else:
                old_customer_list = eval(old_customer_list)
            # new_customer_list = list(set(customer_list)-set(old_customer_list))
            new_customer_list = customer_list
            if not new_customer_list:
                # 无新增符合触发条件的用户
                logger.warning("No new customers.")
                continue
            logger.info("some new customers into customer_list. trigger_id = %s" % t_id)
            old_customer_list.extend(new_customer_list)
            update_list.append((str(old_customer_list), datetime.datetime.now(), t_id))

            # 1、将customer_list反填回数据库
            self.update_customer_list_from_trigger(update_list)
            logger.info("email_trigger update_customer_list_from_trigger success.")

            # 创建任务之前，应该更新一下创建收件人列表
            store = self.store_sender_and_email_by_id(store_id)
            if not store:
                logger.error("store(id=%s) is not exists." % store_id)
                continue
            ems = ems_api.ExpertSender(from_name=store["sender"], from_email=store["sender_address"])
            if not customer_list_id:
                # 创建收件人列表
                res = ems.create_subscribers_list(title)  # 以flow的title命名为收件人列表名称
                if res["code"] != 1:
                    logger.error("create subscribers list failed. the reason is %s" % res["msg"])
                    continue
                customer_list_id = res["data"]
                # 将ListId反填回数据库
                r = self.insert_customer_list_id_from_email_trigger(customer_list_id, t_id)
                if not r:
                    logger.error("insert_customer_list_id_from_email_trigger failed")
                    continue
            # 获取store的from_type, store_name
            from_type, store_site_name = self.get_store_source(store_id)
            # 将new_customer_list转换成邮箱地址列表
            email_list = self.customer_uuid_to_email(new_customer_list) if from_type else self.customer_uuid_to_email_mongo(new_customer_list, store_site_name)
            if not test_email:
                # 对new_customer_list里的收件人进行取消订阅或休眠过滤
                unsubscribed_and_snoozed = self.filter_unsubscribed_and_snoozed_in_the_customer_list(store_id)
                if ENABLE_SUBSCRIBE:
                    email_list = list(set(email_list) - set(unsubscribed_and_snoozed))
                logger.info("filter unsubscribed and snoozed in the customer list in store(id=%s), include: %s" % (
                store_id, set(unsubscribed_and_snoozed)))
            logger.info("new customer list length is %s" % len(email_list))
            # 添加收件人,每次添加不能超过100个收件人
            times = int(len(email_list)//99) + 1
            for t in range(times):
                rest = ems.add_subscriber(customer_list_id, email_list[99*t:99*(t+1)])
                if rest["code"]==-1 or rest["code"]==2:
                    logger.error("add subscribers failed, the reason is %s" % rest["msg"])
                    continue
            invalid_email = rest.get("invalid_email", [])
            valid_email = list(set(email_list) - set(invalid_email))  # 添加到收件人列表成功的邮箱
            logger.info("add subscriber success.customer_list_id is %s" % customer_list_id)
            return_res_email_list = valid_email
            if not valid_email:
                # 无新增符合触发条件的用户
                logger.warning("No new customers were successfully added to the subscriber list.")
                continue
            # ToDo parse email_delay
            excute_time = datetime.datetime.now()+ datetime.timedelta(minutes=1)  # flow从此刻开始，为了避免程序运行时间耽搁，导致第一封邮件容易过去，自动延后5分钟
            for item in json.loads(email_delay):
                if item["type"] == "Email":  # 代表是邮件任务
                    template_id, unit = item["value"], item["unit"]
                    # 通过template_id去创建一个事务性邮件，并返回email_uuid
                    subject, html, product_condition, is_cart = self.get_template_info_by_id(template_id)
                    if not subject:
                        continue
                    email_uuid = self.create_trigger_email_by_template(store_id, template_id, subject, html, t_id)
                    # 将触发邮件任务参数增加到待入库数据列表中
                    valid_email_id_list = self.customer_email_to_uuid(valid_email, store_id) if from_type else self.customer_email_to_uuid_mongo(valid_email, store_site_name)
                    return_res_email_list = valid_email_id_list
                    remark = unit if not test_email else "test"
                    # 如果需要发送的收件人超过100，则需要将收件人分成最多100人的若干份
                    nums = int(len(valid_email_id_list) // 100) + 1
                    for t in range(nums):
                        part_email_list = valid_email_id_list[100 * t:100 * (t + 1)]
                        insert_list.append((email_uuid, template_id, 0, remark, excute_time, str(part_email_list), t_id, 1, datetime.datetime.now(), datetime.datetime.now(), store_id))
                elif item["type"] == "Delay":  # 代表是delay
                    num, unit = item["value"], item["unit"]
                    if unit in ["weeks", "days", "hours", "minutes"]:
                        excute_time += datetime.timedelta(**{unit:num})
                    else:
                        logger.error("delay unit is error, please amend it to days or hours.")
                        continue
                else:
                    logger.error("type=%s is invalid." % item["type"])
                    continue

            # 2、拆解的任务入库email_task
            self.insert_email_task_from_trigger(insert_list)
            logger.info("email_trigger insert_email_task_from_trigger success.")
        return return_res_email_list

    def update_customer_list_from_trigger(self, customer_lists):
        """
        更新 email_trigger 表中 customer_list
        :param customer_lists: 通过trigger_info筛选出来的用户列表
        :return:
        """
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user,
                          password=self.db_password).get_instance()
            cursor = conn.cursor(cursor=pymysql.cursors.DictCursor) if conn else None
            if not cursor:
                return False
            if customer_lists:
                cursor.executemany(
                    """update `email_trigger` set customer_list=%s, update_time=%s where id=%s""",
                    (customer_lists))
                conn.commit()
                logger.info("update customer list from email_trigger success.")
            else:
                logger.warning("customer_lists is empty.")
        except Exception as e:
            logger.exception("update customer list from email_trigger exception: {}".format(e))
            return False
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0
        return True

    def insert_email_task_from_trigger(self, datas):
        """
        插入 email_task 表
        :param datas:
        :return:
        """
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user,
                          password=self.db_password).get_instance()
            cursor = conn.cursor(cursor=pymysql.cursors.DictCursor) if conn else None
            if not cursor:
                return False
            if datas:
                cursor.executemany(
                    """insert into email_task (uuid, template_id,status,remark,execute_time,customer_list,email_trigger_id,type,create_time,update_time,store_id) 
                    values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", (datas))
                conn.commit()
                logger.info("insert email task from trigger success.")
            else:
                logger.warning("datas is empty.")
        except Exception as e:
            logger.exception("insert email task from trigger exception: {}".format(e))
            return False
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0
        return True

    def create_trigger_email_by_template(self, store_id, template_id, subject, html, email_trigger_id):
        """
        若无对应模板的事务性邮件，则创建； 若有，则需要更新一下
        :param store_id: 所属店铺
        :param template_id: 模板ID
        :param subject: 邮件主题
        :param html: 邮件内容
        :param email_trigger_id: 所属trigger ID
        :return:
        """
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user,
                          password=self.db_password).get_instance()
            cursor = conn.cursor(cursor=pymysql.cursors.DictCursor) if conn else None
            if not cursor:
                return None
            # 获取当前店铺name,email
            cursor.execute("select `name`, `sender`, `sender_address` from `store` where id=%s", (store_id,))
            store = cursor.fetchone()
            if not store:
                raise Exception("store is not found, store id={}".format(store_id))
            ems = ems_api.ExpertSender(from_name=store["sender"], from_email=store["sender_address"])
            # 通过template_id查询记录
            cursor.execute("select `id`,`uuid` from `email_record` where store_id=%s and email_template_id=%s and type=1", (store_id, template_id))
            email_res = cursor.fetchall()
            if not email_res:
                # 暂无数据，需要创建，先获取email_uuid
                res = ems.create_transactional_message(subject=subject, html=html)
                if res["code"] != 1:
                    raise Exception(res["msg"])
                email_uuid = res["data"]
                # 创建email_record数据
                cursor.execute(
                    """insert into email_record (uuid,sents,opens,clicks,unsubscribes,open_rate,click_rate,unsubscribe_rate,store_id,email_template_id,type,email_trigger_id,create_time,update_time) 
                    values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", (email_uuid,0,0,0,0,0.0,0.0,0.0,store_id,template_id,1,email_trigger_id,datetime.datetime.now(),datetime.datetime.now()))
                conn.commit()
                logger.info("insert trigger email from email_record success.")
            else:
                logger.info("email_record data was exists. need to update email html templte")
                # 更新邮件内容
                email_uuid = email_res[0]["uuid"]
                res = ems.update_transactional_message(email_id=email_uuid, subject=subject, html=html)
                if res["code"] != 1:
                    raise Exception(res["msg"])
                logger.info("update transactional message success of email_uuid=%s" % email_uuid)
            # # 查询此模板ID对应的email_uuid
            # cursor.execute("select `uuid`, `email_template_id` from `email_record` where email_template_id=%s and email_trigger_id=%s", (template_id,email_trigger_id))
            # result = cursor.fetchone()
            return email_uuid
        except Exception as e:
            logger.exception("insert email task from trigger exception: {}".format(e))
            return None
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0

    def get_template_info_by_id(self, template_id):
        """
        获取模板内容信息
        :param template_id:
        :return:
        """
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user,
                          password=self.db_password).get_instance()
            cursor = conn.cursor(cursor=pymysql.cursors.DictCursor) if conn else None
            if not cursor:
                return False
            cursor.execute("select subject, html, product_condition, is_cart from email_template where id=%s", (template_id))
            result = cursor.fetchone()
            logger.info("get template info by id success.")
            if result:
                return result["subject"], result["html"], result["product_condition"], result["is_cart"]
            else:
                logger.error("Not found this email_template(id=%s)" % template_id)
                return None,None,None,None
        except Exception as e:
            logger.exception("get template info by id exception: {}".format(e))
            return False
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0

    def update_repeat_task_by_id(self, task_id):
        """
        通过task_id删除此条数据
        :param task_id: 主键ID
        :return:
        """
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user,
                          password=self.db_password).get_instance()
            cursor = conn.cursor(cursor=pymysql.cursors.DictCursor) if conn else None
            if not cursor:
                return False
            # cursor.execute("delete from email_task where id=%s", (task_id))
            now_time = datetime.datetime.now()
            cursor.execute("update email_task set status=5,remark='repeat',finished_time=%s,update_time=%s where id=%s", (now_time, now_time, task_id))
            conn.commit()
            logger.info("update email repeat task success. id = %s" % task_id)
            return True
        except Exception as e:
            logger.exception("update email repeat task by id({}) exception: {}".format(task_id, e))
            return False
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0

    def update_task_status(self, task_id_list):
        """
        更新task的状态为正在执行中
        :param task_id_list: 需要更新状态的task_id 列表
        :return:
        """
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user,
                          password=self.db_password).get_instance()
            cursor = conn.cursor(cursor=pymysql.cursors.DictCursor) if conn else None
            if not cursor:
                return False
            # cursor.execute("delete from email_task where id=%s", (task_id))
            # now_time = datetime.datetime.now()
            cursor.execute("update email_task set status=6 where id in %s", (tuple(task_id_list),))
            conn.commit()
            logger.info("update email executing task success. id = %s" % task_id_list)
            return True
        except Exception as e:
            logger.exception("update email executing task by id({}) exception: {}".format(task_id_list, e))
            return False
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0

    def execute_flow_task(self):
        """
        定时获取未执行的flow任务
        :return:
        """
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user,
                          password=self.db_password).get_instance()
            cursor = conn.cursor(cursor=pymysql.cursors.DictCursor) if conn else None
            if not cursor:
                logger.warning("execute_flow_task function no get mysql cursor.")
                return False
            now_time = datetime.datetime.now()
            cursor.execute("""select t.id as id,t.remark as remark,t.execute_time as execute_time,f.id as trigger_id,
            t.customer_list as customer_list, t.uuid as uuid,f.store_id as store_id,f.note as note,f.title as flow_title,
            t.create_time as create_time,f.customer_list_id as customer_list_id, t.template_id as template_id
            from email_task as t join email_trigger as f on t.email_trigger_id=f.id 
            where t.type=1 and t.status=0 and t.uuid is not null and f.customer_list_id is not null and execute_time between %s and %s""",
                           (now_time-datetime.timedelta(minutes=10), now_time+datetime.timedelta(seconds=35)))
            result = cursor.fetchall()
            logger.info("get need to execute flow email tasks success. reslut is %s" % str(result))
            # 将搜索到的task状态改为正在执行中
            task_id_list = [item["id"] for item in result]
            if not self.update_task_status(task_id_list):
                logger.error("Update email task executing status exception.waitting for next search task.")
                raise Exception("Update email task executing status exception.waitting for next search task.")
            for res in result:
                update_tuple_list = []
                recipients_list = []
                if not eval(str(res["customer_list"])):
                    continue
                customer_list = eval(res["customer_list"])
                # 获取store的from_type, store_name
                from_type, store_site_name = self.get_store_source(res["store_id"])
                test_email = True if res["remark"] == "test" else False
                if not test_email:
                    # 先排除2分钟之内收到过此邮件的收件人
                    customers_2minutes = self.get_recipients_from_email_record_by_timedelta(res["store_id"], res["uuid"], time_delta=datetime.timedelta(minutes=-2))
                    customer_list = list(set(customer_list) - set(customers_2minutes))
                    # 如果没有需要发送的邮件，应该把此条任务直接从emil_task表中删掉
                    if not customer_list:
                        logger.info(
                            "no customers need to send email, need to update the email_task status, email_task id is %s" % res[
                                "id"])
                        self.update_repeat_task_by_id(res["id"])
                        continue
                    # 对customer_list里的收件人进行note筛选(收到过此邮件的人)
                    if "customer received an email from this campaign in the last" in res["note"]:
                        for note in eval(res["note"]):
                            if "customer received an email from this campaign in the last" in note:
                                num, unit = note.split("last")[-1].strip().split(".")[0].split(" ")
                                time_dict = {unit: -int(num)}
                                customers_7day = self.get_recipients_from_email_record_by_timedelta(res["store_id"], res["uuid"], time_delta=datetime.timedelta(**time_dict))
                                customer_list = list(set(customer_list)-set(customers_7day))
                                logger.info("filter %s" % note)
                    else:
                        # 默认排除一天之内收到过此邮件的收件人
                        customers_1day = self.get_recipients_from_email_record_by_timedelta(res["store_id"], res["uuid"], time_delta=datetime.timedelta(days=-1))
                        customer_list = list(set(customer_list) - set(customers_1day))
                        logger.info("users did not choose to receive mail time filtering, default filter customers who received this email within a day.")
                        if not customer_list:
                            logger.info("no customers need to send email, need to update the email_task status, email_task id is %s" % res["id"])
                            self.update_repeat_task_by_id(res["id"])
                            continue
                    if ("customer makes a purchase" in res["note"]) and (res["remark"] != "first"):
                        # 对customer_list里的收件人进行note筛选(从task创建时间开始)
                        logger.info("start filter the customer makes a purchase.")
                        customers_purchased = self.filter_purchase_customer(res["store_id"], res["create_time"]) if from_type else self.filter_purchase_customer_mongo(res["store_id"], res["create_time"], store_site_name)
                        customer_list = list(set(customer_list) - set(customers_purchased))
                        logger.info("filter the customer makes a purchase.")
                        if not customer_list:
                            logger.info(
                                "no customers need to send email, need to update the email_task status, email_task id is %s" % res[
                                    "id"])
                            self.update_repeat_task_by_id(res["id"])
                            continue
                # 需要将uuid 转换成email
                email_list = self.customer_uuid_to_email(customer_list) if from_type else self.customer_uuid_to_email_mongo(customer_list, store_site_name)
                if not test_email:
                    # 对customer_list里的收件人进行取消订阅或休眠过滤
                    unsubscribed_and_snoozed = self.filter_unsubscribed_and_snoozed_in_the_customer_list(res["store_id"])
                    email_list = list(set(email_list) - set(unsubscribed_and_snoozed))
                    logger.info("filter unsubscribed and snoozed in the customer list in store(id=%s), include: %s" % (
                    res["store_id"], set(unsubscribed_and_snoozed)))
                send_error_info = ""
                status = 2
                recipients = []
                # 如果没有需要发送的邮件，应该把此条任务直接从emil_task表中删掉
                if not email_list:
                    logger.info("no customers need to send email, need to update the email_task status, email_task id is %s" % res["id"])
                    self.update_repeat_task_by_id(res["id"])
                    continue

                # 开始对筛选过的用户发送邮件
                store = self.store_sender_and_email_by_id(res["store_id"])
                if not store:
                    logger.error("store(id=%s) is not exists." % res["store_id"])
                    return False
                ems = ems_api.ExpertSender(from_name=store["sender"], from_email=store["sender_address"])
                for customer in email_list:
                    # 发送邮件前，有可能需要先更新一下html,获取html模板
                    subject, html, product_condition, is_cart = self.get_template_info_by_id(res["template_id"])
                    # 筛选产品，并更新邮件
                    pr = ProductRecommend()
                    if int(is_cart) == 1:
                        # 获取购物车产品
                        cart_products = pr.get_card_product_mongo(customer, store_site_name, res["flow_title"], res["template_id"], store["domain"], store["service_email"])
                    else:
                        # 获取店铺信息
                        cart_products = pr.get_card_product_mongo(customer, store_site_name, res["flow_title"], res["template_id"], store["domain"], store["service_email"], length=0)
                    logger.info("cart_products: %s" % str(cart_products))
                    top_products = []
                    if "top" in product_condition:
                        # 获取top_products
                        top_products = pr.get_top_product_by_condition(product_condition, res["store_id"], res["flow_title"], res["template_id"])
                    snippets_list = pr.generate_snippets(cart_products, top_products)
                    rest = ems.send_transactional_messages(res["uuid"], customer, res["customer_list_id"], snippets=snippets_list)
                    if rest["code"] != 1:
                        logger.error("send to email(%s) failed, the reason is %s" % (customer, rest["msg"]))
                        msg = rest["msg"]["Message"] if isinstance(rest["msg"], dict) else str(rest["msg"])
                        send_error_info += msg + "; "
                    else:
                        status = 1
                        # 发送成功的收件人记录email_record的表中
                        if customer not in recipients:
                            recipients.append(customer)
                logger.info("send transactional messages {}".format("success" if status == 1 else "fialed"))
                customer_uuid_list = self.customer_email_to_uuid_mongo(recipients, store_site_name)
                logger.info("Successful e-mails are %s in store(%s)"% (str(customer_uuid_list), store_site_name))
                old_recipients_dict = self.get_recipients_list_from_email_record(res["store_id"], res["uuid"])
                for c_uuid in customer_uuid_list:
                        old_recipients_dict.update({c_uuid: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
                # 邮件发送完毕，回填数据
                update_tuple_list.append((str(customer_uuid_list), send_error_info, datetime.datetime.now(), str(customer_list), datetime.datetime.now(), status, res["id"]))
                recipients_list.append((str(old_recipients_dict), datetime.datetime.now(), res["uuid"]))
                if recipients_list:
                    self.update_email_record_recipients_list(recipients_list)
                if update_tuple_list:
                    self.update_flow_email_task(update_tuple_list)
                logger.info("execute flow task(id=%s) finished." % res["id"])
            return True
        except Exception as e:
            logger.exception("execute flow task exception: {}".format(e))
            return False
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0

    def get_recipients_from_email_record_by_timedelta(self, store_id, email_uuid, time_delta=datetime.timedelta(seconds=1)):
        """
        获取时间范围内的customer_uuid_list
        :param store_id: 店铺ID
        :param email_uuid: email uuid
        :param time_delta: 时间范围
        :return: 收件人uuid列表
        """
        logger.info("get_recipients_from_email_record_by_timedelta start")
        recipients = []
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user,
                          password=self.db_password).get_instance()
            cursor = conn.cursor(cursor=pymysql.cursors.DictCursor) if conn else None
            if not cursor:
                return False
            cursor.execute("""select recipients from email_record where store_id=%s and uuid=%s""", (store_id, email_uuid))
            res = cursor.fetchone()
            if not res:
                return recipients
            recipients_dict = {}
            if res["recipients"] and eval(res["recipients"]):
                recipients_dict = eval(res["recipients"])
            for uuid, opt_time in recipients_dict.items():
                if datetime.datetime.strptime(opt_time, "%Y-%m-%d %H:%M:%S") > (datetime.datetime.now()+ time_delta):
                    recipients.append(uuid)
            return recipients
        except Exception as e:
            logger.exception("get_recipients_from_email_record_by_timedelta exception: {}".format(e))
            return recipients
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0

    def get_recipients_list_from_email_record(self, store_id, email_uuid):
        """
        获取已发送此邮件的收件人
        :param store_id: 店铺ID
        :param email_uuid:  email uuid
        :return: recipients_list
        """
        logger.info("get_recipients_list_from_email_record start")
        recipients_dict = {}
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user,
                          password=self.db_password).get_instance()
            cursor = conn.cursor(cursor=pymysql.cursors.DictCursor) if conn else None
            if not cursor:
                return False
            cursor.execute("""select recipients from email_record where store_id=%s and uuid=%s""", (store_id, email_uuid))
            res = cursor.fetchone()
            if not res:
                return recipients_dict
            if res["recipients"] and eval(res["recipients"]):
                recipients_dict = eval(res["recipients"])
            return recipients_dict
        except Exception as e:
            logger.exception("get_recipients_list_from_email_record exception: {}".format(e))
            return recipients_dict
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0

    def update_email_record_recipients_list(self, recipients_list):
        """
        更新已发送的收件人
        :param recipients_list: 收件人email列表
        :return:
        """
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user,
                          password=self.db_password).get_instance()
            cursor = conn.cursor(cursor=pymysql.cursors.DictCursor) if conn else None
            if not cursor:
                return False
            cursor.executemany("""update email_record set recipients=%s, update_time=%s where uuid=%s""", recipients_list)
            conn.commit()
            logger.info("update flow email record recipients datas success.")
        except Exception as e:
            logger.exception("update flow email record recipients datas exception: {}".format(e))
            return False
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0
        return True

    def update_flow_email_task(self, update_tuple_list):
        """
        更新执行任务后的数据
        :param update_tuple_list: 数据元祖列表
        :return:
        """
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user,
                          password=self.db_password).get_instance()
            cursor = conn.cursor(cursor=pymysql.cursors.DictCursor) if conn else None
            if not cursor:
                return False
            cursor.executemany("""update email_task set customer_list=%s,remark=%s,finished_time=%s,customer_list=%s,update_time=%s,status=%s 
                        where id=%s""", update_tuple_list)
            conn.commit()
            logger.info("update flow email task datas success.")
        except Exception as e:
            logger.exception("update flow email task datas exception: {}".format(e))
            return False
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0
        return True


if __name__ == '__main__':
    # condition = {"relation": "&&,||", "group_condition":
    #     [{"group_name": "123", "relation": "&&", "children": [
    #         {"condition": "Customer last click email time",
    #          "relations": [{"relation": "is in the past", "values": [15, 0], "unit": "days"}]},
    #         {"condition": "Customer last click email time", "relations": [
    #             {"relation": "is between date", "values": ["2019-01-30 00:00:00", "2019-01-25 00:00:00"],
    #              "unit": "days"}]}]},
    #      {"group_name": "456", "relation": "&&", "children": [
    #          {"condition": "Customer last click email time",
    #           "relations": [{"relation": "is in the past", "values": [333, 0], "unit": "days"}]}]}]
    #              }

    ac = AnalyzeCondition(mysql_config=MYSQL_CONFIG, mongo_config=MONGO_CONFIG)
    # ac.adapt_placed_order()
    # ac.update_customer_group_list()
    # conditions = ac.get_conditions()
    # for cond in conditions:
    #     cus = ac.get_customers_by_condition(condition=json.loads(cond["relation_info"]), store_id=cond["store_id"])
    #     print(cus)
    # print(ac.filter_purchase_customer(1, datetime.datetime(2019, 7, 24, 0, 0)))
    # print(ac.adapt_all_order(1, [{"relation":"more than","values":["0",1],"unit":"days","errorMsg":""},{"relation":"is over all time","values":[0,1],"unit":"days","errorMsg":""}]))
    # print(ac.filter_received_customer(1, 346))
    # print(ac.update_customer_group_list(store_id=29))
    # print(ac.create_trigger_email_by_template(53, 216, "Update Html TEST", """Update Html TEST""", 124))
    # print(ac.parse_new_customer_group_list())
    print(ac.parse_trigger_tasks())
    # print(ac.execute_flow_task())
    # print(ac.get_template_info_by_id(84))
    # print(ac.update_repeat_task_by_id(7443))
    # print(ac.filter_unsubscribed_and_snoozed_in_the_customer_list(5))
    # print(ac.get_site_name_by_sotre_id(2))
    # print(ac.customer_email_to_uuid_mongo(["mosa_rajvosa87@outlook.com","Quinonesbautista@Gmail.com"],"Astrotrex"))
    # print(ac.adapt_total_order_amount_mongo(1, [{"relation":"is less than","values":["1.00",1],"unit":"days","errorMsg":""},{"relation":"is over all time","values":[0,1],"unit":"days","errorMsg":""}],"Astrotrex"))
    # print(ac.adapt_customer_email_mongo(1, [{"relation":"is end with","values":["ru",1],"unit":"days","errorMsg":""},{"relation":"is over all time","values":[0,1],"unit":"days","errorMsg":""}],"Astrotrex"))
    # print(ac.adapt_is_accept_marketing_mongo(1, [{"relation":"is true","values":["ru",1],"unit":"days","errorMsg":""},{"relation":"is over all time","values":[0,1],"unit":"days","errorMsg":""}],"Astrotrex"))
    # print(ac.adapt_last_order_status())
    # print(ac.adapt_last_order_status_mongo(1, [{"relation":"is null","values":["ru",1],"unit":"days","errorMsg":""},{"relation":"is over all time","values":[0,1],"unit":"days","errorMsg":""}],"Astrotrex"))
    # ac.order_filter_mongo(5, 2, "charrcter", "more than", 1, "2019-05-31T16:27:33+08:00", "2020-05-31T16:27:33+08:00")
    # ac.order_filter(5, 1, [{"relation": "is null", "values": ["ru", 1], "unit": "days", "errorMsg": ""},{"relation": "is over all time", "values": [0, 1], "unit": "days", "errorMsg": ""}], 1,
    #                       "2019-05-31T16:27:33+08:00", "2020-05-31T16:27:33+08:00")
    # print(ac.adapt_last_order_status_mongo(1, [{"relation":"is paid","values":["ru",1],"unit":"days","errorMsg":""},{"relation":"is over all time","values":[0,1],"unit":"days","errorMsg":""}],"Astrotrex"))
    # print(ac.unpaid_order_customers_mongo("charrcter", min_time="2019-08-07T17"))
    # print(ac.get_shop_timezone_mongo("charrcter"))
    # print(ac.get_recipients_list_from_email_record(3,3))
    # print(ac.update_email_record_recipients_list([("[1,2,3]", 501)]))
    # print(ac.get_recipients_from_email_record_by_timedelta(4, 504, datetime.timedelta(days=-3)))
    # print(ac.timezone_transform("2019-08-09 05:31:41.350", 'UTC', 'Asia/Shanghai'))
    # print(ac.unpaid_order_customers_mongo("charrcter", min_time="2019-08-07T17"))
    # print(ac.customer_uuid_to_email_mongo([1077951529024,1078304604224,1079054073920], "Astrotrex"))
    # print(ac.adapt_sign_up_time_mongo(1,[{"relation":"is between date","values":["2019-08-01 00:00:00","2019-08-09 00:00:00"],"unit":"days","errorMsg":""},{"relation":"is over all time","values":[0,1],"unit":"days","errorMsg":""}], "Astrotrex"))
    # print(ac.adapt_last_order_created_time_mongo(1,[{"relation":"is between date","values":["2019-02-10 00:00:00","2019-02-11 00:00:00"],"unit":"days","errorMsg":""},{"relation":"is over all time","values":[0,1],"unit":"days","errorMsg":""}], "Astrotrex"))
    # print(ac.adapt_last_opened_email_time_mongo(1,[{"relation":"is between date","values":["2019-02-10 00:00:00","2019-02-11 00:00:00"],"unit":"days","errorMsg":""},{"relation":"is over all time","values":[0,1],"unit":"days","errorMsg":""}], "Astrotrex"))
    # print(ac.remove_email_task_by_id(950))
