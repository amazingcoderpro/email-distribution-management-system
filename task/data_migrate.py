#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Created by charles on 2019-08-05
# Function: 


from pymongo import MongoClient
from sshtunnel import SSHTunnelForwarder
from config import MONGO_CONFIG, logger
from datetime import datetime, timedelta
from collections import Counter


class DataMigrate:
    """
    数据迁移,
    """
    def __init__(self, mongo_config):
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

        self.client = None
        self.db = None
        self.ssh_server = None

    def init_mongo(self):
        if self.use_ssh:
            self.__init_mongo_by_ssh__()
            return

        try:
            mongo_uri = f"mongodb://{self.mongo_user}:{self.mongo_password}@{self.mongo_host}:{self.mongo_port}/{self.mongo_db}?replicaSet={self.mongo_replicaset}"
            self.client = MongoClient(mongo_uri)
            self.db = self.client[self.mongo_db]
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

    def test_db(self):
        if self.use_ssh:
            self.init_mongo_by_ssh()
        else:
            self.init_mongo()
        print(self.db.collection_names(include_system_collections=False))

    def migrate_top_products(self):
        store_site_names = ["Astrotrex"]
        recent_products = {}
        time_now = datetime.now()
        time_beg = (datetime.now()-timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S")
        recent_3days_paid_products = []
        recent_7days_paid_products = []
        recent_15days_paid_products = []
        recent_30days_paid_products = []
        for store_site in store_site_names:
            order_collection = self.db["shopify_order"]
            orders = order_collection.find({"site_name": store_site, "updated_at": {"$gte": time_beg}}, {"line_items": 1, "updated_at": 1})
            for order in orders:
                line_items = order.get("line_items", [])
                order_updated_time = order.get("updated_at", "")
                order_updated = datetime.strptime(order_updated_time[0: 19], "%Y-%m-%dT%H:%M:%S")
                delta_days = (time_now - order_updated).total_seconds()/3600/24
                products = []
                for pro in line_items:
                    products.append(pro.get("id", ""))
                if delta_days <= 3:
                    recent_3days_paid_products += products
                elif delta_days <= 7:
                    recent_7days_paid_products += products
                elif delta_days <= 15:
                    recent_15days_paid_products += products
                else:
                    recent_30days_paid_products += products

        top6_products_recent3days = [item[0] for item in Counter(recent_3days_paid_products).most_common(6)]
        top6_products_recent7days = [item[0] for item in Counter(recent_7days_paid_products).most_common(6)]
        top6_products_recent15days = [item[0] for item in Counter(recent_15days_paid_products).most_common(6)]
        top6_products_recent30days = [item[0] for item in Counter(recent_30days_paid_products).most_common(6)]

        product_col = self.db["shopify_product"]

        print(top6_products_recent3days)
        print(top6_products_recent7days)
        print(top6_products_recent15days)
        print(top6_products_recent30days)

    def close(self):
        logger.info("")
        if self.client:
            self.client.close()

        if self.ssh_server and self.ssh_server.is_alive:
            self.ssh_server.close()


if __name__ == '__main__':
    dm = DataMigrate(MONGO_CONFIG)
    dm.init_mongo()
    dm.migrate_top_products()
    dm.close()




