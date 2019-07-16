from apscheduler.schedulers.background import BackgroundScheduler
import datetime
import threading
import time
import pymysql
import os

from sdk.shopify.get_shopify_data import ProductsApi
from config import logger, SHOPIFY_CONFIG

MYSQL_PASSWD = os.getenv('MYSQL_PASSWD', None)
MYSQL_HOST = os.getenv('MYSQL_HOST', None)


# 47.52.221.217
class DBUtil:
    def __init__(self, host=MYSQL_HOST, port=3306, db="edm", user="edm", password=MYSQL_PASSWD):
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
    def __init__(self, ):
        self.bk_scheduler = BackgroundScheduler()
        self.bk_scheduler.start()
        self.pinterest_job = None
        self.shopify_job = None
        self.rule_job = None
        self.publish_pin_job = None
        self.update_new_job = None
        self.shopify_collections_job = None
        self.shopify_product_job = None

    def start_job_update_shopify_collections(self, interval=7200):
        # 定时更新shopify collections数据
        logger.info("start_job_update_shopify_collections")
        self.update_shopify_collections()
        self.shopify_collections_job = self.bk_scheduler.add_job(self.update_shopify_collections, 'cron', day_of_week="*", hour=1,
                                                     minute=10)

    def start_job_update_shopify_product(self,interval=7200):
        # 定时更新shopify product
        logger.info("start_job_update_shopify_product")
        self.update_shopify_product()
        self.shopify_product_job = self.bk_scheduler.add_job(self.update_shopify_product, 'cron', day_of_week="*", hour=1,)

    def start_job_update_new(self, interval=120):
        def update_new():
            try:
                conn = DBUtil().get_instance()
                cursor = conn.cursor() if conn else None
                if not cursor:
                    return False

                last_update = datetime.datetime.now()-datetime.timedelta(seconds=interval)

                cursor.execute('''select id from `pinterest_account` where add_time>=%s and state=0 and authorized=1''', (last_update, ))
                accounts = cursor.fetchall()
                for id in accounts:
                    self.update_pinterest_data(id[0])

                cursor.execute('''select username from `user` where create_time>=%s and is_active=1''', (last_update, ))
                users = cursor.fetchall()
                for username in users:
                    self.update_shopify_data(username[0])
            except Exception as e:
                logger.exception("update new exception e={}".format(e))
                return False
            finally:
                cursor.close() if cursor else 0
                conn.close() if conn else 0

        # update_new()
        self.update_new_job = self.bk_scheduler.add_job(update_new, 'interval', seconds=interval, max_instances=50)

    def start_all(self, shopify_update_interval=7200):
        logger.info("TaskProcessor start all work.")
        self.start_job_update_shopify_collections(shopify_update_interval)
        self.start_job_update_shopify_product(shopify_update_interval)

    def stop_all(self):
        logger.warning("TaskProcessor stop_all work.")
        self.bk_scheduler.remove_all_jobs()

    def pause(self):
        logger.info("TaskProcessor pause work.")
        if self.bk_scheduler.running:
            self.bk_scheduler.pause()

    def resume(self):
        logger.info("TaskProcessor resume.")
        self.bk_scheduler.resume()

    def update_shopify_product(self):
        """
         获取所有店铺的所有products, 并保存至数据库
         :return:
         """
        logger.info("[update_shopify_product] is cheking...")
        try:
            conn = DBUtil().get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return False

            cursor.execute(
                    """select store.id, store.url, store.token, store.name from store left join user on store.user_id = user.id where user.is_active = 1""")

            stores = cursor.fetchall()

            # 组装store和collection和product数据，之后放入redis中
            store_collections_dict = {}
            store_product_dict = {}
            for store in stores:
                store_id, store_url, store_token, *_ = store
                if not all([store_url, store_token]):
                    logger.warning("[update_shopify_product] store_url or token is invalid, store id={}".format(store_id))
                    continue

                if "shopify" not in store_url:
                    logger.error("[update_shopify_product] store_url not illegal, store id={}".format(store_id))
                    continue
                # 组装 store
                store_collections_dict[store_id] = {}
                store_collections_dict[store_id]["store"] = store
                # 组装 collection
                cursor.execute("""select id, title, category_id from product_category where store_id=%s""", (store_id,))
                collections = cursor.fetchall()
                store_collections_dict[store_id]["collections"] = collections
                # 组装 product
                store_product_dict[store_id] = {}
                cursor.execute('''select id, uuid, product_category_id from `product` where store_id=%s''', (store_id))
                exist_products = cursor.fetchall()
                for exp in exist_products:
                    store_product_dict[store_id][str(exp[1]) + "_" + str(exp[2])] = exp[0]

            # 遍历数据库中的所有store, 拉产品
            for key, value in store_collections_dict.items():
                store_id, store_url, store_token, store_name = value["store"]

                for collection in value["collections"]:
                    id, collection_title, collection_id = collection
                    since_id = ""
                    uuid_list = []
                    papi = ProductsApi(store_token, store_url)
                    for i in range(0, 100):        # 不管拉没拉完，最多拉250＊100个产品
                        logger.info("[update_shopify_product] get collections product store_id={} store_url={},collection_id={},collection_uuid={}".format(store_id,store_url,id,collection_id))
                        ret = papi.get_collections_products(collection_id, limit=250, since_id=since_id)
                        if ret["code"] != 1:
                            logger.error(
                                "[update_shopify_product] get collections product failed store_id={} store_url={},collection_id={},collection_uuid={}".format(
                                    store_id, store_url, id, collection_id))
                            break
                        if ret["code"] == 1:
                            time_now = datetime.datetime.now()
                            products = ret["data"].get("products", [])
                            logger.info(
                                "[update_shopify_product] collections_product successful store_id={} store_url={},collection_id={},collection_uuid={},since_id={}, len products={}".format(
                                    store_id, store_url, id, collection_id,since_id,len(products)))
                            if not products:
                                break
                            for pro in products:
                                pro_uuid = str(pro.get("id", ""))
                                if pro_uuid in uuid_list:
                                    continue
                                handle = pro.get("handle", "")

                                pro_title = pro.get("title", "")
                                pro_url = "https://{}/products/{}".format(store_url, handle)
                                img_obj = pro.get("image", {})
                                if img_obj:
                                    pro_image = img_obj.get("src", "")
                                elif pro.get("images", []):
                                    pro_image = pro.get("images")[0]
                                else:
                                    pro_image = ""
                                try:
                                    uuid_id = str(pro_uuid) + "_" + str(id)
                                    if uuid_id in store_product_dict[store_id].keys():
                                        pro_id = store_product_dict[store_id][uuid_id]
                                        logger.info("[update_shopify_product] product is already exist, store_id={} store_url={}, product_id={} ".format(store_id,store_url,pro_id))
                                        cursor.execute('''update `product` set name=%s, url=%s, image_url=%s, product_category_id=%s, update_time=%s where id=%s''',
                                                       (pro_title, pro_url, pro_image, id, time_now, pro_id))
                                        conn.commit()
                                    else:
                                        cursor.execute(
                                            "insert into `product` (`name`, `url`, `uuid`, `image_url`,`product_category_id`, `store_id`, `create_time`, `update_time`) values (%s, %s, %s, %s, %s, %s, %s, %s)",
                                            (pro_title, pro_url, pro_uuid, pro_image, id, store_id, time_now, time_now))
                                        pro_id = cursor.lastrowid
                                        logger.info("[update_shopify_product] product is new, store_id={},store_url={}, product_id={}，product_category_id={}".format(store_id,store_url, pro_id, id))
                                        conn.commit()
                                    uuid_list.append(pro_uuid)
                                except Exception as e:
                                    logger.exception("[update_shopify_product] exception, store_id={}, error=%s".format(store_id, str(e)))

                            # 拉完了
                            if len(products) < 250:
                                break
                            else:
                                since_id = products[-1].get("id", "")
                                if not since_id:
                                    break
        except Exception as e:
            logger.exception("[update_shopify_product] exception error=%s".format(str(e)))
            return False
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0
        logger.exception("[update_shopify_product] is finished")
        return True


    def update_shopify_collections(self):
        """
        1. 获取所有店铺的所有类目，并保存至数据库
        """
        logger.info("update_collection is cheking...")
        try:
            conn = DBUtil().get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return False

            cursor.execute(
                    """select store.id, store.url, store.token from store left join user on store.user_id = user.id where user.is_active = 1""")
            stores = cursor.fetchall()

            for store in stores:
                store_id, store_url, store_token = store

                # 取中已经存在的所有products, 只需更新即可
                cursor.execute('''select id, category_id from `product_category` where store_id=%s''', (store_id))
                product_category = cursor.fetchall()
                exist_collections_dict = {}
                for exp in product_category:
                    exist_collections_dict[exp[1]] = exp[0]

                if not all([store_url, store_token]):
                    logger.warning("store url or token is invalid, store id={}".format(store_id))
                    continue

                if "shopify" not in store_url:
                    logger.error("store uri={}, not illegal")
                    continue

                papi = ProductsApi(store_token, store_url)
                # 更新产品类目信息
                res = papi.get_all_collections()
                if res["code"] == 1:
                    result = res["data"]["custom_collections"]
                    result = result + res["data"]["smart_collections"]

                    for collection in result:
                        category_id = collection["id"]
                        url = store_url + "/collections/" + collection["handle"] + "/"
                        title = collection["title"]
                        update_time = datetime.datetime.now()
                        try:
                            if str(category_id) in exist_collections_dict.keys():
                                id = exist_collections_dict[str(category_id)]
                                logger.info("product_collections is already exist, url={}, id={}".format(url,id))
                                cursor.execute(
                                    '''update `product_category` set title=%s, url=%s, category_id=%s, update_time=%s where id=%s''',
                                    (title, url, category_id, update_time, id))
                            else:
                                cursor.execute(
                                    "insert into `product_category` (`title`, `url`, `category_id`, `store_id`, `create_time`, `update_time`) values (%s, %s, %s, %s, %s, %s)",
                                    (title, url, category_id, store_id, update_time, update_time))
                            conn.commit()
                        except Exception as e:
                            logger.exception("update product_category exception e={}".format(e))
        except Exception as e:
            logger.exception("update_collection e={}".format(e))
            return False
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0
        return True


    def update_shopify_sales_volume(self):
        """更新产品销售量"""
        logger.info("update_collection is cheking...")
        try:
            conn = DBUtil().get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return False

            cursor.execute(
                    """select store.id, store.url, store.token from store left join user on store.user_id = user.id where user.is_active = 1""")
            stores = cursor.fetchall()
            if not stores:
                return False

            for store in stores:
                store_id, store_url, store_token = store
                papi = ProductsApi(store_token, store_url)
                # 更新产品类目信息
                res = papi.get_all_collections()
                if res["code"] == 1:
                    pass
        except:
            pass

                
def main():
    tsp = TaskProcessor()
    tsp.start_all(rule_interval=120, publish_pin_interval=120, pinterest_update_interval=7200*3, shopify_update_interval=7200*3, update_new=120)
    while 1:
        time.sleep(1)


def analyze_rule():
    group_condition = {"relation": "&&,||", "condition": "Customer last click email time", "relations": {"is over": {"values": [1, 3], "unit": "days"}, "equal": {"values": [34], "unit": "$"}}},

if __name__ == '__main__':
    # test()
    # main()
    #TaskProcessor().update_shopify_collections()
    # TaskProcessor().update_shopify_product()
    TaskProcessor().update_shopify_sales_volume()
