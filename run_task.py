#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Created by charles on 2019-07-20
# Function: 
import os
import time
from apscheduler.schedulers.background import BackgroundScheduler

from task.ems_data_processor import EMSDataProcessor
from task.shopify_data_processor import ShopifyDataProcessor
from config import logger
from task.customer_group_processor import AnalyzeCondition
from task.template_task_processor import TemplateProcessor

MYSQL_PASSWD = os.getenv('MYSQL_PASSWD', None)
MYSQL_HOST = os.getenv('MYSQL_HOST', None)

# just for test, delete it in product environment
MYSQL_HOST = "47.244.107.240"
MYSQL_PASSWD = "edm@orderplus.com"

db_info = {"host": MYSQL_HOST, "port": 3306, "db": "edm", "user": "edm", "password": MYSQL_PASSWD}


class TaskProcessor:
    """
    任务处理类，用于创建，暂停，启动定时任务
    """
    def __init__(self):
        self.bk_scheduler = BackgroundScheduler()
        self.bk_scheduler.start()
        self.tasks = []

    def create_periodic_task(self, func, seconds, max_instances=10, *args, **kwargs):
        """
        创建间隔性任务
        :param func: 任务处理函数
        :param seconds: 间隔时间，单位秒
        :param args: 参数列表,透传给任务处理函数
        :param kwargs: 参数字典,透传给任务处理函数
        :return: （True, task_id） --成功或失败, 成功时task id不为None
        """
        try:
            task_id = self.bk_scheduler.add_job(func, 'interval', seconds=seconds, max_instances=max_instances, args=args, kwargs=kwargs)
            self.tasks.append({'task_name': func.__name__, "task_id": task_id})
        except Exception as e:
            logger.exception("create_periodic_task　failed, e={}".format(e))
            return False, None

        return True, task_id

    def create_cron_task(self, func, day_of_week, hour, minute, *args, **kwargs):
        """
        创建周期触发式任务(即每周某一天固定时间执行）
        :param func: 任务处理函数
        :param day_of_week: int 或 str, 周内第几天或者星期几 (范围0-6 或者 mon,tue,wed,thu,fri,sat,sun), "*"-代表一周中的每一天
        :param hour: (int 或 str) 时 (范围0-23)
        :param minute: (int 或 str) 分 (范围0-59)
        :param args: 参数列表,透传给任务处理函数
        :param kwargs: 参数字典,透传给任务处理函数
        :return:
        """
        try:
            task_id = self.bk_scheduler.add_job(func, 'cron', day_of_week=day_of_week, hour=hour,
                                                minute=minute, args=args, kwargs=kwargs)
            self.tasks.append({'task_name': func.__name__, "task_id": task_id})
        except Exception as e:
            logger.exception("create_cron_task　failed, e={}".format(e))
            return False, None

        return True, task_id

    def create_timed_task(self, func, run_date, *args, **kwargs):
        """
        创建定时任务，该任务将在指定的时间点仅执行一次
        :param func: 任务处理函数
        :param run_date: (datetime 或 str)	任务的运行日期或时间
        :param args: 参数列表,透传给任务处理函数
        :param kwargs: 参数字典,透传给任务处理函数
        :return:
        """
        try:
            task_id = self.bk_scheduler.add_job(func, "date", run_date=run_date, args=args, kwargs=kwargs)
            self.tasks.append({'task_name': func.__name__, "task_id": task_id})
        except Exception as e:
            logger.exception("create_cron_task　failed, e={}".format(e))
            return False, None

        return True, task_id

    def stop_all(self):
        """
        停止所有任务
        :return:
        """
        logger.warning("TaskProcessor stop_all work.")
        self.bk_scheduler.remove_all_jobs()

    def pause_task(self, task_name="", task_id=""):
        """
        暂停某一任务, 注：名称和id任传一个即可，优先使用id, 如果两个参数都为空，则暂停所有任务
        :param task_name:　任务名称
        :param task_id: 任务id,
        :return: 成功为True, 失败为False
        """
        logger.info("TaskProcessor pause work. task name={}, task id={}".format(task_name, task_id))
        if self.bk_scheduler.running:
            # 两者都不传时，默认代表恢复全部任务
            if not task_id and not task_name:
                self.bk_scheduler.pause()
                logger.info("resume all jobs.")
                return True

            if task_id:
                self.bk_scheduler.pause_job(task_id)
                return True
            else:
                for task in self.tasks:
                    if task.get("task_name", "") == task_name:
                        task_id = task.get("task_id", "")
                        self.bk_scheduler.pause_job(task_id)
                        return True
                else:
                    logger.warning("There have no task for pausing")
                    return False
        else:
            logger.warning("background scheduler is not running in pause!")
            return False

    def resume(self, task_name="", task_id=""):
        """
        恢复某一任务, 注：名称和id任传一个即可，优先使用id, 如果两个参数都为空，则恢复所有任务
        :param task_name:　任务名称
        :param task_id: 任务id
        :return: 成功为True, 失败为False
        """
        logger.info("TaskProcessor resume work. task name={}, task id={}".format(task_name, task_id))
        if self.bk_scheduler.running:
            # 两者都不传时，默认代表恢复全部任务
            if not task_id and not task_name:
                self.bk_scheduler.resume()
                logger.info("resume all jobs.")
                return True

            if task_id:
                self.bk_scheduler.resume_job(task_id)
                return True
            else:
                for task in self.tasks:
                    if task.get("task_name", "") == task_name:
                        task_id = task.get("task_id", "")
                        self.bk_scheduler.resume_job(task_id)
                        return True
                else:
                    logger.warning("There have no task for resuming")
                    return False
        else:
            logger.warning("background scheduler is not running in resume!")
            return False


