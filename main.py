import time as t
from datetime import datetime, time
import yfinance as yf
import http.client, urllib
from keep_alive import keep_alive
import logging
from requests.exceptions import RequestException
import os
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

keep_alive()

start_time = time(3, 0)
end_time = time(10, 30)

# Convert BSE codes to Yahoo Finance format
# For BSE stocks, append .BO
# For NSE stocks, append .NS
codes = ["543272.BO", "532368.BO"]  # Your BSE codes with .BO suffix
stock_names = {}  # Will store company names

stock_history = [{code: None for code in codes}, {code: None for code in codes}, {code: None for code in codes}]

def get_stock_info(symbol):
    """Get current stock info using Yahoo Finance"""
    try:
        ticker = yf.Ticker(symbol)
        
        # Get current data
        hist = ticker.history(period="1d", interval="1m")
        if hist.empty:
            logger.warning(f"No data available for {symbol}")
            return None
        
        # Get the latest price
        latest_price = hist['Close'].iloc[-1]
        
        # Get company info (cache it)
        if symbol not in stock_names:
            try:
                info = ticker.info
                stock_names[symbol] = info.get('longName', info.get('shortName', symbol))
            except:
                stock_names[symbol] = symbol
        
        quote = {
            'currentValue': str(latest_price),
            'companyName': stock_names[symbol],
            'symbol': symbol,
            'timestamp': datetime.now()
        }
        
        logger.info(f"Got quote for {symbol}: {latest_price}")
        return quote
        
    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {e}")
        return None

def send_notification(subject, body, now):
    """Send notification with error handling"""
    conn = None
    conn1 = None
    try:
        # First notification
        conn = http.client.HTTPSConnection("api.pushover.net:443")
        conn.request(
            "POST", "/1/messages.json",
            urllib.parse.urlencode({
                "token": os.environ.get('token'),
                "user": os.environ.get("user"),
                "message": f"{subject}\n{body}",
            }), {"Content-type": "application/x-www-form-urlencoded"})
        response = conn.getresponse()
        logger.info(f"First notification response: {response.status}")
        
        # Second notification
        conn1 = http.client.HTTPSConnection("api.pushover.net:443")
        conn1.request(
            "POST", "/1/messages.json",
            urllib.parse.urlencode({
                "token": os.environ.get('my_token'),
                "user": os.environ.get("my_user_id"),
                "message": f"{subject}\n{body}\n{now}",
            }), {"Content-type": "application/x-www-form-urlencoded"})
        response1 = conn1.getresponse()
        logger.info(f"Second notification response: {response1.status}")
        
    except RequestException as e:
        logger.error(f"ConnectionError: {e}")
    except Exception as e:
        logger.error(f"Notification error: {e}")
    finally:
        if conn:
            conn.close()
        if conn1:
            conn1.close()

# Add a counter for failed attempts
failed_attempts = {code: 0 for code in codes}
MAX_FAILED_ATTEMPTS = 5

logger.info("Starting stock monitoring with Yahoo Finance...")

while True:
    now = datetime.now()
    if now.weekday() in range(0, 5):
        if start_time <= now.time() <= end_time:
            logger.info(f"Checking stocks at {now}")
            
            for _i, code in enumerate(codes):
                # Skip if too many failed attempts
                if failed_attempts[code] >= MAX_FAILED_ATTEMPTS:
                    logger.warning(f"Skipping code {code} due to too many failed attempts")
                    continue
                
                try:
                    logger.info(f"Fetching quote for {code}")
                    quote = get_stock_info(code)
                    
                    if not quote:
                        failed_attempts[code] += 1
                        logger.warning(f"Failed to get quote for {code}. Failed attempts: {failed_attempts[code]}")
                        continue
                    
                    # Reset failed attempts on success
                    failed_attempts[code] = 0
                    
                    # Update stock history
                    stock_history[2][code] = stock_history[1][code]
                    stock_history[1][code] = stock_history[0][code]
                    stock_history[0][code] = quote
                    
                    if all(stock_history[2].values()) and all(stock_history[1].values()) and all(stock_history[0].values()):
                        try:
                            current_value = float(stock_history[0][code]['currentValue'])
                            value_30min_ago = float(stock_history[2][code]['currentValue'])
                            value_15min_ago = float(stock_history[1][code]['currentValue'])
                            
                            percent_change_30min_ago = ((current_value - value_30min_ago) / value_30min_ago) * 100
                            percent_change_15min_ago = ((current_value - value_15min_ago) / value_15min_ago) * 100
                            
                            logger.info(f"Code {code}: 15min change: {percent_change_15min_ago:.2f}%, 30min change: {percent_change_30min_ago:.2f}%")
                            
                            if abs(percent_change_30min_ago) >= 1.5 or abs(percent_change_15min_ago) >= 1.5:
                                subject = f"Stock {stock_history[0][code]['companyName']} Swing Alert"
                                body = f"Stock {stock_history[0][code]['companyName']} has changed "
                                body += f"by {percent_change_15min_ago:.2f}% in the last 15 minutes\n\n" if abs(percent_change_15min_ago) >= 1.5 else f"by {percent_change_30min_ago:.2f}% in the last 30 minutes.\n\n"
                                body += f"30min Ago Value: ₹{stock_history[2][code]['currentValue']}\n"
                                body += f"15min Ago Value: ₹{stock_history[1][code]['currentValue']}\n"
                                body += f"Current Value: ₹{stock_history[0][code]['currentValue']}\n"
                                
                                logger.info(f"Sending alert for {code}: {subject}")
                                send_notification(subject, body, now)
                        
                        except (ValueError, TypeError) as e:
                            logger.error(f"Error calculating percentage change for code {code}: {e}")
                            continue
                        
                except Exception as e:
                    logger.error(f"Error processing code {code}: {e}")
                    failed_attempts[code] += 1
                    continue
        else:
            logger.info(f"Outside trading hours. Current time: {now.time()}")
    else:
        logger.info(f"Weekend. Current day: {now.weekday()}")

    # Sleep for 15 minutes
    logger.info("Sleeping for 15 minutes...")
    t.sleep(30)
