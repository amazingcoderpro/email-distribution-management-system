#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Created by charles on 2019-07-20
# Function: 
import os
import time
from task.task_processor import TaskProcessor


MYSQL_PASSWD = os.getenv('MYSQL_PASSWD', None)
MYSQL_HOST = os.getenv('MYSQL_HOST', None)


def run():
    tsp = TaskProcessor()
    tsp.start_all(rule_interval=120, publish_pin_interval=120, pinterest_update_interval=7200*3, shopify_update_interval=7200*3, update_new=120)
    while 1:
        time.sleep(1)


if __name__ == '__main__':
    run()