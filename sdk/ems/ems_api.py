# -*- coding: utf-8 -*-
# Created by: Leemon7
# Created on: 2019/7/8
import datetime
import json
import re

import xmltodict
from config import logger, EMS_CONFIG
import requests


class ExpertSender:
    def __init__(self, from_name, from_email, api_key=EMS_CONFIG.get("api_key")):
        self.api_key = api_key
        self.host = "https://api6.esv2.com/v2/"
        self.headers = {"Content-Type": "text/xml"}
        self.from_name = from_name if from_name else "Leemon"
        self.from_email = from_email if from_email else "leemon.li@orderplus.com"

    @staticmethod
    def xmltojson(xmlstr, type):
        # parse是的xml解析器
        if not xmlstr.strip():
            return {}
        xmlparse = xmltodict.parse(xmlstr)
        jsonstr = json.dumps(xmlparse, indent=1)
        return json.loads(jsonstr).get("ApiResponse", {}).get(type)

    @staticmethod
    def jsontoxml(jsonstr):
        # xmltodict库的unparse()json转xml
        xmlstr = xmltodict.unparse(jsonstr)
        return xmlstr

    @staticmethod
    def delete_space(html):
        # 删除html中的空行、空格、换行
        rexp = re.compile("\s")
        return ''.join(rexp.split(html))

    def retrun_result(self, funcname, result):
        """封装return"""
        if str(result.status_code).startswith('2'):
            logger.info("%s success!" % funcname)
            return {"code": 1, "msg": "", "data": self.xmltojson(result.text, "Data")}
        else:
            msg = self.xmltojson(result.text, "ErrorMessage")
            logger.info("%s failed! The reason is %s" % (funcname,  msg))
            return {"code": 2, "msg": msg, "data": ""}

    def get_server_time(self):
        """获取服务器时间
        接口Url：http://sms.expertsender.cn/api/v2/methods/get-server-time/
        """
        url = f"{self.host}Api/Time?apiKey={self.api_key}"
        try:
            result = requests.get(url)
            return self.retrun_result("get server time", result)
        except Exception as e:
            return {"code": -1, "msg": str(e), "data": ""}

    def get_messages(self, email_id=None):
        """获取已发送邮件列表
        接口Url：http://sms.expertsender.cn/api/v2/methods/email-messages/get-messages-list/
        """
        if email_id:
            url = f"{self.host}Api/Messages/{email_id}?apiKey={self.api_key}"
        else:
            url = f"{self.host}Api/Messages?apiKey={self.api_key}"
        try:
            result = requests.get(url)
            return self.retrun_result("get messages", result)
        except Exception as e:
            return {"code": -1, "msg": str(e), "data": ""}

    def get_bounces_list(self):
        """获取弹回列表
        接口Url：http://sms.expertsender.cn/api/v2/methods/get-bounces-list/
        """
        url = f"{self.host}Api/Bounces?apiKey={self.api_key}&startDate=2019-07-01&endDate=2019-07-08"
        try:
            result = requests.get(url)
            return result.text
        except Exception as e:
            return {"code": -1, "msg": str(e), "data": ""}

    def get_message_statistics(self, email_id, start_date="1970-01-01", end_date=datetime.datetime.today().date()):
        """
        获取邮件统计数据
        接口Url：http://sms.expertsender.cn/api/v2/methods/email-statistics/get-message-statistics/
        :param email_id: 邮件ID
        :param start_date: 查询开始时间，默认为时间元年
        :param end_date: 查询结束时间，默认为今天
        :return: {'Sent': '61644', 'Bounced': '145', 'Delivered': '61499', 'Opens': '1754', 'UniqueOpens': '1190', 'Clicks': '224', 'UniqueClicks': '205', 'Clickers': '111', 'Complaints': '11', 'Unsubscribes': '159'}
        """
        url = f"{self.host}Api/MessageStatistics/{email_id}?apiKey={self.api_key}&startDate={start_date}&endDate={end_date}"
        try:
            result = requests.get(url)
            return self.retrun_result("get message statistics", result)
        except Exception as e:
            return {"code": -1, "msg": str(e), "data": ""}

    def create_and_send_newsletter(self, list_id_list, subject, content_from_url=None, plain="", html="", delivery_date=None):
        """
        创建及发送Newsletter, 注：如多个listId中存在同样的邮件，只会发一封邮件
        接口Url：http://sms.expertsender.cn/api/v2/methods/email-messages/create-and-send-newsletter/
        :param list_id_list: 发送列表ID组成的列表
        :param subject: 邮件主题
        :param plain: 邮件纯文本
        :param html: html格式邮件内容
        :param content_from_url: 外源下载时使用的Url
        :param delivery_date: 指定发送日期，默认为及时发送
        :return: 邮件ID
        """
        url = f"{self.host}Api/Newsletters"
        data = {"ApiRequest": {
                    "ApiKey": self.api_key,
                    "Data": {
                        "Recipients": {"SubscriberLists": {"SubscriberList": []}},
                        "Content": {
                            "FromName": self.from_name,
                            "FromEmail": self.from_email,
                            "Subject": subject,
                            "Plain": plain,
                            "Html": "{}",
                        },
                        "DeliverySettings": {
                            "ThrottlingMethod": "Auto",
                            # "TimeZone": timeZone,
                            "OverrideDeliveryCap": "true"
                        }
                    }
        }}
        for listId in list_id_list:
            data["ApiRequest"]["Data"]["Recipients"]["SubscriberLists"]["SubscriberList"].append(listId)
        if content_from_url:
            data["ApiRequest"]["Data"]["Content"].update({"ContentFromUrl": {"Url": content_from_url}})
        if delivery_date:
            data["ApiRequest"]["Data"]["DeliverySettings"].update({"DeliveryDate": delivery_date.replace(" ", "T")})
        try:
            xml_data = self.jsontoxml(data)
            xml_data = xml_data.format("<![CDATA[{}]]>".format(html))
            result = requests.post(url, xml_data.encode('utf-8'), headers=self.headers)
            return self.retrun_result("create and send newsletter", result)
        except Exception as e:
            return {"code": -1, "msg": str(e), "data": ""}

    def pause_or_resume_newsletter(self, action, email_id):
        """所有状态为 “InProgress” （进行中）的Newsletter都可以被暂停. 只有状态为 “Paused” （暂停）的Newsletters 可以被继续.
        接口Url：http://sms.expertsender.cn/api/v2/methods/email-messages/pause-or-resume-newsletter/
        :param action: PauseMessage 或者 ResumeMessage
        :param email_id: 邮件ID
        """
        url = f"{self.host}Api/Newsletters/{email_id}"
        data = {"ApiRequest": {
            "ApiKey": self.api_key,
            "Action": action}}
        try:
            result = requests.post(url, self.jsontoxml(data), headers=self.headers)
            return self.retrun_result("pause or resume newsletter", result)
        except Exception as e:
            return {"code": -1, "msg": str(e), "data": ""}

    def create_subscribers_list(self, name, is_seed_list=False):
        """
        创建收件人列表http://sms.expertsender.cn/api/v2/methods/create-subscribers-list/
        :param name: 列表名称
        :param is_seed_list: 标记说明创建列表是收件人列表还是测试列表. 选填. 默认值是“false”（收件人列表）
        :return: 列表ID
        """
        url = f"{self.host}Api/Lists"
        data = {"ApiRequest": {
            "ApiKey": self.api_key,
            "Data": {
                "GeneralSettings": {
                    "Name": name,
                    "isSeedList": str(is_seed_list).lower()
                },
        }}}
        try:
            result = requests.post(url, self.jsontoxml(data), headers=self.headers)
            return self.retrun_result("create subscribers list", result)
        except Exception as e:
            return {"code": -1, "msg": str(e), "data": ""}

    def get_subscriber_lists(self, seed_lists=False):
        """
        获取收件人列表http://sms.expertsender.cn/api/v2/methods/get-subscriber-lists/
        :param seed_lists: 如设为 ‘true’, 只有测试列表会被返回. 如果设为 ‘false’, 只有收件人列表会被返回.
        :return:
        """
        url = f"{self.host}Api/Lists?apiKey={self.api_key}&seedLists={seed_lists}"
        try:
            result = requests.get(url)
            return self.retrun_result("get subscriber lists", result)
        except Exception as e:
            return {"code": -1, "msg": str(e), "data": ""}

    def get_list_or_segment_data(self, query_id, types="List"):
        """
        通过listId或者segmentId获取其下email
        http://sms.expertsender.cn/api/v2/methods/start-a-new-export/
        :param query_id:
        :param types:
        :return:a csv file
        """
        url = f"{self.host}Api/Exports"
        data = {"ApiRequest": {
            "ApiKey": self.api_key,
            "Data": {
                "Type": types,
                "Fields": {"Field": ["Email"]}}}
            }

        if types == "List":
            data["ApiRequest"]["Data"].update({"ListId": query_id})
        elif types == "Segment":
            data["ApiRequest"]["Data"].update({"SegmentId": query_id})
        else:
            return {"code": -1, "msg": "types input error, select 'List' or 'Segment'", "data": ""}
        try:
            result = requests.post(url, self.jsontoxml(data), headers=self.headers)
            return self.retrun_result("add subscriber", result)
        except Exception as e:
            return {"code": -1, "msg": str(e), "data": ""}

    def add_subscriber(self, list_id, email_list):
        """
        添加收件人http://sms.expertsender.cn/api/v2/methods/subscribers/add-subscriber/
        :param list_id: 收件人列表ID
        :param email_list: 需要添加的email列表, 每次API调用最多不能超过100个收件人
        :return: invalid_email为未添加成功的邮箱地址列表
        """
        url = f"{self.host}Api/Subscribers"
        data = {"ApiRequest": {
            "ApiKey": self.api_key,
            "ReturnData": "true",
            "VerboseErrors": "true",
             "MultiData": {"Subscriber": []}}}
        invalid_email = []
        for email in email_list:
            try:
                email.encode('latin-1')
            except Exception as e:
                invalid_email.append(email)
                logger.warning("add this email exception: %s" % str(e))
                continue
            data["ApiRequest"]["MultiData"]["Subscriber"].append(
                {
                    "Mode": "AddAndUpdate",
                    "ListId": list_id,
                    "Email": email,
                }
            )
        try:
            result = requests.post(url, self.jsontoxml(data), headers=self.headers)
            # 解析结果
            if str(result.status_code).startswith('2'):
                logger.info("add subscriber success!")
                return {"code": 1, "msg": "", "data": self.xmltojson(result.text, "Data"), "invalid_email": invalid_email}
            else:

                msg = self.xmltojson(result.text, "ErrorMessage")
                try:
                    error_msg_list = msg["Messages"].get("Message")
                except:
                    error_msg_list = msg.get("Message")
                if "@for" not in str(error_msg_list):
                    logger.info("add subscriber failed! The reason is %s" % error_msg_list)
                    return {"code": 2, "msg": error_msg_list, "data": "", "invalid_email": invalid_email}
                else:
                    error_msg = ""
                    if isinstance(error_msg_list, list):
                        for error_email in error_msg_list:
                            invalid_email.append(error_email.get("@for"))
                            error_msg += " ".join(error_email.values()) + "; "
                    elif isinstance(error_msg_list, dict):
                        invalid_email.append(error_msg_list.get("@for"))
                        error_msg = " ".join(error_msg_list.values())
                    logger.info("add subscriber partial success! The reason is %s" % error_msg)
                    return {"code": 3, "msg": error_msg, "data": "", "invalid_email": invalid_email}
        except Exception as e:
            return {"code": -1, "msg": str(e), "data": ""}

    def delete_subscriber(self, email, list_id=None):
        """
        删除收件人http://sms.expertsender.cn/api/v2/methods/subscribers/delete-subscriber/
        :param list_id: 指定列表ID,若未指定，则针对所有列表删除
        :param email: email 地址
        :return:
        """
        if list_id:
            url = f"{self.host}Api/Subscribers?apiKey={self.api_key}&email={email}&listId={list_id}"
        else:
            url = f"{self.host}Api/Subscribers?apiKey={self.api_key}&email={email}"
        try:
            result = requests.delete(url)
            return self.retrun_result("delete subscriber", result)
        except Exception as e:
            return {"code": -1, "msg": str(e), "data": ""}


    def get_subscriber_activity(self, types, date=datetime.datetime.today().date()):
        """
        获取收件人行为记录http://sms.expertsender.cn/api/v2/methods/subscribers/get-subscriber-activity/
        :param types: Subscriptions, Confirmations, Sends, Opens, Clicks, Complaints, Removals, Bounces,Goals
        :param date: 默认为今天
        :return: csv文件
        """
        url = f"{self.host}Api/Activities?apiKey={self.api_key}&date={date}&type={types}"
        try:
            result = requests.get(url)
            return result.text.split("\r\n")
            # return result.text
        except Exception as e:
            return {"code": -1, "msg": str(e), "data": ""}

    def get_subscriber_statistics(self, list_id):
        """
        获取列表统计数据http://sms.expertsender.cn/api/v2/methods/email-statistics/get-subscriber-statistics/
        :param list_id: 收件人列表ID
        :return:{'SubscriberStatistics': {'SubscriberStatistic': {'IsSummaryRow': 'true', 'ListSize': '1', 'Growth': '1', 'Added': '1', 'AddedUi': '1', 'AddedImport': '0', 'AddedApi': '0', 'AddedWeb': '0', 'Removed': '0', 'RemovedOptOut': '0', 'RemovedUser': '0', 'RemovedBounceLimit': '0', 'RemovedSpam': '0', 'RemovedUserUnknown': '0', 'RemovedBlacklist': '0', 'RemovedApi': '0', 'RemovedImport': '0'}}}
        """
        url = f"{self.host}Api/SubscriberStatistics?apiKey={self.api_key}&scope=List&scopeValue={list_id}"
        try:
            result = requests.get(url)
            return self.retrun_result("get subscriber statistics", result)
        except Exception as e:
            return {"code": -1, "msg": str(e), "data": ""}

    def get_subscriber_information(self, email):
        """
        获取收件人信息http://sms.expertsender.cn/api/v2/methods/subscribers/get-subscriber-information/
        :param email: 邮件地址
        :return:
        """
        url = f"{self.host}Api/Subscribers?apiKey={self.api_key}&email={email}&option=EventsHistory"
        try:
            result = requests.get(url)
            return self.retrun_result("get subscriber statistics", result)
        except Exception as e:
            return {"code": -1, "msg": str(e), "data": ""}

    def get_summary_statistics(self, query_id, types="List"):
        """
        获取细分组信息/列表组信息
        接口Url：http://sms.expertsender.cn/api/v2/methods/sms-mms-statistics/get-summary-statistics/
        :param query_id:细分ID或者列表ID
        :param types:查询类型 "List" or "Segment"
        :return:
        """
        url = f"{self.host}Api/SummaryStatistics?apiKey={self.api_key}&scope={types}&scopeValue={query_id}"
        try:
            result = requests.get(url)
            return self.retrun_result("get summary statistics", result)
        except Exception as e:
            return {"code": -1, "msg": str(e), "data": ""}

    def get_subscriber_segments(self):
        """
        获取所有细分组http://sms.expertsender.cn/api/v2/methods/subscribers/get-subscriber-segments/
        """
        url = f"{self.host}Api/Segments?apiKey={self.api_key}"
        try:
            result = requests.get(url)
            return self.retrun_result("get summary statistics", result)
        except Exception as e:
            return {"code": -1, "msg": str(e), "data": ""}

    def create_transactional_message(self, subject, plain="", html="", content_from_url=None):
        """
        创建事务性邮件 http://sms.expertsender.cn/api/v2/methods/email-messages/create-transactional-message/
        :param subject: 邮件主题
        :param plain: 邮件纯文本
        :param html: 邮件html内容
        :param content_from_url: 邮件资源地址，如都有取其后
        :return: 事务邮件ID
        """
        url = f"{self.host}Api/TransactionalsCreate"
        data = {"ApiRequest": {
            "ApiKey": self.api_key,
            "Data": {
                "Content": {
                    "FromName": self.from_name,
                    "FromEmail": self.from_email,
                    "Subject": subject,
                    "Plain": plain,
                    "Html": "%s",
                },
            }
        }}
        if content_from_url:
            data["ApiRequest"]["Data"]["Content"].update({"ContentFromUrl": {"Url": content_from_url}})
        try:
            xml_data = self.jsontoxml(data)
            xml_data = xml_data % ("<![CDATA[%s]]>" % html)
            result = requests.post(url, xml_data.encode('utf-8'), headers=self.headers)
            return self.retrun_result("create transactional message", result)
        except Exception as e:
            return {"code": -1, "msg": str(e), "data": ""}

    def send_transactional_messages(self, email_id, to_email, list_id, snippets=None):
        """
        发送事务性邮件 http://sms.expertsender.cn/api/v2/methods/email-messages/send-transactional-messages/
        :param email_id: 事务邮件ID
        :param to_email: 收件人，一次只能发送一个
        :return:
        """
        url = f"{self.host}Api/Transactionals/{email_id}"
        data = {"ApiRequest": {
            "ApiKey": self.api_key,
            "Data": {
                "Receiver": {"Email": to_email,"ListId": list_id}}
            }}
        cart_products, top_products = "", ""
        if snippets and isinstance(snippets, list):
            data["ApiRequest"]["Data"]["Snippets"] = {"Snippet": []}
            for snippet in snippets:
                if snippet["name"] == "cart_products":
                    cart_products = snippet["value"]
                    snippet["value"] = "{cart_products}"
                if snippet["name"] == "top_products":
                    top_products = snippet["value"]
                    snippet["value"] = "{top_products}"
                data["ApiRequest"]["Data"]["Snippets"]["Snippet"].append({"Name": snippet["name"], "Value": snippet["value"]})
        try:
            data = self.jsontoxml(data)
            if "{cart_products}" in data and "{top_products}" in data:
                data = data.format(cart_products="<![CDATA[%s]]>" % cart_products, top_products="<![CDATA[%s]]>" % top_products)
            elif "{cart_products}" in data:
                data = data.format(cart_products="<![CDATA[%s]]>" % cart_products)
            elif "{top_products}" in data:
                data = data.format(top_products="<![CDATA[%s]]>" % top_products)
            result = requests.post(url, data.encode('utf-8'), headers=self.headers)
            return self.retrun_result("send transactional messages", result)
        except Exception as e:
            return {"code": -1, "msg": str(e), "data": ""}

    def update_transactional_message(self, email_id, subject, plain="", html="", content_from_url=None):
        """
        更新事务性邮件 http://sms.expertsender.cn/api/v2/methods/email-messages/update-transactional-message/
        :param email_id: 事务邮件ID
        :param subject: 邮件主题
        :param plain: 邮件纯文本
        :param html: 邮件html内容
        :param content_from_url: 邮件资源链接地址
        :return: None
        """
        url = f"{self.host}Api/TransactionalsUpdate/{email_id}"
        data = {"ApiRequest": {
            "ApiKey": self.api_key,
            "Data": {
                "Content": {
                    "FromName": self.from_name,
                    "FromEmail": self.from_email,
                    "Subject": subject,
                    "Plain": plain,
                    "Html": "%s",
                },
            }
        }}
        if content_from_url:
            data["ApiRequest"]["Data"]["Content"].update({"ContentFromUrl": {"Url": content_from_url}})
        try:
            xml_data = self.jsontoxml(data)
            xml_data = xml_data % ("<![CDATA[%s]]>" % html)
            result = requests.put(url, xml_data.encode('utf-8'), headers=self.headers)
            return self.retrun_result("update transactional message", result)
        except Exception as e:
            return {"code": -1, "msg": str(e), "data": ""}

    def delete_message(self, email_id):
        """
        移动邮件到已删除, 如果邮件正在发送中，则将被自动取消.
        http://sms.expertsender.cn/api/v2/methods/email-messages/delete-message/
        :param email_id: 邮件ID
        :return:
        """
        url = f"{self.host}Api/Messages/{email_id}?apiKey={self.api_key}"
        try:
            result = requests.delete(url)
            return self.retrun_result("delete message", result)
        except Exception as e:
            return {"code": -1, "msg": str(e), "data": ""}

    def get_opt_out_link_subscribers(self, list_ids=None, start_date=None, end_date=None, remove_types="OptOutLink"):
        """
        获取点击过邮件中的退订链接的收件人, 退订的用户已经从当前的收件人列表中删除
        http://sms.expertsender.cn/api/v2/methods/subscribers/get-removed-subscribers/
        :param list_ids: 列表标识ID. 选填.可以指定多个列表ID, 用逗号隔开, 如: 12,34,56,789
        :param start_date: 起始日期. 选填. 格式YYYY-MM-DD.
        :param end_date: 结束日期. 选填. 格式YYYY-MM-DD.
        :param remove_types:
        :return:{'RemovedSubscriber': {'Id': '217149', 'Email': 'leemon.li@orderplus.com', 'ListId': '25', 'UnsubscribedOn': '2019-07-29T17:07:44.263'}}
        """
        url = f"{self.host}Api/RemovedSubscribers?apiKey={self.api_key}&removeTypes={remove_types}"
        if list_ids:
            url += f"&listIds={list_ids}"
        if start_date:
            url += f"&startDate={start_date}"
        if end_date:
            url += f"&endDate={end_date}"
        try:
            result = requests.get(url)
            return self.retrun_result("get OptOutLink subscribers", result)
        except Exception as e:
            return {"code": -1, "msg": str(e), "data": ""}

    def get_snoozed_subscribers(self, list_ids=None, start_date=None, end_date=None):
        """
        获取点击过邮件中的退订链接【休眠中】的收件人
        http://sms.expertsender.cn/api/v2/methods/subscribers/get-snoozed-subscribers/
        :param list_ids: 列表标识ID. 选填.可以指定多个列表ID, 用逗号隔开, 如: 12,34,56,789
        :param start_date: 起始日期. 选填. 格式YYYY-MM-DD.
        :param end_date: 结束日期. 选填. 格式YYYY-MM-DD.
        :return:{'SnoozedSubscribers': {'SnoozedSubscriber': {'Email': 'twobercancan@126.com', 'ListId': '25', 'SnoozedUntil': '2019-08-05T17:22:35.407'}}}
        """
        url = f"{self.host}Api/SnoozedSubscribers?apiKey={self.api_key}"
        if list_ids:
            url += f"&listIds={list_ids}"
        if start_date:
            url += f"&startDate={start_date}"
        if end_date:
            url += f"&endDate={end_date}"
        try:
            result = requests.get(url)
            return self.retrun_result("get OptOutLink subscribers", result)
        except Exception as e:
            return {"code": -1, "msg": str(e), "data": ""}


