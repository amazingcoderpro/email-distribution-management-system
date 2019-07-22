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


def sync_last_order_info(store_id, cursor=None):
    if not cursor:
        conn = DBUtil().get_instance()
        cursor = conn.cursor() if conn else None
        if not cursor:
            return False
    cursor.execute(
        """select `status`, `order_update_time`, `order_uuid` from order_event where store_id = %s""", (store_id, ))

    ret = cursor.fetchall()
    if ret:
        cursor.executemany(
            """update customer set `last_order_status`=%s, `last_order_time`=%s where last_order_id = %s""", ret)
        conn.commit()


def save_moth_customer(customer_insert_list, uuid, store_id, cursor=None):
    if not cursor:
        conn = DBUtil().get_instance()
        cursor = conn.cursor() if conn else None
        if not cursor:
            return False

    if customer_insert_list:
        logger.info("customer is already exist [insert], uuid={}".format(uuid))
        cursor.executemany('''insert into `customer` (`uuid`, `last_order_id`,`orders_count`,`sign_up_time`, `first_name`, `last_name`, `customer_email`, `accept_marketing_status`, `store_id`, `payment_amount`, `create_time`, `update_time`)
                                                     values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                           customer_insert_list)
        conn.commit()
    # if customer_update_list:
    #     logger.info("customer is already exist [update], uuid={}".format(uuid))
    #     cursor.executemany('''update `customer` set last_order_id=%s, orders_count=%s, customer_email=%s, accept_marketing_status=%s, update_time=%s, first_name=%s, last_name=%s where uuid=%s''',
    #                        customer_update_list)
    #     conn.commit()


class TaskProcessor:
    def update_shopify_cuntomers(self):
        """
        1. 更新所有客戶的信息
        2. 获取所有店铺的所有类目，并保存至数据库
        """
        logger.info("update_collection is cheking...")
        global since_id

        try:
            conn = DBUtil().get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return False
            cursor.execute(
                """select store.id, store.token, store.url from store left join user on store.user_id = user.id where user.is_active = 1""")
            stores = cursor.fetchall()
            for store in stores:
                customer_insert_list = []
                customer_update_list = []

                store_id, store_token, store_url = store
                papi = ProductsApi(store_token, store_url)

                cursor.execute('''select uuid from `customer` where store_id=%s''', (store_id, ))
                exist_customer = cursor.fetchall()
                exist_customer_list = [item[0] for item in exist_customer]
                since_id = ""
                print("since id", since_id)
                i = 0
                total = 0
                create_at_max = datetime.datetime.now()
                # create_at_max = datetime.datetime.strptime("2018-12-10T03:23:01",  '%Y-%m-%dT%H:%M:%S')
                create_at_min = create_at_max - datetime.timedelta(days=30)
                time_format = "%Y-%m-%dT%H:%M:%S+08:00"
                # need_to_save = []
                store_crate_time = datetime.datetime.now() - datetime.timedelta(days=500)

                while True:
                    logger.info("the %sth get customers;store:%s" % (i, store_id))
                    create_at_max = create_at_max.strftime(time_format) if isinstance(create_at_max, datetime.datetime) else create_at_max
                    if create_at_max < store_crate_time.strftime(time_format):
                        break

                    ret = papi.get_all_customers(limit=250, created_at_min=create_at_min.strftime(time_format),
                                                 created_at_max=create_at_max, since_id=since_id)
                    if ret["code"] != 1:
                        logger.warning("get shop customer failed. ret={}".format(ret))
                        time.sleep(3)
                        continue
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
                            orders_count = int(customer.get("orders_count", ""))
                            last_order_id = customer.get("last_order_id", None)
                            payment_amount = customer.get("total_spent", "")
                            if uuid in exist_customer_list:
                                customer_tuple = (
                                last_order_id, orders_count, customer_email, accepts_marketing, datetime.datetime.now(),
                                first_name, last_name, uuid)
                                customer_update_list.append(customer_tuple)
                            else:
                                customer_tuple = (
                                    uuid, last_order_id, orders_count, sign_up_time,
                                    first_name, last_name, customer_email, accepts_marketing, store_id, payment_amount,
                                    datetime.datetime.now(), datetime.datetime.now())
                                if uuid not in [item[0] for item in customer_insert_list]:
                                    customer_insert_list.append(customer_tuple)

                    # customer_info = ret["data"].get("customers", "")
                    # need_to_save += customer_info

                    # if str(create_at_max) == str(create_at_max):
                    #     since_id = customer_info[-1].get("id", "")

                    cus_ids = [cus["created_at"] for cus in customer_info]
                    cus_ids = sorted(cus_ids)
                    print(len(customer_info))
                    if len(customer_info) == 250:
                        create_at_max = cus_ids[0]
                        print("more than 250, create_at_max={}".format(create_at_max))
                        print("more than 250, create_at_min={}".format(create_at_min))
                    else:
                        print("less than 250, update date range")
                        print(create_at_min.strftime(time_format))
                        create_at_max = create_at_min
                        create_at_min = create_at_max - datetime.timedelta(days=30)
                        save_moth_customer(customer_insert_list, uuid=uuid, store_id=store_id)
                        # 更新customer中的order数据
                        # sync_last_order_info(store_id, cursor=cursor)
                        customer_insert_list = []
                        customer_update_list = []

                    total += len(customer_info)
                    print(total)

                print("-------------")
                print(total)
        except Exception as e:
            logger.exception("update_collection e={}".format(e))
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

