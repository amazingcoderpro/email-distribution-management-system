# -*- coding: utf-8 -*-
# Created by: Leemon7
# Created on: 2019/7/12
import datetime

from config import logger
from sdk.ems.ems_api import ExpertSender
from task.db_util import DBUtil


class EMSDataProcessor:
    def __init__(self, from_name, from_email, store_id, db_info):
        self.store_id = store_id
        self.from_name = from_name
        self.from_email = from_email
        self.ems = ExpertSender(self.from_name, self.from_email)
        self.db_host = db_info.get("host", "")
        self.db_port = db_info.get("port", 3306)
        self.db_name = db_info.get("db", "")
        self.db_user = db_info.get("user", "")
        self.db_password = db_info.get("password", "")

    def insert_subscriber_activity(self, query_date):
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
            insert_list = []
            for tp, item in result.items():
                tp = type_choices[tp]
                for i in item:
                    try:
                        opt_time, email, message_uuid = i.split(",")[0:3]
                    except ValueError as e:
                        logger.info(e)
                        continue
                    cursor.execute("""select id from subscriber_activity where 
                    opt_time=%s and email=%s and message_uuid=%s and type=%s and store_id=%s""", (opt_time, email, int(message_uuid), tp, self.store_id))
                    is_activity = cursor.fetchone()
                    if is_activity:
                        logger.info(f"this subscriber activity exists, params is {opt_time},{email},{message_uuid}.")
                        continue
                    else:
                        now_time = datetime.datetime.now()
                        insert_list.append((opt_time, email, int(message_uuid), tp, self.store_id, now_time, now_time))
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
            # 获取每一个listId对应的ems数据
            update_list = []
            for uuid, store_id in uuid_list:
                if not uuid:
                    continue
                datas = self.ems.get_summary_statistics(uuid)
                if datas["code"]==1 and datas["data"]:
                    statistic = datas["data"]["SummaryStatistics"]["SummaryStatistic"]
                    sents, opens, clicks = int(statistic["Sent"]), int(statistic["Opens"]), int(statistic["Clicks"])
                    open_rate, click_rate = round(opens/sents, 2), round(clicks/sents, 2)
                    update_list.append((sents, opens, clicks, open_rate, click_rate, datetime.datetime.now(), uuid, store_id))
            # 更新数据库
            cursor.executemany(
                """update customer_group set sents=%s, opens=%s, clicks=%s, open_rate=%s, click_rate=%s, update_time=%s where uuid=%s and store_id=%s""", update_list)
            logger.info("update all customer group success.")
            conn.commit()
        except Exception as e:
            logger.exception("update customer group data exception e={}".format(e))
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
                    open_rate, click_rate, unsubscribe_rate = round(opens/sents, 2), round(clicks/sents, 2), round(unsubscribes/sents, 2)
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
            # 从emailReocrd表中获取当前店铺所有非测试邮件的数据
            cursor.execute("""select sum(sents),sum(opens),sum(clicks),sum(unsubscribes),sum(open_rate),sum(click_rate),
            sum(unsubscribe_rate),count(uuid) from email_record where type in (0,1) and store_id=%s""", (self.store_id,))
            sents,opens,clicks,unsubscribes,open_rate,click_rate,unsubscribe_rate,email_count = cursor.fetchone()
            avg_open_rate,avg_click_rate,avg_unsubscribe_rate = round(open_rate/email_count,2),round(click_rate/email_count,2),round(unsubscribe_rate/email_count,2)



        except Exception as e:
            logger.exception("update dashboard data exception e={}".format(e))
            return False
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0



if __name__ == '__main__':
    db_info = {"host": "47.244.107.240", "port": 3306, "db": "edm", "user": "edm", "password": "edm@orderplus.com"}
    obj = EMSDataProcessor("Leemon", "leemon.li@orderplus.com", 1, db_info=db_info)
    # obj.insert_subscriber_activity("2019-07-15")
    # obj.update_customer_group_data()
    # obj.update_email_reocrd_data()
    obj.insert_dashboard_data()