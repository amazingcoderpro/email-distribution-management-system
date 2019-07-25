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
                              "Customer opened email": self.adapt_opened_email,
                              "Customer clicked email": self.adapt_clicked_email,
                              "Customer last order status": self.adapt_last_order_status,
                              "Customer who accept marketing": self.adapt_is_accept_marketing,
                              "Customer Email": self.adapt_customer_email,
                              "Customer total order payment amount": self.adapt_total_order_amount,
                            }
            
    def order_filter(self, store_id, status, relation, value, min_time=None, max_time=None):
        """
        筛选满足订单条件的客户id
        :param store_id: 店铺id
        :param status: 订单状态0－未支付，　１－支付　
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
    
            # between date
            if min_time and max_time:
                cursor.execute(
                    """select `customer_uuid`, count(1) from `order_event` where store_id=%s and status=%s 
                    and `order_update_time`>=%s and `order_update_time`<=%s group by `customer_uuid`""", (store_id, status, min_time, max_time))
            # after, in the past
            elif min_time:
                cursor.execute(
                    """select `customer_uuid`, count(1) from `order_event` where store_id=%s and status=%s 
                    and `order_update_time`>=%s group by `customer_uuid`""", (store_id, status, min_time))
            # before
            elif max_time:
                cursor.execute(
                    """select `customer_uuid`, count(1) from `order_event` where store_id=%s and status=%s 
                    and `order_update_time`<=%s group by `customer_uuid`""", (store_id, status, max_time))
            # over all time
            else:
                cursor.execute(
                    """select `customer_uuid`, count(1) from `order_event` where store_id=%s and status=%s 
                    group by `customer_uuid`""", (store_id, status))
    
            res = cursor.fetchall()
            relation_dict = {"equals": "==", "more than": ">", "less than": "<"}
    
            for uuid, count in res:
                just_str = "{} {} {}".format(count, relation_dict.get(relation), value)
                if eval(just_str):
                    customers.append(uuid[0])
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
                            if diff_add_result["code"] != 1:
                                logger.error("update_customer_group_list add_subscriber failed, diff_add_result={}, "
                                             "group id={}, uuid={}, add emails={}".format(diff_add_result, group_id, uuid, new_add_customers_email_list))

                    if delete_customers:
                        cursor.execute("""select `customer_email` from `customer` where `uuid` in %s""", (delete_customers,))
                        emails = cursor.fetchall()
                        delete_customers_email_list = [em["customer_email"] for em in emails]
                        delete_customers_email_list = [em for em in delete_customers_email_list if em]  # 只要不为空的邮箱
                        if delete_customers_email_list:
                            diff_delete_result = exp.delete_subscriber(delete_customers_email_list, old_uuid)
                            if diff_delete_result["code"] != 1:
                                logger.error("update_customer_group_list delete_subscriber failed, diff_delete_result={}"
                                             ", group id={}, uuid={}, delete emails={}".format(diff_delete_result, group_id, old_uuid, delete_customers_email_list))

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
    ac.update_customer_group_list()
    # conditions = ac.get_conditions()
    # for cond in conditions:
    #     cus = ac.get_customers_by_condition(condition=json.loads(cond["relation_info"]), store_id=cond["store_id"])
    #     print(cus)