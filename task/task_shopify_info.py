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
                # 取中已经存在的所有products, 只需更新即可
                cursor.execute('''select uuid from `customer` where store_id=%s''', (store_id))
                exist_customer = cursor.fetchall()
                exist_customer_list = [item[0] for item in exist_customer]
                # for exp in exist_customer:
                #     exist_customer_dict.append(exp)

                # 更新客户信息
                papi = ProductsApi(store_token, store_url)
                # 更新店铺信息
                since_id = ""
                for i in range(0, 100):
                    ret = papi.get_all_customers(limit=60, since_id=since_id)
                    if ret["code"] != 1:
                        logger.warning("get shop info failed. ret={}".format(ret))
                        break
                    if ret["code"] == 1:
                        customer_info = ret["data"].get("customers", "")
                        for customer in customer_info:
                            uuid = str(customer.get("id", ""))
                            customer_email = customer.get("email", "")
                            create_time = (customer.get("created_at", "")).split('+')[0]
                            sign_up_time = datetime.datetime.strptime(create_time, '%Y-%m-%dT%H:%M:%S')
                            accepts_marketing = customer.get("accepts_marketing", "")
                            first_name = customer.get("first_name", "")
                            last_name = customer.get("last_name", "")
                            payment_amount = customer.get("total_spent", "")

                            if uuid in exist_customer_list:
                                # pro_id = exist_customer_dict[uuid]
                                logger.info("customer is already exist, uuid={}".format(uuid))
                                cursor.execute(
                                    '''update `customer` set customer_email=%s, accept_marketing_status=%s, update_time=%s, first_name=%s, last_name=%s where uuid=%s''',
                                    (customer_email, accepts_marketing, datetime.datetime.now(), first_name, last_name, uuid))
                            else:
                                cursor.execute('''insert into `customer` (`uuid`, `sign_up_time`, `first_name`, `last_name`, `customer_email`, `accept_marketing_status`, `store_id`, `payment_amount`, `create_time`, `update_time`)
                                                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                                               (uuid, sign_up_time, first_name, last_name, customer_email, accepts_marketing, store_id, payment_amount,  datetime.datetime.now(), datetime.datetime.now()))
                                exist_customer_list.append(uuid)
                            conn.commit()
                        # 拉完了
                        if len(customer_info) < 60:
                            break
                        else:
                            since_id = customer_info[-1].get("id", "")
                            if not since_id:
                                break

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

