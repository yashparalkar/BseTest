import time as t
from datetime import datetime, time
import bsedata
from bsedata.bse import BSE
import http.client, urllib
from keep_alive import keep_alive
import logging
from requests.exceptions import RequestException
import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

keep_alive()

# Enhanced BSE initialization with retry logic
def create_bse_session():
    """Create BSE session with proper headers and retry logic"""
    try:
        # Add headers to mimic a real browser
        session = requests.Session()
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        session.headers.update(headers)
        
        # Add retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Initialize BSE with custom session
        bse = BSE(update_codes=True)
        return bse
    except Exception as e:
        logger.error(f"Failed to create BSE session: {e}")
        return None

def validate_quote(quote, code):
    """Validate if quote contains required data"""
    if not quote or quote == {'buy': {}, 'sell': {}}:
        logger.warning(f"Empty quote received for code {code}")
        return False
    
    required_fields = ['currentValue', 'companyName']
    for field in required_fields:
        if field not in quote or not quote[field]:
            logger.warning(f"Missing {field} in quote for code {code}")
            return False
    
    return True

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

# Initialize BSE
bse = create_bse_session()
if not bse:
    logger.error("Failed to initialize BSE. Exiting...")
    exit(1)

start_time = time(3, 0)
end_time = time(10, 30)

codes = [543272, 532368]
stock_history = [{code: None for code in codes}, {code: None for code in codes}, {code: None for code in codes}]

# Add a counter for failed attempts
failed_attempts = {code: 0 for code in codes}
MAX_FAILED_ATTEMPTS = 5

logger.info("Starting stock monitoring...")

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
                    logger.info(f"Fetching quote for code {code}")
                    quote = bse.getQuote(str(code))
                    
                    # Log the full quote for debugging
                    logger.info(f"Full quote for {code}: {quote}")
                    
                    # Validate quote
                    if not validate_quote(quote, code):
                        failed_attempts[code] += 1
                        logger.warning(f"Invalid quote for code {code}. Failed attempts: {failed_attempts[code]}")
                        continue
                    
                    # Reset failed attempts on success
                    failed_attempts[code] = 0
                    
                    # Update stock history for the current interval
                    stock_history[2][code] = stock_history[1][code]
                    stock_history[1][code] = stock_history[0][code]
                    stock_history[0][code] = quote
                    
                    if all(stock_history[2].values()) and all(stock_history[1].values()) and all(stock_history[0].values()):
                        # Calculate the percentage change between 30 minutes ago and now
                        try:
                            current_value = float(stock_history[0][code]['currentValue'])
                            value_30min_ago = float(stock_history[2][code]['currentValue'])
                            value_15min_ago = float(stock_history[1][code]['currentValue'])
                            
                            percent_change_30min_ago = ((current_value - value_30min_ago) / value_30min_ago) * 100
                            percent_change_15min_ago = ((current_value - value_15min_ago) / value_15min_ago) * 100
                            
                            logger.info(f"Code {code}: 15min change: {percent_change_15min_ago:.2f}%, 30min change: {percent_change_30min_ago:.2f}%")
                            
                            if abs(percent_change_30min_ago) >= 1.5 or abs(percent_change_15min_ago) >= 1.5:
                                # Send an email notification
                                subject = f"Stock {stock_history[0][code]['companyName']} Swing Alert"
                                body = f"Stock {stock_history[0][code]['companyName']} has changed "
                                body += f"by {percent_change_15min_ago:.2f}% in the last 15 minutes\n\n" if abs(percent_change_15min_ago) >= 1.5 else f"by {percent_change_30min_ago:.2f}% in the last 30 minutes.\n\n"
                                body += f"30min Ago Value: {stock_history[2][code]['currentValue']}\n"
                                body += f"15min Ago Value: {stock_history[1][code]['currentValue']}\n"
                                body += f"Current Value: {stock_history[0][code]['currentValue']}\n"
                                
                                logger.info(f"Sending alert for {code}: {subject}")
                                send_notification(subject, body, now)
                        
                        except (ValueError, TypeError) as e:
                            logger.error(f"Error calculating percentage change for code {code}: {e}")
                            continue
                        
                except bsedata.exceptions.InvalidStockException as e:
                    logger.warning(f"Ignoring inactive stock with code {code}: {e}")
                    failed_attempts[code] += 1
                    continue
                except Exception as e:
                    logger.error(f"Error processing code {code}: {e}")
                    failed_attempts[code] += 1
                    continue
        else:
            logger.info(f"Outside trading hours. Current time: {now.time()}")
    else:
        logger.info(f"Weekend. Current day: {now.weekday()}")

    # Sleep for 15 minutes before checking again
    logger.info("Sleeping for 15 minutes...")
    t.sleep(30)
