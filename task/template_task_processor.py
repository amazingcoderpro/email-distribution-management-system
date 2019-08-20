#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Created by charles on 2019-07-23
# Function: 
import pymysql
import datetime
import json
# from dateutil.relativedelta import relativedelta
from task.product_recommendation import ProductRecommend
from config import logger
from task.shopify_data_processor import DBUtil
from sdk.ems import ems_api


class TemplateProcessor:
    """
    模板处理类，包括模板规则解析和定时发送
    """
    def __init__(self, db_info):
        self.db_host = db_info.get("host", "")
        self.db_port = db_info.get("port", 3306)
        self.db_name = db_info.get("db", "")
        self.db_user = db_info.get("user", "")
        self.db_password = db_info.get("password", "")
        self.week_day = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6}
        self.days = ["1st of the month", "15th of the month", "Last day of the month", "Everyday"]

    def analyze_templates(self, template_id=None):
        """
        模板规则解析，将周期性模板解析成一个个的task(只解析template型邮件)
        :param template_id:
        :return:
        """
        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user,
                          password=self.db_password).get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return False

            logger.info("analyze_templates start. template_id={}".format(template_id))
            if template_id:
                cursor.execute("""select id, send_rule from `email_template` where status=0 and id=%s""", (template_id, ))
            else:
                # 找到所有状态是待解析，已启用且类型为模板邮件的模板
                # 剔除admin店铺
                cursor.execute("""select id, send_rule, store_id from `email_template` where status=0 and send_type=0 and enable=1 and store_id>1""")

            data = cursor.fetchall()
            if not data:
                logger.info("there have no template for analyzing")
                return True

            for value in data:
                template_id, send_rule, store_id = value
                logger.info("analyze template, template id={}".format(template_id))
                #{"begin_time": "2019-10-01 00:00:00", "end_time": "2019-10-02 00:00:00", "cron_type": "Monday", "cron_time": "18:40:00"}
                send_rule = json.loads(send_rule)
                if not send_rule:
                    continue

                execute_times = []
                time_format = "%Y-%m-%d %H:%M:%S"
                begin_time = datetime.datetime.strptime(send_rule["begin_time"], time_format)
                end_time = datetime.datetime.strptime(send_rule["end_time"], time_format)
                datetime_now = datetime.datetime.now()
                while begin_time <= end_time:
                    cron_type = send_rule.get("cron_type", "")
                    cron_time = datetime.datetime.strptime(send_rule.get("cron_time", ""), "%H:%M:%S").time()

                    # # 小于当前时间的计划任务不需要创建出来
                    # if begin_time < datetime_now:
                    #     begin_time += datetime.timedelta(days=1)
                    #     continue

                    if cron_type in self.days:
                        # 每月１号
                        if cron_type == self.days[0]:
                            if begin_time.day == 1:
                                execute_times.append(datetime.datetime.combine(begin_time.date(), cron_time))
                        # 每月15号
                        elif cron_type == self.days[1]:
                            if begin_time.day == 15:
                                execute_times.append(datetime.datetime.combine(begin_time.date(), cron_time))
                        # 每月最后一天
                        elif cron_type == self.days[2]:
                            if begin_time.month != (begin_time+datetime.timedelta(days=1)).month:
                                execute_times.append(datetime.datetime.combine(begin_time.date(), cron_time))
                        # 每一天
                        elif cron_type == self.days[3]:
                            execute_times.append(datetime.datetime.combine(begin_time.date(), cron_time))
                    else:
                        # 按周几发
                        if self.week_day.get(cron_type, "") == begin_time.weekday():
                            execute_times.append(datetime.datetime.combine(begin_time.date(), cron_time))

                    begin_time += datetime.timedelta(days=1)

                # 一个模板解析完就存一次库
                time_now = datetime.datetime.now()
                for exet in execute_times:
                    cursor.execute("insert into `email_task` (`status`, `execute_time`, `create_time`, `update_time`, "
                                   "`template_id`, `type`, `store_id`) values (%s, %s, %s, %s, %s, %s, %s)", (0, exet, time_now, time_now, template_id, 0, store_id))
                conn.commit()

                time_now = datetime.datetime.now()
                cursor.execute("""update `email_template` set `status`=1, `update_time`=%s where id=%s""", (time_now, template_id))
                conn.commit()

        except Exception as e:
            logger.exception("analyze_templates e={}".format(e))
            return False
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0

    def execute_email_task(self, interval=30):
        """
        执行邮件发送任务(只执行template型邮件的任务)
        :param interval:　间隔周期
        :return:
        """

        try:
            conn = DBUtil(host=self.db_host, port=self.db_port, db=self.db_name, user=self.db_user,
                          password=self.db_password).get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return False

            logger.info("execute_email_task checking..")
            # 先找出当前巡查周期内应该发送的邮件任务
            # dt_min = datetime.datetime.now()-datetime.timedelta(seconds=interval/2+10)
            # dt_max = datetime.datetime.now()+datetime.timedelta(seconds=interval/2+10)
            dt_min = datetime.datetime.now() - datetime.timedelta(seconds=interval / 2 + 10000)
            dt_max = datetime.datetime.now() + datetime.timedelta(seconds=interval / 2 + 10000)
            cursor.execute("""select id, template_id from `email_task` 
            where status=0 and type=0 and execute_time>=%s and execute_time<=%s""", (dt_min, dt_max))

            tasks = cursor.fetchall()
            if not tasks:
                logger.info("This time have no task for executing.")
                return

            for task in tasks:
                # 遍历每一个任务，找到他对应的模板　
                task_id, template_id = task
                logger.info("execute_email_task get need execute task={}".format(task_id))
                cursor.execute("select `status`, `enable`, `customer_group_list`, `subject`, `html`, `store_id`, `title`, `product_condition` from `email_template` where id=%s", (template_id, ))

                # 如果模板的状态变成了已经删除，则不再发送，且把该模板对就的所有未发送的task全置成已删除
                ret = cursor.fetchone()
                template_state, enable, template_group_list, subject, html, store_id, template_title, product_condition = ret
                if template_state == 2:#删除了
                    pass
                    #模板的禁用和删除由接口处理，这里不再做处理了
                    # cursor.execute("""update `email_task` set `status`=4 where template_id=%s　and status=0""", (template_id,))
                    # conn.commit()
                    # logger.info("task's template have been deleted, task id={}, template_id={}".format(task_id, template_id))
                elif enable == 0:
                    pass
                    #模板被禁用了
                else:
                    # 拿到该模板里包含的customer group,每个group对应的邮件组id
                    cursor.execute("select `uuid` from `customer_group` where id in %s", (eval(template_group_list), ))
                    ret = cursor.fetchall()
                    uuids = [uid[0] for uid in ret]
                    uuids = [uid for uid in uuids if uid]   # 去掉里面的空包弹
                    cursor.execute("select `sender`, `sender_address`, `site_name`, `domain`, `service_email` from `store` where id=%s", (store_id, ))
                    sender = cursor.fetchone()

                    if sender and uuids:
                        # 拿到了所对应的邮件组id, 开始发送邮件
                        exp = ems_api.ExpertSender(from_name=sender[0], from_email=sender[1])

                        # 替换 html
                        pr = ProductRecommend()
                        shop_info = pr.get_card_product_mongo("", sender[2], template_title, template_id, sender[3],
                                                                      sender[4], length=0, utm_medium="Newsletter")

                        top_products = []
                        if "top" in product_condition:
                            # 获取top_products
                            top_products = pr.get_top_product_by_condition(product_condition, store_id,
                                                                           template_title, template_id, utm_medium="Newsletter")

                        snippets_dict = pr.generate_snippets(shop_info, top_products, flow=False)
                        for key,val in snippets_dict.items():
                            html = html.replace("*[tr_{}]*".format(key),val)

                        result = exp.create_and_send_newsletter(uuids, subject=subject, html=html)
                        send_result = result["code"]
                        email_id = result["data"]
                        send_msg = "email id: {} ".format(email_id)     # 发送成功后把email id存在remark中
                        if send_result != 1:
                            send_result = 3     # 发送失败
                            send_msg += result["msg"]
                            logger.error(
                                "send template email failed, task={}, template={}, uuids={}, error={}".format(task_id, template_id, uuids, send_msg))
                        else:
                            logger.info(
                                "send template email succeed, task={}, template={}, uuids={}, msg={}, email id={}".format(task_id,
                                                                                                     template_id, uuids,
                                                                                                     send_msg, email_id))

                        time_now = datetime.datetime.now()
                        # 更新任务状态
                        cursor.execute("""update `email_task` set `status`=%s, `remark`=%s, `uuid`=%s, `finished_time`=%s, 
                        `update_time`=%s where id=%s""", (send_result, str(send_msg), str(email_id), time_now, time_now, task_id))
                        conn.commit()

                        # 在email record中插入一条
                        cursor.execute("""insert into `email_record` (`uuid`, `store_id`, `email_template_id`, 
                        `create_time`, `update_time`, `type`, `recipients`) values (%s, %s, %s, %s, %s, %s, %s)""",
                                       (str(email_id), store_id, template_id, time_now, time_now, 0, uuids))
                        conn.commit()
        except Exception as e:
            logger.exception("execute_email_task e={}".format(e))
            return False
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0


if __name__ == '__main__':
    at = TemplateProcessor(db_info={"host": "47.244.107.240", "port": 3306, "db": "edm", "user": "edm", "password": "edm@orderplus.com"})
    # at.analyze_templates()
    at.execute_email_task()
    # at.execute_email_task(interval=666600)

