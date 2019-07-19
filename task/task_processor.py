from apscheduler.schedulers.background import BackgroundScheduler
import datetime
import threading
import time
import pymysql
import os
from dateutil.relativedelta import relativedelta
from sdk.shopify.get_shopify_data import ProductsApi
from config import logger, SHOPIFY_CONFIG

# MYSQL_PASSWD = os.getenv('MYSQL_PASSWD', None)
# MYSQL_HOST = os.getenv('MYSQL_HOST', None)


# MYSQL_HOST=47.244.107.240 MYSQL_PASSWD=   use=edm db=edm
MYSQL_HOST = "47.244.107.240"
MYSQL_PASSWD = "edm@orderplus.com"

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


def order_filter(store_id, status, relation, value, min_time=None, max_time=None):
    """
    筛选满足订单条件的客户id
    :param store_id: 店铺id
    :param status: 订单状态0－未支付，　１－支付　
    :param relation: 订单条件关系，　大于，小于，等于
    :param value: 订单条件值
    :param min_time: 时间筛选范围起点
    :param max_time: 时间筛选范围终点
    :return: list 满足条件的客户列表
    """
    customers = []
    try:
        conn = DBUtil().get_instance()
        cursor = conn.cursor() if conn else None
        if not cursor:
            return customers

        # between date
        if min_time and max_time:
            cursor.execute(
                """select `customer_uuid`, count(1) from `order_event` where store_id=%s and status=%s 
                and `order_update_time`>=%s and `order_update_time`<=%s group by `customer_uuid`""", (store_id, status, min_time, max_time))
        # after, in the past
        elif min_time:
            cursor.execute(
                """select `customer_uuid`, count from `order_event` where store_id=%s and status=%s 
                and `order_update_time`>=%s group by `customer_uuid`""", (store_id, status, min_time))
        # before
        elif max_time:
            cursor.execute(
                """select `customer_uuid`, count from `order_event` where store_id=%s and status=%s 
                and `order_update_time`<=%s group by `customer_uuid`""", (store_id, status, max_time))
        # over all time
        else:
            cursor.execute(
                """select `customer_uuid`, count from `edm.order_event` where store_id=%s and status=%s 
                group by `customer_uuid`""", (store_id, status))

        res = cursor.fetchall()
        relation_dict = {"equals": "==", "more than": ">", "less than": "<"}

        for uuid, count in res:
            just_str = "{} {} {}".format(count, relation_dict.get(relation), value)
            if eval(just_str):
                customers.append(uuid)
    except Exception as e:
        logger.exception("order_filter e={}".format(e))
        return customers
    finally:
        cursor.close() if cursor else 0
        conn.close() if conn else 0
    return customers

def adapt_sign_up_time():
    pass

def adapt_last_order_created_time():
    pass

def adapt_last_opened_email_time():
    pass

def adapt_last_click_email_time():
    pass


condition_dict = {"Customer sign up time": adapt_sign_up_time,
                  "Customer last order created time": adapt_last_order_created_time,
                  "Customer last opened email time": 1,
                  "Customer last click email time": 1}
def date_relation_convert(relation, values, unit="days"):
    def unit_convert(unit_, value):
        if unit_ in ["days", 'weeks']:
            str_delta = "datetime.timedelta({}={})".format(unit_, value)
        else:
            str_delta = "relativedelta({}={})".format(unit_, value)

        return eval(str_delta)

    min_time = None
    max_time = None
    time_now = datetime.datetime.now()
    if relation.lower() in "is in the past":
        min_time = time_now - unit_convert(unit_=unit, value=values[0])
    elif relation.lower() in "is before":
        max_time = datetime.datetime.strptime(values[0], "%Y-%m-%d %H:%M:%S")
    elif relation.lower() in "is after":
        min_time = datetime.datetime.strptime(values[0], "%Y-%m-%d %H:%M:%S")
    elif relation.lower() == "is between date" or relation.lower() == "between date":
        min_time = datetime.datetime.strptime(values[0], "%Y-%m-%d %H:%M:%S")
        max_time = datetime.datetime.strptime(values[1], "%Y-%m-%d %H:%M:%S")
    elif relation.lower() == "is between" or relation.lower() == "between":
        max_time = time_now - unit_convert(unit_=unit, value=values[0])
        min_time = time_now - unit_convert(unit_=unit, value=values[1])
    else:
        # over all time
        min_time = None
        max_time = None

    return min_time, max_time




