#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Created by charles on 2019-07-20
# Function: 
import threading
import pymysql
from pymongo import MongoClient
from sshtunnel import SSHTunnelForwarder

from config import MONGO_CONFIG, logger


class DBUtil:
    def __init__(self, host, port, db, user, password):
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


class MongoDBUtil:
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

        self.conn_pool = {}

    def get_instance(self):
        try:
            name = threading.current_thread().name
            if name not in self.conn_pool:
                client, db, ssh_server = self.__connect()
                self.conn_pool[name] = {"client": client, "db": db, "ssh_server": ssh_server}
        except Exception as e:
            logger.exception("connect mysql error, e={}".format(e))
            return None
        return self.conn_pool[name]["db"]

    def __connect(self):
        if self.use_ssh:
            return self.__connect_by_ssh()

        try:
            mongo_uri = f"mongodb://{self.mongo_user}:{self.mongo_password}@{self.mongo_host}:{self.mongo_port}/{self.mongo_db}?replicaSet={self.mongo_replicaset}"
            client = MongoClient(mongo_uri)
            db = client[self.mongo_db]
            return client, db, None
        except Exception as e:
            logger.exception("Connect mongodb failed!! e={}".format(e))
            raise e

    def __connect_by_ssh(self):
        try:
            ssh_server = SSHTunnelForwarder(ssh_address_or_host=self.ssh_host, ssh_username=self.ssh_user, ssh_password=self.ssh_password,
                                        remote_bind_address=(self.mongo_host, self.mongo_port))
            ssh_server.start()

            client = MongoClient('127.0.0.1', ssh_server.local_bind_port)
            client.get_database(self.mongo_db).authenticate(self.mongo_user, self.mongo_password)
            db = client[self.mongo_db]
            return client, db, ssh_server
        except Exception as e:
            logger.exception("Connect mongodb by ssh failed!! e={}".format(e))
            raise e

    def close(self):
        try:
            name = threading.current_thread().name
            if name in self.conn_pool:
                client = self.conn_pool[name]["client"]
                ssh_server = self.conn_pool[name]["ssh_server"]
                if client:
                    client.close()

                if ssh_server and ssh_server.is_alive:
                    ssh_server.close()

        except Exception as e:
            logger.exception("close mongodb, e={}".format(e))
            return None


if __name__ == '__main__':
    mdb = MongoDBUtil(mongo_config=MONGO_CONFIG)
    db = mdb.get_instance()
    print(db.collection_names(include_system_collections=False))
    mdb.close()