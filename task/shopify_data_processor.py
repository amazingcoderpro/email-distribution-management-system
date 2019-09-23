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


class ShopifyDataProcessor:
    def __init__(self, db_info, mongo_config):
        self.db_host = db_info.get("host", "")
        self.db_port = db_info.get("port", 3306)
        self.db_name = db_info.get("db", "")
        self.db_user = db_info.get("user", "")
        self.db_password = db_info.get("password", "")
        self.root_path = ROOT_PATH
        self.mongo_config = mongo_config

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
                        """select store.id, store.url, store.token, store.name from store left join user on store.user_id = user.id where user.is_active = 1 and store.id != 1 and store.source != 0""")
                stores = cursor.fetchall()
            else:
                stores = input_store

            # 组装store和collection和product数据，之后放入redis中
            for store in stores:
                product_store_uuid_dict = {}
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

                # 组装 collection
                cursor.execute("""select id, category_id from product_category where store_id=%s""", (store_id,))
                collections_list = cursor.fetchall()
                if not collections_list:
                    continue
                # 组装 product
                cursor.execute('''select id, uuid from `product` where store_id=%s''', (store_id))
                exist_products = cursor.fetchall()
                for exp in exist_products:
                    product_store_uuid_dict[str(store_id) + "_" + str(exp[1])] = exp[0]

                # 遍历数据库中的所有store, 拉产品
                for id, collection_id in collections_list:
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
                                    uuid_id = str(store_id) + "_" + str(pro_uuid)
                                    if uuid_id in product_store_uuid_dict:
                                        pro_id = product_store_uuid_dict[uuid_id]
                                        logger.info("[update_shopify_product] product is already exist store_id={} store_url={} product_id={} uuid={} product_category_id={} ".format(store_id,store_url,pro_id, pro_uuid, id))
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
                                    product_store_uuid_dict[uuid_id] = pro_id
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
                            cart_token = order["cart_token"] if order["cart_token"] else ""
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

    def get_opstores_stores(self, site_name=None):
        """
        获取所有来自opstores的店铺id及名称
        :return:
        """
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user, password=self.db_password).get_instance()
            cursor = conn.cursor(cursor=pymysql.cursors.DictCursor) if conn else None
            if not cursor:
                return None

            if site_name:
                cursor.execute("""select id, site_name, url, domain, source from store where id>1 and source=0 and site_name=%s""", (site_name, ))
            else:
                cursor.execute("""select id, site_name, url, domain, source from store where id>1 and source=0""")

            stores = cursor.fetchall()
            return stores
        except Exception as e:
            logger.exception("get_opstores_stores exception e={}".format(e))
            return None
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0

    def update_top_products_mongo(self, site_name=None):
        stores = self.get_opstores_stores(site_name=site_name)
        if not stores:
            logger.warning("There have not stores to update top products")
            return False

        logger.info("update_top_products_mongo, site_name={}".format(site_name))
        try:
            mdb = MongoDBUtil(mongo_config=MONGO_CONFIG)
            db = mdb.get_instance()
            if not db:
                logger.error("update_top_products_mongo error, connect mongo db failed.")
                return False

            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user,
                          password=self.db_password).get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                logger.error("update_top_products_mongo error, connect mysql db failed.")
                return False

            time_beg = (datetime.datetime.now()-datetime.timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S")
            for store in stores:
                recent_3days_paid_products = []
                recent_7days_paid_products = []
                recent_15days_paid_products = []
                recent_30days_paid_products = []
                store_site = store.get("site_name", "")
                if not store_site:
                    continue

                store_id = store.get("id")
                domain = store.get("domain", "")
                source = store.get("source", 0)
                # 只处理来自己opstores的店铺
                if source != 0:
                    continue

                logger.info("start parse top products from mongo, store id={}, name={}".format(store_id, store_site))
                order_collection = db["shopify_order"]
                orders = order_collection.find(
                    {"site_name": store_site, "updated_at": {"$gte": time_beg}, "financial_status": "paid"},
                    {"_id": 0, "line_items": 1, "updated_at": 1})

                top_three_time = datetime.datetime.now() - datetime.timedelta(days=3)
                top_seven_time = datetime.datetime.now() - datetime.timedelta(days=7)
                top_fifteen_time = datetime.datetime.now() - datetime.timedelta(days=15)
                top_thirty_time = datetime.datetime.now() - datetime.timedelta(days=30)

                for order in orders:
                    line_items = order.get("line_items", [])
                    order_updated_time = order.get("updated_at", "")
                    order_updated = datetime.datetime.strptime(order_updated_time[0: 19], "%Y-%m-%dT%H:%M:%S")
                    for pro in line_items:
                        if not pro.get("product_exists", False):
                            continue

                        if order_updated >= top_thirty_time:
                            recent_30days_paid_products.append(pro.get("product_id", ""))
                        if order_updated >= top_fifteen_time:
                            recent_15days_paid_products.append(pro.get("product_id", ""))
                        if order_updated >= top_seven_time:
                            recent_7days_paid_products.append(pro.get("product_id", ""))
                        if order_updated >= top_three_time:
                            recent_3days_paid_products.append(pro.get("product_id", ""))

                top6_product_ids_recent3days = [item[0] for item in Counter(recent_3days_paid_products).most_common(4)]
                top6_product_ids_recent7days = [item[0] for item in Counter(recent_7days_paid_products).most_common(4)]
                top6_product_ids_recent15days = [item[0] for item in Counter(recent_15days_paid_products).most_common(4)]
                top6_product_ids_recent30days = [item[0] for item in Counter(recent_30days_paid_products).most_common(4)]

                top6_products_3days = []
                top6_products_7days = []
                top6_products_15days = []
                top6_products_30days = []
                product_col = db["shopify_product"]
                all_top = top6_product_ids_recent3days+top6_product_ids_recent7days+top6_product_ids_recent15days+top6_product_ids_recent30days
                all_top = [int(item) for item in all_top]
                all_top = list(set(all_top))
                if all_top:
                    products = product_col.find({"id": {"$in": all_top}, "site_name": store_site},
                                                {"_id": 0, "id": 1, "title": 1, "handle": 1, "variants.price": 1,
                                                 "image.src": 1})
                    # products = product_col.find({"id": {"$in": all_top}, "site_name": store_site},
                    #                             {"id": 1, "title": 1, "handle": 1})
                    for pro in products:
                        product_info = {
                            "uuid": pro["id"],
                            "name": pro["title"],
                            "price": pro["variants"][0].get("price", 0),
                            "image_url": pro["image"].get("src", ""),
                            "url": f"https://{domain}/products/{pro['handle']}"
                        }
                        if pro["id"] in top6_product_ids_recent3days:
                            top6_products_3days.append(product_info)
                        if pro["id"] in top6_product_ids_recent7days:
                            top6_products_7days.append(product_info)
                        if pro["id"] in top6_product_ids_recent15days:
                            top6_products_15days.append(product_info)
                        if pro["id"] in top6_product_ids_recent30days:
                            top6_products_30days.append(product_info)

                current_time = datetime.datetime.now()
                cursor.execute(
                    """select id from top_product where store_id = %s """, (store_id))
                store = cursor.fetchall()
                if not store:
                    cursor.execute(
                        "insert into `top_product` (`top_three`, `top_seven`, `top_fifteen`, `top_thirty`, `store_id`, `create_time`, `update_time`) values (%s, %s, %s, %s, %s, %s, %s)",
                        (json.dumps(top6_products_3days), json.dumps(top6_products_7days), json.dumps(top6_products_15days), json.dumps(top6_products_30days), store_id, current_time, current_time))
                    conn.commit()
                else:
                    cursor.execute(
                        '''update `top_product` set `top_three`=%s, `top_seven`=%s, `top_fifteen`=%s, `top_thirty`=%s, `update_time`=%s where `store_id`=%s''',
                        (json.dumps(top6_products_3days), json.dumps(top6_products_7days), json.dumps(top6_products_15days), json.dumps(top6_products_30days), current_time, store_id))
                    conn.commit()
        except Exception as e:
            logger.exception("update_top_products_mongo e={}".format(e))
        finally:
            mdb.close()
            cursor.close() if "cursor" in locals() else 0
            conn.close() if "conn" in locals() else 0

    def update_top_product(self, store=None):
        """更新tot product"""
        logger.info("update_top_product is cheking...")
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user, password=self.db_password).get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return False
            if not store:
                cursor.execute(
                    """select store.id, store.url, store.token from store left join user on store.user_id = user.id where user.is_active = 1 and store.id != 1 and store.source = 1""")
                stores = cursor.fetchall()
                if not stores:
                    return False
            else:
                stores = store

            for store in stores:
                store_id, store_url, store_token, *_ = store
                logger.info("update_top_product is checking... store_id={}".format(store_id))
                top_three_product_list, top_seven_product_list, top_fifteen_product_list, top_thirty_product_list = [],[],[],[]
                top_three_time = datetime.datetime.combine(datetime.date.today() - datetime.timedelta(days=3),datetime.time.min)
                top_seven_time = datetime.datetime.combine(datetime.date.today() - datetime.timedelta(days=7),datetime.time.min)
                top_fifteen_time = datetime.datetime.combine(datetime.date.today() - datetime.timedelta(days=15),datetime.time.min)
                top_thirty_time = datetime.datetime.combine(datetime.date.today() - datetime.timedelta(days=30),datetime.time.min)
                cursor.execute(
                    """select id, product_info,order_update_time from order_event where store_id = %s and order_update_time >= %s and status==1""",(store_id,top_thirty_time))
                order_events = cursor.fetchall()
                if not order_events:
                    continue
                for item in order_events:
                    id, product_info, order_update_time = item
                    product_info = json.loads(product_info)
                    if not product.get("product_id", None):
                        continue

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

                top_three_product_list = [item[0] for item in Counter(top_three_product_list).most_common(4)]
                top_seven_product_list = [item[0] for item in Counter(top_seven_product_list).most_common(4)]
                top_fifteen_product_list = [item[0] for item in Counter(top_fifteen_product_list).most_common(4)]
                top_thirty_product_list = [item[0] for item in Counter(top_thirty_product_list).most_common(4)]
                current_time = datetime.datetime.now()

                # top_three
                if top_three_product_list:
                    logger.info("update_top_product is cheking... store_id={} 3_product_list={}".format(store_id,top_three_product_list))
                    cursor_dict.execute(
                        """select id,name,url,uuid,price,image_url from product where store_id = %s and uuid in %s""",(store_id, top_three_product_list))
                    top_three_product = cursor_dict.fetchall()

                    top_three_list = []
                    exit_top_three_list = []
                    for item in top_three_product:
                        if item["uuid"] not in exit_top_three_list:
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
                if top_seven_product_list:
                    logger.info("update_top_product is cheking... store_id={} 7_product_list={}".format(store_id, top_seven_product_list))
                    cursor_dict.execute(
                        """select id,name,url,uuid,price,image_url from product where store_id = %s and uuid in %s""",(store_id, top_seven_product_list))
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
                if top_fifteen_product_list:
                    logger.info("update_top_product is cheking... store_id={} 15_product_list={}".format(store_id, top_fifteen_product_list))
                    cursor_dict.execute(
                        """select id,name,url,uuid,price, image_url from product where store_id = %s and uuid in %s""",(store_id, top_fifteen_product_list))
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


                # top_thirty
                if top_thirty_product_list:
                    logger.info("update_top_product is cheking... store_id={} 30_product_list={}".format(store_id, top_thirty_product_list))
                    cursor_dict.execute(
                        """select id,name,url,uuid,price, image_url from product where store_id = %s and uuid in %s""",(store_id, top_thirty_product_list))
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
            cursor.close() if "cursor" in locals() else 0
            cursor_dict.close() if "cursor_dict" in locals() else 0
            conn.close() if "conn" in locals() else 0
        logger.info("update_top_product is finished...")
        return True

    def update_store_repeat_customers(self, store_id, source, site_name, cursor, conn):
        # 店铺来自非opstore时从mysql取数据
        orders_gte2 = 0
        total_paid_customers = 0
        try:
            mdb = MongoDBUtil(mongo_config=self.mongo_config)
            mongo_db = mdb.get_instance()

            if source == 1:
                # 获取当前店铺支付订单大于等于2的用户数
                cursor.execute(
                    """select count(customer_uuid) from (SELECT customer_uuid, count(id) as num FROM order_event where store_id= %s and status_tag='paid' group by customer_uuid) as res where num >= 2;""",
                    (store_id,))
                orders_gte2 = cursor.fetchone()[0]

                # 获取当前店铺的用户总量
                cursor.execute("""SELECT count(id)  FROM  order_event where store_id= %s;""", (store_id,))
                total_paid_customers = cursor.fetchone()[0]
            else:  # 来自opstores
                all_paid_customers = []
                all_orders_gte2 = []
                # 支付订单数大于等于2的用户总量
                paid_results = mongo_db["shopify_order"]
                group = {
                    '_id': "$customer.id",
                    'count': {'$sum': 1}
                }
                paid_customers = paid_results.aggregate(
                    [{"$match": {"site_name": site_name}}, {"$group": group}], allowDiskUse=True)

                for res in paid_customers:
                    uuid = res.get("_id", "")
                    count = res.get("count", 0)
                    if uuid:
                        all_paid_customers.append(uuid)
                        if count >= 2:
                            all_orders_gte2.append(uuid)
                orders_gte2 = len(all_orders_gte2)
                total_paid_customers = len(all_paid_customers)

            # 更新dashboard total_customer 和 repate_customers数据
            now_date = datetime.datetime.now() + datetime.timedelta(days=-1)
            zero_time = now_date - datetime.timedelta(hours=now_date.hour, minutes=now_date.minute,
                                                      seconds=now_date.second, microseconds=now_date.microsecond)
            last_time = zero_time + datetime.timedelta(hours=23, minutes=59, seconds=59)
            cursor.execute(
                """update dashboard set repeat_customers=%s, total_customers=%s where store_id=%s and store_id !=1 and create_time between %s and %s""",
                (orders_gte2, total_paid_customers, store_id, zero_time, last_time))
            conn.commit()
        except Exception as e:
            logger.exception("get_store_repeat_customers catch exception={}".format(e))
        finally:
            mdb.close()

        return orders_gte2, total_paid_customers

    def update_trigger_ga(self, store_id, cursor, conn):
        update_email_trigger_dict = {}
        update_trigger_value = []
        cursor.execute(
            """select email_trigger_id, revenue, sessions, transcations from email_template where store_id= %s""", (store_id,))
        email_trigger_list = cursor.fetchall()

        for tg_id, rev, tg_sess, tg_order in email_trigger_list:
            if tg_id in update_email_trigger_dict.keys():
                update_email_trigger_dict[tg_id][0] += rev
                update_email_trigger_dict[tg_id][1] += tg_sess
                update_email_trigger_dict[tg_id][2] += tg_order
            else:
                update_email_trigger_dict[tg_id] = [rev, tg_sess, tg_order]
        for trigger_id, list_email_trigger in update_email_trigger_dict.items():
            # trigger 转化率
            conversion_rate = round(list_email_trigger[2] / list_email_trigger[1], 4) if list_email_trigger[1] else 0
            res = (round(float(list_email_trigger[0]), 4), list_email_trigger[1], list_email_trigger[2], conversion_rate, trigger_id)
            update_trigger_value.append(res)

        # 更新email_tiggers数据
        cursor.executemany("""update email_trigger set revenue=revenue+%s, sessions=sessions+%s, transcations=transcations+%s, conversion_rate=%s where id=%s""", update_trigger_value)
        logger.info("update_trigger_ga is successful store_id={},".format(store_id))
        conn.commit()

    def update_dashboard_ga(self, store_id, shopify_total_results, now_date, zero_time, last_time, orders_gte2, total_paid_customers, cursor, conn):
        # 获取当前店铺Dashboard所有旧的GA数据,用于累加出最新的总数据,以用于更新dashboard表
        cursor.execute(
            """select total_orders, total_revenue, total_sessions from dashboard where store_id= %s and create_time between %s and %s""",
            (store_id, zero_time + datetime.timedelta(days=-1), last_time + datetime.timedelta(days=-1)))
        orders_info = cursor.fetchone()
        total_orders = total_revenue = total_sessions = 0
        if orders_info:
            total_orders, total_revenue, total_sessions = orders_info
            total_orders = 0 if not total_orders else total_orders
            total_revenue = 0.0 if not total_revenue else total_revenue
            total_sessions = 0 if not total_sessions else total_sessions

        sessions = shopify_total_results.get("sessions", 0)
        orders = shopify_total_results.get("transactions", 0)
        revenue = shopify_total_results.get("revenue", 0.0)
        total_orders += orders
        total_sessions += sessions
        total_revenue += revenue

        # 平均转换率  总支付订单数÷总流量
        avg_conversion_rate = round(total_orders / total_sessions, 6) if total_sessions else 0
        # 重复的购买率 支付订单数≥2的用户数据÷总用户数量
        avg_repeat_purchase_rate = round(orders_gte2 / total_paid_customers, 6) if total_paid_customers else 0

        # 更新dashboard数据, dashboard数据直接取自ga,不用从其他表收集
        cursor.execute("""select id from dashboard where store_id=%s and create_time between %s and %s""",
                       (store_id, zero_time, last_time))
        dashboard_id = cursor.fetchone()
        if dashboard_id:
            # update
            cursor.execute("""update dashboard set  update_time=%s, session=%s, orders=%s, revenue=%s, total_orders=%s,
                                    total_sessions=%s, total_revenue=%s, avg_conversion_rate=%s, avg_repeat_purchase_rate=%s where id=%s""",
                           (datetime.datetime.now(), sessions, orders, revenue, total_orders, total_sessions,
                            total_revenue, avg_conversion_rate, avg_repeat_purchase_rate, dashboard_id[0]))
        else:
            # insert
            cursor.execute("""insert into dashboard (create_time, update_time, store_id, session, orders, revenue,
                                  total_orders, total_sessions, total_revenue, avg_conversion_rate, avg_repeat_purchase_rate)
                            values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                           (now_date, datetime.datetime.now(), store_id, sessions, orders, revenue, total_orders,
                            total_sessions, total_revenue,avg_conversion_rate, avg_repeat_purchase_rate))

        logger.info(
            "update store {} dashboard data in [{}] successful. revenue={}, total_revenue={},total_orders={},total_sessions={}, avg_conversion_rate={}, avg_repeat_purchase_rate={} "
            .format(store_id, now_date.strftime("%Y-%m-%d"), revenue, total_revenue, total_orders, total_sessions,
                    avg_conversion_rate, avg_repeat_purchase_rate))
        conn.commit()

    def updata_shopify_ga(self, store_id=None):
        logger.info("update_shopify GA is cheking...")
        """
        每天凌晨十分拉取GA数据
        :return:
        """
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user,
                          password=self.db_password).get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return False

            # 获取所有店铺
            if store_id:
                cursor.execute("""select id, store_view_id, source, site_name from store where id = %s""", (store_id, ))
            else:
                cursor.execute("""select id, store_view_id, source, site_name from store where id != 1""")
            stores = cursor.fetchall()

            # 遍历所有店铺
            for store in stores:
                store_id, store_view_id, source, site_name = store
                # 配置时间
                results_list = []
                now_date = datetime.datetime.now()+datetime.timedelta(days=-1)
                zero_time = now_date - datetime.timedelta(hours=now_date.hour, minutes=now_date.minute,
                                                          seconds=now_date.second, microseconds=now_date.microsecond)
                last_time = zero_time + datetime.timedelta(hours=23, minutes=59, seconds=59)

                # 更新店铺用户及重复购买信息
                orders_gte2, total_paid_customers = self.update_store_repeat_customers(store_id, source, site_name, cursor, conn)

                if not store_view_id:
                    logger.warning("updata_shopify_ga store_view_id does not exist， store_id={}".format(store_id))
                    continue

                g_api = GoogleApi(view_id=store_view_id,
                                 json_path=os.path.join(self.root_path, r"sdk//googleanalytics//client_secrets.json"))
                ga_results = g_api.get_report(key_word="", start_time="1daysAgo", end_time="today")
                # data_list = {}
                if ga_results["code"] != 1:
                    logger.error("updata_shopify_ga msg is error. msg={},store_id={}, view_id={}".format(ga_results["msg"], store_id, store_view_id))
                    continue

                shopify_data = ga_results.get("data", {})
                data_list = shopify_data.get("results", {})
                logger.info("updata_shopify_ga msg is success. store_id={}, view_id={}".format(store_id, store_view_id))
                for values in data_list.items():
                    res = (values[1].get("sessions", ""), values[1].get("transactions", ""), values[1].get("revenue", ""), datetime.datetime.now(), values[0])
                    results_list.append(res)

                # 更新email_template的数据
                cursor.executemany(
                    """update email_template set sessions=sessions+%s, transcations=transcations+%s, revenue=revenue+%s ,update_time=%s where id =%s""",
                    results_list)
                conn.commit()

                # 更新email_trigger的数据
                self.update_trigger_ga(store_id, cursor, conn)

                # 更新dashboard数据
                self.update_dashboard_ga(store_id, shopify_data.get("total_results", {}), now_date, zero_time, last_time,
                                         orders_gte2, total_paid_customers, cursor, conn)

        except Exception as e:
            logger.exception("update dashboard data exception e={}".format(e))
            return False
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0
        return True

    def update_template_trigger(self):
        """
        更新trigger和templant表中emali_trigger_id 同步 临时代码
        :return:
        """
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user,
                          password=self.db_password).get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return False
            # 获取所有店铺
            cursor.execute(
                """select id, store_view_id, source, site_name from store where id > 0""")
            stores = cursor.fetchall()
            triggers_list = []
            for store in stores:
                store_id = store[0]
                cursor.execute("""select id, email_delay from email_trigger where store_id=%s""", (store_id,))
                trigger_info = cursor.fetchall()
                for triggers in trigger_info:
                    try:
                        template_list = [trigger["value"] for trigger in json.loads(triggers[1]) if
                                         trigger["type"] == "Email"]
                    except:
                        print(triggers[0], triggers[1])

                    for id in template_list:
                        res = (id, triggers[0])
                        triggers_list.append(res)
                print(template_list)
            cursor.executemany(
                """update email_template set email_trigger_id=%s where id =%s""",
                triggers_list)
            conn.commit()
        except Exception as e:
            logger.exception("update dashboard data exception e={}".format(e))
            return False
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0
            return True

    def update_store_webhook(self, store=None):
        store_id, store_url, store_token, store_create_time, *_ = store[0]
        logger.info("update_store_webhook is checking... store_id={}".format(store_id))
        webhooks = [
            {'address': 'https://smartsend.seamarketings.com/api/v1/webhook/cart/update/', 'topic': 'carts/update'},
            {'address': 'https://smartsend.seamarketings.com/api/v1/webhook/order/paid/', 'topic': 'orders/paid'},
            {'address': 'https://smartsend.seamarketings.com/api/v1/webhook/customers/create/','topic': 'customers/create'},
            {'address': 'https://smartsend.seamarketings.com/api/v1/webhook/customers/update/','topic': 'customers/update'},
            {'address': 'https://smartsend.seamarketings.com/api/v1/webhook/checkouts/create/','topic': 'checkouts/create'},
            {'address': 'https://smartsend.seamarketings.com/api/v1/webhook/checkouts/update/','topic': 'checkouts/update'},
            {'address': 'https://smartsend.seamarketings.com/api/v1/webhook/checkouts/delete/','topic': 'checkouts/delete'},
        ]
        webhook_info = shopify_webhook.ProductsApi(shop_uri=store_url, access_token=store_token)
        for webhook in webhooks:
            logger.info("update_store_webhook store_id={}, webhook_topic={}".format(store_id, webhook["topic"]))
            webhook_result = webhook_info.create_webhook(topic=webhook.get("topic", ""), address=webhook.get("address", ""))
            if webhook_result["code"] == 2:
                logger.error("update_store_webhook auth failed store_id={}, error_manage={}".format(store_id, webhook_result["msg"]))

    def create_template(self, store=None):
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user,
                          password=self.db_password).get_instance()
            cursor_dict = conn.cursor(cursor=pymysql.cursors.DictCursor) if conn else None
            if not cursor_dict:
                return False
            store_id, *_ = store[0]
            logger.info("create_template is beginning...store_id={}".format(store_id))

            create_time = datetime.datetime.now()
            update_time = datetime.datetime.now()

            template_record = {}
            cursor_dict.execute(
                """select id, title, description, relation_info from customer_group where store_id = 1 and state != 2""")
            customer_group = cursor_dict.fetchall()

            for item in customer_group:
                cursor_dict.execute(
                    "insert into `customer_group` (`title`, `description`,`relation_info`, `open_rate`, `click_rate`, `members`, `state`, `store_id`, `create_time`, `update_time`) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (item["title"],item["description"],item["relation_info"],0,0,0,0,store_id,create_time,update_time))
                conn.commit()
                template_record[item["id"]] = cursor_dict.lastrowid

            email_template_record = {}
            cursor_dict.execute(
                """select id, title, description, subject, heading_text, headline, body_text, customer_group_list, send_rule, send_type, html, logo, banner, is_cart, product_title from email_template where store_id = 1 and status != 2""")
            email_template = cursor_dict.fetchall()

            for item in email_template:
                customer_group_list = eval(item["customer_group_list"])
                for key, val in enumerate(customer_group_list):
                    customer_group_list[key] = template_record[val]

                cursor_dict.execute(
                    "insert into `email_template` (`title`, `description`, `subject`, `heading_text`, `customer_group_list`, `headline`, `body_text`, `send_rule`, `html`, `send_type`, `status`,`enable`,`revenue`,`sessions`,`transcations`, `logo`, `banner`, `is_cart`, `product_title`, `store_id`, `create_time`, `update_time`) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (item["title"],item["description"],item["subject"],item["heading_text"],str(customer_group_list),item["headline"],item["body_text"],item["send_rule"],item["html"],item["send_type"],0,0,0,0,0,item["logo"],item["banner"],item["is_cart"],item["product_title"], store_id,create_time,update_time))
                conn.commit()
                email_template_record[item["id"]] = cursor_dict.lastrowid

            cursor_dict.execute(
                """select title, description, relation_info, email_delay, note, is_open, status from email_trigger where store_id = 1 and draft = 0 and status != 2""")
            email_trigger = cursor_dict.fetchall()

            for item in email_trigger:
                email_delay = json.loads(item["email_delay"])
                for key, val in enumerate(email_delay):
                    if val["type"] == "Email":
                        val["value"] = email_template_record[val["value"]]

                cursor_dict.execute(
                    "insert into `email_trigger` (`title`, `description`, `open_rate`, `click_rate`, `revenue`, `relation_info`, `email_delay`, `note`, `status`, `store_id`, `is_open`,`draft`,`create_time`, `update_time`) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (item["title"],item["description"],0,0,0,item["relation_info"],str(email_delay),item["note"],item["status"],store_id,item["is_open"],0, create_time,update_time))
                conn.commit()

        except Exception as e:
            logger.exception("create_template e={}".format(e))
            return False
        finally:
            cursor_dict.close() if cursor_dict else 0
            conn.close() if conn else 0

        logger.info("create_template is finished...")
        return True

    def update_new_shopify(self):
        logger.info("update_new_shopify is cheking...")
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user, password=self.db_password).get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return False

            cursor.execute(
                """select store.id, store.url, store.token, store_create_time, store.source, store.domain, store.name, store.site_name from store left join user on store.user_id = user.id where user.is_active = 1 and store.init = 0 and store.id>1""")
            uninit_stores = cursor.fetchall()
            if not uninit_stores:
                logger.info("update_new_shopify is ending...")
                return False
            stores = []
            ids = []
            for store in uninit_stores:
                id, url, token, create_time, source, domain, name, site_name = store
                ids.append(id)
                stores.append(store)

            cursor.execute(
                '''update `store` set init=%s,update_time=%s where id in %s''',(1, datetime.datetime.now(), ids))
            conn.commit()

            for store in stores:
                # update_time = datetime.datetime.now()
                store_id = store[0]
                logger.info("update_new_shopify begin update data store_id={}".format(store_id))
                store = (store,)
                if store[0][4] == 1:
                    self.create_template(store)
                    self.update_shopify_collections(store)
                    self.update_shopify_orders(store)
                    self.update_shopify_product(store)
                    self.update_top_product(store)

                    # 新店铺拉客户, 初始拉取一次，以后由webhook推送新顾客的创建事件
                    self.update_shopify_customers(store=store)
                    self.update_shopify_order_customer(store)
                    self.update_store_webhook(store)

                    logger.info("update_new_shopify end init data store_id={}".format(store[0]))
                else:
                    # 对来自opstores的新入店铺，拉取top　products
                    logger.info("update_new_shopify store from opstores, store={}".format(store[0]))
                    site_name = self.sync_shop_info_from_mongo(store)
                    if site_name:
                        self.update_top_products_mongo(site_name)
                    else:
                        cursor.execute(
                            '''update `store` set init=%s,update_time=%s where id=%s''',
                            (0, datetime.datetime.now(), store_id))
                        conn.commit()

        except Exception as e:
            logger.exception("update_collection e={}".format(e))
            return False
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0

    def sync_shop_info_from_mongo(self, store):
        if not store:
            return None

        store_id, shopify_domain, *_ = store[0]
        if not shopify_domain:
            return None

        logger.info("sync_shop_info_from_mongo shopify_domain={}".format(shopify_domain))
        try:
            mdb = MongoDBUtil(mongo_config=MONGO_CONFIG)
            db = mdb.get_instance()
            if not db:
                logger.error("update_top_products_mongo error, connect mongo db failed.")
                return None



            shop_collection = db["shopify_shop_info"]
            shop = shop_collection.find_one({"myshopify_domain": shopify_domain},
                                           {"_id": 0, "site_name": 1, "email": 1, "domain": 1, "name": 1,
                                            "money_in_emails_format": 1, "timezone": 1, "customer_email": 1, "created_at": 1})
            if not shop:
                logger.warning("Not find shop information in mongo db. shopify_domain={}".format(shopify_domain))
                return None

            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user,
                          password=self.db_password).get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                logger.error("cannot connect MySQL.")
                return None

            site_name = shop.get("site_name", "")
            name = shop.get("name", "")
            domain = shop.get("domain", "")
            sender = name
            sender_address = "noreply@letter.{}.com".format(name.lower())
            email = shop.get("email", "")
            service_email = shop.get("customer_email", "service@{}.com".format(name.lower()))
            if not service_email:
                service_email = "service@{}.com".format(name.lower())
            currency = shop.get("money_in_emails_format", "$").split("{{")[0][-2:]
            timezone = shop.get("timezone", "(GMT+08:00) Asia/Shanghai")
            create_time_str = shop.get("created_at", "")
            create_time = datetime.datetime.strptime(create_time_str[0:19], "%Y-%m-%dT%H:%M:%S")
            cursor.execute(
                "update `store` set name=%s, domain=%s, email=%s, timezone=%s, sender=%s, sender_address=%s, "
                "service_email=%s, currency=%s, site_name=%s, update_time=%s, store_create_time=%s where id=%s",
                (name, domain, email,
                 timezone, sender, sender_address,
                 service_email, currency, site_name,
                 datetime.datetime.now(),
                 create_time, store_id))

            conn.commit()
            return site_name
        except Exception as e:
            logger.exception("sync_shop_info_from_mongo e={}".format(e))
            return None
        finally:
            mdb.close()
            cursor.close() if 'cursor' in locals().keys() else 0
            conn.close() if 'conn' in locals().keys() else 0

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
                    """select store.id, store.url, store.token, store_create_time from store left join user on store.user_id = user.id where user.is_active = 1""")
                stores = cursor.fetchall()

            logger.info("update_shopify_customers checking... sotres={}".format(stores))
            for store in stores:
                customer_insert_list = []
                customer_update_list = []
                total_insert_ids = []

                store_id, store_url, store_token, store_create_time, *_ = store
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

                logger.info("start get store customers, store id={}, store create time={}".format(store_id, store_create_time))
                need_update_orders = []
                while times < 10000:
                    create_at_max = create_at_max.strftime(time_format) if isinstance(create_at_max, datetime.datetime) else create_at_max[0:19]
                    create_at_min = create_at_min.strftime(time_format) if isinstance(create_at_min, datetime.datetime) else create_at_min[0:19]
                    # 已经超过店铺的创建时间
                    if create_at_max < store_create_time.strftime(time_format):
                        logger.warning("customer create time max({}) < store create time({}), break.".format(create_at_max, store_create_time))
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

                            # 将需要同步信息的Order id保存下来，　并不是每个顾客都有last order 的
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

    def update_shopify_order_customer(self, store):
        """
        # 用户的订单表 和  用户的信息表同步
        :return:
        """
        store_id, *_ = store[0]
        logger.info("update_shopify_order_customer is cheking... store_id={}".format(store_id))
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user,
                          password=self.db_password).get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return False
            cursor.execute("""select `status`, `order_update_time`, `order_uuid` from `order_event` where store_id=%s""",(store_id,))
            ret = cursor.fetchall()
            if ret:
                logger.info("update_shopify_order_customer store_id={}".format(store_id,))
                cursor.executemany(
                    """update customer set `last_order_status`=%s, `last_order_time`=%s where last_order_id = %s""",
                    ret)
            conn.commit()
        except Exception as e:
            logger.exception("update_shopify_order_customer store_id={},e={}".format(store_id, e))
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0
        logger.info("update_shopify_order_customer is ending... store_id={}".format(store_id))
        return True

    def update_admin_dashboard(self):
        logger.info("update_admin_dashboard is cheking...")
        """
        统计dashboard所有的统计数据 
        :return:
        """
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user,
                          password=self.db_password).get_instance()
            cursor = conn.cursor(cursor=pymysql.cursors.DictCursor) if conn else None
            if not cursor:
                return False
            now_date = datetime.datetime.now() + datetime.timedelta(days=-1)
            zero_time = now_date - datetime.timedelta(hours=now_date.hour, minutes=now_date.minute,
                                                      seconds=now_date.second, microseconds=now_date.microsecond)
            last_time = zero_time + datetime.timedelta(hours=23, minutes=59, seconds=59)

            # 更新dashboard数据
            cursor.execute("""select `revenue`, `total_revenue`,`orders`,`total_orders`, `session`, `total_sessions`,`total_sent`, 
                                `total_open`, `total_click`, `total_unsubscribe`, `repeat_customers`, `total_customers`, `clicks`,
                                 `opens`, `sents`, `store_id` from dashboard where create_time between %s and %s and store_id !=1""",
                           (zero_time, last_time))
            total_dashboard = cursor.fetchall()
            dashboard_revenue = 0.0
            dashboard_total_revenue = 0.0
            dashboard_order = 0
            dashboard_session = 0
            dashboard_total_sessions = 0
            dashboard_total_orders = 0
            dashboard_total_sent = 0
            dashboard_total_open = 0
            dashboard_total_click = 0
            dashboard_total_unsubscribe = 0
            dashboard_total_customers = 0
            dashboard_repeat_customers = 0
            dashboard_clicks = 0
            dashboard_opens = 0
            dashboard_sents = 0
            today_max_revenue = 0
            today_max_revenue_store_id = 0
            today_max_orders = 0
            max_revenue = 0
            max_revenue_store_id = 0
            max_orders = 0

            for dashboard in total_dashboard:
                revenue = dashboard.get("revenue", 0.0)
                orders = dashboard.get("orders", 0)
                total_orders = dashboard.get("total_orders", 0)

                if revenue > max_revenue and revenue>0:
                    today_max_revenue = revenue
                    today_max_revenue_store_id = dashboard.get("store_id", 0)
                    today_max_orders = orders

                total_revenue = dashboard.get("total_revenue", 0.0)
                if total_revenue>0 and total_revenue>max_revenue:
                    max_revenue = total_revenue
                    max_revenue_store_id = dashboard.get("store_id", 0)
                    max_orders = total_orders

                session = dashboard.get("session", 0)
                total_sessions = dashboard.get("total_sessions", 0)
                total_sent = dashboard.get("total_sent", 0)
                total_sent = 0 if not total_sent else total_sent
                total_open = dashboard.get("total_open", 0)
                total_open = 0 if not total_open else total_open
                total_click = dashboard.get("total_click", 0)
                total_click = 0 if not total_click else total_click
                total_unsubscribe = dashboard.get("total_unsubscribe", 0)
                total_unsubscribe = 0 if not total_unsubscribe else total_unsubscribe
                repeat_customers = dashboard.get("repeat_customers", 0)
                total_customers = dashboard.get("total_customers", 0)
                clicks = dashboard.get("clicks", 0)
                clicks = 0 if not clicks else clicks
                opens = dashboard.get("opens", 0)
                opens = 0 if not opens else opens
                sents = dashboard.get("sents", 0)
                sents = 0 if not sents else sents
                dashboard_revenue += revenue
                dashboard_total_revenue += total_revenue
                dashboard_order += orders
                dashboard_session += session
                dashboard_total_sessions += total_sessions
                dashboard_total_orders += total_orders
                dashboard_total_sent += total_sent
                dashboard_total_open += total_open
                dashboard_total_click += total_click
                dashboard_total_unsubscribe += total_unsubscribe
                dashboard_total_customers += total_customers
                dashboard_repeat_customers += repeat_customers
                dashboard_clicks += clicks
                dashboard_sents += sents
                dashboard_opens += opens

            # 平均转换率  总支付订单数÷总流量
            avg_conversion_rate = round(dashboard_total_orders / dashboard_total_sessions, 6) if dashboard_total_sessions else 0
            # 重复的购买率 支付订单数≥2的用户数据÷总用户数量
            avg_repeat_purchase_rate = round(dashboard_repeat_customers / dashboard_total_customers, 6) if dashboard_total_customers else 0
            avg_open_rate = round(dashboard_total_open / dashboard_total_sent, 4) if dashboard_total_open and dashboard_total_sent else 0
            avg_click_rate = round(dashboard_total_click / dashboard_total_sent, 4) if dashboard_total_click and dashboard_total_sent else 0
            avg_unsubscribe_rate = round(dashboard_total_unsubscribe / dashboard_total_sent, 4) if dashboard_total_unsubscribe and dashboard_total_sent else 0

            cursor.execute("""select `store_id` from dashboard where create_time between %s and %s and store_id =1""",
                           (zero_time, last_time))
            store_id = cursor.fetchone()
            if store_id:
                cursor.execute("""update dashboard set update_time=%s, revenue=%s, total_revenue=%s, orders=%s, total_orders=%s, session=%s,
                                                       total_sessions=%s, total_sent=%s, total_open=%s, total_click=%s,
                                                       total_unsubscribe=%s, avg_conversion_rate=%s, avg_open_rate=%s,
                                                       avg_click_rate=%s, avg_unsubscribe_rate=%s, avg_repeat_purchase_rate=%s, repeat_customers=%s,
                                                       total_customers=%s, clicks=%s, sents=%s, opens=%s
                                                       where create_time between %s and %s and store_id =1""",
                               (datetime.datetime.now(), dashboard_revenue, dashboard_total_revenue, dashboard_order, dashboard_total_orders,
                                dashboard_session, dashboard_total_sessions, dashboard_total_sent, dashboard_total_open, dashboard_total_click,
                                dashboard_total_unsubscribe, avg_conversion_rate, avg_open_rate, avg_click_rate,
                                avg_unsubscribe_rate, avg_repeat_purchase_rate, dashboard_repeat_customers, dashboard_total_customers,
                                dashboard_clicks, dashboard_sents, dashboard_opens, zero_time, last_time))
            else:
                cursor.execute(
                    """insert into `dashboard` (`update_time`, `revenue`, `total_revenue`, `orders`, `total_orders`, `session`, `total_sessions`, `total_sent`, `total_open`,
                     `total_click`, `total_unsubscribe`, `avg_conversion_rate`, `avg_open_rate`, `avg_click_rate`, `avg_unsubscribe_rate`, `avg_repeat_purchase_rate`, `repeat_customers`,
                     `total_customers`, `create_time`, `clicks`, `sents`, `opens`, `store_id`)
                      values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                      (datetime.datetime.now(), dashboard_revenue, dashboard_total_revenue, dashboard_order, dashboard_total_orders,
                       dashboard_session, dashboard_total_sessions, dashboard_total_sent, dashboard_total_open,
                       dashboard_total_click, dashboard_total_unsubscribe, avg_conversion_rate, avg_open_rate, avg_click_rate,
                       avg_unsubscribe_rate, avg_repeat_purchase_rate, dashboard_repeat_customers, dashboard_total_customers,now_date,
                       dashboard_clicks, dashboard_sents, dashboard_opens, 1))
            conn.commit()

            max_revenue_store = today_max_revenue_store = ""
            if max_revenue_store_id > 0:
                cursor.execute("select `domain`, `currency` from store where id=%s", (max_revenue_store_id, ))
                res = cursor.fetchone()
                if res:
                    max_revenue_store = res.get('domain', '')
                    max_store_currency = res.get('currency', '')

            if today_max_revenue_store_id>0:
                cursor.execute("select `domain`, `currency` from store where id=%s", (today_max_revenue_store_id, ))
                res = cursor.fetchone()
                if res:
                    today_max_revenue_store = res.get('domain', '')
                    today_max_store_currency = res.get('currency', '')

            cursor.execute("select `id` from store where id!=1")
            all_store = cursor.fetchall()

            # 更新admin eamil_trigger的数据
            cursor.execute("SELECT id from email_trigger where store_id=1 and `status`=1 AND draft=0")
            admin_trigger_ids = cursor.fetchall()
            for trigger_id in admin_trigger_ids:
                email_trigger_id = trigger_id.get("id", "")
                total_revenue = 0.0
                trigger_total_sents = 0
                total_sessions = 0
                total_transcations = 0
                cursor.execute("SELECT revenue, total_sents, sessions, transcations from email_trigger where store_id!=1 and email_trigger_id=%s", (email_trigger_id,))
                trigger_value = cursor.fetchall()
                for trigger_num in trigger_value:
                    revenue = trigger_num.get("revenue", "")
                    total_sents = trigger_num.get("total_sents", "")
                    sessions = trigger_num.get("sessions", "")
                    transcations = trigger_num.get("transcations", "")
                    total_revenue += round(float(revenue), 4)
                    trigger_total_sents += total_sents
                    total_sessions += sessions
                    total_transcations += transcations
                conversion_rate = round(total_transcations / total_sessions, 4) if total_sessions else 0
                cursor.execute("""update email_trigger set revenue=%s, total_sents=%s, sessions=%s, transcations=%s, conversion_rate=%s where id=%s""",
                                  (total_revenue, trigger_total_sents, total_sessions, total_transcations, conversion_rate, email_trigger_id))
                logger.info("update email_trigger admin date is successful, id={}".format(email_trigger_id))
                conn.commit()

            webhook = 'https://oapi.dingtalk.com/robot/send?access_token=28aaa98ec46c76bed2bbb114f1a3713280dbbf1c652bdb36b11aa680013d58d4'
            xiaoding = DingtalkChatbot(webhook)
            text = f'各位大佬, SmartSend每日收益快报为您呈现:\n当前用户数: {len(all_store)}\n促成总订单数: {dashboard_total_orders}\n系统累计收益: {round(dashboard_total_revenue, 2)}$ \n平均转化率: {round(avg_conversion_rate*100, 2)}%\n平均复购率: {round(avg_repeat_purchase_rate*100, 2)}%\n累计发送邮件量: {dashboard_total_sent}\n平均点击率: {round(avg_click_rate*100, 2)}%\n平均打开率: {round(avg_open_rate*100, 2)}%\n邮件退订率: {round(avg_unsubscribe_rate*100, 2)}%\n'
            if today_max_revenue_store:
                text += f"昨日收益最佳店铺：{today_max_revenue_store}, 昨日订单数:{today_max_orders}, 收益金额:{round(today_max_revenue, 2)}{today_max_store_currency}\n"
            if max_revenue_store:
                text += f"累计收益最佳店铺：{max_revenue_store}, 累计订单数:{max_orders}, 收益金额:{round(max_revenue, 2)}{max_store_currency}\n"
            xiaoding.send_text(msg=text, is_at_all=True)

            logger.info("update_admin_dashboard update is successful")
        except Exception as e:
            logger.exception("update update_admin_dashboard data exception e={}".format(e))
            return False
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0
        return True


