import datetime
import json
import os
import time
import pymysql
from collections import Counter

from sdk.googleanalytics.google_oauth_info import GoogleApi
from sdk.shopify.get_shopify_data import ProductsApi
from config import logger, SHOPIFY_CONFIG
from task.db_util import DBUtil
from config import logger, ROOT_PATH
from sdk.shopify import shopify_webhook


class ShopifyDataProcessor:
    def __init__(self, db_info):
        self.db_host = db_info.get("host", "")
        self.db_port = db_info.get("port", 3306)
        self.db_name = db_info.get("db", "")
        self.db_user = db_info.get("user", "")
        self.db_password = db_info.get("password", "")
        self.root_path = ROOT_PATH

    def save_customer_db(self, customer_insert_list, customer_update_list, cursor=None, conn=None):
        if not cursor:
            conn = DBUtil().get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return False

        try:
            if customer_insert_list:
                cursor.executemany('''insert into `customer` (`uuid`, `last_order_id`,`orders_count`,`sign_up_time`, `first_name`, `last_name`, `customer_email`, `accept_marketing_status`, `store_id`, `payment_amount`, `create_time`, `update_time`)
                                                             values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                                   customer_insert_list)
                conn.commit()

            if customer_update_list:
                cursor.executemany(
                    '''update `customer` set last_order_id=%s, orders_count=%s, customer_email=%s, accept_marketing_status=%s, update_time=%s, first_name=%s, last_name=%s where uuid=%s''',
                    customer_update_list)
                conn.commit()
            logger.info("save customer  data is success")
        except Exception as e:
            logger.exception("save_customer_db e={}".format(e))

    def update_shopify_product(self, input_store=None):
        """
         获取所有店铺的所有products, 并保存至数据库
         :return:
         """
        logger.info("[update_shopify_product] is cheking...")
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user, password=self.db_password).get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return False

            # 如果store为None，证明任务是周期性任务，否则为 新店铺
            if not input_store:
                cursor.execute(
                        """select store.id, store.url, store.token, store.name from store left join user on store.user_id = user.id where user.is_active = 1""")
                stores = cursor.fetchall()
            else:
                stores = input_store

            # 组装store和collection和product数据，之后放入redis中
            store_collections_dict = {}
            store_product_dict = {}
            for store in stores:
                store_id, store_url, store_token, *_ = store

                if not input_store:
                    # 判断此店铺的update_time最大一条数据，如果此数据小于当前时间23小时，就继续。
                    cursor.execute(
                        """select id,update_time from `product` where store_id = %s order by update_time desc limit 1"""%(store_id))
                    product = cursor.fetchone()
                    yesterday_time = (datetime.datetime.now() - datetime.timedelta(hours=24))
                    if product and product[1] > yesterday_time:
                        logger.warning("update_shopify_product this store was renewed in 24 hours store_id={} product_id={} product_update_time={}".format(store_id, product[0], product[1]))
                        continue

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
                store_id, store_url, store_token, *_ = value["store"]

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

                                variants = pro.get("variants", [])

                                price = 0
                                if variants:
                                    price = float(variants[0].get("price", "0"))

                                try:
                                    uuid_id = str(pro_uuid) + "_" + str(id)
                                    if uuid_id in store_product_dict[store_id].keys():
                                        pro_id = store_product_dict[store_id][uuid_id]
                                        logger.info("[update_shopify_product] product is already exist, store_id={} store_url={}, product_id={},product_category_id={} ".format(store_id,store_url,pro_id,id))
                                        cursor.execute('''update `product` set name=%s, url=%s, image_url=%s,price=%s,product_category_id=%s, update_time=%s where id=%s''',
                                                       (pro_title, pro_url, pro_image,price, id, time_now, pro_id))
                                        conn.commit()
                                    else:
                                        cursor.execute(
                                            "insert into `product` (`name`, `url`, `uuid`, `price`,`image_url`,`product_category_id`, `store_id`, `create_time`, `update_time`) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                                            (pro_title, pro_url, pro_uuid, price, pro_image, id, store_id, time_now, time_now))
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
        logger.info("update shopify product is finished")
        return True

    def update_shopify_collections(self, input_store=None):
        """
        1. 获取所有店铺的所有类目，并保存至数据库
        """
        logger.info("update_collection is cheking...")
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user, password=self.db_password).get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return False

            # 如果store为None，证明任务是周期性任务，否则为 新店铺
            if not input_store:
                cursor.execute(
                        """select store.id, store.url, store.token from store left join user on store.user_id = user.id where user.is_active = 1""")
                stores = cursor.fetchall()
            else:
                stores = input_store

            for store in stores:
                store_id, store_url, store_token, *_ = store

                if not input_store:
                    # 判断此店铺的update_time最大一条数据，如果此数据小于当前时间23小时，就继续。
                    cursor.execute(
                        """select id, update_time from `product_category` where store_id = %s order by update_time desc limit 1"""%(store_id,))
                    product_category = cursor.fetchone()
                    yesterday_time = (datetime.datetime.now() - datetime.timedelta(hours=24))
                    if product_category and product_category[1] > yesterday_time:
                        logger.warn("update_collection this store was renewed in 24 hours store_id={} product_category_id={} product_category_update_time={}".format(store_id,product_category[0],product_category[1]))
                        continue

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
        logger.info("update_collection update finished")
        return True

    def update_shopify_orders(self, input_store=None):
        """更新店铺的订单"""
        logger.info("update_shopify_orders is cheking...")
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user, password=self.db_password).get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return False
            # 如果store为None，证明任务是周期性任务，否则为 新店铺
            if not input_store:
                cursor.execute(
                        """select store.id, store.url, store.token from store left join user on store.user_id = user.id where user.is_active = 1""")
                stores = cursor.fetchall()
                if not stores:
                    return False
            else:
                stores = input_store
            for store in stores:
                store_id, store_url, store_token, *_ = store

                cursor.execute(
                    """select order_uuid from order_event where store_id={}""".format(store_id))
                orders = cursor.fetchall()
                order_list = [item[0] for item in orders] if orders else []

                papi = ProductsApi(store_token, store_url)

                created_at_max = datetime.datetime.now()
                created_at_min = datetime.datetime.combine(datetime.date.today() - datetime.timedelta(days=121), datetime.time.min)
                for i in range(0, 1000):
                    res = papi.get_all_orders(created_at_min, created_at_max)
                    if res["code"] != 1:
                        logger.error("update order info failed, store id={}".format(store_id))
                        break
                    else:
                        orders = res["data"].get("orders", [])
                        logger.info("get store history order info succeed, orders={}".format(len(orders)))
                        for order in orders:
                            order_uuid = order["id"]
                            if order_uuid in order_list:
                                continue
                            if order["financial_status"] == "paid":
                                status = 1
                            else:
                                status = 0
                            customer_uuid = order["customer"]["id"]
                            order_create_time = order["created_at"].replace("T"," ").split("+")[0]
                            order_update_time = order["updated_at"].replace("T"," ").split("+")[0]
                            total_price = order["total_price"]
                            status_tag = order["financial_status"]
                            status_url = order["order_status_url"]
                            checkout_id = order["checkout_id"]
                            create_time = datetime.datetime.now()
                            update_time = datetime.datetime.now()
                            li = []
                            for item in order["line_items"]:
                                product_id = item["product_id"]
                                title = item["title"]
                                price = float(item["price"])
                                quantity = item["quantity"]
                                li.append({"product_id":product_id,"title":title,"price":price,"quantity":quantity})
                            product_info = json.dumps(li)
                            cursor.execute(
                                "insert into `order_event` (`order_uuid`,`checkout_id`, `status`,`status_tag`,`status_url`,`product_info`,`customer_uuid`,`total_price`,`store_id`,`order_create_time`,`order_update_time`,`create_time`, `update_time`) values (%s,%s,%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                                (order_uuid, checkout_id, status, status_tag, status_url, product_info, customer_uuid, total_price, store_id, order_create_time, order_update_time, create_time, update_time))
                            conn.commit()
                            order_id = cursor.lastrowid
                            order_list.append(order_uuid)

                        # 拉完了
                        if len(orders) < 250:
                            break
                        else:
                            created_at_max = orders[-1].get("created_at", "")

        except Exception as e:
            logger.exception("update_shopify_orders e={}".format(e))
            return False
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0
        logger.info("update_shopify_orders id finished")
        return True

    def update_top_product(self,store=None):
        """更新tot product"""
        logger.info("update_top_product is cheking...")
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user, password=self.db_password).get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return False
            if not store:
                cursor.execute(
                    """select store.id, store.url, store.token from store left join user on store.user_id = user.id where user.is_active = 1""")
                stores = cursor.fetchall()
                if not stores:
                    return False
            else:
                stores = store

            for store in stores:
                store_id, store_url, store_token = store
                top_three_product_list,top_seven_product_list,top_fifteen_product_list,top_thirty_product_list = [],[],[],[]
                top_three_time = datetime.datetime.combine(datetime.date.today() - datetime.timedelta(days=3),datetime.time.min)
                top_seven_time = datetime.datetime.combine(datetime.date.today() - datetime.timedelta(days=7),datetime.time.min)
                top_fifteen_time = datetime.datetime.combine(datetime.date.today() - datetime.timedelta(days=15),datetime.time.min)
                top_thirty_time = datetime.datetime.combine(datetime.date.today() - datetime.timedelta(days=30),datetime.time.min)
                cursor.execute(
                    """select id, product_info,order_update_time from order_event where store_id = %s and order_update_time >= %s""",(store_id,top_thirty_time))
                order_events = cursor.fetchall()
                if not order_events:
                    continue
                for item in order_events:
                    id, product_info, order_update_time = item
                    product_info = json.loads(product_info)
                    if order_update_time >= top_thirty_time:
                        for product in product_info:
                            top_thirty_product_list.append(product["product_id"])
                    if order_update_time >= top_fifteen_time:
                        for product in product_info:
                            top_fifteen_product_list.append(product["product_id"])
                    if order_update_time >= top_seven_time:
                        for product in product_info:
                            top_seven_product_list.append(product["product_id"])
                    if order_update_time >= top_three_time:
                        for product in product_info:
                            top_three_product_list.append(product["product_id"])

                cursor_dict = conn.cursor(cursor=pymysql.cursors.DictCursor)

                top_three_product_list = [item[0] for item in Counter(top_three_product_list).most_common(6)]
                top_seven_product_list = [item[0] for item in Counter(top_seven_product_list).most_common(6)]
                top_fifteen_product_list = [item[0] for item in Counter(top_fifteen_product_list).most_common(6)]
                top_thirty_product_list = [item[0] for item in Counter(top_thirty_product_list).most_common(6)]
                current_time = datetime.datetime.now()


                # top_three
                cursor_dict.execute(
                    """select id,name,url,uuid,price,image_url,state from product where store_id = %s and uuid in %s""",(store_id, top_three_product_list))
                top_three_product = cursor_dict.fetchall()

                top_three_list = []
                exit_top_three_list = []
                for item in top_three_product:
                    if item["uuid"] not in exit_top_three_list:
                        item["image_url"] = item["image_url"] + ""
                        exit_top_three_list.append(item["uuid"])
                        top_three_list.append(item)
                cursor.execute(
                    """select id from top_product where store_id = %s """,(store_id))
                store = cursor.fetchall()
                if not store:
                    cursor.execute(
                        "insert into `top_product` (`top_three`, `store_id`, `create_time`, `update_time`) values (%s, %s, %s, %s)",
                        (json.dumps(top_three_list),store_id, current_time,current_time))
                    conn.commit()
                else:
                    cursor.execute(
                        '''update `top_product` set top_three=%s,update_time=%s where store_id=%s''', (json.dumps(top_three_list),current_time, store_id))
                    conn.commit()


                # top_seven
                cursor_dict.execute(
                    """select id,name,url,uuid,price,image_url,state from product where store_id = %s and uuid in %s""",(store_id, top_seven_product_list))
                top_seven_product = cursor_dict.fetchall()

                top_seven_list = []
                exit_top_seven_list = []
                for item in top_seven_product:
                    if item["uuid"] not in exit_top_seven_list:
                        exit_top_seven_list.append(item["uuid"])
                        top_seven_list.append(item)
                cursor.execute(
                    """select id from top_product where store_id = %s """,(store_id))
                store = cursor.fetchall()
                if not store:
                    cursor.execute(
                        "insert into `top_product` (`top_seven`, `store_id`, `create_time`, `update_time`) values (%s, %s, %s, %s)",
                        (json.dumps(top_seven_list),store_id, current_time,current_time))
                    conn.commit()
                else:
                    cursor.execute(
                        '''update `top_product` set top_seven=%s,update_time=%s where store_id=%s''', (json.dumps(top_seven_list),current_time, store_id))
                    conn.commit()


                # top_fifteen
                cursor_dict.execute(
                    """select id,name,url,uuid,price, image_url,state from product where store_id = %s and uuid in %s""",(store_id, top_fifteen_product_list))
                top_fifteen_product = cursor_dict.fetchall()

                top_fifteen_list = []
                exit_top_fifteen_list = []
                for item in top_fifteen_product:
                    if item["uuid"] not in exit_top_fifteen_list:
                        exit_top_fifteen_list.append(item["uuid"])
                        top_fifteen_list.append(item)
                cursor.execute(
                    """select id from top_product where store_id = %s """,(store_id))
                store = cursor.fetchall()
                if not store:
                    cursor.execute(
                        "insert into `top_product` (`top_fifteen`, `store_id`, `create_time`, `update_time`) values (%s, %s, %s, %s)",
                        (json.dumps(top_fifteen_list),store_id, current_time,current_time))
                    conn.commit()
                else:
                    cursor.execute(
                        '''update `top_product` set top_fifteen=%s,update_time=%s where store_id=%s''', (json.dumps(top_fifteen_list),current_time, store_id))
                    conn.commit()


                ## top_thirty
                cursor_dict.execute(
                    """select id,name,url,uuid,price, image_url,state from product where store_id = %s and uuid in %s""",(store_id, top_thirty_product_list))
                top_thirty_product = cursor_dict.fetchall()

                top_thirty_list = []
                exit_top_thirty_list = []
                for item in top_thirty_product:
                    if item["uuid"] not in exit_top_thirty_list:
                        exit_top_thirty_list.append(item["uuid"])
                        top_thirty_list.append(item)
                cursor.execute(
                    """select id from top_product where store_id = %s """,(store_id))
                store = cursor.fetchall()
                if not store:
                    cursor.execute(
                        "insert into `top_product` (`top_thirty`, `store_id`, `create_time`, `update_time`) values (%s, %s, %s, %s)",
                        (json.dumps(top_thirty_list),store_id, current_time,current_time))
                    conn.commit()
                else:
                    cursor.execute(
                        '''update `top_product` set top_thirty=%s,update_time=%s where store_id=%s''', (json.dumps(top_thirty_list),current_time, store_id))
                    conn.commit()
        except Exception as e:
            logger.exception("update_top_product e={}".format(e))
            return False
        finally:
            cursor.close() if cursor else 0
            cursor_dict.close() if cursor_dict else 0
            conn.close() if conn else 0
        logger.info("update_top_product is finished...")
        return True

    def updata_shopify_ga(self):
        logger.info("update_shopify GA is cheking...")
        """
        每天凌晨一点拉取GA数据
        :return:
        """
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user,
                          password=self.db_password).get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return False
            # 获取所有店铺
            cursor.execute("""select id from store""")
            for store in cursor.fetchall():
                store_id = store[0]
                # 配置时间
                results_list = []
                now_date = datetime.datetime.now()
                zero_time = now_date - datetime.timedelta(hours=now_date.hour, minutes=now_date.minute,
                                                          seconds=now_date.second, microseconds=now_date.microsecond)
                last_time = zero_time + datetime.timedelta(hours=23, minutes=59, seconds=59)
                # 获取当前店铺所有的orders
                cursor.execute(
                    """select total_orders, total_revenue, total_sessions from dashboard where store_id= %s and update_time between %s and %s""",
                    (store_id, zero_time - datetime.timedelta(days=1), last_time - datetime.timedelta(days=1)))
                orders_info = cursor.fetchone()
                if orders_info:
                    total_orders, total_revenue, total_sessions = orders_info
                    if total_orders is None:
                        total_orders= 0
                    if total_revenue is None:
                        total_revenue= 0.0
                    if total_sessions is None:
                        total_sessions= 0
                else:
                    total_orders = total_revenue = total_sessions = 0

                # 获取当前店铺支付订单大于等于2的用户数
                cursor.execute(
                    """select count(customer_uuid) from (SELECT customer_uuid, count(id) as num FROM order_event where store_id= %s and status_tag='paid' group by customer_uuid) as res where num >= 2;""",
                    (store_id,))
                orders_gte2 = cursor.fetchone()[0]

                # 获取当前店铺的用户总量
                cursor.execute("""SELECT count(id)  FROM  order_event where store_id= %s;""", (store_id,))
                total_cumtomers = cursor.fetchone()[0]

                # 获取GA数据
                cursor.execute(
                    """select store.store_view_id from store where store.id = %s""", (store_id,))
                store_view_id = cursor.fetchone()[0]
                if store_view_id:
                    papi = GoogleApi(view_id=store_view_id,
                                     json_path=os.path.join(self.root_path, r"sdk//googleanalytics//client_secrets.json"))
                    shopify_google_data = papi.get_report(key_word="", start_time="1daysAgo", end_time="today")
                    data_list = {}
                    if shopify_google_data["code"] == 1:
                        data_list = shopify_google_data.get("data", {}).get("results", {})
                        for values in data_list.items():
                            res = (values[1].get("sessions", ""), values[1].get("transactions", ""), values[1].get("revenue", ""), datetime.datetime.now(), values[0])
                            results_list.append(res)
                        shopify_total_results = shopify_google_data.get("data", {}).get("total_results", {})
                        sessions = shopify_total_results.get("sessions", 0)
                        orders = shopify_total_results.get("transactions", 0)
                        revenue = shopify_total_results.get("revenue", 0.0)
                        total_orders += orders
                        total_sessions += sessions
                        total_revenue += revenue

                        # 平均转换率  总支付订单数÷总流量
                        avg_conversion_rate = (total_orders / total_sessions) if total_sessions else 0
                        # 重复的购买率 支付订单数≥2的用户数据÷总用户数量
                        avg_repeat_purchase_rate = (orders_gte2 / total_cumtomers) if total_cumtomers else 0
                    else:
                        sessions = orders = revenue = total_orders = total_sessions = total_revenue = avg_conversion_rate = avg_repeat_purchase_rate = 0

                # 更新email_template的数据
                cursor.executemany(
                    """update email_template set sessions=%s, transcations=%s, revenue=%s ,update_time=%s where id =%s""",
                    results_list)

                # 更新email_trigger的数据
                cursor.execute("""select id, email_delay from email_trigger where store_id=%s""",(store_id, ))
                trigger_info = cursor.fetchall()
                trigger_tuple = []
                for triggers in trigger_info:
                    template_list = [trigger["value"] for trigger in json.loads(triggers[1]) if trigger["type"]=="Email"]
                    template_revenue =0.0
                    for templante_info in template_list:
                        template_revenue += data_list.get(templante_info, {}).get("revenue", 0.0)
                    trigger_tuple.append((template_revenue,datetime.datetime.now(),triggers[0]))

                # 更新email_tiggers数据
                cursor.executemany("""update email_trigger set revenue=%s, update_time=%s where id=%s""", trigger_tuple)

                # 更新dashboard数据
                cursor.execute("""select id from dashboard where store_id=%s and update_time between %s and %s""",
                               (store_id, zero_time, last_time))
                dashboard_id = cursor.fetchone()
                if dashboard_id:
                    # update
                    cursor.execute("""update dashboard set  update_time=%s, session=%s, orders=%s, revenue=%s, total_orders=%s, 
                                        total_sessions=%s, total_revenue=%s, avg_conversion_rate=%s, avg_repeat_purchase_rate=%s where id=%s""",
                                        (now_date,sessions, orders, revenue, total_orders, total_sessions, total_revenue,
                                         avg_conversion_rate, avg_repeat_purchase_rate, dashboard_id[0]))
                else:
                    # insert
                    cursor.execute("""insert into dashboard ( create_time, update_time, store_id,session, orders, revenue, 
                                      total_orders, total_sessions, total_revenue, avg_conversion_rate, avg_repeat_purchase_rate) 
                            values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                                   (now_date, now_date, store_id, sessions, orders, revenue, total_orders, total_sessions, total_revenue,
                                    avg_conversion_rate, avg_repeat_purchase_rate))

                logger.info("update store(%s) dashboard success at %s." % (store_id, now_date))
                conn.commit()
        except Exception as e:
            logger.exception("update dashboard data exception e={}".format(e))
            return False
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0
        return True

    def update_store_webhook(self, store=None):
        webhooks = [
            {'address': 'https://smartsend.seamarketings.com/api/v1/webhook/cart/update/', 'topic': 'carts/update'},
            {'address': 'https://smartsend.seamarketings.com/api/v1/webhook/order/paid/', 'topic': 'orders/paid'},
            {'address': 'https://smartsend.seamarketings.com/api/v1/webhook/customers/create/','topic': 'customers/create'},
            {'address': 'https://smartsend.seamarketings.com/api/v1/webhook/customers/update/','topic': 'customers/update'},
            {'address': 'https://smartsend.seamarketings.com/api/v1/webhook/checkouts/create/','topic': 'checkouts/create'},
            {'address': 'https://smartsend.seamarketings.com/api/v1/webhook/checkouts/update/','topic': 'checkouts/update'},
            {'address': 'https://smartsend.seamarketings.com/api/v1/webhook/checkouts/delete/','topic': 'checkouts/delete'},
        ]
        webhook_info = shopify_webhook.products_api(shop_uri=store[0][1], access_token=store[0][2])
        for webhook in webhooks:
            webhook_info.create_webhook(topic=webhook.get("topic", ""), address=webhook.get("address", ""))

    def update_new_shopify(self):
        logger.info("update_new_shopify is cheking...")
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user, password=self.db_password).get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return False

            cursor.execute(
                """select store.id, store.url, store.token, store_create_time from store left join user on store.user_id = user.id where user.is_active = 1 and store.init = 0""")
            store = cursor.fetchone()
            if not store:
                logger.info("update_new_shopify is ending... no store need update")
                return False

            update_time = datetime.datetime.now()

            cursor.execute(
                '''update `store` set init=%s,update_time=%s where id=%s''',(1, update_time, store[0]))
            conn.commit()
            logger.info("update_new_shopify begin update data store_id={}".format(store[0]))
            store = (store,)
            self.update_shopify_collections(store)
            self.update_shopify_orders(store)
            self.update_shopify_product(store)
            self.update_top_product(store)

            # 新店铺拉客户, 初始拉取一次，以后由webhook推送新顾客的创建事件
            self.update_shopify_customers(store=store)
            # TODO 同步shopify customer 和 order的数据同步
            self.update_shopify_order_customer()

            # TODO 新店铺创建模版

            # TODO 新的店铺创建webhook
            self.update_store_webhook(store)

            logger.info("update_new_shopify end init data store_id={}".format(store[0]))

        except Exception as e:
            logger.exception("update_collection e={}".format(e))
            return False
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0

    def update_shopify_customers(self, store=None):
        """
        1. 更新所有客戶的信息
        2. 获取所有店铺的所有类目，并保存至数据库
        """
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user,
                          password=self.db_password).get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return False

            if store:
                stores = store
            else:
                cursor.execute(
                    """select store.id, store.url, store.token from store left join user on store.user_id = user.id where user.is_active = 1""")
                stores = cursor.fetchall()

            for store in stores:
                customer_insert_list = []
                customer_update_list = []
                total_insert_ids = []

                store_id, store_url, store_token = store
                if not all([store_url, store_token]):
                    logger.warning("the store have not url or token, store id={}".format(store_id))
                    continue

                papi = ProductsApi(store_token, store_url)
                cursor.execute('''select uuid from `customer` where store_id=%s''', (store_id, ))
                exist_customer = cursor.fetchall()
                exist_customer_list = [item[0] for item in exist_customer]

                times = 1
                create_at_max = datetime.datetime.now() #- datetime.timedelta(days=262)
                create_at_min = create_at_max - datetime.timedelta(days=30)
                time_format = "%Y-%m-%dT%H:%M:%S"
                # store_create_time = datetime.datetime.now()-datetime.timedelta(days=400)    ##临时的
                cursor.execute("select `store_create_time` from `store` where 'id'=%s", (store_id, ))
                ret = cursor.fetchone()
                if ret and ret[0]:
                    store_create_time = ret[0]
                else:
                    store_create_time = datetime.datetime.now() - datetime.timedelta(days=1000)

                need_update_orders = []
                while times < 10000:
                    create_at_max = create_at_max.strftime(time_format) if isinstance(create_at_max, datetime.datetime) else create_at_max[0:19]
                    create_at_min = create_at_min.strftime(time_format) if isinstance(create_at_min, datetime.datetime) else create_at_min[0:19]
                    # 已经超过店铺的创建时间
                    if create_at_max < store_create_time.strftime(time_format):
                        break

                    ret = papi.get_all_customers(limit=250, created_at_min=create_at_min+"+08:00", created_at_max=create_at_max+"+08:00")
                    if ret["code"] != 1:
                        logger.warning("get shop customer failed. store_id={}, ret={}".format(store_id, ret))
                        continue
                    else:
                        customer_info = ret["data"].get("customers", [])
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

                            #将需要同步信息的Order id保存下来，　并不是每个顾客都有last order 的
                            if last_order_id:
                                need_update_orders.append((store_id, last_order_id))

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
                                if uuid not in total_insert_ids:
                                    customer_insert_list.append(customer_tuple)
                                    total_insert_ids.append(uuid)

                    cus_create_ats = [cus["created_at"] for cus in customer_info]
                    cus_create_ats = sorted(cus_create_ats)

                    if len(customer_info) >= 250:
                        old_create_at_max = create_at_max
                        new_create_at_max = datetime.datetime.strptime(cus_create_ats[0][0:19], time_format) - datetime.timedelta(seconds=1)
                        create_at_max = new_create_at_max.strftime(time_format)
                        if old_create_at_max <= create_at_max:
                            new_create_at_max = datetime.datetime.strptime(old_create_at_max,
                                                                           time_format) - datetime.timedelta(hours=1)
                            create_at_max = new_create_at_max.strftime(time_format)
                        if create_at_max <= create_at_min:
                            create_at_min = datetime.datetime.strptime(create_at_max, time_format) - datetime.timedelta(days=30)
                    else:
                        create_at_max = datetime.datetime.strptime(create_at_min, time_format) - datetime.timedelta(seconds=1)
                        create_at_min = create_at_max - datetime.timedelta(days=30)

                    # 拉一次存一次，以防止长时间后数据链接断开
                    # 每拉够一月，保存一次
                    self.save_customer_db(customer_insert_list, customer_update_list, cursor=cursor, conn=conn)
                    logger.info(
                        "save_customer_db, times={}, insert list={}, update list={}, time min={}, time max={}, ".format(
                            times, len(customer_insert_list), len(customer_update_list), create_at_min, create_at_max))
                    customer_insert_list = []
                    customer_update_list = []
                    times += 1

                # 更新customer中的last order数据
                if need_update_orders:
                    cursor.executemany(
                        """select `status`, `order_update_time`, `order_uuid`, `store_id` from `order_event` where store_id=%s and order_uuid=%s""",
                        need_update_orders)

                    ret = cursor.fetchall()
                    if ret:
                        cursor.executemany(
                            """update customer set `last_order_status`=%s, `last_order_time`=%s where last_order_id = %s and store_id=%s""",
                            ret)
                    conn.commit()
        except Exception as e:
            logger.exception("update_shopify_customers e={}".format(e))
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0
        return True

    def update_shopify_order_customer(self):
        """
        # 用户的订单表 和  用户的信息表同步
        :return:
        """
        logger.info("Synchronize customer and order data is cheking...")
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user,
                          password=self.db_password).get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return False
            cursor.execute("""select `status`, `order_update_time`, `order_uuid`, `store_id` from `order_event` """,)
            ret = cursor.fetchall()
            if ret:
                cursor.executemany(
                    """update customer set `last_order_status`=%s, `last_order_time`=%s where last_order_id = %s and store_id=%s""",
                    ret)
            conn.commit()
        except Exception as e:
            logger.exception("Synchronize customer and order data e={}".format(e))
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0
        return True


if __name__ == '__main__':
    db_info = {"host": "47.244.107.240", "port": 3306, "db": "edm", "user": "edm", "password": "edm@orderplus.com"}
    #ShopifyDataProcessor(db_info=db_info).update_shopify_collections()
    #ShopifyDataProcessor(db_info=db_info).update_shopify_product()
    # ShopifyDataProcessor(db_info=db_info).update_shopify_orders()
    # ShopifyDataProcessor(db_info=db_info).update_top_product()
    # 拉取shopify GA 数据
    ShopifyDataProcessor(db_info=db_info).updata_shopify_ga()
    # 订单表 和  用户表 之间的数据同步
    # ShopifyDataProcessor(db_info=db_info).update_shopify_order_customer()
    # ShopifyDataProcessor(db_info=db_info).update_shopify_customers()

