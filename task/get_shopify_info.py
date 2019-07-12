from apscheduler.schedulers.background import BackgroundScheduler
import datetime
import threading
import time
import pymysql
import os

from sdk.shopify.get_shopify_data import ProductsApi
from config import logger

MYSQL_PASSWD = os.getenv('MYSQL_PASSWD', None)
MYSQL_HOST = os.getenv('MYSQL_HOST', None)


# 47.52.221.217
class DBUtil:
    def __init__(self, host="47.244.107.240", port=3306, db="edm", user="edm", password="edm@orderplus.com"):
        self.conn_pool = {}
        self.host = host
        self.port = port
        self.db = db
        self.user = user
        self.pwd = password

    def get_instance(self):
        try:
            name = threading.current_thread().name
            if name not in self.conn_pool:
                conn = pymysql.connect(
                    host=self.host,
                    port=self.port,
                    db=self.db,
                    user=self.user,
                    password=self.pwd,
                    charset='utf8'
                )
                # conn.connect_timeout
                self.conn_pool[name] = conn
        except Exception as e:
            logger.exception("connect mysql error, e={}".format(e))
            return None
        return self.conn_pool[name]


class TaskProcessor:
    def update_shopify_cuntomers(self):
        """
        1. 更新所有客戶的信息
        2. 获取所有店铺的所有类目，并保存至数据库
        """
        logger.info("update_collection is cheking...")
        try:
            conn = DBUtil().get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return False
            cursor.execute(
                """select store.id, store.token, store.url from store left join user on store.user_id = user.id where user.is_active = 1""")
            stores = cursor.fetchall()

            for store in stores:
                store_id, store_token, store_url = store
                papi = ProductsApi(store_token, store_url)
                # 更新店铺信息
                ret = papi.get_all_customers()
                if ret["code"] == 1:
                    customer_info = ret["data"].get("customers", "")
                    for customer in customer_info:
                        customer_id = customer.get("id", "")
                        customer_email = customer.get("email", "")
                        accepts_marketing = customer.get("accepts_marketing", "")
                        created_at = customer.get("created_at", "")
                        state = customer.get("state", "")
                        payment_amount = customer.get("last_name", "")
                        customer_name = customer.get("first_name", "")+customer.get("last_name", "")

                        # shop_myshopify_domain = shop.get("myshopify_domain", "")
                        cursor.execute('''insert into `customer` (`name`, `customer_email`, `accept_marketing_status`, `store_id`, `payment_amount`, `create_time`, `update_time`)
                                        values (%s, %s, %s, %s, %s, %s, %s)''',
                                       (customer_name, customer_email, accepts_marketing, store_id, payment_amount,  datetime.datetime.now(), datetime.datetime.now()))
                        conn.commit()
                else:
                    logger.warning("get shop info failed. ret={}".format(ret))
        except Exception as e:
            logger.exception("update_collection e={}".format(e))
            return False
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0
        return True


def main():
    tsp = TaskProcessor()
    while 1:
        time.sleep(1)


if __name__ == '__main__':
    # test()
    # main()
    access_token = "d1063808be79897450ee5030e1c163ef"
    id = "3583116148816"
    shop_uri = "charrcter.myshopify.com"
    TaskProcessor().update_shopify_cuntomers()
