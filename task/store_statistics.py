import datetime
import json
import os
import pymysql
from collections import Counter

from sdk.googleanalytics.google_oauth_info import GoogleApi
from sdk.shopify.get_shopify_data import ProductsApi
from config import logger, ROOT_PATH, MONGO_CONFIG, MYSQL_CONFIG
from sdk.shopify import shopify_webhook
from task.db_util import DBUtil, MongoDBUtil
from dingtalkchatbot.chatbot import DingtalkChatbot


class StoreStatistics:
    """站点发送明细明细统计"""
    def __init__(self, db_info, mongo_config):
        self.db_host = db_info.get("host", "")
        self.db_port = db_info.get("port", 3306)
        self.db_name = db_info.get("db", "")
        self.db_user = db_info.get("user", "")
        self.db_password = db_info.get("password", "")
        self.root_path = ROOT_PATH
        self.mongo_config = mongo_config

    def update_store_statistics(self):
        # 更新每天的站点明细信息
        logger.info("update_store_statistics is cheking...")
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user,
                          password=self.db_password).get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return False
            # 获取所有店铺
            cursor.execute("""select id, name from store where id!=1""")
            for store in cursor.fetchall():
                store_id, name = store
                # 从emailReocrd表中获取当前店铺所有非测试邮件的数据
                cursor.execute("""select sum(sents),sum(opens),sum(clicks),sum(unsubscribes),sum(open_rate),sum(click_rate),
                       sum(unsubscribe_rate),count(uuid) from email_record where store_id=%s""", (store_id,))
                new_res = []
                for r in cursor.fetchone():
                    if not r:
                        new_res.append(0)
                    else:
                        new_res.append(r)
                sents, opens, clicks, unsubscribes, open_rate, click_rate, unsubscribe_rate, email_count = tuple(
                    new_res)
                avg_open_rate = round(opens / sents, 4) if opens and sents else 0
                avg_click_rate = round(clicks / sents, 4) if clicks and sents else 0
                avg_unsubscribe_rate = round(unsubscribes / sents, 4) if unsubscribes and sents else 0
                # 配置时间
                now_date = datetime.datetime.now()
                zero_time = now_date - datetime.timedelta(hours=now_date.hour, minutes=now_date.minute,
                                                          seconds=now_date.second, microseconds=now_date.microsecond)
                last_time = zero_time + datetime.timedelta(hours=23, minutes=59, seconds=59)


                # 计算当天的的增量数据
                delta_sent, delta_open, delta_click = 0, 0, 0
                cursor.execute(
                    """select total_sent,total_open,total_click from dashboard where store_id=%s and create_time between %s and %s""",
                    (store_id, zero_time - datetime.timedelta(days=1), last_time - datetime.timedelta(days=1)))
                yesterday_data = cursor.fetchall()
                if yesterday_data:
                    yesterday_sent, yesterday_open, yesterday_click = yesterday_data[0]
                    delta_sent, delta_open, delta_click = sents - yesterday_sent, opens - yesterday_open, clicks - yesterday_click
                # 更新数据入库
                cursor.execute("""select id from dashboard where store_id=%s and create_time between %s and %s""",
                               (store_id, zero_time, last_time))
                dashboard_id = cursor.fetchone()

                # if dashboard_id:
                #     # update
                #     cursor.execute("""update dashboard set sents=%s, opens=%s, clicks=%s, total_sent=%s, total_open=%s, total_click=%s, total_unsubscribe=%s, avg_open_rate=%s,
                #             avg_click_rate=%s, avg_unsubscribe_rate=%s, update_time=%s where id=%s""",
                #                    (delta_sent, delta_open, delta_click, sents, opens, clicks, unsubscribes,
                #                     avg_open_rate, avg_click_rate, avg_unsubscribe_rate, now_date, dashboard_id[0]))
                # else:
                #     # insert
                #     cursor.execute("""insert into dashboard (total_customers,repeat_customers,revenue,orders,total_revenue,total_orders,total_sessions,session,avg_repeat_purchase_rate,avg_conversion_rate,
                #            sents, opens, clicks, total_sent, total_open, total_click, total_unsubscribe, avg_open_rate, avg_click_rate, avg_unsubscribe_rate, create_time, update_time, store_id)
                #            values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                #                    (0, 0, 0, 0, 0, 0, 0, 0, 0.0, 0.0, delta_sent, delta_open, delta_click, sents, opens,
                #                     clicks, unsubscribes, avg_open_rate, avg_click_rate, avg_unsubscribe_rate, now_date,
                #                     now_date, store_id))
                logger.info("update store(%s) dashboard success at %s." % (store_id, now_date))
                conn.commit()
        except Exception as e:
            logger.exception("update dashboard data exception e={}".format(e))
            return False
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0


if __name__ == '__main__':
    # 统计store的数据
    StoreStatistics(db_info=MYSQL_CONFIG, mongo_config=MONGO_CONFIG).update_store_statistics()




