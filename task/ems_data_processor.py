# -*- coding: utf-8 -*-
# Created by: Leemon7
# Created on: 2019/7/12
import datetime
import os

from config import logger
from sdk.ems.ems_api import ExpertSender
from task.db_util import DBUtil


class EMSDataProcessor:
    def __init__(self, from_name, from_email, db_info):
        self.ems = ExpertSender(from_name, from_email)
        self.db_host = db_info.get("host", "")
        self.db_port = db_info.get("port", 3306)
        self.db_name = db_info.get("db", "")
        self.db_user = db_info.get("user", "")
        self.db_password = db_info.get("password", "")

    def insert_subscriber_activity(self, query_date=datetime.datetime.today().date()-datetime.timedelta(days=1)):
        """
        将收件人行为记录入库，type包括Opens, Clicks, Sends
        :param query_date: 需要查询的日期，单位为一天，格式为2019-07-15
        :return:
        """
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user, password=self.db_password).get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return False
            # 获取行为记录数据
            result = {}
            type_choices = {'Opens': 0, 'Clicks': 1, 'Sends': 2}
            for tp in ["Opens", "Clicks", "Sends"]:
                result[tp] = self.ems.get_subscriber_activity(tp, query_date)[1:]
            # 查出系统所有的uuid对的店铺id
            cursor.execute("""select uuid,store_id from email_record where uuid is not null""")
            uuids = cursor.fetchall()
            if not uuids:
                logger.warning("no available uuid")
                return False
            uuid_store = {item[0]: item[1] for item in uuids}
            insert_list = []
            for tp, item in result.items():
                tp = type_choices[tp]
                for i in item:
                    try:
                        opt_time, email, message_uuid = i.split(",")[0:3]
                    except ValueError as e:
                        logger.info(e)
                        continue
                    # 需要通过message_uuid获取店铺id
                    if message_uuid not in uuid_store:
                        continue
                    store_id = uuid_store[message_uuid]
                    cursor.execute("""select id from subscriber_activity where 
                    opt_time=%s and email=%s and message_uuid=%s and type=%s and store_id=%s""", (opt_time, email, int(message_uuid), tp, store_id))
                    is_activity = cursor.fetchone()
                    if is_activity:
                        logger.info(f"this subscriber activity exists, params is {opt_time},{email},{message_uuid}.")
                        continue
                    else:
                        now_time = datetime.datetime.now()
                        insert_list.append((opt_time, email, int(message_uuid), tp, store_id, now_time, now_time))
            if insert_list:
                cursor.executemany("""insert into subscriber_activity (opt_time,email,message_uuid,type,store_id,create_time,update_time) values
                                        (%s,%s,%s,%s,%s,%s,%s)""", insert_list)
                conn.commit()
            logger.info(f"insert subscriber activity success at {query_date}.")
        except Exception as e:
            logger.exception("insert subscriber activity exception e={}".format(e))
            return False
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0
            return True

    def update_customer_group_data(self):
        """
        更新状态未删除的客户组ems数据
        :return:
        """
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user, password=self.db_password).get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return False
            # 获取当前用户组listId
            cursor.execute("""select uuid,store_id from customer_group where state in (0,1)""")
            uuid_list = cursor.fetchall()
            # 获取每一个用户组listId对应的ems数据
            group_update_list = []
            for uuid, store_id in uuid_list:
                if not uuid:
                    continue
                datas = self.ems.get_summary_statistics(uuid)
                if datas["code"]==1 and datas["data"]:
                    statistic = datas["data"]["SummaryStatistics"]["SummaryStatistic"]
                    sents, opens, clicks = int(statistic["Sent"]), int(statistic["Opens"]), int(statistic["Clicks"])
                    open_rate, click_rate = round(opens/sents,5) if sents else 0.0, round(clicks/sents,5) if sents else 0.0
                    group_update_list.append((sents, opens, clicks, open_rate, click_rate, datetime.datetime.now(), uuid, store_id))
            # 更新数据库
            cursor.executemany(
                """update customer_group set sents=%s, opens=%s, clicks=%s, open_rate=%s, click_rate=%s, update_time=%s where uuid=%s and store_id=%s""", group_update_list)
            logger.info("update all customer group ems datas success.")
            conn.commit()

            # 获取当前flow的ListId
            cursor.execute("""select customer_list_id,store_id from email_trigger where status in (0,1)""")
            list_id_list = cursor.fetchall()
            # 获取每一个flow的ListId对应的ems数据
            flow_update_list = []
            for uuid, store_id in list_id_list:
                if not uuid:
                    continue
                datas = self.ems.get_summary_statistics(uuid)
                if datas["code"] == 1 and datas["data"]:
                    statistic = datas["data"]["SummaryStatistics"]["SummaryStatistic"]
                    sents, opens, clicks = int(statistic["Sent"]), int(statistic["Opens"]), int(statistic["Clicks"])
                    open_rate, click_rate = round(opens / sents,5) if sents else 0.0, round(clicks / sents,5) if sents else 0.0
                    flow_update_list.append((sents, open_rate, click_rate, datetime.datetime.now(), uuid, store_id))
            # 更新数据库
            cursor.executemany(
                """update email_trigger set total_sents=%s, open_rate=%s, click_rate=%s, update_time=%s where customer_list_id=%s and store_id=%s""",
                flow_update_list)
            logger.info("update all email trigger ems datas success.")
            conn.commit()
        except Exception as e:
            logger.exception("update customer group and email trigger ems datas exception e={}".format(e))
            return False
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0

    def update_email_reocrd_data(self):
        """
        更新已发送邮件的ems数据
        :return:
        """
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user, password=self.db_password).get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return False
            # 获取当前所有已发送邮件
            cursor.execute("""select uuid,store_id from email_record""")
            uuid_list = cursor.fetchall()
            # 获取每一个listId对应的ems数据
            update_list = []
            for uuid, store_id in uuid_list:
                if not uuid:
                    continue
                datas = self.ems.get_message_statistics(uuid)
                if datas["code"]==1 and datas["data"]:
                    statistic = datas["data"]
                    sents, opens, clicks, unsubscribes = int(statistic["Sent"]), int(statistic["Opens"]), int(statistic["Clicks"]), int(statistic["Unsubscribes"])
                    if sents:
                        open_rate, click_rate, unsubscribe_rate = (opens/sents), (clicks/sents), (unsubscribes/sents)
                    else:
                        open_rate = click_rate = unsubscribe_rate = 0
                    update_list.append((sents, opens, clicks, unsubscribes, open_rate, click_rate, unsubscribe_rate, datetime.datetime.now(), uuid, store_id))
            # 更新数据库
            cursor.executemany("""update email_record set sents=%s, opens=%s, clicks=%s, unsubscribes=%s, open_rate=%s, click_rate=%s, unsubscribe_rate=%s, update_time=%s where uuid=%s and store_id=%s""",
                           update_list)
            logger.info("update all email record success.")
            conn.commit()
        except Exception as e:
            logger.exception("update email reocrd data exception e={}".format(e))
            return False
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0
        return True

    def insert_dashboard_data(self):
        """
        每天定时拉取数据入库，最新数据为截止到昨天23:59:59
        :return:
        """
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user, password=self.db_password).get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return False
            # 获取所有店铺
            cursor.execute("""select id from store""")
            for store in cursor.fetchall():
                store_id = store[0]
                # 从emailReocrd表中获取当前店铺所有非测试邮件的数据
                cursor.execute("""select sum(sents),sum(opens),sum(clicks),sum(unsubscribes),sum(open_rate),sum(click_rate),
                sum(unsubscribe_rate),count(uuid) from email_record where store_id=%s""", (store_id,))
                new_res = []
                for r in cursor.fetchone():
                    if not r:
                        new_res.append(0)
                    else:
                        new_res.append(r)
                sents,opens,clicks,unsubscribes,open_rate,click_rate,unsubscribe_rate,email_count = tuple(new_res)

                avg_open_rate = (open_rate/email_count) if open_rate and email_count else 0
                avg_click_rate = (click_rate/email_count) if click_rate and email_count else 0
                avg_unsubscribe_rate = (unsubscribe_rate/email_count) if unsubscribe_rate and email_count else 0
                # 配置时间
                now_date = datetime.datetime.now()
                zero_time = now_date - datetime.timedelta(hours=now_date.hour, minutes=now_date.minute,
                                                           seconds=now_date.second, microseconds=now_date.microsecond)
                last_time = zero_time + datetime.timedelta(hours=23, minutes=59, seconds=59)
                # 获取当前店铺所有的orders
                # cursor.execute("""select total_orders, total_revenue, total_sessions from dashboard where store_id= %s and update_time between %s and %s""",
                #                (store_id, zero_time-datetime.timedelta(days=1), last_time-datetime.timedelta(days=1)))
                # orders_info = cursor.fetchone()
                # if orders_info:
                #     total_orders, total_revenue, total_sessions = orders_info
                # else:
                #     total_orders = total_revenue = total_sessions = 0
                #
                # # 获取当前店铺支付订单大于等于2的用户数
                # cursor.execute("""select count(customer_uuid) from (SELECT customer_uuid, count(id) as num FROM order_event where store_id= %s and status_tag='paid' group by customer_uuid) as res where num >= 2;""", (store_id, ))
                # orders_gte2 = cursor.fetchone()[0]
                #
                # # 获取当前店铺的用户总量
                # cursor.execute("""SELECT count(id)  FROM  order_event where store_id= %s;""", (store_id, ))
                # total_cumtomers = cursor.fetchone()[0]
                #
                # # 获取GA数据
                # cursor.execute(
                #     """select store.store_view_id from store where store.id = %s""", (store_id, ))
                # store_view_id = cursor.fetchone()[0]
                # if store_view_id:
                #     papi = GoogleApi(view_id=store_view_id, json_path=os.path.join(ROOT_PATH, r"sdk\googleanalytics\client_secrets.json"))
                #     shopify_google_data = papi.get_report(key_word="", start_time="1daysAgo", end_time="today")
                #     shopify_dict = shopify_google_data.get("total_results", {})
                #     sessions = shopify_dict.get("sessions", 0)
                #     orders = shopify_dict.get("transactions", 0)
                #     revenue = shopify_dict.get("revenue", 0.0)
                #     total_orders += orders
                #     total_sessions += sessions
                #     total_revenue += revenue
                #     # 平均转换率  总支付订单数÷总流量
                #     avg_conversion_rate = (total_orders/ total_sessions) if total_sessions else 0
                #     # 重复的购买率 支付订单数≥2的用户数据÷总用户数量
                #     avg_repeat_purchase_rate = (orders_gte2/total_cumtomers) if total_cumtomers else 0
                # else:
                #     sessions=orders=revenue=total_orders=total_sessions=total_revenue=avg_conversion_rate=avg_repeat_purchase_rate = 0

                # 更新数据入库
                cursor.execute("""select id from dashboard where store_id=%s and update_time between %s and %s""", (store_id, zero_time, last_time))
                dashboard_id = cursor.fetchone()
                if dashboard_id:
                    # update
                    cursor.execute("""update dashboard set total_sent=%s, total_open=%s, total_click=%s, total_unsubscribe=%s, avg_open_rate=%s,
                     avg_click_rate=%s, avg_unsubscribe_rate=%s, update_time=%s where id=%s""",
                     (sents,opens,clicks,unsubscribes,avg_open_rate,avg_click_rate,avg_unsubscribe_rate,now_date, dashboard_id[0]))
                else:
                    # insert
                    cursor.execute("""insert into dashboard (revenue,orders,total_revenue,total_orders,total_sessions,session,avg_repeat_purchase_rate,avg_conversion_rate,
                    total_sent, total_open, total_click, total_unsubscribe, avg_open_rate,
                     avg_click_rate, avg_unsubscribe_rate, create_time, update_time, store_id) 
                    values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (0,0,0,0,0,0,0.0,0.0,sents,opens,clicks,unsubscribes,avg_open_rate,avg_click_rate,avg_unsubscribe_rate,now_date,now_date,store_id))
                logger.info("update store(%s) dashboard success at %s." % (store_id, now_date))
                conn.commit()
        except Exception as e:
            logger.exception("update dashboard data exception e={}".format(e))
            return False
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0
        return True

    def update_unsubscriber_and_snoozed_customers(self):
        """
        定时更新取消订阅和休眠的收件人，时间间隔为半小时
        :return:
        """
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user, password=self.db_password).get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return False
            update_list,insert_list = [], []
            # 获取取消订阅的收件人
            unsubscriber_result = self.ems.get_opt_out_link_subscribers()
            # 获取休眠的收件人
            snoozed_result = self.ems.get_snoozed_subscribers()
            # 查询出目前系统中所有可用的listID对应的store_id(group_list)
            cursor.execute("select uuid, store_id from customer_group")
            store_result_group_list = cursor.fetchall()
            # 查询出目前系统中所有可用的listID对应的store_id(email_trigger)
            cursor.execute("select customer_list_id, store_id from email_trigger")
            store_result_trigger = cursor.fetchall()
            store_dict = {}
            if store_result_group_list:
                store_dict.update({store[0]:store[1] for store in store_result_group_list if store[0]})
            if store_result_trigger:
                store_dict.update({store[0]:store[1] for store in store_result_trigger if store[0]})
            if not store_result_trigger and not store_result_group_list:
                logger.warning("No customer groups are available.")
                return True

            if unsubscriber_result["code"] != 1 and snoozed_result["code"] != 1:
                logger.error("get unsubscriber and snoozed customers failed.")
                return False
            # 查询出customer_unsubscribe table 已存在的email
            cursor.execute("select email, store_id, id from customer_unsubscribe")
            only_field = cursor.fetchall()
            only = {only[0]+str(only[1]): only[2] for only in only_field}
            if unsubscriber_result["code"] == 1:
                logger.info("sttart update unsubscriber customers.")
                unsubscriber_customers_list = unsubscriber_result["data"]["RemovedSubscribers"]["RemovedSubscriber"]
                for cus in unsubscriber_customers_list:
                    # 通过ListId获取store_id
                    store_id = store_dict.get(cus["ListId"])
                    if store_id:
                        try:
                            Unsubscribed_date = datetime.datetime.strptime(cus["UnsubscribedOn"], "%Y-%m-%dT%H:%M:%S.%f")
                        except:
                            Unsubscribed_date = datetime.datetime.strptime(cus["UnsubscribedOn"], "%Y-%m-%dT%H:%M:%S")
                        if cus["Email"]+str(store_id) in only:
                            update_list.append((Unsubscribed_date, 1, datetime.datetime.now(), only[cus["Email"]+str(store_id)]))
                        else:
                            insert_list.append((Unsubscribed_date, 1, datetime.datetime.now(), datetime.datetime.now(), cus["Email"], store_id))
                        logger.info("email(%s) Unsubscribed success in store(id=%s), UnsubscribedOn %s." % (cus["Email"], store_id, cus["UnsubscribedOn"]))
            if snoozed_result["code"] == 1:
                logger.info("sttart update snoozed customers.")
                snoozed_customers_list = snoozed_result["data"]["SnoozedSubscribers"]["SnoozedSubscriber"]
                for cust in snoozed_customers_list:
                    # 通过ListId获取store_id
                    store_id = store_dict.get(cust["ListId"])
                    if store_id:
                        try:
                            Unsubscribed_date = datetime.datetime.strptime(cust["SnoozedUntil"], "%Y-%m-%dT%H:%M:%S.%f")
                        except:
                            Unsubscribed_date = datetime.datetime.strptime(cust["SnoozedUntil"], "%Y-%m-%dT%H:%M:%S")
                        if cust["Email"] + str(store_id) in only:
                            update_list.append((Unsubscribed_date, 2, datetime.datetime.now(), only[cust["Email"]+str(store_id)]))
                        else:
                            insert_list.append((Unsubscribed_date, 2, datetime.datetime.now(), datetime.datetime.now(), cust["Email"], store_id))
                        logger.info("email(%s) Snoozed success in store(id=%s), SnoozedUntil %s." % (cust["Email"], store_id, cust["SnoozedUntil"]))
            # 更新数据库
            cursor.executemany("""update customer_unsubscribe set unsubscribe_date=%s, unsubscribe_status=%s, update_time=%s where id=%s""",
                           update_list)
            cursor.executemany(
                """insert into customer_unsubscribe (unsubscribe_date,unsubscribe_status,update_time,create_time,email,store_id)
                values (%s,%s,%s,%s,%s,%s)""", insert_list)
            logger.info("update unsubscriber and snoozed customers success.")
            conn.commit()
        except Exception as e:
            logger.exception("update unsubscriber and snoozed customers exception e={}".format(e))
            return False
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0
        return True


if __name__ == '__main__':
    db_info = {"host": "47.244.107.240", "port": 3306, "db": "edm", "user": "edm", "password": "edm@orderplus.com"}
    obj = EMSDataProcessor("Leemon", "leemon.li@orderplus.com", db_info=db_info)
    # obj.insert_subscriber_activity()
    # obj.update_customer_group_data()
    # obj.update_email_reocrd_data()
    # obj.insert_dashboard_data()
    obj.update_unsubscriber_and_snoozed_customers()