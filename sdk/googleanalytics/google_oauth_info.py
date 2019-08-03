# -*-coding:utf-8-*-
import sys
from apiclient import discovery
from oauth2client.service_account import ServiceAccountCredentials
from config import logger
from config import SHOPIFY_CONFIG


class GoogleApi():
    def __init__(self, view_id, ga_source=SHOPIFY_CONFIG.get("utm_source"), json_path=""):
        """
        获取店铺的GA数据
        :param view_id: 视图的id
        :param key_words: 来源的关键字
        """
        self.SCOPES = ['https://www.googleapis.com/auth/analytics.readonly']
        if json_path:
            self.KEY_FILE_LOCATION = json_path
        else:
            self.KEY_FILE_LOCATION = 'client_secrets.json'
        self.VIEW_ID = view_id
        self.ga_source = ga_source

    def get_report(self, key_word, start_time, end_time):
        """
         Queries the Analytics Reporting API V4.
        Args:
          analytics: An authorized Analytics Reporting API V4 service object.
        Returns:
          The Analytics Reporting API V4 response.
        """
        try:
            credentials = ServiceAccountCredentials.from_json_keyfile_name(self.KEY_FILE_LOCATION, self.SCOPES)
            # Build the service object.
            analytics = discovery.build('analyticsreporting', 'v4', credentials=credentials)
            analytics_info = analytics.reports().batchGet(
                body={
                    "reportRequests":
                        [
                            {
                                "viewId": self.VIEW_ID,
                                "dateRanges": [
                                    {'startDate': start_time, 'endDate': end_time},
                                ],
                                "metrics": [
                                    {"expression": "ga:sessions"},  # pageviews
                                    # {"expression": "ga:Users"},      # uv
                                    # {"expression": "ga:newUsers"},
                                    {"expression": "ga:transactions"},  # 交易数量
                                    {"expression": "ga:transactionRevenue"},  # 销售总金额
                                    # {"expression": "ga:hits"},  # 点击量
                                    # {"expression": "ga:itemRevenue"}
                                ],
                                "dimensions": [
                                    {"name": "ga:source"},
                                    {"name": "ga:keyword"},
                                ],
                                "dimensionFilterClauses": [
                                    {
                                        "filters": [
                                            {
                                                "dimensionName": "ga:source",
                                                "operator": "EXACT",
                                                "expressions": [self.ga_source]
                                            }]
                                        }]
                                 }]
                                }).execute()

            results = {}
            total_results = {"sessions":0, "transactions": 0, "revenue": 0}

            for report in analytics_info.get('reports', []):
                for row in report.get('data', {}).get('rows', []):
                    dimensions = row.get('dimensions', [])
                    dateRangeValues = row.get('metrics', [])
                    if dimensions[1] == key_word or not key_word:
                        temp_key = dimensions[1].split('_')
                        if len(temp_key)==1:
                            temp_key_word = temp_key[0]
                        elif len(temp_key) == 2:
                            temp_key_word = temp_key[1]
                        else:
                            pass
                        values = dateRangeValues[0].get('values', [])
                        if values:
                            if temp_key_word not in results:
                                results[temp_key_word] = {"sessions": int(values[0]), "transactions": int(values[1]),
                                                          "revenue": float(values[2])}
                            else:
                                results[temp_key_word]["sessions"] += int(values[0])
                                results[temp_key_word]["transactions"] += int(values[1])
                                results[temp_key_word]["revenue"] += float(values[2])

                for res in results.values():
                    total_results["sessions"] += res["sessions"]
                    total_results["transactions"] += res["transactions"]
                    total_results["revenue"] += res["revenue"]
                # print({"code": 1, "data": {"results": results, "total_results":total_results}, "msg": ""})
                return {"code": 1, "data": {"results": results, "total_results":total_results}, "msg": ""}
        except Exception as e:
            logger.error("get google analytics info is failed, msg={}".format(str(e)))
            return {"code": 2, "data": "", "msg": str(e)}


if __name__ == '__main__':

    google_data = GoogleApi(view_id="180765506")
    print(google_data.get_report(key_word="", start_time="1daysAgo", end_time="today"))
    print(1)




