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
start_time = time(3, 0)
end_time = time(10, 30)

codes = [
    532368, 532648, 521064, 532667, 532670, 543272, 532505, 500285, 532525, 
    539436, 532885, 532749, 532610, 500268, 543248, 523630, 500113, 514162, 
    500470, 543330, 506022, 500339, 532234, 513599, 532822, 500116, 543331,
    533162
]
# codes = [543272, 532368]
stock_history = [{code: None for code in codes}, {code: None for code in codes}, {code: None for code in codes}]

# Define the trading hours
while True:
    now = datetime.now()
    if now.weekday() in range(0, 5):
        if start_time <= now.time() <= end_time:
    # Check if it's within trading hours
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
                        
                            try:
                                conn = http.client.HTTPSConnection("api.pushover.net:443")
                                conn.request(
                                     "POST", "/1/messages.json",
                                     urllib.parse.urlencode({
                                     "token": os.environ.get('token'),
                                     "user": os.environ.get("user"),
                                     "message": f"{subject}\n{body}",
                                }), {"Content-type": "application/x-www-form-urlencoded"})
                                conn.getresponse()
                                conn1 = http.client.HTTPSConnection("api.pushover.net:443")
                                conn1.request(
                                    "POST", "/1/messages.json",
                                    urllib.parse.urlencode({
                                    "token": os.environ.get('my_token'),
                                    "user": os.environ.get("my_user_id"),
                                    "message": f"{subject}\n{body}\n{now}",
                                }), {"Content-type": "application/x-www-form-urlencoded"})
                                conn1.getresponse()
                            except RequestException as e:
                                print(f"ConnectionError: {e}")
                            except Exception as e:
                                print(e)
                            finally:
                                if conn1:
                                    conn.close()
                                    conn1.close()
                            
                except bsedata.exceptions.InvalidStockException as e:
                    print(f"Ignoring inactive stock with code {code}: {e}")
                    continue
                except Exception as e:
                    print(e)
                    continue

  # Sleep for a minute before checking again
    t.sleep(900)
