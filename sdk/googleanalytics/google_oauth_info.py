# -*-coding:utf-8-*-
import sys
from apiclient import discovery
from oauth2client.service_account import ServiceAccountCredentials
from config import logger


class GoogleApi():
    def __init__(self, view_id, ga_source="pinbooster", json_path=""):
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

    def get_report(self):
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
                    'reportRequests': [
                        {
                            'viewId': self.VIEW_ID,
                            'dateRanges': [{'startDate': '1000daysAgo', 'endDate': 'today'}],
                            'metrics': [
                                {"expression": "ga:sessions"},
                                {"expression": "ga:transactions"},  # 交易数量
                                {"expression": "ga:transactionRevenue"},  # 销售总金额
                            ],
                            "dimensions": [
                                                {"name": "ga:source"},
                                                {"name": "ga:keyword"},
                                            ],
                        }]
                }
            ).execute()
            for report in analytics_info.get('reports', []):
                dateRangeValues = report.get('data', {}).get('totals', [])
                results = {
                           "sessions":  int(dateRangeValues[0].get("values", "")[0]),
                           "transactions": int(dateRangeValues[0].get("values", "")[1]),
                            "revenue": float(dateRangeValues[0].get("values", "")[2])}
                return results
        except Exception as e:
            logger.error("get google analytics info is failed, msg={}".format(str(e)))
            return {"code": 2, "data": "", "msg": str(e)}


if __name__ == '__main__':
    google_data = GoogleApi(view_id="198387424")
    print(google_data.get_report())
    print(1)



