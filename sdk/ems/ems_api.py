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
    def __init__(self, fromName, fromEmail, apiKey="0x53WuKGWlbq2MQlLhLk"):
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
            data["ApiRequest"]["Data"]["Content"].update({"ContentFromUrl": {"Url": contentFromUrl}})
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
    <title>jquery</title></head>
<body>
<div class="showBox" style="overflow-wrap: break-word; text-align: center; font-size: 14px;">
    <div style="margin: 0px auto; width: 100%; border-bottom: 1px solid rgb(204, 204, 204); padding-bottom: 20px;">
        <div style="margin: 0px auto; width: 30%;"><h2>Subject Line</h2>
            <div>1111</div>
        </div>
    </div>
    <div style="width: 100%; padding-bottom: 20px;">
        <div style="margin: 0px auto; width: 70%; line-height: 20px; padding: 20px 0px;">
            <div style="padding: 10px 0px;">1111</div>
            <div style="padding: 10px 0px;">If you are having trouble viewing this email, please click here.</div>
        </div>
    </div>
    <div style="width: 100%; padding-bottom: 20px;">
        <div style="width: 30%; margin: 0px auto;"><img
                src="data:image/jpeg;base64,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"
                style="width: 100%;"></div>
    </div>
    <div style="width: 100%; padding-bottom: 20px;">
        <div style="width: 100%;"><img
                src="data:image/jpeg;base64,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"
                style="width: 100%;"></div>
    </div>
    <div style="width: 100%; padding-bottom: 20px;">
        <div style="font-size: 28px; font-weight: 700;">1111111111</div>
    </div>
    <div style="width: 100%; padding-bottom: 20px;">
        <div style="font-family: &quot;Segoe UI Emoji&quot;; font-weight: 400; font-style: normal; font-size: 16px;">
            1111111111111
        </div>
    </div>
    <div style="width: calc(100% - 24px); padding: 20px 12px;">
        <div style="width: calc(50% - 24px); margin: 10px; display: inline-block; vertical-align: top; border: 1px solid rgb(204, 204, 204);">
            <img src="https://cdn.shopify.com/s/files/1/0026/8386/3113/products/3239379_fec7b8d74a.jpg?v=1540285396"
                 style="width: 100%;">
            <h3 style="font-weight: 700;">Fashion Round Collar Split Joint Shirt</h3>
            <h3>21.99</h3></div>
        <div style="width: calc(50% - 24px); margin: 10px; display: inline-block; vertical-align: top; border: 1px solid rgb(204, 204, 204);">
            <img src="https://cdn.shopify.com/s/files/1/0026/8386/3113/products/3106049_3.jpg?v=1541469232"
                 style="width: 100%;">
            <h3 style="font-weight: 700;">AEC BQ-618 Smart Wireless Bluetooth Stereo Headphone</h3>
            <h3>36.95</h3></div>
        <div style="width: calc(50% - 24px); margin: 10px; display: inline-block; vertical-align: top; border: 1px solid rgb(204, 204, 204);">
            <img src="https://cdn.shopify.com/s/files/1/0026/8386/3113/products/3251816_1ea6f747ef.jpg?v=1538995144"
                 style="width: 100%;">
            <h3 style="font-weight: 700;">Bluetooth Smart Watch For Android Smartphone With Camera</h3>
            <h3>27.99</h3></div>
        <div style="width: calc(50% - 24px); margin: 10px; display: inline-block; vertical-align: top; border: 1px solid rgb(204, 204, 204);">
            <img src="https://cdn.shopify.com/s/files/1/0026/8386/3113/products/3240986_dd0362926a.jpg?v=1541672865"
                 style="width: 100%;">
            <h3 style="font-weight: 700;">Large Capacity Oxford 18 Inch Laptop Bag USB Charging Port Camouflage Outdoor
                Travel Backpack</h3>
            <h3>28.95</h3></div>
        <div style="width: calc(50% - 24px); margin: 10px; display: inline-block; vertical-align: top; border: 1px solid rgb(204, 204, 204);">
            <img src="https://cdn.shopify.com/s/files/1/0026/8386/3113/products/2_d1ec7f5c-50b0-4eae-93df-ffe147e5880b.gif?v=1557485987"
                 style="width: 100%;">
            <h3 style="font-weight: 700;">Fashion Mens Stripe Gradient Ramp Knit Sweater</h3>
            <h3>38.99</h3></div>
        <div style="width: calc(50% - 24px); margin: 10px; display: inline-block; vertical-align: top; border: 1px solid rgb(204, 204, 204);">
            <img src="https://cdn.shopify.com/s/files/1/0026/8386/3113/products/3201117_fe91264cf2.png?v=1541246010"
                 style="width: 100%;">
            <h3 style="font-weight: 700;">Travel Casual Shoes</h3>
            <h3>20.9</h3></div>
    </div>
    <div style="width: 100%; padding-bottom: 20px;">
        <div style="display: inline-block; padding: 20px; background: rgb(0, 0, 0); color: rgb(255, 255, 255); font-size: 16px; font-weight: 900; border-radius: 10px;">
            Back to Shop &gt;&gt;&gt;
        </div>
    </div>
    <div style="width: 100%; padding-bottom: 20px;">
        <div>{shop_email}</div>
    </div>
    <div style="width: 100%; padding-bottom: 20px;">
        <div>{year} {shop_name}. All rights reserved.</div>
    </div>
    <div style="width: 100%; padding-bottom: 20px;">
        <div>{shop_address}</div>
    </div>
    <div style="width: 100%; padding-bottom: 20px;">
        <div style="display: inline-block; padding: 10px; color: rgb(204, 204, 204); font-size: 14px; border-radius: 10px; border: 1px solid rgb(204, 204, 204);">
            Unsubscribe
        </div>
    </div>
</div>
</body>
</html>"""
    ems = ExpertSender("Leemon", "leemon.li@orderplus.com")
    # print(ems.get_message_statistics(328))
    # print(ems.get_messages(348))
    # print(ems.create_subscribers_list("Test001"))
    # print(ems.add_subscriber(29, ["twobercancan@126.com", "leemon.li@orderplus.com"]))
    # html = open("index.html")
    print(ems.create_and_send_newsletter([29], "HelloWorld TTT", html=html_b)) # ,"2019-07-09 21:09:00"
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
    # print(ems.get_list_or_segment_data(29))  # 11
    # print(ems.get_export_progress(11))  # 11
    # print(ems.clear_subscriber(25, ""))  # 11
    # print(ems.add_subscriber(25, ["limengqiAliase@163.com", "leemon.li@orderplus.com"]))
    # print(ems.create_transactional_message("transactional message test", contentFromUrl="http://sources.aopcdn.com/edm/html/buzzyly/20190625/1561447955806.html"))  # 350
    # print(ems.send_transactional_messages(350, "leemon.li@orderplus.com"))  # 350
    # print(ems.update_transactional_message(350, "Aliase", "limengqiAliase@163.com", "transactional message test 11", html=html_b))  # 350
    # print(ems.delete_message(349))

