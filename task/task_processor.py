from apscheduler.schedulers.background import BackgroundScheduler
import datetime
import threading
import time
import pymysql
import os

from io import BytesIO
import base64
from PIL import Image
import requests
import re

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

    def start_all(self, shopify_update_interval=7200 ):
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

    def update_shopify_product(self, url=""):
        """
         获取所有店铺的所有products, 并保存至数据库
         :return:
         """
        logger.info("update_shopify_product is cheking...")
        try:
            conn = DBUtil().get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return False
            if url:
                cursor.execute(
                    '''select store.id, store.uri, store.token, store.name, store.url, store.user_id, store.store_view_id from store left join user on store.user_id = user.id where user.is_active = 1 and url=%s''',
                    (url,))
            else:
                cursor.execute(
                    """select store.id, store.uri, store.token, store.name, store.url, store.user_id, store.store_view_id from store left join user on store.user_id = user.id where user.is_active = 1""")

            stores = cursor.fetchall()

            cursor.execute('''select tag from `product_history_data` where id>0''')
            tags = cursor.fetchall()
            if not tags:
                tag_max = 1
            else:
                tag_max = max([tag[0] if tag[0] else 0 for tag in tags])

            # 组装store和collection和product数据，之后放入redis中
            store_collections_dict = {}
            store_product_dict = {}
            for store in stores:
                store_id, store_uri, store_token, *_ = store
                if not all([store_uri, store_token]):
                    logger.warning("store url or token is invalid, store id={}".format(store_id))
                    continue

                if "shopify" not in store_uri:
                    logger.error("update_shopify_product store uri={}, not illegal".format(store_uri))
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

            # 遍历数据库中的所有store,获取GA数据,拉产品
            new_product = {}
            for key, value in store_collections_dict.items():
                store_id, store_uri, store_token, store_name, store_url, user_id, store_view_id = value["store"]

                cursor.execute(
                    """select user_id from store where id=%s""", (store_id))
                user_id = cursor.fetchone()[0]

                cursor.execute(
                    """select id from rule where id=%s""",(user_id))
                is_user = cursor.fetchall()

                for collection in value["collections"]:
                    id, collection_title, collection_id = collection
                    # 获取该店铺的ga数据
                    gapi = GoogleApi(view_id=store_view_id, ga_source=SHOPIFY_CONFIG.get("utm_source", "pinbooster"), json_path=os.path.join(sys.path[0], "sdk//googleanalytics//client_secrets.json"))
                    reports = gapi.get_report(key_word="", start_time="1daysAgo", end_time="today")

                    since_id = ""
                    uuid_list = []
                    papi = ProductsApi(store_token, store_uri)
                    for i in range(0, 100):        # 不管拉没拉完，最多拉250＊100个产品
                        logger.info("update_shopify_product get product store_id={},store_token={},store_uri={},collection_id={},collection_uuid={}".format(store_id,store_token,store_uri,id,collection_id))
                        ret = papi.get_collections_products(collection_id, limit=250, since_id=since_id)
                        if ret["code"] != 1:
                            logger.warning("get shop products failed. ret={}".format(ret))
                            break
                        if ret["code"] == 1:
                            time_now = datetime.datetime.now()
                            products = ret["data"].get("products", [])
                            logger.info("get all products succeed, limit=250, since_id={}, len products={}".format(since_id,len(products)))
                            if not products:
                                break
                            for pro in products:
                                pro_uuid = str(pro.get("id", ""))
                                if pro_uuid in uuid_list:
                                    continue

                                handle = pro.get("handle", "")

                                pro_title = pro.get("title", "")
                                pro_url = "https://{}/products/{}".format(store_url, handle)
                                pro_type = pro.get("product_type", "")
                                variants = pro.get("variants", [])
                                pro_sku = handle.upper()

                                pro_price = 0
                                if variants:
                                    # pro_sku = variants[0].get("sku", "")
                                    pro_price = float(variants[0].get("price", "0"))

                                pro_tags = pro.get("tags", "")
                                img_obj = pro.get("image", {})
                                if img_obj:
                                    pro_image = img_obj.get("src", "")
                                elif pro.get("images", []):
                                    pro_image = pro.get("images")[0]
                                else:
                                    pro_image = ""
                                thumbnail = self.image_2_base64(pro_image)
                                try:
                                    if pro.get("published_at", ""):
                                        time_str = pro.get("published_at", "")[0:-6]
                                        pro_publish_time = datetime.datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S")
                                    else:
                                        pro_publish_time = None
                                except:
                                    pro_publish_time = None

                                try:
                                    uniq_id = str(pro_uuid) + "_" + str(id)
                                    if uniq_id in store_product_dict[store_id].keys():
                                        pro_id = store_product_dict[store_id][uniq_id]
                                        logger.info("product is already exist, pro_uuid={}, pro_id={}".format(pro_uuid, pro_id))
                                        cursor.execute('''update `product` set sku=%s, url=%s, name=%s, price=%s, tag=%s, update_time=%s, image_url=%s, thumbnail=%s, publish_time=%s, product_category_id=%s where id=%s''',
                                                       (pro_sku, pro_url, pro_title, pro_price, pro_tags, time_now, pro_image, thumbnail, pro_publish_time, id, pro_id))
                                        conn.commit()
                                    else:

                                        cursor.execute(
                                            "insert into `product` (`sku`, `url`, `name`, `image_url`,`thumbnail`, `price`, `tag`, `create_time`, `update_time`, `store_id`, `publish_time`, `uuid`, `product_category_id`) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                                            (pro_sku, pro_url, pro_title, pro_image, thumbnail, pro_price, pro_tags, time_now,
                                             time_now, store_id, pro_publish_time, pro_uuid,id))
                                        pro_id = cursor.lastrowid
                                        conn.commit()
                                        if not is_user:
                                            continue
                                        if store_id not in new_product.keys():
                                            new_product[store_id] = {id:[(pro_id, pro_title, pro_url)]}
                                        else:
                                            if id not in new_product[store_id].keys():
                                                new_product[store_id][id] = [(pro_id, pro_title, pro_url)]
                                            else:
                                                new_product[store_id][id].append((pro_id, pro_title, pro_url))
                                    uuid_list.append(pro_uuid)
                                except Exception as e:
                                    logger.exception("update product exception.")

                                if not store_view_id:
                                    logger.warning("this product have no store view id, product id={}, store id={}".format(pro_id, store_id))
                                    continue

                                pro_uuid = "google" # 测试
                                ga_data = gapi.get_report(key_word=pro_uuid, start_time="1daysAgo", end_time="today")
                                time_now = datetime.datetime.now()
                                if reports.get("code", 0) == 1:
                                    data = reports.get("data", {})
                                    pro_report = data.get(pro_uuid, {})
                                    # 这个产品如果没有关联的pin，就不用保存历史数据了
                                    # 单一产品更新数据时不保存历史数据，tag会错乱
                                    if pro_report and not url:
                                        pv = int(pro_report.get("sessions", 0))
                                        uv = int(pro_report.get("users", 0))
                                        nuv = int(pro_report.get("new_users", 0))
                                        hits = int(pro_report.get("hits", 0))
                                        transactions = int(pro_report.get("transactions", 0))
                                        transactions_revenue = float(pro_report.get("revenue", 0))
                                        # cursor.execute('''select product_visitors from `product_history_data` where product_id=%s and tag=%s''', (pro_id, tag_max))
                                        # visitors = cursor.fetchone()
                                        # total_visitors = uv
                                        # if visitors:
                                        #     total_visitors += visitors[0]
                                        # 如果全是0就不存了
                                        if not (pv == 0 and uv == 0 and nuv == 0 and transactions == 0):
                                            cursor.execute('''insert into `product_history_data` (`product_visitors`, `product_new_visitors`, `product_clicks`, `product_scan`, `product_sales`, `product_revenue`, `update_time`, `product_id`, `store_id`, `tag`) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''', (uv, nuv, hits, pv, transactions, transactions_revenue, time_now, pro_id, store_id, tag_max+1))
                                            conn.commit()
                                else:
                                    logger.warning("get GA data failed, store view id={}, key_words={}".format(store_view_id, pro_uuid))

                            # 拉完了
                            if len(products) < 250:
                                break
                            else:
                                since_id = products[-1].get("id", "")
                                if not since_id:
                                    break

            self.update_rule(conn, cursor, new_product)
        except Exception as e:
            logger.exception("get_products e={}".format(e))
            return False
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0

        return True


    def update_shopify_collections(self):
        """
        1. 更新所有的店铺
        2. 获取所有店铺的所有类目，并保存至数据库
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
                # 更新店铺信息
                # ret = papi.get_shop_info()
                # if ret["code"] == 1:
                #     shop = ret["data"].get("shop", {})
                #     logger.info("shop info={}".format(shop))
                #     shop_uuid = shop.get("id", "")
                #     shop_name = shop.get("name", "")
                #     shop_timezone = shop.get("timezone", "")
                #     shop_domain = shop.get("domain", "")
                #     shop_email = shop.get("email", "")
                #     shop_owner = shop.get("shop_owner", "")
                #     shop_country_name = shop.get("country_name", "")
                #     created_at = shop.get("created_at", '')
                #     updated_at = shop.get("updated_at", '')
                #     shop_phone = shop.get("phone", "")
                #     shop_city = shop.get("city", '')
                #     shop_currency = shop.get("currency", "USD")
                #     # shop_myshopify_domain = shop.get("myshopify_domain", "")
                #     cursor.execute('''update `store` set uuid=%s, name=%s, domain=%s, timezone=%s, email=%s, owner_name=%s,
                #     owner_phone=%s, country=%s, city=%s, store_create_time=%s, store_update_time=%s, currency=%s where id=%s''',
                #                    (shop_uuid, shop_name, shop_domain, shop_timezone, shop_email, shop_owner, shop_phone,
                #                     shop_country_name, shop_city, datetime.datetime.strptime(created_at[0:-6], "%Y-%m-%dT%H:%M:%S"),
                #                     datetime.datetime.strptime(updated_at[0:-6], "%Y-%m-%dT%H:%M:%S"), shop_currency, store_id))
                #     conn.commit()
                # else:
                #     logger.warning("get shop info failed. ret={}".format(ret))

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


def main():
    tsp = TaskProcessor()
    tsp.start_all(rule_interval=120, publish_pin_interval=120, pinterest_update_interval=7200*3, shopify_update_interval=7200*3, update_new=120)
    while 1:
        time.sleep(1)


if __name__ == '__main__':
    # test()
    # main()
    TaskProcessor().update_shopify_collections()
