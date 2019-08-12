#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Created by charles on 2019-05-13
# Function: 
import os
import logging
from log_config import log_config

log_config.init_log_config("logs", "edm")
logger = logging.getLogger()

SHOPIFY_CONFIG = {
    "client_id": "14afd1038ae052d9f13604af3e5e3ce3",
    "client_secret": "abbd97d861f25a7d36034ff96f0a2d97",
    "ask_permission_uri": "https://smartsend.seamarketings.com/api/v1/auth/shopify/ask_permission/",
    "redirect_uri": "https://smartsend.seamarketings.com/api/v1/auth/shopify/callback/",
    "scopes": ["read_content", "write_content", "read_themes", "write_themes", "read_products",
               "write_products", "read_product_listings", "read_customers", "write_customers",
               "read_all_orders", "read_orders", "write_orders", "read_shipping", "write_draft_orders", "read_inventory",
               "write_inventory", "read_shopify_payments_payouts", "read_draft_orders", "read_locations",
               "read_script_tags", "write_script_tags", "read_fulfillments", "write_shipping", "read_analytics",
               "read_checkouts", "write_resource_feedbacks", "write_checkouts", "read_reports", "write_reports",
               "read_price_rules", "write_price_rules", "read_marketing_events", "write_marketing_events",
               "read_resource_feedbacks", "read_shopify_payments_disputes", "write_fulfillments"],
    "utm_format": "/?utm_source=smartsend&utm_medium={email_category}&utm_campaign={template_name}&utm_term={product_uuid_template_id}",
    "utm_source": "smartsend"
}


SYS_CONFIG = {
    "system_timezone": "UTC/GMT +8 hours"
}


EMS_CONFIG = {
    "api_key": "0x53WuKGWlbq2MQlLhLk"
}


MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "47.244.107.240"),
    "port": 3306,
    "db": "edm",
    "user": "edm",
    "password": os.getenv("MYSQL_PASSWD", "edm@orderplus.com")
}

MONGO_CONFIG = {
    "host": "dds-j6cd6095509954a41348-pub.mongodb.rds.aliyuncs.com",
    "port": 3717,
    "db": "looklook",
    "user": "orderplus_edm",
    "password": 'edm123456789',
    "replica_set": "mgset-13096445",
    "auth_type": "SCRAM-SHA-1",
    "ssh": False,
    # "ssh_host": "47.244.107.240",
    # "ssh_user": "root",
    # "ssh_password": "ZBzZehr+WLonFxax"
}

ROOT_PATH = os.path.dirname(os.path.abspath(__file__))
ENABLE_SUBSCRIBE = True     # 是启用取消订阅，启用后不再发送邮件给那些已经取消订阅的人