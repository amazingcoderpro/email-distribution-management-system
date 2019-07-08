#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Created by charles on 2019-05-13
# Function: 

import logging
from log_config import log_config

log_config.init_log_config("logs", "seo")
logger = logging.getLogger()

SHOPIFY_CONFIG = {
    "client_id": "a09fec07bed3a3db749cfed6029dcdef",
    "client_secret": "ae743a3a05e5a549315cd203e6a35387",
    "ask_permission_uri": "https://autometa.seamarketings.com/api/v1/auth/shopify/ask_permission/",
    "redirect_uri": "https://autometa.seamarketings.com/api/v1/auth/shopify/callback/",
    "scopes": ["read_content", "write_content", "read_themes", "write_themes", "read_products",
               "write_products", "read_product_listings", "read_customers", "write_customers",
               "read_orders", "write_orders", "read_shipping", "write_draft_orders", "read_inventory",
               "write_inventory", "read_shopify_payments_payouts", "read_draft_orders", "read_locations",
               "read_script_tags", "write_script_tags", "read_fulfillments", "write_shipping", "read_analytics",
               "read_checkouts", "write_resource_feedbacks", "write_checkouts", "read_reports", "write_reports",
               "read_price_rules", "write_price_rules", "read_marketing_events", "write_marketing_events",
               "read_resource_feedbacks", "read_shopify_payments_disputes", "write_fulfillments"],
}


SYS_CONFIG = {
    "system_timezone": "UTC/GMT +8 hours"
}