def get_suitable_customers(condition, store_id):
    relations = {"relation": "&&,||", "group_condition":[{"group_name":"Group One","relation":"||","children":[
        {"condition":"Customer paid order",
         "relations":[{"relation":"equals","value":["1"],"unit":"days"},
                      {"relation":"is over all time","value":["1"],"unit":"days"}]},
        {"condition":"Customer last cart created time","relations":
            [{"relation":"is in the past","value":["60"],"unit":"days"}]}]},{"group_name":"Group Two","relation":"||","children":[{"condition":"Customer who accept marketing","relations":[{"relation":"is true","value":["30"],"unit":"days"}]}]}]}

    {"relation": "&&,||", "group_condition": [{"group_name": "one", "relation": "&&", "children": [
        {"condition": "Customer sign up time",
         "relations": [{"relation": "is in the past", "value": [15, 0], "unit": "days"}]},
        {"condition": "Customer subscribe time",
         "relations": [{"relation": "is in the past", "value": [15, 0], "unit": "days"}]},
        {"condition": "Customer placed order", "relations": [{"relation": "more than", "value": [0, 0], "unit": "days"},
                                                             {"relation": "is in the past", "value": [15, 0],
                                                              "unit": "days"}]}]},
                                              {"group_name": "two", "relation": "&&", "children": [
                                                  {"condition": "Customer who accept marketing", "relations": [
                                                      {"relation": "is true", "value": ["30"], "unit": "days"}]}]}]}

    {"relation": "&&,||", "group_condition": [{"group_name": "123", "relation": "&&", "children": [
        {"condition": "Customer last click email time",
         "relations": [{"relation": "is in the past", "values": [15, 0], "unit": "days"}]},
        {"condition": "Customer last click email time", "relations": [
            {"relation": "is between date", "values": ["2019-01-30 00:00:00", "2019-01-25 00:00:00"],
             "unit": "days"}]}]}, {"group_name": "456", "relation": "&&", "children": [
        {"condition": "Customer last click email time",
         "relations": [{"relation": "is in the past", "values": [333, 0], "unit": "days"}]}]}]}

    store_id = 2
    group_condition = relations.get("group_condition", [])
    gc_relation = relations.get("relation", "").split(",")
    for gc in group_condition:
        children = gc.get("children", [])
        child_relation = gc.get("relation", "&&")

        for child in children:
            condition = child.get("condition", "")
            # 这几个的relation是两个
            if condition in ["Customer placed order", "Customer paid order", "Customer opened email", "Customer clicked email"]:
                relations = child.get("relations", [])
                values = child.get("value")
                order_max_time = datetime.datetime.now()
                order_min_time = None
                if relations[1] == "is in the past":
                    if child.get("unit", "days") == "days":
                        order_min_time = order_max_time - datetime.timedelta(days=values[0])
                    elif child.get("unit", "weeks") == "weeks":
                        order_min_time = order_max_time - datetime.timedelta(weeks=values[0])
                    elif child.get("unit", "months") == "months":
                        order_min_time = order_max_time - relativedelta(months=values[0])
                    elif child.get("unit", "years") == "years":
                        order_min_time = order_max_time - relativedelta(years=values[0])
                elif relations[1] == "over all time":
                    order_min_time = None
                elif relations[1] == "between date":
                    order_min_time = values[0]
                    order_max_time = values[1]
                elif relations[1] == 'before':
                    order_max_time = values[0]
                elif relations[1] == 'after':
                    order_min_time = values[0]
                if condition == "Customer paid order":
                    sql = "select `customer_uuid` where create_time>=%s and status=1"










def pinterest_client():
    pass


if __name__ == '__main__':
    # test()
    # main()
    #TaskProcessor().update_shopify_collections()
    # TaskProcessor().update_shopify_product()
    # TaskProcessor().update_shopify_sales_volume()
    # pinterest_client()
    print(date_relation_convert("in the past", [30], unit="years"))
    print(date_relation_convert("is between", [15, 30], unit="days"))
    print(date_relation_convert("is between date", ["2019-01-25 00:00:00", "2019-06-25 00:00:00"]))
    print(date_relation_convert("before", ["2019-01-25 00:00:00"]))

    min_date, max_date = date_relation_convert("is between date", ["2019-07-15 22:00:00", "2019-07-19 10:00:00"])
    print(order_filter(store_id=1, status=1, relation="less than", value=5, min_time=min_date, max_time=max_date))