from pushbullet import PushBullet
from bsedata.bse import BSE
from datetime import datetime, time
print(datetime.now())
access_token = "o.C5GgjDpMQ8j4OOjRiFFPyYZYZFifItOU"
pb = PushBullet(access_token)

bse = BSE(update_codes=True)

stock = []
codes = [
    543272, 532368, 532648, 532670, 539436, 543331, 532667, 500285, 532822,
    532666, 542655, 543688, 535113, 542655
]
s=bse.getQuote('543272')
pb.push_note('h', s['currentValue'])