if __name__ == '__main__':
    # db_info = {"host": "47.244.107.240", "port": 3306, "db": "edm", "user": "edm", "password": "edm@orderplus.com"}
    # ShopifyDataProcessor(db_info=db_info).update_shopify_collections()
    # ShopifyDataProcessor(db_info=db_info).create_template()
    # ShopifyDataProcessor(db_info=db_info).update_shopify_orders()
    # ShopifyDataProcessor(db_info=db_info).update_top_products_mongo()
    # 拉取shopify GA 数据
    ShopifyDataProcessor(db_info=MYSQL_CONFIG, mongo_config=MONGO_CONFIG).updata_shopify_ga()
    # 统计admin的数据
    ShopifyDataProcessor(db_info=MYSQL_CONFIG, mongo_config=MONGO_CONFIG).update_admin_dashboard()
    # 订单表 和  用户表 之间的数据同步
    # ShopifyDataProcessor(db_info=db_info).update_shopify_order_customer()
    # ShopifyDataProcessor(db_info=db_info).update_shopify_customers()
    # ShopifyDataProcessor(db_info=db_info).update_shopify_order_customer((4,1))
    # ShopifyDataProcessor(db_info=db_info).update_store_webhook((4,"tiptopfree.myshopify.com","84ae42dd2bda781f84d8fd1d199dba88", "iii"))
    # ShopifyDataProcessor(db_info=db_info).update_shopify_customers()
    # ShopifyDataProcessor(db_info=db_info).update_new_shopify()
    # ShopifyDataProcessor(db_info=db_info).update_shopify_orders()
    # ShopifyDataProcessor(db_info=MYSQL_CONFIG, mongo_config=MONGO_CONFIG).update_template_trigger()
    # ShopifyDataProcessor(db_info=MYSQL_CONFIG, mongo_config=MONGO_CONFIG).update_trigger_ga()

