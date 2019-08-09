#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Created by charles on 2019-08-05
# Function: 

from collections import Counter
from datetime import datetime, timedelta
import pymysql
from pymongo import MongoClient
from sshtunnel import SSHTunnelForwarder

from config import MONGO_CONFIG, MYSQL_CONFIG, logger
from task.db_util import DBUtil, MongoDBUtil

import json
class DataMigrate:
    """
    数据迁移,
    """
    def __init__(self, mongo_config, mysql_config):
        self.mongo_host = mongo_config.get("host", "")
        self.mongo_port = mongo_config.get("port", 27017)
        self.mongo_db = mongo_config.get("db", "looklook")
        self.mongo_user = mongo_config.get("user", "")
        self.mongo_password = mongo_config.get("password", "")
        self.mongo_replicaset = mongo_config.get("replica_set", "")
        self.mongo_auth_type = mongo_config.get("auth_type", "SCRAM-SHA-1")

        # 是否使用ssh
        self.use_ssh = mongo_config.get("ssh", False)
        self.ssh_host = mongo_config.get("ssh_host", "")
        self.ssh_user = mongo_config.get("ssh_user", "")
        self.ssh_password = mongo_config.get("ssh_password", "")

        # mysql配置
        self.db_host = mysql_config.get("host", "")
        self.db_port = mysql_config.get("port", 3306)
        self.db_name = mysql_config.get("db", "")
        self.db_user = mysql_config.get("user", "")
        self.db_password = mysql_config.get("password", "")

        self.client = None
        self.db = None
        self.ssh_server = None

    def init_mongo(self):
        if self.use_ssh:
            self.__init_mongo_by_ssh__()
            return self.db

        try:
            mongo_uri = f"mongodb://{self.mongo_user}:{self.mongo_password}@{self.mongo_host}:{self.mongo_port}/{self.mongo_db}?replicaSet={self.mongo_replicaset}"
            self.client = MongoClient(mongo_uri)
            self.db = self.client[self.mongo_db]
            return self.db
        except Exception as e:
            logger.exception("Connect mongodb failed!! e={}".format(e))
            raise e

    def __init_mongo_by_ssh__(self):
        try:
            self.ssh_server = SSHTunnelForwarder(ssh_address_or_host=self.ssh_host, ssh_username=self.ssh_user, ssh_password=self.ssh_password,
                                        remote_bind_address=(self.mongo_host, self.mongo_port))
            self.ssh_server.start()

            self.client = MongoClient('127.0.0.1', self.ssh_server.local_bind_port)
            self.client.get_database(self.mongo_db).authenticate(self.mongo_user, self.mongo_password)
            self.db = self.client[self.mongo_db]
        except Exception as e:
            logger.exception("Connect mongodb by ssh failed!! e={}".format(e))
            raise e

    def test_mongo_connection(self):
        if self.use_ssh:
            self.init_mongo_by_ssh()
        else:
            self.init_mongo()
        print(self.db.collection_names(include_system_collections=False))

    def get_all_stores(self):
        """
        获取所有店铺id及名称
        :return:
        """
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user, password=self.db_password).get_instance()
            cursor = conn.cursor(cursor=pymysql.cursors.DictCursor) if conn else None
            if not cursor:
                return None

            cursor.execute("""select id, name, url, domain, source from store where id>0""")
            stores = cursor.fetchall()
            return stores
        except Exception as e:
            logger.exception("get_all_stores exception e={}".format(e))
            return None
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0

    def update_top_products_mongo(self):
        stores = self.get_all_stores()
        if not stores:
            logger.warning("There have not stores to update top products")

        mdb = MongoDBUtil(mongo_config=MONGO_CONFIG)
        db = mdb.get_instance()

        conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user,
                      password=self.db_password).get_instance()
        cursor = conn.cursor() if conn else None
        if not cursor:
            return False

        time_now = datetime.now()
        time_beg = (datetime.now()-timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S")
        recent_3days_paid_products = []
        recent_7days_paid_products = []
        recent_15days_paid_products = []
        recent_30days_paid_products = []
        for store in stores:
            store_site = store.get("name", "")
            store_id = store.get("id")
            domain = store.get("domain", "")
            source = store.get("source", 0)
            # if source != 0:
            #     continue

            logger.info("start parse top products from mongo, store id={}, name={}".format(store_id, store_site))
            order_collection = db["shopify_order"]
            orders = order_collection.find({"site_name": store_site, "updated_at": {"$gte": time_beg}}, {"line_items": 1, "updated_at": 1})
            for order in orders:
                line_items = order.get("line_items", [])
                order_updated_time = order.get("updated_at", "")
                order_updated = datetime.strptime(order_updated_time[0: 19], "%Y-%m-%dT%H:%M:%S")
                delta_days = (time_now - order_updated).total_seconds()/3600/24
                products = []
                idx = 0
                for pro in line_items:
                    if delta_days <= 3:
                        recent_3days_paid_products.append(pro.get("product_id", ""))
                    elif delta_days <= 7:
                        recent_7days_paid_products.append(pro.get("product_id", ""))
                    elif delta_days <= 15:
                        recent_15days_paid_products.append(pro.get("product_id", ""))
                    else:
                        recent_30days_paid_products.append(pro.get("product_id", ""))

            top6_product_ids_recent3days = [item[0] for item in Counter(recent_3days_paid_products).most_common(6)]
            top6_product_ids_recent7days = [item[0] for item in Counter(recent_7days_paid_products).most_common(6)]
            top6_product_ids_recent15days = [item[0] for item in Counter(recent_15days_paid_products).most_common(6)]
            top6_product_ids_recent30days = [item[0] for item in Counter(recent_30days_paid_products).most_common(6)]

            top6_products_3days = []
            top6_products_7days = []
            top6_products_15days = []
            top6_products_30days = []
            product_col = db["shopify_product"]
            all_top = top6_product_ids_recent3days+top6_product_ids_recent7days+top6_product_ids_recent15days+top6_product_ids_recent30days
            all_top = [int(item) for item in all_top]
            if all_top:
                products = product_col.find({"id": {"$in": all_top}}, {"id": 1, "title": 1, "handle": 1, "variants.price": 1, "image.src": 1})
                # products = product_col.find({"id": {"$in": all_top}, "site_name": store_site},
                #                             {"id": 1, "title": 1, "handle": 1})
                for pro in products:
                    product_info = {
                        "uuid": pro["id"],
                        "name": pro["title"],
                        "price": pro["variants"][0].get("price", 0),
                        "image_url": pro["image"].get("src", ""),
                        "url": f"{domain}/products/{pro['handle']}"
                    }
                    if pro["id"] in top6_product_ids_recent3days:
                        top6_products_3days.append(product_info)
                    elif pro["id"] in top6_product_ids_recent7days:
                        top6_products_7days.append(product_info)
                    elif pro["id"] in top6_product_ids_recent15days:
                        top6_products_15days.append(product_info)
                    else:
                        top6_products_30days.append(product_info)

            current_time = datetime.now()
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

        mdb.close()



    def close(self):
        logger.info("")
        if self.client:
            self.client.close()

        if self.ssh_server and self.ssh_server.is_alive:
            self.ssh_server.close()


if __name__ == '__main__':
    dm = DataMigrate(MONGO_CONFIG, MYSQL_CONFIG)
    dm.update_top_products_mongo()
    dm.close()
