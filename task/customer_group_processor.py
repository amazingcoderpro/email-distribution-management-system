#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Created by charles on 2019-07-19
# Function: 
import pymysql
import datetime
import json
from dateutil.relativedelta import relativedelta
from config import logger
from task.shopify_data_processor import DBUtil
from sdk.ems import ems_api

class AnalyzeCondition:
    def __init__(self, db_info):        
        self.db_host = db_info.get("host", "")
        self.db_port = db_info.get("port", 3306)
        self.db_name = db_info.get("db", "")
        self.db_user = db_info.get("user", "")
        self.db_password = db_info.get("password", "")
        self.condition_dict = {"Customer sign up time": self.adapt_sign_up_time,
                              "Customer last order created time": self.adapt_last_order_created_time,
                              "Customer last opened email time": self.adapt_last_opened_email_time,
                              "Customer last click email time": self.adapt_last_click_email_time,
                              "Customer placed order": self.adapt_placed_order,
                              "Customer paid order": self.adapt_paid_order,
                              "Customer order number is": self.adapt_all_order,
                              "Customer opened email": self.adapt_opened_email,
                              "Customer clicked email": self.adapt_clicked_email,
                              "Customer last order status": self.adapt_last_order_status,
                              "Customer who accept marketing": self.adapt_is_accept_marketing,
                              "Customer Email": self.adapt_customer_email,
                              "Customer total order payment amount": self.adapt_total_order_amount,
                            }
        self.note_dict = {"customer makes a purchase": self.filter_purchase_customer,
                          "customer received an email from this campaign in the last 7 days": self.filter_received_customer,
                        }
            
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
            # 判断需要查询的状态
            if status == 2:
                status = (0, 1)
            else:
                status = (status, )
            # between date
            if min_time and max_time:
                cursor.execute(
                    """select `customer_uuid`, count(1) from `order_event` where store_id=%s and status in %s
                    and `order_update_time`>=%s and `order_update_time`<=%s group by `customer_uuid`""", (store_id, status, min_time, max_time))
            # after, in the past
            elif min_time:
                cursor.execute(
                    """select `customer_uuid`, count(1) from `order_event` where store_id=%s and status in %s
                    and `order_update_time`>=%s group by `customer_uuid`""", (store_id, status, min_time))
            # before
            elif max_time:
                cursor.execute(
                    """select `customer_uuid`, count(1) from `order_event` where store_id=%s and status in %s
                    and `order_update_time`<=%s group by `customer_uuid`""", (store_id, status, max_time))
            # over all time
            else:
                cursor.execute(
                    """select `customer_uuid`, count(1) from `order_event` where store_id=%s and status in %s
                    group by `customer_uuid`""", (store_id, status))
    
            res = cursor.fetchall()
            relation_dict = {"equals": "==", "more than": ">", "less than": "<"}
    
            for uuid, count in res:
                just_str = "{} {} {}".format(count, relation_dict.get(relation), value)
                if eval(just_str):
                    customers.append(uuid)
        except Exception as e:
            logger.exception("order_filter e={}".format(e))
            return customers
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0
        return customers
    
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
        except Exception as e:
            logger.exception("adapt_sign_up_time e={}".format(e))
            return customers
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0
        return customers
    
    def adapt_last_order_created_time(self, store_id, relations):
        """
        适配出所有上次订单时间符合条件的客户id
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
                    """select `uuid` from `customer` where store_id=%s and `last_order_time`>=%s and `last_order_time`<=%s""",
                    (store_id, min_time, max_time))
            # after, in the past
            elif min_time:
                cursor.execute(
                    """select `uuid` from `customer` where store_id=%s and `last_order_time`>=%s""", (store_id, min_time))
            # before
            elif max_time:
                cursor.execute("""select `uuid` from `customer` where store_id=%s and `last_order_time`<=%s""",
                               (store_id, max_time))
            # over all time
            else:
                cursor.execute("""select `uuid` from `customer` where store_id=%s""", (store_id, ))
    
            res = cursor.fetchall()
            for uuid in res:
                customers.append(uuid[0])
        except Exception as e:
            logger.exception("adapt_last_order_created_time e={}".format(e))
            return customers
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0
        return customers

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
    
        except Exception as e:
            logger.exception("adapt_last_opened_email_time e={}".format(e))
            return customers
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0
        return customers
    
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
    
        except Exception as e:
            logger.exception("adapt_last_click_email_time e={}".format(e))
            return customers
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0
        return customers
    
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
                    """select `email`, count from `subscriber_activity` where store_id=%s and type=%s 
                    and `opt_time`>=%s group by `email`""", (store_id, opt_type, min_time))
            # before
            elif max_time:
                cursor.execute(
                    """select `email`, count from `subscriber_activity` where store_id=%s and type=%s 
                    and `opt_time`<=%s group by `email`""", (store_id, opt_type, max_time))
            # over all time
            else:
                cursor.execute(
                    """select `email`, count from `subscriber_activity` where store_id=%s and type=%s 
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
    
        except Exception as e:
            logger.exception("email_opt_filter e={}".format(e))
            return customers
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0
        return customers

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
        except Exception as e:
            logger.exception("adapt_last_order_status e={}".format(e))
            return customers
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0
        return customers
    
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
        except Exception as e:
            logger.exception("adapt_is_accept_marketing e={}".format(e))
            return customers
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0
        return customers
    
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
        except Exception as e:
            logger.exception("adapt_customer_email e={}".format(e))
            return customers
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0
        return customers
    
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
        except Exception as e:
            logger.exception("adapt_total_order_amount e={}".format(e))
            return customers
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0
        return customers
    
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
            time_now = datetime.datetime.now()
            if relation.lower() in "is in the past":
                min_time = time_now - unit_convert(unit_=unit, value=values[0])
            elif relation.lower() in "is before":
                max_time = datetime.datetime.strptime(values[0], "%Y-%m-%d %H:%M:%S")
            elif relation.lower() in "is after":
                min_time = datetime.datetime.strptime(values[0], "%Y-%m-%d %H:%M:%S")
            elif relation.lower() == "is between date" or relation.lower() == "between date":
                min_time = datetime.datetime.strptime(values[0], "%Y-%m-%d %H:%M:%S")
                max_time = datetime.datetime.strptime(values[1], "%Y-%m-%d %H:%M:%S")
            elif relation.lower() == "is between" or relation.lower() == "between":
                max_time = time_now - unit_convert(unit_=unit, value=values[0])
                min_time = time_now - unit_convert(unit_=unit, value=values[1])
            else:
                # over all time
                min_time = None
                max_time = None
        except Exception as e:
            logger.exception("date_relation_convert catch exception: {}".format(e))
    
        return min_time, max_time

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
                    adapter = self.condition_dict.get(condition_name, None)
                    if adapter:
                        customers = adapter(store_id=store_id, relations=child.get("relations", []))
    
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

    def get_conditions(self, store_id=None, condition_id=None):
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
                cursor.execute(
                    """select `store_id`, `id`, `title`, `relation_info` from `customer_group` where store_id=%s""",
                    (store_id, ))
            elif condition_id:
                cursor.execute(
                    """select `store_id`, `id`, `title`, `relation_info` from `customer_group` where id=%s""",
                    (condition_id, ))
            else:
                # 未删除的才取出来
                cursor.execute(
                    """select `store_id`, `id`, `title`, `relation_info` from `customer_group` where id>=0 and state!=2""")
    
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

    def update_customer_group_list(self, store_id=None):
        """
        更新所有待解析的customer group, 同时创建email group id
        :param store_id:
        :return:
        """
        logger.info("update_customer_group_list trigger, store_id={}".format(store_id))
        conditions = self.get_conditions(store_id=store_id)
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
                # 新的顾客列表，转成邮件
                new_customer_list = value["customer_list"]

                logger.info("update group id={}, new customer list length={}".format(group_id, len(new_customer_list)))

                if new_customer_list:
                    cursor.execute("""select `customer_email` from `customer` where `uuid` in %s""", (new_customer_list, ))
                    emails = cursor.fetchall()
                    new_customer_email_list = [em["customer_email"] for em in emails]
                    new_customer_email_list = [em for em in new_customer_email_list if em]
                else:
                    new_customer_email_list = []

                # 获取这个group, 看看他有没有已经创建过email group id
                cursor.execute("select `uuid`, `customer_list` from `customer_group` where id=%s", (value["group_id"], ))
                customer_group = cursor.fetchone()
                if customer_group:
                    old_uuid = customer_group["uuid"]
                    if customer_group["customer_list"]:
                        old_customer_list = eval(customer_group["customer_list"])
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
                        cursor.execute("""select `customer_email` from `customer` where `uuid` in %s""", (new_add_customers,))
                        emails = cursor.fetchall()
                        new_add_customers_email_list = [em["customer_email"] for em in emails]
                        new_add_customers_email_list = [em for em in new_add_customers_email_list if em] #只要不为空的邮箱
                        if new_add_customers_email_list:
                            diff_add_result = exp.add_subscriber(old_uuid, new_add_customers_email_list)
                            if diff_add_result["code"] == 1:
                                logger.info("add_subscriber succeed, uuid={}".find(old_uuid))
                            elif diff_add_result["code"] == 3:
                                logger.warning("add_subscriber partly succeed, uuid={}, invalid email={}".find(old_uuid, diff_add_result.get("invalid_email", [])))
                            else:
                                logger.error("update_customer_group_list add_subscriber failed, diff_add_result={}, "
                                             "group id={}, uuid={}, add emails={}".format(diff_add_result, group_id, uuid, new_add_customers_email_list))

                    if delete_customers:
                        cursor.execute("""select `customer_email` from `customer` where `uuid` in %s""", (delete_customers,))
                        emails = cursor.fetchall()
                        delete_customers_email_list = [em["customer_email"] for em in emails]
                        delete_customers_email_list = [em for em in delete_customers_email_list if em]  # 只要不为空的邮箱
                        if delete_customers_email_list:
                            for email in delete_customers_email_list:
                                diff_delete_result = exp.delete_subscriber(email, old_uuid)
                                if diff_delete_result["code"] != 1:
                                    logger.error("update_customer_group_list delete_subscriber failed, diff_delete_result={}"
                                                ", group id={}, uuid={}, delete email={}".format(diff_delete_result, group_id, old_uuid, email))

                    cursor.execute(
                        "update `customer_group` set customer_list=%s, update_time=%s, state=1 where id=%s",
                        (str(new_customer_list), datetime.datetime.now(), group_id))
                    conn.commit()
                else:
                    # 还没有创建过email group id
                    logger.info("customer group have not been analyzed, need analyze")
                    # 如果customer list为空，则暂时不创建email group
                    if not new_customer_email_list:
                        continue

                    email_group_name = f"{store['name']}_{group_title}_{datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S')}".replace(" ", "_")
                    create_result = exp.create_subscribers_list(name=email_group_name)

                    if create_result["code"] == 1:
                        uuid = create_result["data"]
                        logger.info("customer group analyze and create email group id={}".format(uuid))
                        add_result = exp.add_subscriber(str(uuid), new_customer_email_list)
                        if add_result["code"] != 1:
                            logger.error("update_customer_group_list add_subscriber failed, group id={}, uuid={}, result={}".format(group_id, uuid, add_result))
                        cursor.execute(
                            "update `customer_group` set uuid=%s, customer_list=%s, update_time=%s, state=1 where id=%s",
                            (str(uuid), str(new_customer_list), datetime.datetime.now(), group_id))
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

    def filter_received_customer(self, store_id, email_id):
        """
        7天之内收到过此邮件的用户
        :param store_id: 用户所属的店铺
        :return: 满足条件的用户email列表
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
                """select `email` from `subscriber_activity` where store_id=%s and message_uuid=%s and type=2 and opt_time > %s""",
                (store_id, email_id, datetime.datetime.now()-datetime.timedelta(days=7)))
            res = cursor.fetchall()
            if res:
                for ret in res:
                    result.append(ret.get('email'))
        except Exception as e:
            logger.exception("adapt_last_order_created_time e={}".format(e))
            return result
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0
        return result

    def get_trigger_conditions(self, store_id=None, condition_id=None):
        """
        批量获取email trigger中的condition
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
                    """select `store_id`, `id`, `title`, `relation_info`, `email_delay`, `note`, `customer_list` from `email_trigger` where store_id=%s and id=%s""",
                    (store_id, condition_id))
            elif store_id:
                # 未删除的才取出来
                cursor.execute(
                    """select `store_id`, `id`, `title`, `relation_info`, `email_delay`, `note`, `customer_list` from `email_trigger` where store_id=%s and type!=2""",
                    (store_id,))
            elif condition_id:
                cursor.execute(
                    """select `store_id`, `id`, `title`, `relation_info`, `email_delay`, `note`, `customer_list` from `email_trigger` where id=%s""",
                    (condition_id,))
            else:
                # 未删除的才取出来
                cursor.execute(
                    """select `store_id`, `id`, `title`, `relation_info`, `email_delay`, `note`, `customer_list` from `email_trigger` where id>=0 and type!=2""")

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

    def parse_trigger_tasks(self):
        """
        解析触发邮件任务, 定时获取符合触发信息的新用户，并且创建定时任务
        :return: True or False
        """
        # 获取所有trigger条件
        trigger_conditions = self.get_trigger_conditions()
        update_list = []
        insert_list = []
        for cond in trigger_conditions:
            store_id, t_id, title, relation_info, email_delay, note, old_customer_list = cond.values()
            customer_list = self.get_customers_by_condition(condition=json.loads(cond["relation_info"]),
                                                          store_id=cond["store_id"])
            if not customer_list:
                # 无符合触发条件的用户
                logger.warning("Not found customers matching the search relation_info: %s"% json.loads(cond["relation_info"]))
                continue
            # 计算新增用户，创建新的任务，第一次应全是新增用户
            if not eval(str(old_customer_list)):
                old_customer_list = []
            else:
                old_customer_list = eval(old_customer_list)
            new_customer_list = list(set(customer_list)-set(old_customer_list))
            if not new_customer_list:
                # 无新增符合触发条件的用户
                logger.warning("No new customers.")
                continue
            old_customer_list.extend(new_customer_list)
            update_list.append((str(old_customer_list), datetime.datetime.now(), t_id))

            # ToDo parse email_delay
            excute_time = datetime.datetime.now() # flow从此刻开始
            for item in eval(email_delay):
                if item["type"] == 1:  # 代表是邮件任务
                    template_id, unit = item["values"], item["unit"]
                    # 通过template_id去创建一个事务性邮件，并返回email_uuid
                    subject, html = self.get_template_info_by_id(template_id)
                    email_uuid = self.create_trigger_email_by_template(store_id, template_id, subject, html, t_id)[0]
                    # 将触发邮件任务参数增加到待入库数据列表中
                    insert_list.append((email_uuid, template_id, 0, unit, excute_time, str(new_customer_list), t_id, 1, datetime.datetime.now(), datetime.datetime.now()))
                elif item["type"] == 0:  # 代表是delay
                    num, unit = item["values"], item["unit"]
                    if unit in ["days", "hours"]:
                        excute_time += datetime.timedelta(**{unit:num})
                    else:
                        logger.error("delay unit is error, please amend it to days or hours.")
                        return False
                else:
                    logger.error("type=%s is invalid."% item["type"])
                    return False

        # 1、将customer_list反填回数据库
        if not self.update_customer_list_from_trigger(update_list):
            return False
        # 2、拆解的任务入库email_task
        return self.insert_email_task_from_trigger(insert_list)

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
                    """insert into email_task (uuid, template_id,state,remark,execute_time,customer_list,email_trigger_id,type,create_time,update_time) 
                    values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", (datas))
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
        若无对应模板的事务性邮件，则创建
        :param store_id: 所属店铺
        :param template_id:
        :return:
        """
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user,
                          password=self.db_password).get_instance()
            cursor = conn.cursor(cursor=pymysql.cursors.DictCursor) if conn else None
            if not cursor:
                return False
            # 通过template_id查询记录
            cursor.execute("select `id` from `email_record` where store_id=%s and email_template_id=%s and type=1", (store_id, template_id))
            if not cursor.fetchall():
                # 暂无数据，需要创建，先获取email_uuid
                # 获取当前店铺name,email
                cursor.execute("select `name`, `sender`, `sender_address` from `store` where id=%s", (store_id,))
                store = cursor.fetchone()
                if not store:
                    raise Exception("store is not found, store id={}".format(store_id))
                ems = ems_api.ExpertSender(from_name=store["sender"], from_email=store["sender_address"])
                res = ems.create_transactional_message(subject, html)
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
                logger.info("email_record data was exists.")
            # 查询此模板ID对应的email_uuid
            cursor.execute("select `uuid`, `email_template_id` from `email_record` where email_template_id=%s and email_trigger_id=%s", (template_id,email_trigger_id))
            result = cursor.fetchone()
        except Exception as e:
            logger.exception("insert email task from trigger exception: {}".format(e))
            return False
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0
        return result

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
            cursor.execute("select subject, html from email_template where id=%s", (template_id))
            result = cursor.fetchone()
            logger.info("get template info by id success.")
        except Exception as e:
            logger.exception("get template info by id exception: {}".format(e))
            return False
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0
        return result


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

    ac = AnalyzeCondition(db_info={"host": "47.244.107.240", "port": 3306, "db": "edm", "user": "edm", "password": "edm@orderplus.com"})
    # ac.update_customer_group_list()
    # conditions = ac.get_conditions()
    # for cond in conditions:
    #     cus = ac.get_customers_by_condition(condition=json.loads(cond["relation_info"]), store_id=cond["store_id"])
    #     print(cus)
    # print(ac.filter_purchase_customer(1, datetime.datetime(2019, 7, 24, 0, 0)))
    # print(ac.adapt_all_order(1, [{"relation":"more than","values":["0",1],"unit":"days","errorMsg":""},{"relation":"is over all time","values":[0,1],"unit":"days","errorMsg":""}]))
    # print(ac.filter_received_customer(1, 372))
    print(ac.parse_trigger_tasks())