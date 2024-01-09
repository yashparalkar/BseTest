import time as t
from datetime import datetime, time
from pushbullet import PushBullet
import bsedata
from bsedata.bse import BSE
import http.client, urllib
from keep_alive import keep_alive

keep_alive()
access_token = "o.C5GgjDpMQ8j4OOjRiFFPyYZYZFifItOU"
pb = PushBullet(access_token)

bse = BSE(update_codes=True)

stocks = []
codes = [
    543272, 532368, 532648, 532670, 539436, 543331, 532667, 500285, 532822,
    532666, 542655, 543688, 535113, 542655
]
stock_history = [{code: None
                  for code in codes}, {code: None
                                       for code in codes},
                 {code: None
                  for code in codes}]

# Define the trading hours
for code in codes:
  stocks.append(bse.getQuote(str(code)))
  for stock in stocks:
    pb.push_note("Stock Price", f"Price of {stock['companyName']} is {stock['currentValue']}")
