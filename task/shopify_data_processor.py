import datetime
import json
import pymysql
from collections import Counter
from sdk.shopify.get_shopify_data import ProductsApi
from config import logger, SHOPIFY_CONFIG
from task.db_util import DBUtil


class ShopifyDataProcessor:
    def __init__(self, db_info):
        self.db_host = db_info.get("host", "")
        self.db_port = db_info.get("port", 3306)
        self.db_name = db_info.get("db", "")
        self.db_user = db_info.get("user", "")
        self.db_password = db_info.get("password", "")

    def update_shopify_product(self):
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

                                variants = pro.get("variants", [])

                                price = 0
                                if variants:
                                    price = float(variants[0].get("price", "0"))

                                try:
                                    uuid_id = str(pro_uuid) + "_" + str(id)
                                    if uuid_id in store_product_dict[store_id].keys():
                                        pro_id = store_product_dict[store_id][uuid_id]
                                        logger.info("[update_shopify_product] product is already exist, store_id={} store_url={}, product_id={} ".format(store_id,store_url,pro_id))
                                        cursor.execute('''update `product` set name=%s, url=%s, image_url=%s,price=%s,product_category_id=%s, update_time=%s where id=%s''',
                                                       (pro_title, pro_url, pro_image,price, id, time_now, pro_id))
                                        conn.commit()
                                    else:
                                        cursor.execute(
                                            "insert into `product` (`name`, `url`, `uuid`,`price`,`image_url`,`product_category_id`, `store_id`, `create_time`, `update_time`) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
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
        logger.exception("[update_shopify_product] is finished")
        return True

    def update_shopify_collections(self):
        """
        1. 获取所有店铺的所有类目，并保存至数据库
        """
        logger.info("update_collection is cheking...")
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user, password=self.db_password).get_instance()
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

    def update_shopify_orders(self):
        """更新店铺的订单"""
        logger.info("update_collection is cheking...")
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user, password=self.db_password).get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return False

            cursor.execute(
                    """select store.id, store.url, store.token, store.order_init from store left join user on store.user_id = user.id where user.is_active = 1""")
            stores = cursor.fetchall()
            if not stores:
                return False

            for store in stores:
                store_id, store_url, store_token, store_init = store
                if store_init == 1:
                    continue

                cursor.execute(
                    """select order_uuid from order_event where store_id={}""".format(store_id))
                orders = cursor.fetchall()
                order_list = [item[0] for item in orders] if orders else []

                papi = ProductsApi(store_token, store_url)

                created_at_max = datetime.datetime.now()
                created_at_min = datetime.datetime.combine(datetime.date.today() - datetime.timedelta(days=5000), datetime.time.min)
                for i in range(0, 1000):
                    res = papi.get_all_orders(created_at_min, created_at_max)
                    if res["code"] != 1:
                        break
                    if res["code"] == 1:
                        orders = res["data"]["orders"]
                        for order in orders:
                            order_uuid = order["id"]
                            if order_uuid in order_list:
                                continue
                            if order["financial_status"] != "unpaid":
                                status = 1
                            else:
                                status = 0
                            customer_uuid = order["customer"]["id"]
                            order_create_time = order["created_at"].replace("T"," ").split("+")[0]
                            order_update_time = order["updated_at"].replace("T"," ").split("+")[0]
                            total_price = order["total_price"]
                            status_tag = order["financial_status"]
                            status_url = order["order_status_url"]
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
                                "insert into `order_event` (`order_uuid`, `status`,`status_tag`,`status_url`,`product_info`,`customer_uuid`,`total_price`,`store_id`,`order_create_time`,`order_update_time`,`create_time`, `update_time`) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                                (order_uuid, status, status_tag, status_url, product_info, customer_uuid, total_price, store_id, order_create_time, order_update_time, create_time, update_time))
                            conn.commit()
                            order_id = cursor.lastrowid
                            order_list.append(order_uuid)

                        # 拉完了
                        if len(orders) < 100:
                            cursor.execute(
                                '''update `store` set order_init=1 where id=%s''',(store_id))
                            conn.commit()
                            break
                        else:
                            created_at_max = orders[-1].get("created_at", "")

        except Exception as e:
            logger.exception("update_collection e={}".format(e))
            return False
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0
        return True

    def update_top_product(self):
        """更新tot product"""
        logger.info("update_top_product is cheking...")
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user, password=self.db_password).get_instance()
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
                    """select id,name,url,uuid,price image_url from product where store_id = %s and uuid in %s""",(store_id, top_three_product_list))
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
                cursor_dict.execute(
                    """select id,name,url,uuid, image_url from product where store_id = %s and uuid in %s""",(store_id, top_seven_product_list))
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
                    """select id,name,url,uuid, image_url from product where store_id = %s and uuid in %s""",(store_id, top_fifteen_product_list))
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
                    """select id,name,url,uuid, image_url from product where store_id = %s and uuid in %s""",(store_id, top_thirty_product_list))
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
            logger.exception("update_collection e={}".format(e))
            return False
        finally:
            cursor.close() if cursor else 0
            cursor_dict.close() if cursor else 0
            conn.close() if conn else 0
        return True


if __name__ == '__main__':
    db_info = {"host": "47.244.107.240", "port": 3306, "db": "edm", "user": "edm", "password": "edm@orderplus.com"}
    #ShopifyDataProcessor(db_info=db_info).update_shopify_collections()
    ShopifyDataProcessor(db_info=db_info).update_shopify_product()
    #ShopifyDataProcessor(db_info=db_info).update_shopify_orders()
    ShopifyDataProcessor(db_info=db_info).update_top_product()

