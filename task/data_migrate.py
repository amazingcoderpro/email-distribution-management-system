#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Created by charles on 2019-08-05
# Function: 


from pymongo import MongoClient
from sshtunnel import SSHTunnelForwarder
from config import MONGO_CONFIG, logger


class DataMigrate:
    """

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
        try:
            mongo_uri = f"mongodb://{self.mongo_user}:{self.mongo_password}@{self.mongo_host}:{self.mongo_port}/{self.mongo_db}?replicaSet={self.mongo_replicaset}"
            self.client = MongoClient(mongo_uri)
            self.db = self.client[self.mongo_db]
        except Exception as e:
            logger.exception("Connect mongodb failed!! e={}".format(e))
            raise e

    def init_mongo_by_ssh(self):
        self.ssh_server = SSHTunnelForwarder(ssh_address_or_host=self.ssh_host, ssh_username=self.ssh_user, ssh_password=self.ssh_password,
                                    remote_bind_address=(self.mongo_host, self.mongo_port))
        self.ssh_server.start()
        self.client = MongoClient('127.0.0.1', self.ssh_server.local_bind_port)
        self.client.get_database(self.mongo_db).authenticate(self.mongo_user, self.mongo_password)
        self.db = self.client[self.mongo_db]

    def test_db(self):
        if self.use_ssh:
            self.init_mongo_by_ssh()
        else:
            self.init_mongo()
        print(self.db.collection_names(include_system_collections=False))

    def migrate_top_products(self):
        store_site_names = ["Astrotrex"]
        for store_site in store_site_names:
            order_collection = self.db["shopify_order"]
            order_collection.find({"site_name": store_site})



if __name__ == '__main__':
    dm = DataMigrate(MONGO_CONFIG)
    dm.test_db()



