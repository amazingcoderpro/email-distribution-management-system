# -*- coding: utf-8 -*-
# Created by: Leemon7
# Created on: 2019/7/12
import datetime

from config import logger
from sdk.ems.ems_api import ExpertSender
from task.task_processor import DBUtil


class GetEMSData:
    def __init__(self, api_key, from_email, store_id):
        self.store_id = store_id
        self.from_email = from_email
        self.api_key = api_key
        self.ems = ExpertSender(self.api_key, self.from_email)

    def insert_subscriber_activity(self, query_date):
        """
        将收件人行为记录入库，type包括Opens, Clicks, Sends
        :param query_date: 需要查询的日期，单位为一天，格式为2019-07-15
        :return:
        """
        try:
            conn = DBUtil().get_instance()
            cursor = conn.cursor() if conn else None
            if not cursor:
                return False
            # 获取行为记录数据
            result = {}
            type_choices = {'Opens': 0, 'Clicks': 1, 'Sends': 2}
            for tp in ["Opens", "Clicks"]:
                # Date,Email,MessageId,MessageSubject,CustomSubscriberId
                result[tp] = self.ems.get_subscriber_activity(tp, query_date)[1:]
            for tp, item in result.items():
                tp = type_choices[tp]
                for i in item:
                    try:
                        opt_time, email, message_uuid = i.split(",")[0:3]
                        print(opt_time, email, message_uuid)
                    except ValueError as e:
                        logger.info(e)
                        continue
                    cursor.execute("""select id from subscriber_activity where 
                    opt_time=%s and email=%s and message_uuid=%s and type=%s and store_id=%s""", (opt_time, email, int(message_uuid), tp, self.store_id))
                    is_activity = cursor.fetchone()
                    if is_activity:
                        logger.info(f"this subscriber activity exists, params is {opt_time},{email},{message_uuid}.")
                        continue
                    else:
                        now_time = datetime.datetime.now()
                        cursor.execute("""insert into subscriber_activity (opt_time,email,message_uuid,type,store_id,create_time,update_time) values
                        (%s,%s,%s,%s,%s,%s,%s)""", (opt_time, email, int(message_uuid), tp, self.store_id, now_time, now_time))
                        logger.info(f"insert a new subscriber activity success.")
                conn.commit()
        except Exception as e:
            logger.exception("insert subscriber activity exception e={}".format(e))
            return False
        finally:
            cursor.close() if cursor else 0
            conn.close() if conn else 0


if __name__ == '__main__':
    obj = GetEMSData("0x53WuKGWlbq2MQlLhLk", "leemon.li@orderplus.com", 1)
    obj.insert_subscriber_activity("2019-07-15")