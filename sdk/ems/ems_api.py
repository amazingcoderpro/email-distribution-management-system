# -*- coding: utf-8 -*-
# Created by: Leemon7
# Created on: 2019/7/8
import datetime
import json
import re

import xmltodict
from config import logger
import requests


class ExpertSender:
    def __init__(self, apiKey, fromName, fromEmail):
        self.api_key = apiKey
        self.host = "https://api6.esv2.com/v2/"
        self.headers = {"Content-Type": "text/xml"}
        self.from_name = fromName
        self.from_email = fromEmail

    @staticmethod
    def xmltojson(xmlstr, type):
        # parse是的xml解析器
        if not xmlstr.strip():
            return {}
        xmlparse = xmltodict.parse(xmlstr)
        jsonstr = json.dumps(xmlparse, indent=1)
        return json.loads(jsonstr)["ApiResponse"].get(type)

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

    def get_messages(self, emailID=None):
        """获取已发送邮件列表
        接口Url：http://sms.expertsender.cn/api/v2/methods/email-messages/get-messages-list/
        """
        if emailID:
            url = f"{self.host}Api/Messages/{emailID}?apiKey={self.api_key}"
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

    def get_message_statistics(self, emailID, startDate="1970-01-01", endDate=datetime.datetime.today().date()):
        """
        获取邮件统计数据
        接口Url：http://sms.expertsender.cn/api/v2/methods/email-statistics/get-message-statistics/
        :param emailID: 邮件ID
        :param startDate: 查询开始时间，默认为时间元年
        :param endDate: 查询结束时间，默认为今天
        :return: {'Sent': '61644', 'Bounced': '145', 'Delivered': '61499', 'Opens': '1754', 'UniqueOpens': '1190', 'Clicks': '224', 'UniqueClicks': '205', 'Clickers': '111', 'Complaints': '11', 'Unsubscribes': '159'}
        """
        url = f"{self.host}Api/MessageStatistics/{emailID}?apiKey={self.api_key}&startDate={startDate}&endDate={endDate}"
        try:
            result = requests.get(url)
            return self.retrun_result("get message statistics", result)
        except Exception as e:
            return {"code": -1, "msg": str(e), "data": ""}

    def create_and_send_newsletter(self, listId_list, subject, contentFromUrl=None, plain="", html="", deliveryDate=None, timeZone="UTC"):
        """
        创建及发送Newsletter, 注：如多个listId中存在同样的邮件，只会发一封邮件
        接口Url：http://sms.expertsender.cn/api/v2/methods/email-messages/create-and-send-newsletter/
        :param listId_list: 发送列表ID组成的列表
        :param subject: 邮件主题
        :param plain: 邮件纯文本
        :param html: html格式邮件内容
        :param contentFromUrl: 外源下载时使用的Url
        :param deliveryDate: 指定发送日期，默认为及时发送
        :return: 邮件ID
        """
        url = f"{self.host}Api/Newsletters"
        data = {"ApiRequest": {
                    "ApiKey": self.api_key,
                    "Data": {
                        "Recipients": {"SubscriberLists": {"SubscriberList": []}},
                        "Content": {
                            "FromEmail": self.from_email,
                            "Subject": subject,
                            "Plain": plain,
                            "Html": "%s",
                        },
                        "DeliverySettings": {
                            "ThrottlingMethod": "Auto",
                            # "TimeZone": timeZone,
                            "OverrideDeliveryCap": "true"
                        }
                    }
        }}
        for listId in listId_list:
            data["ApiRequest"]["Data"]["Recipients"]["SubscriberLists"]["SubscriberList"].append(listId)
        if contentFromUrl:
            data["ApiRequest"]["Data"]["Content"].update({"ContentFromUrl": contentFromUrl})
        if deliveryDate:
            data["ApiRequest"]["Data"]["DeliverySettings"].update({"DeliveryDate": deliveryDate.replace(" ", "T")})
        try:
            xml_data = self.jsontoxml(data)
            xml_data = xml_data % ("<![CDATA[%s]]>" % html)
            result = requests.post(url, xml_data, headers=self.headers)
            return self.retrun_result("create and send newsletter", result)
        except Exception as e:
            return {"code": -1, "msg": str(e), "data": ""}

    def pause_or_resume_newsletter(self, action, emailId):
        """所有状态为 “InProgress” （进行中）的Newsletter都可以被暂停. 只有状态为 “Paused” （暂停）的Newsletters 可以被继续.
        接口Url：http://sms.expertsender.cn/api/v2/methods/email-messages/pause-or-resume-newsletter/
        :param action: PauseMessage 或者 ResumeMessage
        :param emailId: 邮件ID
        """
        url = f"{self.host}Api/Newsletters/{emailId}"
        data = {"ApiRequest": {
            "ApiKey": self.api_key,
            "Action": action}}
        try:
            result = requests.post(url, self.jsontoxml(data), headers=self.headers)
            return self.retrun_result("pause or resume newsletter", result)
        except Exception as e:
            return {"code": -1, "msg": str(e), "data": ""}

    def create_subscribers_list(self, name, isSeedList=False):
        """
        创建收件人列表http://sms.expertsender.cn/api/v2/methods/create-subscribers-list/
        :param name: 列表名称
        :param isSeedList: 标记说明创建列表是收件人列表还是测试列表. 选填. 默认值是“false”（收件人列表）
        :return: 列表ID
        """
        url = f"{self.host}Api/Lists"
        data = {"ApiRequest": {
            "ApiKey": self.api_key,
            "Data": {
                "GeneralSettings": {
                    "Name": name,
                    "isSeedList": str(isSeedList).lower()
                },
        }}}
        try:
            result = requests.post(url, self.jsontoxml(data), headers=self.headers)
            return self.retrun_result("create subscribers list", result)
        except Exception as e:
            return {"code": -1, "msg": str(e), "data": ""}

    def get_subscriber_lists(self, seedLists=False):
        """
        获取收件人列表http://sms.expertsender.cn/api/v2/methods/get-subscriber-lists/
        :param seedLists: 如设为 ‘true’, 只有测试列表会被返回. 如果设为 ‘false’, 只有收件人列表会被返回.
        :return:
        """
        url = f"{self.host}Api/Lists?apiKey={self.api_key}&seedLists={seedLists}"
        try:
            result = requests.get(url)
            return self.retrun_result("get subscriber lists", result)
        except Exception as e:
            return {"code": -1, "msg": str(e), "data": ""}

    def get_list_or_segment_data(self, queryId, types="List"):
        """
        通过listId或者segmentId获取其下email
        http://sms.expertsender.cn/api/v2/methods/start-a-new-export/
        :param queryId:
        :param types:
        :return:
        """
        url = f"{self.host}Api/Exports"
        data = {"ApiRequest": {
            "ApiKey": self.api_key,
            "Data": {
                "Type": types,
                "Fields": {"Field": ["Email"]}}}
            }

        if types == "List":
            data["ApiRequest"]["Data"].update({"ListId": queryId})
        elif types == "Segment":
            data["ApiRequest"]["Data"].update({"SegmentId": queryId})
        else:
            return {"code": -1, "msg": "types input error, select 'List' or 'Segment'", "data": ""}
        try:
            result = requests.post(url, self.jsontoxml(data), headers=self.headers)
            return self.retrun_result("add subscriber", result)
        except Exception as e:
            return {"code": -1, "msg": str(e), "data": ""}

    def get_export_progress(self, exportId):
        """
        获取数据导出进度http://sms.expertsender.cn/api/v2/methods/get-export-progress/
        :param exportId: 导出任务ID
        :return:
        """
        url = f"{self.host}Api/Exports/{exportId}?apiKey={self.api_key}"
        try:
            result = requests.get(url)
            result = self.retrun_result("get export progress", result)
            if result["code"] != 1 or result["data"]["Status"]!="Completed":
                result["code"] = 2
            return result
        except Exception as e:
            return {"code": -1, "msg": str(e), "data": ""}

    def add_subscriber(self, listId, emailList):
        """
        添加收件人http://sms.expertsender.cn/api/v2/methods/subscribers/add-subscriber/
        :param listId: 收件人列表ID
        :param emailList: 需要添加的email列表
        :return:
        """
        url = f"{self.host}Api/Subscribers"
        data = {"ApiRequest": {
            "ApiKey": self.api_key,
            "ReturnData": "true",
             "MultiData": {"Subscriber": []}}}
        for email in emailList:
            data["ApiRequest"]["MultiData"]["Subscriber"].append(
                {
                    "Mode": "AddAndUpdate",
                    "ListId": listId,
                    "Email": email,
                }
            )
        try:
            result = requests.post(url, self.jsontoxml(data), headers=self.headers)
            return self.retrun_result("add subscriber", result)
        except Exception as e:
            return {"code": -1, "msg": str(e), "data": ""}

    def delete_subscriber(self, email, listId=None):
        """
        删除收件人http://sms.expertsender.cn/api/v2/methods/subscribers/delete-subscriber/
        :param listId: 指定列表ID,若未指定，则针对所有列表删除
        :param email: email 地址
        :return:
        """
        if listId:
            url = f"{self.host}Api/Subscribers?apiKey={self.api_key}&email={email}&listId={listId}"
        else:
            url = f"{self.host}Api/Subscribers?apiKey={self.api_key}&email={email}"
        try:
            result = requests.delete(url)
            return self.retrun_result("delete subscriber", result)
        except Exception as e:
            return {"code": -1, "msg": str(e), "data": ""}

    def clear_subscriber(self, listId, csvUrl):
        """
        清空收件人列表所有收件人http://sms.expertsender.cn/api/v2/methods/imports/import-subscribers-to-list/
        """
        url = f"{self.host}Api/ImportToListTasks"
        data = {"ApiRequest": {
            "ApiKey": self.api_key,
            "Data": {
                "Source": {"Url": csvUrl},
                "Target": {"Name": "clear subscriber", "SubscriberList": listId},
                "ImportSetup": {"Mode": "Synchronize"}}
            }}
        try:
            result = requests.post(url, self.jsontoxml(data), headers=self.headers)
            return self.retrun_result("clear subscriber", result)
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

    def get_subscriber_statistics(self, listId):
        """
        获取列表统计数据http://sms.expertsender.cn/api/v2/methods/email-statistics/get-subscriber-statistics/
        :param listId: 收件人列表ID
        :return:{'SubscriberStatistics': {'SubscriberStatistic': {'IsSummaryRow': 'true', 'ListSize': '1', 'Growth': '1', 'Added': '1', 'AddedUi': '1', 'AddedImport': '0', 'AddedApi': '0', 'AddedWeb': '0', 'Removed': '0', 'RemovedOptOut': '0', 'RemovedUser': '0', 'RemovedBounceLimit': '0', 'RemovedSpam': '0', 'RemovedUserUnknown': '0', 'RemovedBlacklist': '0', 'RemovedApi': '0', 'RemovedImport': '0'}}}
        """
        url = f"{self.host}Api/SubscriberStatistics?apiKey={self.api_key}&scope=List&scopeValue={listId}"
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

    def get_summary_statistics(self, queryId, types="List"):
        """
        获取细分组信息/列表组信息
        接口Url：http://sms.expertsender.cn/api/v2/methods/sms-mms-statistics/get-summary-statistics/
        :param queryId:细分ID或者列表ID
        :param types:查询类型 "List" or "Segment"
        :return:
        """
        url = f"{self.host}Api/SummaryStatistics?apiKey={self.api_key}&scope={types}&scopeValue={queryId}"
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

    def create_transactional_message(self, subject, plain="", html="", contentFromUrl=None):
        """
        创建事务性邮件 http://sms.expertsender.cn/api/v2/methods/email-messages/create-transactional-message/
        :param subject: 邮件主题
        :param plain: 邮件纯文本
        :param html: 邮件html内容
        :param contentFromUrl: 邮件资源地址，如都有取其后
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
        if contentFromUrl:
            data["ApiRequest"]["Data"]["Content"].update({"ContentFromUrl": {"Url": contentFromUrl}})
        try:
            xml_data = self.jsontoxml(data)
            xml_data = xml_data % ("<![CDATA[%s]]>" % html)
            result = requests.post(url, xml_data, headers=self.headers)
            return self.retrun_result("create transactional message", result)
        except Exception as e:
            return {"code": -1, "msg": str(e), "data": ""}

    def send_transactional_messages(self, emailId, toEmail):
        """
        发送事务性邮件 http://sms.expertsender.cn/api/v2/methods/email-messages/send-transactional-messages/
        :param emailId: 事务邮件ID
        :param toEmail: 收件人，一次只能发送一个
        :return:
        """
        url = f"{self.host}Api/Transactionals/{emailId}"
        data = {"ApiRequest": {
            "ApiKey": self.api_key,
            "Data": {
                "Receiver": {"Email": toEmail}}
            }}
        try:
            result = requests.post(url, self.jsontoxml(data), headers=self.headers)
            return self.retrun_result("send transactional messages", result)
        except Exception as e:
            return {"code": -1, "msg": str(e), "data": ""}

    def update_transactional_message(self, emailId, fromName, fromEmail, subject, plain="", html="", contentFromUrl=None):
        """
        更新事务性邮件 http://sms.expertsender.cn/api/v2/methods/email-messages/update-transactional-message/
        :param emailId: 事务邮件ID
        :param fromName: 发件人姓名
        :param fromEmail: 发件人邮箱
        :param subject: 邮件主题
        :param plain: 邮件纯文本
        :param html: 邮件html内容
        :param contentFromUrl: 邮件资源链接地址
        :return: None
        """
        url = f"{self.host}Api/TransactionalsUpdate/{emailId}"
        data = {"ApiRequest": {
            "ApiKey": self.api_key,
            "Data": {
                "Content": {
                    "FromName": fromName,
                    "FromEmail": fromEmail,
                    "Subject": subject,
                    "Plain": plain,
                    "Html": "%s",
                },
            }
        }}
        if contentFromUrl:
            data["ApiRequest"]["Data"]["Content"].update({"ContentFromUrl": {"Url": contentFromUrl}})
        try:
            xml_data = self.jsontoxml(data)
            xml_data = xml_data % ("<![CDATA[%s]]>" % html)
            result = requests.put(url, xml_data, headers=self.headers)
            return self.retrun_result("update transactional message", result)
        except Exception as e:
            return {"code": -1, "msg": str(e), "data": ""}

    def delete_message(self, emailId):
        """
        移动邮件到已删除, 如果邮件正在发送中，则将被自动取消.
        http://sms.expertsender.cn/api/v2/methods/email-messages/delete-message/
        :param emailId: 邮件ID
        :return:
        """
        url = f"{self.host}Api/Messages/{emailId}?apiKey={self.api_key}"
        try:
            result = requests.delete(url)
            return self.retrun_result("delete message", result)
        except Exception as e:
            return {"code": -1, "msg": str(e), "data": ""}


if __name__ == '__main__':
    html_b = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>jquery</title>

</head>
<body>


<div style="text-align:center;margin:50px 0; font:normal 50px/24px 'MicroSoft YaHei';color:red">
<p>fit browers:360,FireFox,Chrome,Opera.</p>
<p>source:<a href="http://sc.chinaz.com/" target="_blank">ChinaZ</a></p>
<img src="http://f.hiphotos.baidu.com/image/h%3D300/sign=e6821d0a831001e9513c120f880f7b06/a71ea8d3fd1f4134d244519d2b1f95cad0c85ee5.jpg">

</div>
</body>
</html>"""
    ems = ExpertSender("0x53WuKGWlbq2MQlLhLk", "Leemon", "leemon.li@orderplus.com")
    print(ems.get_message_statistics(328))
    # print(ems.get_messages(348))
    # print(ems.create_subscribers_list("Test001"))
    # print(ems.add_subscriber(26, ["twobercancan@126.com", "leemon.li@orderplus.com"]))
    # print(ems.create_and_send_newsletter(25, "HelloWorld","expertsender",html_b)) # ,"2019-07-09 21:09:00"
    # print(ems.get_subscriber_activity("Opens"))
    # print(ems.get_subscriber_information("twobercancan@126.com"))
    # print(ems.get_subscriber_activity())
    # print(ems.get_summary_statistics(63))
    # print(ems.get_server_time())
    # print(ems.get_message_statistics(349))
    # print(ems.create_and_send_newsletter([25,26], "two listID", "expertsender test 2")) # ,"2019-07-09 21:09:00"
    # print(ems.get_messages(349))
    # print(ems.get_subscriber_lists())
    # print(ems.create_subscribers_list("Test001"))
    # print(ems.get_subscriber_activity("Opens", "2019-07-15"))
    # print(ems.get_subscriber_information("twobercancan@126.com"))
    # print(ems.get_subscriber_activity())
    # print(ems.get_summary_statistics(63))
    # print(ems.delete_subscriber("leemon.li@orderplus.com", 26))
    # print(ems.get_list_or_segment_data(25))  # 11
    # print(ems.get_export_progress(11))  # 11
    # print(ems.clear_subscriber(25, ""))  # 11
    # print(ems.add_subscriber(25, ["limengqiAliase@163.com", "leemon.li@orderplus.com"]))
    # print(ems.create_transactional_message("transactional message test", contentFromUrl="http://sources.aopcdn.com/edm/html/buzzyly/20190625/1561447955806.html"))  # 350
    # print(ems.send_transactional_messages(350, "leemon.li@orderplus.com"))  # 350
    # print(ems.update_transactional_message(350, "Aliase", "limengqiAliase@163.com", "transactional message test 11", html=html_b))  # 350
    # print(ems.delete_message(349))

