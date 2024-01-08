import smtplib
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

stock = []
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
start_time = time(3, 30)
end_time = time(10, 0)

while True:
  now = datetime.now()
  if now.weekday() in range(0, 5):
    # Check if it's within trading hours
    if start_time <= now.time() <= end_time:
      for _i, code in enumerate(codes):
        try:
          quote = bse.getQuote(str(code))
          quote.pop('buy')
          quote.pop('sell')

          # Update stock history for the current interval
          stock_history[2][code] = stock_history[1][code]
          stock_history[1][code] = stock_history[0][code]
          stock_history[0][code] = quote

          if all(stock_history[2].values()) and all(
              stock_history[1].values()) and all(stock_history[0].values()):
            # Calculate the percentage change between 20 minutes ago and now
            percent_change_30min_ago = (
                (float(stock_history[0][code]['currentValue']) -
                 float(stock_history[2][code]['currentValue'])) /
                float(stock_history[2][code]['currentValue'])) * 100

            # Calculate the percentage change between 10 minutes ago and now
            percent_change_15min_ago = (
                (float(stock_history[0][code]['currentValue']) -
                 float(stock_history[1][code]['currentValue'])) /
                float(stock_history[1][code]['currentValue'])) * 100

            if abs(percent_change_30min_ago) >= 1 or abs(
                percent_change_15min_ago) >= 1:
              # Send an email notification
              subject = f"Stock {stock_history[0][code]['companyName']} Swing Alert"
              body = f"Stock {stock_history[0][code]['companyName']} has changed "
              body += f"by {percent_change_15min_ago:.2f}% in the last 15 minutes\n\n" if abs(
                  percent_change_15min_ago
              ) >= 1 else f"by {percent_change_30min_ago:.2f}% in the last 30 minutes.\n\n"
              body += f"30min Ago Value: {stock_history[2][code]['currentValue']}\n"
              body += f"15min Ago Value: {stock_history[1][code]['currentValue']}\n"
              body += f"Current Value: {stock_history[0][code]['currentValue']}\n"
              message = f"Subject: {subject}\n\n{body}"

              push = pb.push_note(subject, body)

              try:
                conn = http.client.HTTPSConnection("api.pushover.net:443")
                conn.request(
                    "POST", "/1/messages.json",
                    urllib.parse.urlencode({
                        "token": "ae7qnfbucxiojph9pip8ht4snfj2ji",
                        "user": "uuxzqfp8x77jkib2ymb8a65ub1688h",
                        "message": f"{subject}\n{body}",
                    }), {"Content-type": "application/x-www-form-urlencoded"})
                conn.getresponse()
              finally:
                conn.close()

        except bsedata.exceptions.InvalidStockException as e:
          print(f"Ignoring inactive stock with code {code}: {e}")

  # Sleep for a minute before checking again
  t.sleep(900)
