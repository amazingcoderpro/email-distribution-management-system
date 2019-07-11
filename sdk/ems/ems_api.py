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
    def __init__(self, apiKey, fromEmail):
        self.api_key = apiKey
        self.host = "https://api6.esv2.com/v2/"
        self.headers = {"Content-Type": "text/xml"}
        self.from_email = fromEmail

    @staticmethod
    def xmltojson(xmlstr, type):
        # parse是的xml解析器
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
        """获取服务器时间"""
        url = f"{self.host}Api/Time?apiKey={self.api_key}"
        try:
            result = requests.get(url)
            return self.retrun_result("get server time", result)
        except Exception as e:
            return {"code": -1, "msg": str(e), "data": ""}

    def get_messages(self, emailID=None):
        """获取已发送邮件列表"""
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
        """获取弹回列表"""
        url = f"{self.host}Api/Bounces?apiKey={self.api_key}&startDate=2019-07-01&endDate=2019-07-08"
        try:
            result = requests.get(url)
            return result.text
        except Exception as e:
            return {"code": -1, "msg": str(e), "data": ""}

    def get_message_statistics(self, emailID, startDate="1970-01-01", endDate=datetime.datetime.today().date()):
        """
        获取邮件统计数据
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

    def create_and_send_newsletter(self, listId, subject, plain="", html="", deliveryDate=None, timeZone="UTC"):
        """
        创建及发送Newsletter
        :param listId: 发送列表ID
        :param subject: 邮件主题
        :param plain: 邮件纯文本
        :param html: html格式邮件内容
        :param deliveryDate: 指定发送日期，默认为及时发送
        :return:
        """
        url = f"{self.host}Api/Newsletters"
        data = {"ApiRequest": {
                    "ApiKey": self.api_key,
                    "Data":{
                        "Recipients": {"SubscriberLists": [{"SubscriberList": listId}, ]},
                        "Content": {
                            "FromEmail": self.from_email,
                            "Subject": subject,
                            "Plain": plain,
                            "Html": "%s",
                            # "ContentFromUrl": {"Url": "http://sources.aopcdn.com/edm/html/buzzyly/20190625/1561447955806.html"}
                        },
                        "DeliverySettings": {
                            "ThrottlingMethod": "Auto",
                            # "TimeZone": timeZone,
                            "OverrideDeliveryCap": "true"
                        }
                    }
        }}
        if deliveryDate:
            data["ApiRequest"]["Data"]["DeliverySettings"].update({"DeliveryDate": deliveryDate.replace(" ", "T")})
        try:
            xml_data = self.jsontoxml(data)
            xml_data = xml_data % ("<![CDATA[%s]]>" % html)
            result = requests.post(url, xml_data, headers=self.headers)
            return self.retrun_result("create and send newsletter", result)
        except Exception as e:
            return {"code": -1, "msg": str(e), "data": ""}

    def create_subscribers_list(self, name, isSeedList=False):
        """
        创建收件人列表
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
        获取收件人列表
        :param seedLists: 如设为 ‘true’, 只有测试列表会被返回. 如果设为 ‘false’, 只有收件人列表会被返回.
        :return:
        """
        url = f"{self.host}Api/Lists?apiKey={self.api_key}&seedLists={seedLists}"
        try:
            result = requests.get(url)
            return self.retrun_result("get subscriber lists", result)
        except Exception as e:
            return {"code": -1, "msg": str(e), "data": ""}

    def add_subscriber(self, listId, emailList):
        """
        添加收件人
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
                    # "Firstname": "John",
                    # "Lastname": "Smith",
                    # "TrackingCode": "123",
                    # "Vendor": "xyz",
                    # "Ip": "11.22.33.44"
                }
            )
        try:
            result = requests.post(url, self.jsontoxml(data), headers=self.headers)
            return self.retrun_result("add subscriber", result)
        except Exception as e:
            return {"code": -1, "msg": str(e), "data": ""}

    def get_subscriber_activity(self, types, date=datetime.datetime.today().date()):
        """
        获取收件人行为记录
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
        获取列表统计数据
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
        获取收件人信息
        :param email: 邮件地址
        :return:
        """
        url = f"{self.host}Api/Subscribers?apiKey={self.api_key}&email={email}&option=EventsHistory"
        try:
            result = requests.get(url)
            return self.retrun_result("get subscriber statistics", result)
        except Exception as e:
            return {"code": -1, "msg": str(e), "data": ""}

    def get_summary_statistics(self, segmentId):
        """
        获取细分组信息
        :param segmentId:细分ID
        :return:
        """
        url = f"{self.host}Api/SummaryStatistics?apiKey={self.api_key}&scope=Segment&scopeValue={segmentId}"
        try:
            result = requests.get(url)
            return self.retrun_result("get summary statistics", result)
        except Exception as e:
            return {"code": -1, "msg": str(e), "data": ""}

    def get_subscriber_segments(self):
        """获取所有细分组"""
        url = f"{self.host}Api/Segments?apiKey={self.api_key}"
        try:
            result = requests.get(url)
            return self.retrun_result("get summary statistics", result)
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
    ems = ExpertSender("0x53WuKGWlbq2MQlLhLk", "leemon.li@orderplus.com")
    # print(ems.get_message_statistics(318))
    # print(ems.create_and_send_newsletter(25, "HelloWorld","expertsender",html_b)) # ,"2019-07-09 21:09:00"
    # print(ems.get_messages(318))
    # print(ems.create_subscribers_list("Test001"))
    # print(ems.add_subscriber(26, ["twobercancan@126.com", "leemon.li@orderplus.com"]))
    print(ems.get_subscriber_activity("Opens"))
    # print(ems.get_subscriber_information("twobercancan@126.com"))
    # print(ems.get_subscriber_activity())
    # print(ems.get_summary_statistics(63))