if __name__ == '__main__':
    html_b = """<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no"><title>jquery</title><style>a:hover{text-decoration: underline!important; }.hide{display:none!important;}.bannerText{border:0px!important;}</style></head><body><div style="width:880px;margin:0 auto;"><div class="showBox" style="overflow-wrap: break-word; text-align: center; font-size: 14px; width: 100%; margin: 0px auto;"><div style="width: 100%; padding: 20px 0px;"><div style="font-size: 30px; border: 1px solid rgb(221, 221, 221); font-weight: 900; padding: 12px 0px; width: 30%; margin: 0px auto;">YOUR LOGO</div></div><div style="width: 100%; padding-bottom: 20px; position: relative; overflow: hidden;"><div class="bannerText" style="position: absolute; left: 180px; top: 147px; text-align: left; width: 400px; line-height: 30px; font-size: 17px; color: rgb(0, 0, 0); border: 2px dashed rgb(204, 204, 204);"><div></div><div>we really miss you, please enjoy this specially customized 20% coupon. Happy shopping day! </div><div></div><div></div></div><div style="width: 100%;"><img src="https://smartsend.seamarketings.com/media/29/io8w9r7gcnx34fd.jpg" style="width: 100%;"></div></div><!----><!----><div class="" style="width: 100%; padding-bottom: 20px; font-size: 20px; font-weight: 800;">
                                Product Title
                        </div><div style="width: 856px; padding: 20px 12px;">
                            <div style="width:46%;margin:10px;display:inline-block;vertical-align: top;"><a href="https://www.charrcter.com/products/womens-v-neck-lace-fringe-dress?utm_source=smartsend&utm_medium=Newsletter&utm_campaign=test001-six day no buy&utm_term=1280400293935_216"><img src="https://cdn.shopify.com/s/files/1/0062/9106/2831/products/3448384_672c5fe89e_0a032732-313b-4ba3-8a41-f5062375f28d.jpg?v=1562581258" style="width:100%;"/></a><h3 style="font-weight:700;white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 14px;">Women's V-Neck Lace Fringe Dress</h3></div><div style="width:46%;margin:10px;display:inline-block;vertical-align: top;"><a href="https://www.charrcter.com/products/5fb51d2696d7?utm_source=smartsend&utm_medium=Newsletter&utm_campaign=test001-six day no buy&utm_term=2173743431734_216"><img src="https://cdn.shopify.com/s/files/1/0152/7218/1814/products/3239958_5522f421c0.jpg?v=1560926774" style="width:100%;"/></a><h3 style="font-weight:700;white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 14px;">Topshe Krawattehalsband Feder</h3></div><div style="width:46%;margin:10px;display:inline-block;vertical-align: top;"><a href="https://www.charrcter.com/products/6ebc7a65768c?utm_source=smartsend&utm_medium=Newsletter&utm_campaign=test001-six day no buy&utm_term=2173760176182_216"><img src="https://cdn.shopify.com/s/files/1/0152/7218/1814/products/3273500_3ca3e8baca.jpg?v=1560928063" style="width:100%;"/></a><h3 style="font-weight:700;white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 14px;">Topshe V Lockere Passform Drucken</h3></div><div style="width:46%;margin:10px;display:inline-block;vertical-align: top;"><a href="https://www.charrcter.com/products/casual-printed-round-neck-short-sleeve-shirt?utm_source=smartsend&utm_medium=Newsletter&utm_campaign=test001-six day no buy&utm_term=3631119302761_216"><img src="https://cdn.shopify.com/s/files/1/0250/5818/1225/products/3488953_c85ee5eb1b.jpg?v=1563764695" style="width:100%;"/></a><h3 style="font-weight:700;white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 14px;">Casual Printed Round Neck Short Sleeve Shirt</h3></div>
                        </div><div style="width: calc(100% - 24px); padding: 20px 12px; text-align: center;">
                        @2006-2019 <a href="https://www.charrcter.com?utm_source=smartsend&utm_medium=Newsletter&utm_campaign=test001-six day no buy&utm_term=216" target="_blank">www.charrcter.com</a>  Copyright,All Rights Reserved
                    </div><div style="width: calc(100% - 24px); padding: 20px 12px; text-align: center;"><a href="*[link_unsubscribe]*" target="_blank" style="text-decoration: none; cursor: pointer; color: rgb(254, 34, 46); padding: 0px 10px; border-right: 2px solid rgb(204, 204, 204); font-size: 24px;">UNSUBSCRIBE</a><a href="https://www.charrcter.com/pages/faq?utm_source=smartsend&utm_medium=Newsletter&utm_campaign=test001-six day no buy&utm_term=216" target="_blank" style="text-decoration: none; cursor: pointer; color: rgb(254, 34, 46); padding: 0px 10px; border-right: 2px solid rgb(204, 204, 204); font-size: 24px;">HELP CENTER</a><a href="https://www.charrcter.com/pages/privacy-policy?utm_source=smartsend&utm_medium=Newsletter&utm_campaign=test001-six day no buy&utm_term=216" target="_blank" style="text-decoration: none; cursor: pointer; color: rgb(254, 34, 46); padding: 0px 10px; border-right: 2px solid rgb(204, 204, 204); font-size: 24px;">PRIVACY POLICY</a><a href="https://www.charrcter.com/pages/about-us?utm_source=smartsend&utm_medium=Newsletter&utm_campaign=test001-six day no buy&utm_term=216" target="_blank" style="text-decoration: none; cursor: pointer; color: rgb(254, 34, 46); padding: 0px 10px; font-size: 24px;">ABOUT US</a></div><div style="width: calc(100% - 24px); padding: 20px 12px; text-align: center;">
                        This email was sent a notification-only address that cannot accept incoming email PLEASE
                        DO NOT REPLY to this message. if you have any questions or concerns.please email us:neal.zhang@orderplus.com
                    </div></div></div></body></html>"""
    ems = ExpertSender("Leemon", "leemon.li@orderplus.com")
    # print(ems.get_message_statistics(372))
    # print(ems.get_messages(348))
    # print(ems.create_subscribers_list("Test001"))
    print(ems.add_subscriber(25, ['suzanne@gmail.com', 'g_bozzolo@libero.it', 'felicia@flochildrenswear.com.au']))
    # html = open("index.html")
    # print(ems.create_and_send_newsletter([86], "取消订阅完测试", html="<a href='https://baidu.com'>Unsubscribe</a>")) # ,"2019-07-09 21:09:00"
    # print(ems.get_subscriber_activity("Opens"))
    # print(ems.get_subscriber_information("twobercancan@126.com"))
    # print(ems.get_subscriber_activity())
    # print(ems.get_summary_statistics(63))
    # print(ems.get_server_time())
    # print(ems.get_message_statistics(349))
    # print(ems.create_and_send_newsletter([26], "two listID", html=html_b)) # ,"2019-07-09 21:09:00"
    # print(ems.get_messages(349))
    # print(ems.get_subscriber_lists())
    # print(ems.create_subscribers_list("Test001"))
    # print(ems.get_subscriber_activity("Opens", "2019-07-15"))
    # print(ems.get_subscriber_information("twobercancan@126.com"))
    # print(ems.get_subscriber_activity())
    # print(ems.get_summary_statistics(63))
    # print(ems.delete_subscriber("leemon.li@orderplus.com", 26))
    # print(ems.get_list_or_segment_data(29))  # 11
    # print(ems.get_export_progress(11))  # 11
    # print(ems.clear_subscriber(25, ""))  # 11
    # print(ems.add_subscriber(86, ["leemon.li@orderplus.com"]))
    # print(ems.create_transactional_message("snippet transactiona message test1", html="<a href='www.baidu.com'>*[tr_snippetname]*</a>"))  # 462
    # print(ems.send_transactional_messages(462, "leemon.li@orderplus.com", 25, [{"name": "href", "value": "https://www.baidu.com"}, {"name": "linkname", "value": "<p style='color:red'>百度百度</p>"}]))  # 350
    # print(ems.send_transactional_messages(461, "leemon.li@orderplus.com", 25, [{"name": "ShopName", "value": "aaaaa"},{"name": "Firstname", "value": "bbbbb"},{"name": "CartProducts", "value": "<tr></tr>"},{"name": "AbandonedCheckoutUrl", "value": "dddddd"}]))  # 350
    # print(ems.update_transactional_message(461, "update template test 10", html="""Dear *[tr_firstname]* <a href="*[tr_abandoned_checkout_url]*">welcome to *[tr_shop_name]*</a>product--- *[tr_cart_products]*"""))  # 350
    # print(ems.delete_message(349))
    # print(ems.get_opt_out_link_subscribers())
    # print(ems.get_snoozed_subscribers(86))

