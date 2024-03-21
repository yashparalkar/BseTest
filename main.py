import time as t
from datetime import datetime, time
import bsedata
from bsedata.bse import BSE
import http.client, urllib
from keep_alive import keep_alive
import logging
from requests.exceptions import RequestException
import os

keep_alive()

bse = BSE(update_codes=True)
start_time = time(9, 0)
end_time = time(16, 0)
now = datetime.now()

stocks = []
codes = [ 543272, 532368, 532648, 532670, 539436, 543331, 532667, 500285, 532822,
     542655, 543688, 500116]
stock_history = [{code: None for code in codes}, {code: None for code in codes}, {code: None for code in codes}]

# Define the trading hours
conn1 = http.client.HTTPSConnection("api.pushover.net:443")
conn1.request(
   "POST", "/1/messages.json",
   urllib.parse.urlencode({
     "token": os.environ.get('my_token'),
     "user": os.environ.get("my_user_id"),
     "message": f"time: {now}",
 }), {"Content-type": "application/x-www-form-urlencoded"})
conn1.getresponse()
t.sleep(900)
# this was added with git