def test_task_processor():
    def test_processor(a, b):
        print("I'm a test processor, a={}, b={}".format(a, b))

    tp = TaskProcessor()
    tp.create_periodic_task(test_processor, seconds=5, a="aa", b="bb")
    while 1:
        time.sleep(1)


def run():
    tp = TaskProcessor()

    # 所有定时任务在此创建

    # 定期更新customer group
    ac = AnalyzeCondition(db_info=db_info)
    tp.create_periodic_task(ac.update_customer_group_list, seconds=7200)

    # 模板解析定时任务
    tmp = TemplateProcessor(db_info=db_info)
    tp.create_periodic_task(tmp.analyze_templates,  seconds=300)

    # 模板邮件定时发送任务
    tp.create_periodic_task(tmp.execute_email_task, seconds=120, max_instances=50, interval=120)

    # shopify 定时更新任务, 请放在这下面
    sdp = ShopifyDataProcessor(db_info=db_info)
    tp.create_periodic_task(sdp.update_new_shopify, seconds=120, max_instances=50)   # 新店铺拉 产品类目 产品 订单 top_product
    tp.create_cron_task(sdp.update_shopify_collections, "*", 12, 00)
    tp.create_cron_task(sdp.update_shopify_product, "*", 12, 00)
    tp.create_cron_task(sdp.update_top_product, "*", 12, 00)

    # ems 定时更新任务请放在这下面
    ems = EMSDataProcessor("Leemon", "leemon.li@orderplus.com", db_info=db_info)
    tp.create_cron_task(ems.insert_subscriber_activity, "*", 0, 30)  # 每天0:1:0拉取昨天一整天的行为记录
    tp.create_cron_task(ems.update_customer_group_data, "*", 0, 5)  # 每天23:50:0更新到目前时间用户组最新ems数据
    tp.create_cron_task(ems.update_email_reocrd_data, "*", 0, 5)  # 每天23:50:0更新到目前时间已发送邮件最新ems数据
    tp.create_cron_task(ems.insert_dashboard_data, "*", 1, 0)  # 每天23:50:0更新dashboard最新数据

    while 1:
        time.sleep(1)


if __name__ == '__main__':
    run()
