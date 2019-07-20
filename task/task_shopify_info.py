from apscheduler.schedulers.background import BackgroundScheduler
import datetime
import threading
import time
import pymysql
import os
import sys

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
                customer_insert_list = []
                customer_update_list = []
                store_id, store_token, store_url = store
                papi = ProductsApi(store_token, store_url)
                created_at_max = "2019-05-19T05:28:29+8:00"

                cursor.execute('''select uuid from `customer` where store_id=%s''', (store_id, ))
                exist_customer = cursor.fetchall()
                exist_customer_list = [item[0] for item in exist_customer]
                i = 0
                # for i in range(40):
                while True:
                    logger.info("the %sth get customers;store:%s" % (i, store_id))
                    ret = papi.get_all_customers(limit=250, created_at_max=created_at_max)
                    print(created_at_max)
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

                            # if last_order_id:
                            #     order_status = papi.get_orders_id(order_id=last_order_id)
                            #     if order_status.get("code", -1) == 0:
                            #         orderinfo = order_status["data"].get("orders", [])
                            #         orderinfo = orderinfo[0] if orderinfo else {}
                            #         if orderinfo.get("financial_status"):
                            #             financial_status = 0 if orderinfo.get("financial_status", "") == "paid" else 1
                            #             last_order_data = (orderinfo.get("updated_at", "")).split('+')[0]
                            #             last_order_time = datetime.datetime.strptime(last_order_data, '%Y-%m-%dT%H:%M:%S')
                            # financial_status = 0
                            # last_order_time = datetime.datetime.now()

                            if uuid in exist_customer_list:
                                customer_tuple = (last_order_id, orders_count, customer_email, accepts_marketing, datetime.datetime.now(), first_name, last_name, uuid)
                                customer_update_list.append(customer_tuple)
                            else:
                                customer_tuple = (
                                uuid, last_order_id, orders_count, sign_up_time,
                                first_name, last_name, customer_email, accepts_marketing, store_id, payment_amount,
                                datetime.datetime.now(), datetime.datetime.now())
                                if uuid not in [item[0] for item in customer_insert_list]:
                                    customer_insert_list.append(customer_tuple)
                                    # exist_customer_list.append(uuid)
                        i += 1
                        if len(customer_info) < 250:
                            break
                        else:
                            created_at_max = customer_info[-1].get("created_at", "")
                            print(created_at_max)
                            print(len(customer_info))
                            if not created_at_max:
                                break

                # 数据入库
                logger.warn("customer insert Memory usage", sys.getsizeof(customer_insert_list), len(customer_insert_list))
                logger.warn("customer updata Memory usage", sys.getsizeof(customer_update_list), len(customer_update_list))
                if customer_insert_list:
                    # customer_insert_info = str(customer_insert_list)[1:-1]
                    logger.info("customer is already exist [insert], uuid={}".format(uuid))
                    cursor.executemany('''insert into `customer` (`uuid`, `last_order_id`,`orders_count`,`sign_up_time`, `first_name`, `last_name`, `customer_email`, `accept_marketing_status`, `store_id`, `payment_amount`, `create_time`, `update_time`)
                                                 values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                                       customer_insert_list)
                    conn.commit()
                if customer_update_list:
                    logger.info("customer is already exist [update], uuid={}".format(uuid))
                    cursor.executemany(
                        '''update `customer` set last_order_id=%s, orders_count=%s, customer_email=%s, accept_marketing_status=%s, update_time=%s, first_name=%s, last_name=%s where uuid=%s''',
                        customer_update_list)
                    conn.commit()
        except Exception as e:
            logger.exception("update_collection e={}".format(e))
            # return False

        # try:
        #     if customer_insert_list:
        #         # customer_insert_info = str(customer_insert_list)[1:-1]
        #         logger.info("customer is already exist [insert], uuid={}".format(uuid))
        #         cursor.executemany('''insert into `customer` (`uuid`, `last_order_id`,`orders_count`,`sign_up_time`, `first_name`, `last_name`, `customer_email`, `accept_marketing_status`, `store_id`, `payment_amount`, `create_time`, `update_time`)
        #                                      values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
        #                                     customer_insert_list)
        #         conn.commit()
        #     if customer_update_list:
        #         logger.info("customer is already exist [update], uuid={}".format(uuid))
        #         cursor.executemany(
        #             '''update `customer` set last_order_id=%s, orders_count=%s, customer_email=%s, accept_marketing_status=%s, update_time=%s, first_name=%s, last_name=%s where uuid=%s''',
        #             customer_update_list)
        #         conn.commit()
        #
        # except Exception as e:
        #     logger.exception("update_collection e={}".format(e))
        #     return False
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

