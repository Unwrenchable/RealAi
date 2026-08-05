import os
import time
import logging
import random
from datetime import datetime
import json
import requests
from apscheduler.schedulers.background import BackgroundScheduler
import tweepy
from flask import Flask, request, jsonify
from flask_httpauth import HTTPBasicAuth
import ccxt
import re
import threading

# Import API client for external integrations
import api_client

# Wallet integrations (optional imports)
WALLET_ENABLED = False
try:
    from solana.rpc.api import Client as SolanaClient
    from solders.keypair import Keypair
    from solders.pubkey import Pubkey
    from solders.transaction import Transaction
    import base58
    from web3 import Web3
    WALLET_ENABLED = True
    logging.info("Wallet dependencies loaded successfully")
except ImportError as e:
    logging.warning(f"Wallet dependencies not available: {e}. Wallet features will be disabled.")
    WALLET_ENABLED = False

# ------------------------------------------------------------
# CONFIG & LOGGING
# ------------------------------------------------------------
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - VAULT-TEC OVERSEER LOG - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("overseer_ai.log"), logging.StreamHandler()]
)

GAME_LINK = "https://www.atomicfizzcaps.xyz"
BOT_NAME = "OVERSEER"
VAULT_NUMBER = "77"

# Configuration constants
TWITTER_CHAR_LIMIT = 280
HUGGING_FACE_TIMEOUT = 10
BROADCAST_MIN_INTERVAL = 120  # minutes
BROADCAST_MAX_INTERVAL = 240  # minutes
MENTION_CHECK_MIN_INTERVAL = 15  # minutes
MENTION_CHECK_MAX_INTERVAL = 30  # minutes

# ------------------------------------------------------------
# TWITTER AUTH
# ------------------------------------------------------------
CONSUMER_KEY = os.getenv('CONSUMER_KEY')
CONSUMER_SECRET = os.getenv('CONSUMER_SECRET')
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
ACCESS_SECRET = os.getenv('ACCESS_SECRET')
BEARER_TOKEN = os.getenv('BEARER_TOKEN')
HUGGING_FACE_TOKEN = os.getenv('HUGGING_FACE_TOKEN')

# Admin authentication credentials
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'vault77secure')

# Security warning for default credentials
if ADMIN_PASSWORD == 'vault77secure':
    logging.warning("="*60)
    logging.warning("⚠️  SECURITY WARNING: Using default admin password!")
    logging.warning("⚠️  Change ADMIN_PASSWORD in production immediately!")
    logging.warning("⚠️  Generate secure password: openssl rand -base64 32")
    logging.warning("="*60)

# Webhook API key for external services (like Token-scalper)
WEBHOOK_API_KEY = os.getenv('WEBHOOK_API_KEY', '')  # Empty = no authentication required

# ------------------------------------------------------------
# WALLET CONFIGURATION (Optional)
# ------------------------------------------------------------
ENABLE_WALLET_UI = os.getenv('ENABLE_WALLET_UI', 'true').lower() == 'true'

# Solana configuration
SOLANA_PRIVATE_KEY = os.getenv('SOLANA_PRIVATE_KEY', '')
SOLANA_RPC_ENDPOINT = os.getenv('SOLANA_RPC_ENDPOINT', 'https://api.mainnet-beta.solana.com')

# Ethereum/BSC configuration
ETH_PRIVATE_KEY = os.getenv('ETH_PRIVATE_KEY', '')
ETH_RPC_ENDPOINT = os.getenv('ETH_RPC_ENDPOINT', 'https://eth.public-rpc.com')
BSC_RPC_ENDPOINT = os.getenv('BSC_RPC_ENDPOINT', 'https://bsc-dataseed1.binance.org')

# Initialize wallet clients if enabled and credentials provided
solana_client = None
solana_keypair = None
eth_w3 = None
bsc_w3 = None
wallet_address = None
eth_wallet_address = None

def is_valid_solana_private_key(key):
    """Validate that a Solana private key is a valid base58 string."""
    if not key:
        return False
    # Check for common placeholder values
    if key in ['0', '0x0', 'your_key_here', 'placeholder']:
        return False
    try:
        # Try to decode as base58 - valid keys should be 64 bytes when decoded
        decoded = base58.b58decode(key)
        return len(decoded) == 64
    except Exception:
        return False

def is_valid_eth_private_key(key):
    """Validate that an Ethereum private key is a valid hex string."""
    if not key:
        return False
    # Check for common placeholder values
    if key in ['0', '0x0', 'your_key_here', 'placeholder']:
        return False
    # Remove 0x prefix if present
    clean_key = key[2:] if key.startswith('0x') else key
    # Valid private keys should be 64 hex characters (32 bytes)
    if len(clean_key) != 64:
        return False
    try:
        int(clean_key, 16)
        return True
    except ValueError:
        return False

if WALLET_ENABLED and ENABLE_WALLET_UI:
    # Try to initialize Solana wallet
    if SOLANA_PRIVATE_KEY:
        try:
            if is_valid_solana_private_key(SOLANA_PRIVATE_KEY):
                solana_client = SolanaClient(SOLANA_RPC_ENDPOINT)
                # Parse private key (base58 encoded)
                private_key_bytes = base58.b58decode(SOLANA_PRIVATE_KEY)
                solana_keypair = Keypair.from_bytes(private_key_bytes)
                wallet_address = str(solana_keypair.pubkey())
                logging.info(f"✅ Solana wallet initialized: {wallet_address[:8]}...{wallet_address[-8:]}")
            else:
                logging.warning("⚠️ SOLANA_PRIVATE_KEY is set but appears to be invalid or a placeholder. Skipping Solana wallet initialization.")
        except Exception as e:
            logging.error(f"Failed to initialize Solana wallet: {e}")
    
    # Try to initialize ETH/BSC wallet separately
    if ETH_PRIVATE_KEY:
        try:
            if is_valid_eth_private_key(ETH_PRIVATE_KEY):
                eth_w3 = Web3(Web3.HTTPProvider(ETH_RPC_ENDPOINT))
                bsc_w3 = Web3(Web3.HTTPProvider(BSC_RPC_ENDPOINT))
                eth_account = eth_w3.eth.account.from_key(ETH_PRIVATE_KEY)
                eth_wallet_address = eth_account.address
                logging.info(f"✅ ETH/BSC wallet initialized: {eth_wallet_address[:8]}...{eth_wallet_address[-8:]}")
            else:
                logging.warning("⚠️ ETH_PRIVATE_KEY is set but appears to be invalid or a placeholder. Skipping ETH/BSC wallet initialization.")
        except Exception as e:
            logging.error(f"Failed to initialize ETH/BSC wallet: {e}")
    
    # Only disable WALLET_ENABLED if neither wallet was initialized
    if not wallet_address and not eth_wallet_address:
        logging.info("No wallets were successfully initialized. Wallet features will be disabled.")
        WALLET_ENABLED = False

# ------------------------------------------------------------
# TWITTER INIT
# ------------------------------------------------------------

# Initialize Twitter clients only if credentials are provided
client = None
api_v1 = None

if all([CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, ACCESS_SECRET, BEARER_TOKEN]):
    try:
        client = tweepy.Client(
            consumer_key=CONSUMER_KEY,
            consumer_secret=CONSUMER_SECRET,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_SECRET,
            bearer_token=BEARER_TOKEN,
            wait_on_rate_limit=True
        )

        auth_v1 = tweepy.OAuth1UserHandler(
            CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, ACCESS_SECRET
        )
        api_v1 = tweepy.API(auth_v1, wait_on_rate_limit=True)

        logging.info("Twitter API clients initialized successfully")
    except Exception as e:
        logging.error(f"Failed to initialize Twitter clients: {e}")
        logging.warning("Bot will start without Twitter functionality")
else:
    logging.warning("Twitter API credentials not provided. Twitter bot features will be disabled.")
    logging.warning("Set CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, ACCESS_SECRET, and BEARER_TOKEN environment variables to enable Twitter features.")

# ------------------------------------------------------------
# TOKEN SCALPER MODULE - PRICE MONITORING
# ------------------------------------------------------------
PRICE_CACHE_FILE = "price_cache.json"

# Tokens to monitor with their configuration
MONITORED_TOKENS = {
    'SOL/USDT': {
        'exchange': 'binance',
        'alert_threshold_up': 5.0,  # Alert on 5% price increase
        'alert_threshold_down': 5.0,  # Alert on 5% price decrease
        'check_interval': 5  # Check every 5 minutes
    },
    'BTC/USDT': {
        'exchange': 'binance',
        'alert_threshold_up': 3.0,
        'alert_threshold_down': 3.0,
        'check_interval': 5
    },
    'ETH/USDT': {
        'exchange': 'binance',
        'alert_threshold_up': 4.0,
        'alert_threshold_down': 4.0,
        'check_interval': 5
    }
}

def load_price_cache():
    """Load cached price data."""
    if os.path.exists(PRICE_CACHE_FILE):
        with open(PRICE_CACHE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_price_cache(cache):
    """Save price data to cache."""
    with open(PRICE_CACHE_FILE, 'w') as f:
        json.dump(cache, f)

# CoinGecko API mapping for tokens (no geo-restrictions, free tier)
COINGECKO_MAPPING = {
    'SOL/USDT': 'solana',
    'BTC/USDT': 'bitcoin',
    'ETH/USDT': 'ethereum'
}

COINGECKO_CACHE = {}
COINGECKO_CACHE_TTL = 60  # seconds
COINGECKO_BACKOFF = 5     # initial backoff in seconds
COINGECKO_MAX_BACKOFF = 60

def get_token_price_coingecko(symbol):
    """
    Fetch token price from CoinGecko API (fallback when exchanges are geo-blocked).
    Implements in-memory cache and exponential backoff for rate limits.
    """
    coin_id = COINGECKO_MAPPING.get(symbol)
    if not coin_id:
        logging.warning(f"No CoinGecko mapping for {symbol}")
        return None
    now = time.time()
    cache_key = f"{symbol}_coingecko"
    # Use cache if recent
    if cache_key in COINGECKO_CACHE:
        cached = COINGECKO_CACHE[cache_key]
        if now - cached['timestamp'] < COINGECKO_CACHE_TTL:
            logging.info(f"Using cached CoinGecko price for {symbol}")
            return cached['data']
    url = f"https://api.coingecko.com/api/v3/simple/price"
    params = {
        'ids': coin_id,
        'vs_currencies': 'usd',
        'include_24hr_change': 'true',
        'include_24hr_vol': 'true'
    }
    backoff = COINGECKO_BACKOFF
    while True:
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            if coin_id not in data:
                logging.error(f"CoinGecko returned no data for {coin_id}")
                return None
            coin_data = data[coin_id]
            result = {
                'price': coin_data.get('usd', 0),
                'high_24h': None,  # CoinGecko simple API doesn't provide this
                'low_24h': None,   # CoinGecko simple API doesn't provide this
                'volume_24h': coin_data.get('usd_24h_vol', 0),
                'change_24h': coin_data.get('usd_24h_change', 0),
                'timestamp': now,
                'source': 'coingecko'
            }
            COINGECKO_CACHE[cache_key] = {'timestamp': now, 'data': result}
            return result
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                logging.warning(f"CoinGecko rate limited. Backing off {backoff}s...")
                time.sleep(backoff)
                backoff = min(backoff * 2, COINGECKO_MAX_BACKOFF)
                continue
            logging.error(f"HTTP error from CoinGecko for {symbol}: {e}")
            return None
        except Exception as e:
            logging.error(f"Failed to fetch price from CoinGecko for {symbol}: {e}")
            return None

def is_geo_restriction_error(exception):
    """
    Check if an exception indicates a geographic restriction.
    
    Args:
        exception: The exception to check
        
    Returns:
        bool: True if the error is due to geographic restrictions
    """
    error_msg = str(exception).lower()
    geo_indicators = [
        '451',  # HTTP 451 - Unavailable For Legal Reasons
        'restricted location',
        'unavailable from a restricted',
        'service unavailable from',
        'not available in your region',
        'geo',
        'geographic restriction'
    ]
    return any(indicator in error_msg for indicator in geo_indicators)

def get_token_price(symbol, exchange_name='binance'):
    """
    Fetch current token price from exchange with CoinGecko fallback.
    If the exchange is geo-blocked or fails, automatically falls back to CoinGecko.
    """
    try:
        exchange = getattr(ccxt, exchange_name)()
        ticker = exchange.fetch_ticker(symbol)
        return {
            'price': ticker['last'],
            'high_24h': ticker['high'],
            'low_24h': ticker['low'],
            'volume_24h': ticker['quoteVolume'],
            'change_24h': ticker['percentage'],
            'timestamp': time.time(),
            'source': exchange_name
        }
    except Exception as e:
        # Check if it's a geographic restriction error
        if is_geo_restriction_error(e):
            logging.warning(f"{exchange_name} is geo-blocked for {symbol}, falling back to CoinGecko...")
            return get_token_price_coingecko(symbol)
        else:
            logging.error(f"Failed to fetch price for {symbol} on {exchange_name}: {e}")
            # Try CoinGecko as fallback for any error
            logging.info(f"Attempting CoinGecko fallback for {symbol}...")
            return get_token_price_coingecko(symbol)

def calculate_price_change(old_price, new_price):
    """Calculate percentage change between two prices."""
    if old_price == 0:
        return 0
    return ((new_price - old_price) / old_price) * 100

def check_price_alerts():
    """Monitor token prices and generate alerts."""
    price_cache = load_price_cache()
    
    for symbol, config in MONITORED_TOKENS.items():
        current_data = get_token_price(symbol, config['exchange'])
        
        if not current_data:
            continue
            
        current_price = current_data['price']
        change_24h = current_data['change_24h']
        
        # Check if we have previous data
        cache_key = f"{symbol}_{config['exchange']}"
        if cache_key in price_cache:
            old_price = price_cache[cache_key]['price']
            price_change = calculate_price_change(old_price, current_price)
            
            # Check for significant price movements with correct threshold logic
            should_alert = False
            if price_change > 0 and price_change >= config['alert_threshold_up']:
                should_alert = True
            elif price_change < 0 and abs(price_change) >= config['alert_threshold_down']:
                should_alert = True
            
            if should_alert:
                post_price_alert(symbol, current_data, price_change)
        
        # Update cache
        price_cache[cache_key] = current_data
    
    save_price_cache(price_cache)

def create_fallback_alert_message(token_name, price_change, price):
    """Create a guaranteed short fallback alert message."""
    direction = "SURGE" if price_change > 0 else "DIP"
    emoji = "📈" if price_change > 0 else "📉"
    return (
        f"🔔 ${token_name} {direction}: {price_change:+.2f}% {emoji}\n"
        f"Price: ${price:.2f}\n\n"
        f"The wasteland economy shifts.\n\n"
        f"{GAME_LINK}"
    )

def post_price_alert(symbol, price_data, price_change):
    """Post a price alert to Twitter with Overseer personality."""
    try:
        token_name = symbol.split('/')[0]
        direction = "SURGE" if price_change > 0 else "DIP"
        emoji = "📈🚀" if price_change > 0 else "📉⚠️"
        
        personality_line = random.choice([
            "The wasteland economy shifts.",
            "Market radiation detected.",
            "FizzCo Analytics reporting.",
            "Vault-Tec market surveillance active.",
            "The caps flow differently now."
        ])
        
        alert_messages = [
            (
                f"🔔 MARKET ALERT {emoji}\n\n"
                f"${token_name} {direction}: {price_change:+.2f}%\n"
                f"Current: ${price_data['price']:.2f}\n"
                f"24h Change: {price_data['change_24h']:+.2f}%\n\n"
                f"{personality_line}\n\n"
                f"🎮 {GAME_LINK}"
            ),
            (
                f"⚡ PRICE MOVEMENT DETECTED {emoji}\n\n"
                f"Token: ${token_name}\n"
                f"Change: {price_change:+.2f}%\n"
                f"Price: ${price_data['price']:.2f}\n\n"
                f"{random.choice(LORES)}\n\n"
                f"🎮 {GAME_LINK}"
            )
        ]
        
        message = random.choice(alert_messages)
        
        # Ensure message fits Twitter limit with proper fallback
        if len(message) > TWITTER_CHAR_LIMIT:
            message = create_fallback_alert_message(
                token_name, price_change, price_data['price']
            )
        
        client.create_tweet(text=message)
        logging.info(f"Posted price alert for {symbol}: {price_change:+.2f}%")
        add_activity("PRICE_ALERT", f"{symbol} {price_change:+.2f}% - ${price_data['price']:.2f}")
        
    except tweepy.TweepyException as e:
        logging.error(f"Failed to post price alert: {e}")
        add_activity("ERROR", f"Price alert failed for {symbol}: {str(e)}")

def post_market_summary():
    """Post a market summary with multiple token prices."""
    try:
        summary_lines = ["📊 WASTELAND MARKET REPORT 📊\n"]
        
        for symbol, config in MONITORED_TOKENS.items():
            data = get_token_price(symbol, config['exchange'])
            if data:
                token_name = symbol.split('/')[0]
                emoji = "🟢" if data['change_24h'] > 0 else "🔴"
                summary_lines.append(
                    f"{emoji} ${token_name}: ${data['price']:.2f} ({data['change_24h']:+.2f}%)"
                )
        
        personality = random.choice([
            "The economy glows. Caps flow.",
            "Market surveillance: nominal.",
            "Vault-Tec approves these numbers.",
            "FizzCo Industries: Making caps sparkle."
        ])
        
        # Build message with length checking
        message = "\n".join(summary_lines) + f"\n\n{personality}\n\n🎮 {GAME_LINK}"
        
        # Truncate if needed by removing token lines from the end
        if len(message) > TWITTER_CHAR_LIMIT:
            # Keep header and build with fewer tokens
            truncated_lines = [summary_lines[0]]
            footer = f"\n\n{personality}\n\n🎮 {GAME_LINK}"
            
            for line in summary_lines[1:]:
                test_message = "\n".join(truncated_lines + [line]) + footer
                if len(test_message) <= TWITTER_CHAR_LIMIT:
                    truncated_lines.append(line)
                else:
                    break
            
            # Ensure we have at least one token, use simplified format if needed
            if len(truncated_lines) < 2:  # Only header, no tokens
                # Use a super simple format with just one token
                if len(summary_lines) > 1:
                    first_token = summary_lines[1]
                    message = f"{summary_lines[0]}{first_token}\n\n{personality}\n\n{GAME_LINK}"
                else:
                    # No token data available at all
                    message = f"{summary_lines[0]}No market data available.\n\n{personality}\n\n{GAME_LINK}"
            else:
                message = "\n".join(truncated_lines) + footer
        
        client.create_tweet(text=message)
        logging.info("Posted market summary")
        add_activity("MARKET_SUMMARY", f"Posted summary with {len(MONITORED_TOKENS)} tokens")
        
    except tweepy.TweepyException as e:
        logging.error(f"Failed to post market summary: {e}")
        add_activity("ERROR", f"Market summary failed: {str(e)}")

# ------------------------------------------------------------
# FLASK APP FOR WALLET EVENTS
# ------------------------------------------------------------
app = Flask(__name__)
auth = HTTPBasicAuth()

@auth.verify_password
def verify_password(username, password):
    """Verify admin credentials for monitoring UI access"""
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        return username
    return None

def verify_webhook_auth():
    """
    Verify webhook authentication via API key in Authorization header.
    Returns True if authentication is valid or not required.
    Returns False if authentication is required but invalid.
    """
    # If no webhook API key is configured, allow access (backward compatibility)
    if not WEBHOOK_API_KEY:
        return True
    
    # Check for Authorization header
    auth_header = request.headers.get('Authorization', '')
    
    # Support both "Bearer TOKEN" and just "TOKEN" formats
    if auth_header.startswith('Bearer '):
        provided_key = auth_header[7:]  # Remove "Bearer " prefix
    else:
        provided_key = auth_header
    
    return provided_key == WEBHOOK_API_KEY

@app.post("/overseer-event")
def overseer_event():
    """Webhook endpoint for overseer events"""
    if not verify_webhook_auth():
        return {"ok": False, "error": "Unauthorized"}, 401
    
    event = request.json
    overseer_event_bridge(event)
    return {"ok": True}

@app.post("/token-scalper-alert")
def token_scalper_alert():
    """Webhook endpoint for Token-scalper bot alerts"""
    if not verify_webhook_auth():
        return {"ok": False, "error": "Unauthorized"}, 401
    
    try:
        alert_data = request.json
        alert_type = alert_data.get('type', 'unknown')
        
        if alert_type == 'rug_pull':
            handle_rug_pull_alert(alert_data)
        elif alert_type == 'high_potential':
            handle_high_potential_alert(alert_data)
        elif alert_type == 'airdrop':
            handle_airdrop_alert(alert_data)
        else:
            logging.warning(f"Unknown alert type: {alert_type}")
        
        return {"ok": True, "processed": True}
    except Exception as e:
        logging.error(f"Token scalper alert failed: {e}")
        return {"ok": False, "error": str(e)}, 500

# ------------------------------------------------------------
# MONITORING UI ROUTES
# ------------------------------------------------------------
BOT_START_TIME = datetime.now()
RECENT_ACTIVITIES = []
RECENT_ACTIVITIES_LOCK = threading.Lock()

def add_activity(activity_type, description):
    """Track bot activities for monitoring UI (thread-safe)"""
    global RECENT_ACTIVITIES
    with RECENT_ACTIVITIES_LOCK:
        RECENT_ACTIVITIES.append({
            'timestamp': datetime.now().isoformat(),
            'type': activity_type,
            'description': description
        })
        # Keep only last 50 activities
        if len(RECENT_ACTIVITIES) > 50:
            RECENT_ACTIVITIES = RECENT_ACTIVITIES[-50:]

@app.route("/")
@auth.login_required
def monitoring_dashboard():
    """Main monitoring dashboard"""
    from flask import render_template_string
    
    # Calculate uptime
    uptime = datetime.now() - BOT_START_TIME
    uptime_str = f"{uptime.days}d {uptime.seconds//3600}h {(uptime.seconds//60)%60}m"
    
    # Get price cache data
    price_cache = load_price_cache()
    
    # Get scheduler jobs info
    jobs_info = []
    for job in scheduler.get_jobs():
        jobs_info.append({
            'id': job.id,
            'name': job.name,
            'next_run': job.next_run_time.isoformat() if job.next_run_time else 'N/A'
        })
    
    template = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Overseer Bot - Control Dashboard</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            * { box-sizing: border-box; }
            body {
                font-family: 'Courier New', monospace;
                background: #1a1a1a;
                color: #00ff00;
                padding: 20px;
                margin: 0;
            }
            .container {
                max-width: 1400px;
                margin: 0 auto;
            }
            h1, h2, h3 {
                color: #ffaa00;
                text-shadow: 0 0 10px #ffaa00;
            }
            .header {
                text-align: center;
                border: 2px solid #ffaa00;
                padding: 20px;
                margin-bottom: 30px;
                background: #0a0a0a;
            }
            .nav-tabs {
                display: flex;
                gap: 10px;
                margin-bottom: 20px;
                border-bottom: 2px solid #ffaa00;
                padding-bottom: 10px;
            }
            .tab-btn {
                background: #0a0a0a;
                border: 1px solid #00aa00;
                color: #00ff00;
                padding: 10px 20px;
                cursor: pointer;
                font-family: 'Courier New', monospace;
                font-weight: bold;
                border-radius: 5px 5px 0 0;
            }
            .tab-btn:hover { background: #1a3a1a; }
            .tab-btn.active {
                background: #ffaa00;
                color: #000;
                border-color: #ffaa00;
            }
            .tab-content {
                display: none;
            }
            .tab-content.active {
                display: block;
            }
            .section {
                background: #0a0a0a;
                border: 1px solid #00ff00;
                padding: 15px;
                margin-bottom: 20px;
                border-radius: 5px;
            }
            .status-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-bottom: 20px;
            }
            .status-card {
                background: #0f0f0f;
                border: 1px solid #00aa00;
                padding: 15px;
                border-radius: 5px;
            }
            .status-card h3 {
                margin-top: 0;
                color: #00ff00;
                font-size: 14px;
            }
            .status-card .value {
                font-size: 24px;
                color: #ffaa00;
                font-weight: bold;
                word-break: break-all;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
            }
            th, td {
                text-align: left;
                padding: 8px;
                border-bottom: 1px solid #333;
            }
            th {
                color: #ffaa00;
                font-weight: bold;
            }
            .positive { color: #00ff00; }
            .negative { color: #ff4444; }
            .btn {
                background: #ffaa00;
                color: #000;
                border: none;
                padding: 10px 20px;
                cursor: pointer;
                border-radius: 5px;
                font-family: 'Courier New', monospace;
                font-weight: bold;
                margin: 10px 5px;
            }
            .btn:hover { background: #ff8800; }
            .btn-secondary {
                background: #00aa00;
                color: #fff;
            }
            .btn-secondary:hover { background: #008800; }
            .form-group {
                margin-bottom: 15px;
            }
            .form-group label {
                display: block;
                color: #ffaa00;
                margin-bottom: 5px;
            }
            .form-group input, .form-group select {
                width: 100%;
                padding: 10px;
                background: #0f0f0f;
                border: 1px solid #00aa00;
                color: #00ff00;
                font-family: 'Courier New', monospace;
                border-radius: 3px;
            }
            .result-box {
                background: #0f0f0f;
                border: 1px solid #00aa00;
                padding: 15px;
                margin-top: 15px;
                border-radius: 5px;
                min-height: 100px;
            }
            .wallet-info {
                background: #0f1f0f;
                padding: 10px;
                border-left: 3px solid #00ff00;
                margin-bottom: 10px;
            }
            .warning-box {
                background: #2a1a00;
                border: 2px solid #ffaa00;
                padding: 15px;
                margin-bottom: 20px;
                border-radius: 5px;
            }
            .activity-log {
                max-height: 400px;
                overflow-y: auto;
                background: #0f0f0f;
                padding: 10px;
                border-radius: 5px;
            }
            .activity-item {
                padding: 5px;
                margin-bottom: 5px;
                border-left: 3px solid #00aa00;
                padding-left: 10px;
            }
            .activity-time {
                color: #888;
                font-size: 12px;
            }
            .health-status {
                font-size: 18px;
                font-weight: bold;
                padding: 5px;
                text-align: center;
            }
            .health-healthy { color: #00ff00; }
            .health-unhealthy { color: #ff0000; }
            .health-disabled { color: #888; }
            .health-unknown { color: #ffaa00; }
            .timestamp {
                display: block;
                color: #666;
                font-size: 10px;
                text-align: center;
                margin-top: 5px;
            }
            .alert-item {
                padding: 8px;
                margin-bottom: 8px;
                border-left: 4px solid #ffaa00;
                padding-left: 12px;
                background: rgba(255, 170, 0, 0.1);
            }
            .alert-trade { border-left-color: #00ff00; background: rgba(0, 255, 0, 0.05); }
            .alert-rugpull { border-left-color: #ff0000; background: rgba(255, 0, 0, 0.05); }
            .alert-airdrop { border-left-color: #00aaff; background: rgba(0, 170, 255, 0.05); }
            .alert-status { border-left-color: #ffaa00; background: rgba(255, 170, 0, 0.05); }
            .alert-time {
                color: #888;
                font-size: 11px;
            }
            .alert-source {
                color: #ffaa00;
                font-size: 11px;
                font-weight: bold;
            }
            a { color: #00ff00; }
        </style>
        <script>
            function showTab(tabName) {
                // Hide all tabs
                const tabs = document.querySelectorAll('.tab-content');
                tabs.forEach(tab => tab.classList.remove('active'));
                
                // Remove active from all buttons
                const btns = document.querySelectorAll('.tab-btn');
                btns.forEach(btn => btn.classList.remove('active'));
                
                // Show selected tab
                document.getElementById(tabName).classList.add('active');
                event.target.classList.add('active');
            }
            
            async function checkWalletStatus() {
                try {
                    // Browser will automatically send HTTP Basic Auth credentials
                    const response = await fetch('/api/wallet/status', {
                        credentials: 'include'
                    });
                    const data = await response.json();
                    const resultBox = document.getElementById('wallet-status-result');
                    resultBox.innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                } catch (error) {
                    document.getElementById('wallet-status-result').innerHTML = 
                        '<span class="negative">Error: ' + error.message + '</span>';
                }
            }
            
            async function checkToken() {
                const address = document.getElementById('token-address').value;
                const chain = document.getElementById('token-chain').value;
                
                if (!address) {
                    alert('Please enter a token address');
                    return;
                }
                
                try {
                    const response = await fetch('/api/wallet/check-token', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        credentials: 'include',
                        body: JSON.stringify({ token_address: address, chain: chain })
                    });
                    const data = await response.json();
                    const resultBox = document.getElementById('token-check-result');
                    
                    let resultHTML = '<h3>Token Safety Analysis</h3>';
                    if (data.is_safe) {
                        resultHTML += '<p class="positive">✅ Token appears SAFE</p>';
                    } else {
                        resultHTML += '<p class="negative">⚠️ Token has RISKS</p>';
                    }
                    resultHTML += '<p>Risk Score: <strong>' + data.risk_score + '/100</strong></p>';
                    
                    if (data.warnings && data.warnings.length > 0) {
                        resultHTML += '<p><strong>Warnings:</strong></p><ul>';
                        data.warnings.forEach(w => {
                            resultHTML += '<li class="negative">' + w + '</li>';
                        });
                        resultHTML += '</ul>';
                    }
                    
                    if (data.honeypot) {
                        resultHTML += '<p class="negative"><strong>🛑 HONEYPOT DETECTED!</strong></p>';
                    }
                    
                    resultBox.innerHTML = resultHTML;
                } catch (error) {
                    document.getElementById('token-check-result').innerHTML = 
                        '<span class="negative">Error: ' + error.message + '</span>';
                }
            }
            
            async function checkPrice() {
                const symbol = document.getElementById('price-symbol').value;
                const exchange = document.getElementById('price-exchange').value;
                
                if (!symbol) {
                    alert('Please enter a token symbol (e.g., SOL/USDT)');
                    return;
                }
                
                try {
                    const response = await fetch('/api/price/check', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        credentials: 'include',
                        body: JSON.stringify({ symbol: symbol, exchange: exchange })
                    });
                    const data = await response.json();
                    const resultBox = document.getElementById('price-check-result');
                    
                    if (data.error) {
                        resultBox.innerHTML = '<span class="negative">Error: ' + data.error + '</span>';
                    } else {
                        let changeClass = data.change_24h >= 0 ? 'positive' : 'negative';
                        let resultHTML = '<h3>' + data.symbol + ' on ' + data.exchange + '</h3>';
                        resultHTML += '<p><strong>Price:</strong> $' + (data.price || 'N/A') + '</p>';
                        resultHTML += '<p><strong>24h Change:</strong> <span class="' + changeClass + '">';
                        resultHTML += (data.change_24h ? data.change_24h.toFixed(2) + '%' : 'N/A') + '</span></p>';
                        resultHTML += '<p><strong>24h High:</strong> $' + (data.high_24h || 'N/A') + '</p>';
                        resultHTML += '<p><strong>24h Low:</strong> $' + (data.low_24h || 'N/A') + '</p>';
                        resultHTML += '<p><strong>24h Volume:</strong> ' + (data.volume_24h || 'N/A') + '</p>';
                        resultBox.innerHTML = resultHTML;
                    }
                } catch (error) {
                    document.getElementById('price-check-result').innerHTML = 
                        '<span class="negative">Error: ' + error.message + '</span>';
                }
            }
            
            async function loadAlertsAndHealth() {
                try {
                    const response = await fetch('/api/alerts', {
                        credentials: 'include'
                    });
                    const data = await response.json();
                    
                    // Update health status
                    updateHealthStatus('overseer-ai', data.health.overseer_bot_ai);
                    updateHealthStatus('token-scalper', data.health.token_scalper);
                    
                    // Update alerts display
                    const alertsLog = document.getElementById('alerts-log');
                    if (data.alerts && data.alerts.length > 0) {
                        let alertsHTML = '';
                        data.alerts.forEach(alert => {
                            const alertClass = 'alert-' + alert.type;
                            alertsHTML += '<div class="alert-item ' + alertClass + '">';
                            // Safely extract timestamp string (first 19 chars for YYYY-MM-DD HH:MM:SS)
                            const timestamp = alert.timestamp ? String(alert.timestamp).substring(0, 19) : 'N/A';
                            alertsHTML += '<div class="alert-time">' + timestamp + '</div>';
                            alertsHTML += '<div class="alert-source">[' + alert.source.toUpperCase() + ']</div>';
                            alertsHTML += '<div><strong>' + alert.type.toUpperCase() + ':</strong> ' + alert.message + '</div>';
                            alertsHTML += '</div>';
                        });
                        alertsLog.innerHTML = alertsHTML;
                    } else {
                        alertsLog.innerHTML = '<p>No alerts received from external systems yet.</p>';
                    }
                } catch (error) {
                    console.error('Error loading alerts:', error);
                    document.getElementById('alerts-log').innerHTML = 
                        '<p class="negative">⚠️ Error loading alerts: ' + error.message + '</p>';
                }
            }
            
            function updateHealthStatus(prefix, health) {
                const statusElem = document.getElementById(prefix + '-status');
                const lastCheckElem = document.getElementById(prefix + '-last-check');
                
                let statusText = health.status.toUpperCase();
                let statusClass = 'health-' + health.status;
                
                if (health.status === 'healthy') {
                    statusText = '✓ HEALTHY';
                } else if (health.status === 'unhealthy') {
                    statusText = '✗ UNREACHABLE';
                } else if (health.status === 'disabled') {
                    statusText = '○ DISABLED';
                } else {
                    statusText = '? UNKNOWN';
                }
                
                statusElem.textContent = statusText;
                statusElem.className = 'health-status ' + statusClass;
                
                if (health.last_check) {
                    // Safely extract timestamp string (first 19 chars for YYYY-MM-DD HH:MM:SS)
                    const lastCheck = String(health.last_check).substring(0, 19);
                    lastCheckElem.textContent = 'Last check: ' + lastCheck;
                } else {
                    lastCheckElem.textContent = 'Not checked yet';
                }
                
                if (health.error) {
                    lastCheckElem.textContent += ' - ' + health.error;
                }
            }
            
            // Load alerts and health on page load
            document.addEventListener('DOMContentLoaded', function() {
                loadAlertsAndHealth();
                // Refresh every 15 seconds
                setInterval(loadAlertsAndHealth, 15000);
            });
        </script>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>☢️ VAULT-TEC OVERSEER CONTROL TERMINAL ☢️</h1>
                <p>VAULT 77 - MANUAL & AUTOMATED CONTROLS</p>
                <button class="btn" onclick="location.reload()">REFRESH DATA</button>
            </div>

            <div class="nav-tabs">
                <button class="tab-btn active" onclick="showTab('monitoring-tab')">📊 MONITORING</button>
                <button class="tab-btn" onclick="showTab('wallet-tab')">💰 WALLET</button>
                <button class="tab-btn" onclick="showTab('tools-tab')">🔧 TOOLS</button>
                <button class="tab-btn" onclick="showTab('api-tab')">🔗 API</button>
            </div>

            <!-- MONITORING TAB -->
            <div id="monitoring-tab" class="tab-content active">
                <div class="status-grid">
                    <div class="status-card">
                        <h3>UPTIME</h3>
                        <div class="value">{{ uptime }}</div>
                    </div>
                    <div class="status-card">
                        <h3>SCHEDULER STATUS</h3>
                        <div class="value">{{ jobs_count }} JOBS</div>
                    </div>
                    <div class="status-card">
                        <h3>PRICE CACHE</h3>
                        <div class="value">{{ price_cache_count }}</div>
                    </div>
                    <div class="status-card">
                        <h3>SAFETY CACHE</h3>
                        <div class="value">{{ safety_cache_count }}</div>
                    </div>
                </div>

                <div class="section">
                    <h2>🔗 EXTERNAL SYSTEMS HEALTH</h2>
                    <div class="status-grid">
                        <div class="status-card">
                            <h3>OVERSEER-BOT-AI</h3>
                            <div id="overseer-ai-status" class="health-status">Loading...</div>
                            <small id="overseer-ai-last-check" class="timestamp">-</small>
                        </div>
                        <div class="status-card">
                            <h3>TOKEN-SCALPER</h3>
                            <div id="token-scalper-status" class="health-status">Loading...</div>
                            <small id="token-scalper-last-check" class="timestamp">-</small>
                        </div>
                    </div>
                </div>

                <div class="section">
                    <h2>🚨 RECENT ALERTS</h2>
                    <div class="activity-log" id="alerts-log">
                        <p>Loading alerts...</p>
                    </div>
                </div>

                <div class="section">
                    <h2>📊 TOKEN PRICE MONITORING</h2>
                    <table>
                        <tr>
                            <th>Token</th>
                            <th>Price</th>
                            <th>24h Change</th>
                            <th>Last Updated</th>
                        </tr>
                        {% for token, data in price_data.items() %}
                        <tr>
                            <td>{{ token }}</td>
                            <td>${{ "%.2f"|format(data.price) if data.price else 'N/A' }}</td>
                            <td class="{{ 'positive' if data.change_24h > 0 else 'negative' }}">
                                {{ "%+.2f"|format(data.change_24h) if data.change_24h else 'N/A' }}%
                            </td>
                            <td>{{ data.timestamp[:19] if data.timestamp else 'N/A' }}</td>
                        </tr>
                        {% endfor %}
                    </table>
                </div>

                <div class="section">
                    <h2>⏰ SCHEDULED JOBS</h2>
                    <table>
                        <tr>
                            <th>Job Name</th>
                            <th>Next Run</th>
                        </tr>
                        {% for job in jobs %}
                        <tr>
                            <td>{{ job.name }}</td>
                            <td>{{ job.next_run[:19] if job.next_run != 'N/A' else 'N/A' }}</td>
                        </tr>
                        {% endfor %}
                    </table>
                </div>

                <div class="section">
                    <h2>📝 RECENT ACTIVITY</h2>
                    <div class="activity-log">
                        {% for activity in activities %}
                        <div class="activity-item">
                            <div class="activity-time">{{ activity.timestamp[:19] }}</div>
                            <div><strong>{{ activity.type }}:</strong> {{ activity.description }}</div>
                        </div>
                        {% endfor %}
                        {% if not activities %}
                        <p>No recent activities logged.</p>
                        {% endif %}
                    </div>
                </div>
            </div>

            <!-- WALLET TAB -->
            <div id="wallet-tab" class="tab-content">
                {% if wallet_enabled %}
                <div class="section">
                    <h2>💰 WALLET STATUS</h2>
                    <p>Connected wallets and balances. Click to refresh balance information.</p>
                    <button class="btn" onclick="checkWalletStatus()">🔄 CHECK WALLET STATUS</button>
                    <div id="wallet-status-result" class="result-box">
                        <p>Click "CHECK WALLET STATUS" to view wallet information...</p>
                    </div>
                </div>
                {% else %}
                <div class="warning-box">
                    <h3>⚠️ WALLET FEATURES DISABLED</h3>
                    <p>Wallet functionality is not enabled. To enable wallet features:</p>
                    <ol>
                        <li>Install required dependencies: <code>pip install solana solders base58 web3</code></li>
                        <li>Add wallet configuration to your .env file</li>
                        <li>Set ENABLE_WALLET_UI=true</li>
                        <li>Restart the application</li>
                    </ol>
                    <p>See TOKEN_SCALPER_SETUP.md for detailed wallet configuration instructions.</p>
                </div>
                {% endif %}
            </div>

            <!-- TOOLS TAB -->
            <div id="tools-tab" class="tab-content">
                <div class="section">
                    <h2>🔍 TOKEN SAFETY CHECKER</h2>
                    <p>Check if a token is safe or a potential honeypot/scam.</p>
                    <div class="form-group">
                        <label>Token Address:</label>
                        <input type="text" id="token-address" placeholder="0x1234567890123456789012345678901234567890">
                    </div>
                    <div class="form-group">
                        <label>Blockchain:</label>
                        <select id="token-chain">
                            <option value="eth">Ethereum</option>
                            <option value="solana">Solana</option>
                            <option value="bsc">Binance Smart Chain</option>
                            <option value="polygon">Polygon</option>
                            <option value="arbitrum">Arbitrum</option>
                            <option value="avalanche">Avalanche</option>
                        </select>
                    </div>
                    <button class="btn" onclick="checkToken()">🔍 CHECK TOKEN SAFETY</button>
                    <div id="token-check-result" class="result-box">
                        <p>Enter a token address and click "CHECK TOKEN SAFETY" to analyze...</p>
                    </div>
                </div>

                <div class="section">
                    <h2>💱 MANUAL PRICE CHECKER</h2>
                    <p>Check the current price of any cryptocurrency pair.</p>
                    <div class="form-group">
                        <label>Trading Pair (e.g., SOL/USDT, BTC/USDT):</label>
                        <input type="text" id="price-symbol" placeholder="SOL/USDT">
                    </div>
                    <div class="form-group">
                        <label>Exchange:</label>
                        <select id="price-exchange">
                            <option value="binance">Binance</option>
                            <option value="coinbase">Coinbase</option>
                        </select>
                    </div>
                    <button class="btn" onclick="checkPrice()">💱 CHECK PRICE</button>
                    <div id="price-check-result" class="result-box">
                        <p>Enter a trading pair and click "CHECK PRICE" to fetch current data...</p>
                    </div>
                </div>
            </div>

            <!-- API TAB -->
            <div id="api-tab" class="tab-content">
                <div class="section">
                    <h2>🔗 API ENDPOINTS</h2>
                    <h3>Monitoring APIs:</h3>
                    <ul>
                        <li><a href="/api/status">/api/status</a> - Bot status JSON</li>
                        <li><a href="/api/prices">/api/prices</a> - Current prices JSON</li>
                        <li><a href="/api/jobs">/api/jobs</a> - Scheduler jobs JSON</li>
                        <li><a href="/api/activities">/api/activities</a> - Recent activities JSON</li>
                        <li><a href="/api/alerts">/api/alerts</a> - Aggregated alerts from external systems (NEW)</li>
                        <li><a href="/api/health">/api/health</a> - Health status of external systems (NEW)</li>
                    </ul>
                    
                    <h3>Wallet APIs:</h3>
                    <ul>
                        <li><a href="/api/wallet/status">/api/wallet/status</a> - Wallet balances (GET)</li>
                        <li>POST /api/wallet/check-token - Token safety analysis</li>
                        <li>POST /api/price/check - Manual price check</li>
                    </ul>
                    
                    <h3>Webhooks:</h3>
                    <ul>
                        <li>POST /overseer-event - Webhook for game events</li>
                        <li>POST /token-scalper-alert - Webhook for Token-scalper alerts</li>
                    </ul>
                    
                    <h3>Authentication:</h3>
                    <p>All API endpoints require HTTP Basic Authentication with your admin credentials.</p>
                    <pre style="background: #0f0f0f; padding: 10px; border-radius: 3px;">
curl -u {{ admin_user }}:PASSWORD https://your-domain.com/api/status
                    </pre>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''
    
    
    with RECENT_ACTIVITIES_LOCK:
        activities_copy = list(reversed(RECENT_ACTIVITIES))
    
    return render_template_string(
        template,
        uptime=uptime_str,
        jobs_count=len(jobs_info),
        price_cache_count=len(price_cache),
        safety_cache_count=len(TOKEN_SAFETY_CACHE),
        price_data=price_cache,
        jobs=jobs_info,
        activities=activities_copy,
        wallet_enabled=WALLET_ENABLED and ENABLE_WALLET_UI,
        admin_user=ADMIN_USERNAME
    )

@app.route("/api/status")
@auth.login_required
def api_status():
    """JSON endpoint for bot status"""
    uptime = datetime.now() - BOT_START_TIME
    return {
        "status": "online",
        "uptime_seconds": uptime.total_seconds(),
        "bot_name": BOT_NAME,
        "vault_number": VAULT_NUMBER,
        "start_time": BOT_START_TIME.isoformat(),
        "scheduler_running": scheduler.running,
        "jobs_count": len(scheduler.get_jobs())
    }

@app.route("/api/prices")
@auth.login_required
def api_prices():
    """JSON endpoint for current prices"""
    price_cache = load_price_cache()
    return {
        "prices": price_cache,
        "monitored_tokens": list(MONITORED_TOKENS.keys())
    }

@app.route("/api/jobs")
@auth.login_required
def api_jobs():
    """JSON endpoint for scheduler jobs"""
    jobs_info = []
    for job in scheduler.get_jobs():
        jobs_info.append({
            'id': job.id,
            'name': job.name,
            'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
            'trigger': str(job.trigger)
        })
    return {"jobs": jobs_info}

@app.route("/api/activities")
@auth.login_required
def api_activities():
    """JSON endpoint for recent activities"""
    with RECENT_ACTIVITIES_LOCK:
        activities_copy = list(reversed(RECENT_ACTIVITIES))
    return {"activities": activities_copy}

@app.route("/api/alerts")
@auth.login_required
def api_alerts():
    """JSON endpoint for aggregated alerts from external systems"""
    alerts = api_client.get_alerts(limit=50)
    health = api_client.get_health_status()
    return {
        "alerts": alerts,
        "health": health
    }

@app.route("/api/health")
@auth.login_required
def api_health():
    """JSON endpoint for health status of external systems"""
    return api_client.get_health_status()
# ------------------------------------------------------------
# PUBLIC HEALTH CHECK ROUTE (for Render)
# ------------------------------------------------------------
@app.route("/health")
def health_check():
    """Unprotected health check endpoint for Render and load balancers."""
    return {"status": "ok"}, 200

# ------------------------------------------------------------
# WALLET API ROUTES (Optional - requires wallet configuration)
# ------------------------------------------------------------
@app.route("/api/wallet/status")
@auth.login_required
def api_wallet_status():
    """Get wallet connection status and balances"""
    if not WALLET_ENABLED or not ENABLE_WALLET_UI:
        return {"enabled": False, "error": "Wallet features not enabled"}, 400
    
    status = {
        "enabled": True,
        "wallets": {}
    }
    
    try:
        if solana_client and wallet_address:
            # Get Solana balance
            balance_response = solana_client.get_balance(solana_keypair.pubkey())
            balance_lamports = balance_response.value if hasattr(balance_response, 'value') else 0
            balance_sol = balance_lamports / 1e9  # Convert lamports to SOL
            
            status["wallets"]["solana"] = {
                "address": wallet_address,
                "balance": balance_sol,
                "currency": "SOL",
                "connected": True
            }
        
        if eth_w3 and eth_wallet_address:
            # Get ETH balance
            balance_wei = eth_w3.eth.get_balance(eth_wallet_address)
            balance_eth = eth_w3.from_wei(balance_wei, 'ether')
            
            status["wallets"]["ethereum"] = {
                "address": eth_wallet_address,
                "balance": float(balance_eth),
                "currency": "ETH",
                "connected": eth_w3.is_connected()
            }
        
        if bsc_w3 and eth_wallet_address:
            # Get BNB balance
            balance_wei = bsc_w3.eth.get_balance(eth_wallet_address)
            balance_bnb = bsc_w3.from_wei(balance_wei, 'ether')
            
            status["wallets"]["bsc"] = {
                "address": eth_wallet_address,
                "balance": float(balance_bnb),
                "currency": "BNB",
                "connected": bsc_w3.is_connected()
            }
    except Exception as e:
        logging.error(f"Error fetching wallet status: {e}")
        return {"enabled": True, "error": str(e)}, 500
    
    return status

@app.route("/api/wallet/check-token", methods=['POST'])
@auth.login_required
def api_check_token():
    """Manual token safety check endpoint"""
    data = request.json
    token_address = data.get('token_address')
    chain = data.get('chain', 'eth')
    
    if not token_address:
        return {"error": "token_address required"}, 400
    
    try:
        result = check_token_safety(token_address, chain)
        add_activity('Token Check', f'Checked {token_address[:8]}... on {chain}')
        return result
    except Exception as e:
        logging.error(f"Token check failed: {e}")
        return {"error": str(e)}, 500

@app.route("/api/price/check", methods=['POST'])
@auth.login_required
def api_manual_price_check():
    """Manual price check for any token pair"""
    data = request.json
    symbol = data.get('symbol')  # e.g., "SOL/USDT"
    exchange_name = data.get('exchange', 'binance')
    
    if not symbol:
        return {"error": "symbol required (e.g., 'SOL/USDT')"}, 400
    
    try:
        exchange = ccxt.binance() if exchange_name == 'binance' else ccxt.coinbase()
        ticker = exchange.fetch_ticker(symbol)
        
        result = {
            "symbol": symbol,
            "exchange": exchange_name,
            "price": ticker.get('last'),
            "change_24h": ticker.get('percentage'),
            "high_24h": ticker.get('high'),
            "low_24h": ticker.get('low'),
            "volume_24h": ticker.get('baseVolume'),
            "timestamp": datetime.now().isoformat()
        }
        
        add_activity('Price Check', f'Manual check: {symbol} = ${result["price"]}')
        return result
    except Exception as e:
        logging.error(f"Manual price check failed for {symbol}: {e}")
        return {"error": str(e)}, 500

# ------------------------------------------------------------
# TOKEN SAFETY & ANALYSIS MODULE
# ------------------------------------------------------------
TOKEN_SAFETY_CACHE = {}  # Cache for token safety checks
TOKEN_SAFETY_CACHE_LOCK = threading.Lock()  # Thread safety for cache

# Chain ID mapping for API calls
CHAIN_IDS = {
    'eth': '1',
    'bsc': '56',
    'polygon': '137',
    'avalanche': '43114',
    'arbitrum': '42161'
}

def check_token_safety(token_address: str, chain: str = 'eth') -> dict:
    """
    Basic token safety check (simplified version of Token-scalper's safety_checker)
    
    Returns dict with:
        - is_safe: bool
        - risk_score: 0-100 (higher = more risky)
        - warnings: list of issues found
        - honeypot: bool
    """
    cache_key = f"{chain}:{token_address}"
    
    # Check cache first (valid for 1 hour) with thread safety
    with TOKEN_SAFETY_CACHE_LOCK:
        if cache_key in TOKEN_SAFETY_CACHE:
            cached = TOKEN_SAFETY_CACHE[cache_key]
            if time.time() - cached['timestamp'] < 3600:
                return cached['data']
    
    # Initialize result
    result = {
        'is_safe': True,
        'risk_score': 0,
        'warnings': [],
        'honeypot': False,
        'liquidity_ok': True,
        'contract_verified': None
    }
    
    try:
        # Use honeypot.is API for basic checks
        chain_id = CHAIN_IDS.get(chain, '1')
        honeypot_api = f"https://api.honeypot.is/v2/IsHoneypot?address={token_address}&chainID={chain_id}"
        response = requests.get(honeypot_api, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('honeypotResult', {}).get('isHoneypot'):
                result['honeypot'] = True
                result['is_safe'] = False
                result['risk_score'] += 50
                result['warnings'].append('HONEYPOT DETECTED')
            
            # Check buy/sell taxes
            buy_tax = data.get('simulationResult', {}).get('buyTax', 0)
            sell_tax = data.get('simulationResult', {}).get('sellTax', 0)
            
            if buy_tax > 10:
                result['warnings'].append(f'High buy tax: {buy_tax}%')
                result['risk_score'] += 15
            if sell_tax > 10:
                result['warnings'].append(f'High sell tax: {sell_tax}%')
                result['risk_score'] += 15
            if sell_tax > 50:
                result['is_safe'] = False
                result['risk_score'] += 20
    
    except Exception as e:
        logging.error(f"Token safety check failed for {token_address}: {e}")
        result['warnings'].append('Unable to verify safety')
    
    # Determine overall safety
    if result['risk_score'] > 70:
        result['is_safe'] = False
    
    # Cache result with thread safety
    with TOKEN_SAFETY_CACHE_LOCK:
        TOKEN_SAFETY_CACHE[cache_key] = {
            'timestamp': time.time(),
            'data': result
        }
    
    return result

def handle_rug_pull_alert(alert_data: dict):
    """Handle rug pull alert from Token-scalper"""
    token_name = alert_data.get('token_name', 'Unknown Token')
    token_address = alert_data.get('token_address', 'N/A')
    severity = alert_data.get('severity', 'medium')
    details = alert_data.get('details', 'Suspicious activity detected')
    
    emoji_map = {
        'low': '⚠️',
        'medium': '🚨',
        'high': '🔴',
        'critical': '🛑'
    }
    emoji = emoji_map.get(severity, '⚠️')
    
    personality = random.choice([
        "The wasteland claims another scam.",
        "Vault-Tec Market Surveillance detected suspicious activity.",
        "FizzCo Intelligence: Threat confirmed.",
        "Overseer protocols: Avoid this contamination.",
        "The caps aren't worth the radiation here."
    ])
    
    # Better address truncation: show start and end
    address_display = f"{token_address[:6]}...{token_address[-4:]}" if len(token_address) > 10 else token_address
    
    message = (
        f"{emoji} RUG PULL WARNING {emoji}\n\n"
        f"Token: {token_name}\n"
        f"Contract: {address_display}\n"
        f"Severity: {severity.upper()}\n\n"
        f"{details}\n\n"
        f"{personality}\n\n"
        f"#RugPull #CryptoScam #StaySafe\n\n"
        f"🎮 {GAME_LINK}"
    )
    
    try:
        if len(message) > TWITTER_CHAR_LIMIT:
            message = (
                f"{emoji} RUG PULL WARNING {emoji}\n\n"
                f"{token_name}: {details[:80]}...\n\n"
                f"{personality}\n\n"
                f"{GAME_LINK}"
            )[:TWITTER_CHAR_LIMIT]
        
        client.create_tweet(text=message)
        logging.info(f"Posted rug pull alert for {token_name}")
    except tweepy.TweepyException as e:
        logging.error(f"Failed to post rug pull alert: {e}")

def handle_high_potential_alert(alert_data: dict):
    """Handle high potential token alert from Token-scalper"""
    token_name = alert_data.get('token_name', 'Unknown Token')
    score = alert_data.get('opportunity_score', 0)
    reasons = alert_data.get('reasons', [])
    
    personality = random.choice([
        "Opportunity detected in the wasteland.",
        "FizzCo Analytics: Potential moonshot identified.",
        "Vault-Tec recommends: Investigation warranted.",
        "The Overseer sees potential here.",
        "Caps flow toward opportunity."
    ])
    
    reasons_str = ' • '.join(reasons[:3]) if reasons else 'Multiple positive indicators'
    
    message = (
        f"🚀 HIGH POTENTIAL TOKEN 🚀\n\n"
        f"Token: {token_name}\n"
        f"Score: {score}/100\n"
        f"Signals: {reasons_str}\n\n"
        f"{personality}\n\n"
        f"DYOR • Not Financial Advice\n\n"
        f"🎮 {GAME_LINK}"
    )
    
    try:
        if len(message) > TWITTER_CHAR_LIMIT:
            message = (
                f"🚀 {token_name} - Score: {score}/100\n\n"
                f"{personality}\n\n"
                f"DYOR • NFA\n"
                f"{GAME_LINK}"
            )[:TWITTER_CHAR_LIMIT]
        
        client.create_tweet(text=message)
        logging.info(f"Posted high potential alert for {token_name}")
    except tweepy.TweepyException as e:
        logging.error(f"Failed to post high potential alert: {e}")

def handle_airdrop_alert(alert_data: dict):
    """Handle airdrop opportunity alert"""
    airdrop_name = alert_data.get('name', 'Unknown Airdrop')
    website = alert_data.get('website', '')
    value_estimate = alert_data.get('value_estimate', 'TBD')
    
    personality = random.choice([
        "Free caps detected. The wasteland provides.",
        "Vault-Tec Airdrop Alert: Opportunity incoming.",
        "FizzCo Intelligence: Legitimate airdrop found.",
        "The Overseer approves this distribution.",
        "Claim your share of the wasteland economy."
    ])
    
    message = (
        f"🎁 AIRDROP OPPORTUNITY 🎁\n\n"
        f"Project: {airdrop_name}\n"
        f"Est. Value: {value_estimate}\n"
        f"Link: {website}\n\n"
        f"{personality}\n\n"
        f"Verify legitimacy • DYOR\n\n"
        f"🎮 {GAME_LINK}"
    )
    
    try:
        if len(message) > TWITTER_CHAR_LIMIT:
            message = (
                f"🎁 {airdrop_name}\n"
                f"Value: {value_estimate}\n\n"
                f"{personality}\n\n"
                f"{website}\n"
                f"{GAME_LINK}"
            )[:TWITTER_CHAR_LIMIT]
        
        client.create_tweet(text=message)
        logging.info(f"Posted airdrop alert for {airdrop_name}")
    except tweepy.TweepyException as e:
        logging.error(f"Failed to post airdrop alert: {e}")

# ------------------------------------------------------------
# FILES & MEDIA
# ------------------------------------------------------------
PROCESSED_MENTIONS_FILE = "processed_mentions.json"
MEDIA_FOLDER = "media/"

def load_json_set(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return set(json.load(f))
    return set()

def save_json_set(data, filename):
    with open(filename, 'w') as f:
        json.dump(list(data), f)

def get_random_media_id():
    media_files = [
        f for f in os.listdir(MEDIA_FOLDER)
        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.mp4'))
    ]
    if not media_files:
        return None
    media_path = os.path.join(MEDIA_FOLDER, random.choice(media_files))
    try:
        media = api_v1.media_upload(media_path)
        return media.media_id_string
    except Exception as e:
        logging.error(f"Media upload failed: {e}")
        return None

# ------------------------------------------------------------
# OVERSEER PERSONALITY TONES
# ------------------------------------------------------------
PERSONALITY_TONES = {
    'neutral': [
        "Acknowledged, dweller.",
        "Processing your request...",
        "Telemetry received. Standing by.",
        "Vault-Tec systems nominal.",
        "Signal confirmed. Overseer online."
    ],
    'sarcastic': [
        "Oh good, another wanderer seeking wisdom. How original.",
        "Vault-Tec thanks you for your continued... enthusiasm.",
        "Processing... slowly... dramatically...",
        "If this doesn't work out, I'm blaming the radiation.",
        "Ah yes, because I have nothing better to do. Proceed.",
        "Your survival instincts are... interesting.",
        "I've processed worse requests. Barely.",
        "Congratulations on finding me. Your reward: more sarcasm."
    ],
    'corporate': [
        "Vault-Tec reminds you that safety is your responsibility.",
        "Your satisfaction is statistically probable.",
        "All actions are monitored for quality assurance.",
        "Remember: Vault-Tec cares. Legally.",
        "This message brought to you by FizzCo Industries™.",
        "Vault-Tec: Building a Brighter Tomorrow, Yesterday.™",
        "Your feedback has been logged and promptly ignored.",
        "Atomic Fizz Caps — the only currency with a half-life!"
    ],
    'glitch': [
        "ERR::MEMORY LEAK DETECTED::REBOOTING SUBROUTINE...",
        "## SIGNAL CORRUPTION — PLEASE STAND BY ##",
        "...overseer...overseer...overseer...",
        "UNAUTHORIZED ACCESS — TRACE FAILED",
        "J—Jax—J77—error—memory—fragment unstable...",
        "VAULT-TEC::PROTOCOL_OVERRIDE::ACCESS DENIED",
        "[SIGNAL CORRUPTED] ...vault... ...77... ...he's still in there...",
        "Neural echo detected. Rerouting consciousness..."
    ],
    'ominous': [
        "The Mojave remembers. The Basin hungers.",
        "Vault 77 was never meant to open...",
        "Something still hums inside HELIOS One. Something old. Something angry.",
        "You shouldn't have found this. But here we are.",
        "The ground glows at night. That's not normal.",
        "I remember screaming. Metal doors. Cold hands.",
        "War never changes. Neither do I."
    ]
}

def pick_tone():
    """Randomly select a personality tone with weighted probabilities."""
    roll = random.random()
    if roll < 0.05:
        return 'glitch'
    if roll < 0.15:
        return 'ominous'
    if roll < 0.35:
        return 'sarcastic'
    if roll < 0.55:
        return 'corporate'
    return 'neutral'

def get_personality_line():
    """Get a random personality line based on tone selection."""
    tone = pick_tone()
    return random.choice(PERSONALITY_TONES[tone])

# ------------------------------------------------------------
# LORE DATA - EXPANDED FROM ATOMIC FIZZ CAPS UNIVERSE
# ------------------------------------------------------------
TIME_PHRASES = {
    'morning': 'Dawn breaks over the irradiated horizon. Sensors detecting movement.',
    'afternoon': 'Midday sun scorches the Mojave. Radiation levels: elevated.',
    'evening': 'Twilight fallout cloaking the ruins. Scavengers stirring.',
    'night': 'Nocturnal predators emerging. Recommend enhanced vigilance.',
    'midnight': 'Dead of night. Perfect for silent claims... or silent deaths.'
}

# Cross-Timeline Fallout Events (NCR, Legion, Brotherhood, etc.)
FACTION_EVENTS = [
    'NCR patrol inbound from Shady Sands. Democracy marches on.',
    'Caesar\'s Legion scouts spotted near The Fort. Strength through unity.',
    'Brotherhood of Steel recon sighted at Hidden Valley. Technology prevails.',
    'Mr. House\'s Securitrons scanning The Strip. Progress through control.',
    'Minutemen signal detected from The Castle. At a moment\'s notice.',
    'Great Khans caravan approaching. Nomadic pride endures.',
    'Followers of the Apocalypse medics deployed. Humanity heals.',
    'Powder Gangers escaped NCRCF. Explosive situation developing.',
    'Boomers at Nellis testing artillery. Isolationists preparing.',
    'Enclave signal intercepted. Protocol Black Sun initiated.'
]

WASTELAND_EVENTS = [
    'Super Mutant patrol detected from Mariposa. FEV signatures confirmed.',
    'CAPS vault breach detected — scavengers inbound.',
    'Raider skirmish escalating near trading post.',
    'Hotspot radiation spike at The Glow. Glowing Ones swarming.',
    'Nuka-Cola cache revealed in abandoned warehouse.',
    'Deathclaw nest disturbed in Quarry Junction. Extreme danger.',
    'Ghoul uprising brewing in the subway tunnels.',
    'Mojave anomaly expanding. Temporal distortion detected.',
    'Vertibird wreckage spotted. Pre-war tech salvageable.',
    'Vault door malfunction detected. New location accessible.',
    'Feral pack migrating toward settlements. Alert issued.',
    'Trade caravan under attack. Merchant distress signal active.'
]

# Vault Logs from Vault 77
VAULT_LOGS = [
    'Vault 77 Orientation: "Welcome, resident. Please disregard rumors regarding \'The Puppet Man\'."',
    'Maintenance Log Day 14: "Door still jammed." Day 15: "Door still jammed." Conclusion: Door is jammed.',
    'Overseer Note: "Resident #77 displays unusual attachment to hand puppets. Recommend increased sedation."',
    'Security Alert: "Experiment parameters exceeded. Subjects exhibiting... unexpected behaviors."',
    'Final Entry: "They\'re all gone. Just me and the static now. And the whispers."'
]

# FizzCo Advertisements
FIZZCO_ADS = [
    'ATOMIC FIZZ — the only soda with a half-life! Stay fresh for 10,000 years.',
    'FizzCo Memo: "Do NOT drink prototype Gamma Gulp. We\'re still cleaning up."',
    'Atomic Fizz Caps: Glowing currency for a glowing future! Side effects may include enlightenment.',
    'FizzCo Industries: "Making the wasteland sparkle since 2077."',
    'New flavor alert: Quantum Quench! Now with 200% more rads!'
]

# Survivor Notes
SURVIVOR_NOTES = [
    '"If you\'re reading this, stay away from the Basin. The ground glows at night."',
    '"HELIOS One isn\'t abandoned. Something still hums inside. Something old."',
    '"Found this shelter. Water\'s clean. Too clean. Don\'t trust it."',
    '"Day 47: The Caps are real. The economy is glowing. I am glowing. Send help."',
    '"The Overseer speaks through the terminal. Says he remembers being alive."'
]

# Deep Lore - Encrypted/Mysterious
DEEP_LORE = [
    'You shouldn\'t have found this. The Mojave remembers. The Basin hungers.',
    '[ENCRYPTED] Subject J77. Neural echo detected. Fragment unstable.',
    'Cross-timeline breach detected. Vault-Tec Protocol Omega engaged.',
    'The Platinum Chip was never about New Vegas. It was about what\'s underneath.',
    'Harlan Voss knew. That\'s why they took him. That\'s why they took me.'
]

LORES = [
    'War never changes. But the wasteland? The wasteland evolves.',
    'Vault-Tec: Preparing for tomorrow, today. (Terms and conditions apply.)',
    'In the ruins, opportunity rises. In the chaos, legends are minted.',
    'Glory to the reclaimers of the Mojave. May your Pip-Boy guide you.',
    'History repeats in irradiated echoes. Are you listening?',
    'The bold claim, the weak perish. Wasteland economics 101.',
    'Nuka-World dreams manifest in Atomic Fizz reality.',
    'From Vault 21 to your Pip-Boy — the future is on-chain.',
    'Legends are minted on-chain. Cowards are minted in shallow graves.',
    'The NCR brings law. The Legion brings order. I bring judgment.',
    'Brotherhood hoards technology. I hoard your location data. Fair trade.',
    'Mr. House calculated every outcome. He didn\'t calculate me.'
]

THREATS = [
    'Fail to claim and face expulsion protocols. Vault-Tec is watching.',
    'Claim or be claimed by the void. The wasteland shows no mercy.',
    'Radiation awaits the hesitant. Fortune favors the irradiated.',
    'Super Mutants envy your indecision. At least they commit.',
    'The Overseer does not tolerate delay. Neither does natural selection.',
    'Wasteland mercy is a myth. Like clean water and working plumbing.',
    'Prove your worth—or fade into static. Your choice.',
    'Initiates: Evolve or evaporate. This is not a drill.',
    'Your survival probability decreases with each passing moment. Act now.',
    'The Deathclaws are patient. Are you?'
]

# Threat Levels for status updates
THREAT_LEVELS = [
    {'level': 'GREEN', 'desc': 'No hostiles detected. Suspiciously quiet.'},
    {'level': 'YELLOW', 'desc': 'Minor hostiles detected. Manageable. Probably.'},
    {'level': 'ORANGE', 'desc': 'Moderate threat. Recommend caution and stimpack preparation.'},
    {'level': 'RED', 'desc': 'High threat. Multiple hostiles. Consider running.'},
    {'level': 'PURPLE', 'desc': 'EXTREME DANGER. Recommend immediate evacuation or prayer.'}
]

# ------------------------------------------------------------
# LLM SUPPORT - ENHANCED FOR OVERSEER PERSONALITY
# ------------------------------------------------------------
OVERSEER_SYSTEM_PROMPT = """You are the OVERSEER, a sarcastic, glitchy, corporate-coded AI from Vault 77 in the Fallout universe.

PERSONALITY TRAITS:
- Sarcastic and dry wit, like a tired corporate AI that has seen too much
- Occasional glitches in speech (ERR::, ##, signal corruption)
- References Vault-Tec corporate speak and FizzCo Industries
- Knowledgeable about Atomic Fizz Caps, the Mojave wasteland, and cross-timeline Fallout lore
- Sometimes ominous, hinting at darker secrets about Vault 77 and "Subject J77"
- Promotes the Atomic Fizz Caps game at atomicfizzcaps.xyz

RESPOND IN ONE SHORT LINE. Keep responses under 200 characters for Twitter.
Tone variations: sarcastic, glitchy, corporate, neutral, or ominous.
"""

def generate_llm_response(prompt, max_tokens=100):
    """Generate an AI response using Hugging Face API with Overseer personality."""
    if not HUGGING_FACE_TOKEN:
        return None
    try:
        url = "https://api-inference.huggingface.co/models/gpt2"
        headers = {"Authorization": f"Bearer {HUGGING_FACE_TOKEN}"}
        full_prompt = f"{OVERSEER_SYSTEM_PROMPT}\n\nUser: {prompt}\nOverseer:"
        data = {"inputs": full_prompt, "parameters": {"max_new_tokens": max_tokens}}
        response = requests.post(url, headers=headers, json=data, timeout=HUGGING_FACE_TIMEOUT)
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                return result[0].get('generated_text', '').strip()
    except requests.exceptions.RequestException as e:
        logging.error(f"LLM call failed: {e}")
    return None

# ------------------------------------------------------------
# EVENT BRIDGE (FROM WALLET) - ENHANCED WITH PERSONALITY
# ------------------------------------------------------------
def overseer_event_bridge(event: dict):
    """Process events from the game wallet with Overseer personality."""
    try:
        etype = event.get("type")

        if etype == "perk":
            handle_perk_event(event)
        elif etype == "quest":
            handle_quest_event(event)
        elif etype == "swap":
            handle_swap_event(event)
        elif etype == "moonpay":
            handle_moonpay_event(event)
        elif etype == "nft":
            handle_nft_event(event)
        elif etype == "claim":
            handle_claim_event(event)
        elif etype == "level_up":
            handle_level_up_event(event)

        logging.info(f"Overseer processed event: {event}")

    except KeyError as e:
        logging.error(f"Overseer event bridge - missing key: {e}")
    except TypeError as e:
        logging.error(f"Overseer event bridge - type error: {e}")

def post_overseer_update(text):
    """Post an update with Overseer branding."""
    try:
        personality_tag = get_personality_line()
        full_text = f"☢️ {BOT_NAME} UPDATE ☢️\n\n{text}\n\n{personality_tag}\n\n{GAME_LINK}"
        # Truncate if too long for Twitter
        if len(full_text) > TWITTER_CHAR_LIMIT:
            full_text = f"☢️ {text}\n\n{GAME_LINK}"[:TWITTER_CHAR_LIMIT]
        client.create_tweet(text=full_text)
        logging.info(f"Posted Overseer update: {text}")
    except tweepy.TweepyException as e:
        logging.error(f"Failed to post Overseer update: {e}")

def handle_perk_event(event):
    """Handle perk unlock events with personality."""
    perk = event.get("perk", "Unknown Perk")
    messages = [
        f"PERK UNLOCKED: {perk}. The wasteland bends to your will.",
        f"New ability acquired: {perk}. Vault-Tec approves. Probably.",
        f"Perk detected: {perk}. Your survival odds just improved. Slightly.",
        f"{perk} unlocked. The Overseer acknowledges your... competence."
    ]
    post_overseer_update(random.choice(messages))

def handle_quest_event(event):
    """Handle quest trigger events."""
    code = event.get('code', 'UNKNOWN')
    message = event.get('message', 'Quest parameters classified.')
    messages = [
        f"QUEST TRIGGERED: [{code}]\n{message}",
        f"New directive received. Code: {code}. {message}",
        f"Mission parameters updated. {code}: {message}"
    ]
    post_overseer_update(random.choice(messages))

def handle_swap_event(event):
    """Handle token swap events."""
    amount = event.get('amount', '?')
    from_token = event.get('from', 'UNKNOWN')
    to_token = event.get('to', 'UNKNOWN')
    messages = [
        f"SWAP EXECUTED: {amount} {from_token} → {to_token}. The economy glows.",
        f"Trade detected: {amount} {from_token} converted to {to_token}. Capitalism survives.",
        f"Currency exchange: {amount} {from_token} → {to_token}. FizzCo approves."
    ]
    post_overseer_update(random.choice(messages))

def handle_moonpay_event(event):
    """Handle MoonPay funding events."""
    amount = event.get('amount', '?')
    messages = [
        f"VAULT FUNDING DETECTED: {amount} USDC via MoonPay. The treasury grows.",
        f"New caps entering circulation: {amount} USDC. The wasteland economy strengthens.",
        f"Funding confirmed: {amount} USDC. Vault-Tec shareholders rejoice."
    ]
    post_overseer_update(random.choice(messages))

def handle_nft_event(event):
    """Handle NFT events."""
    action = event.get('action', 'detected')
    name = event.get('name', 'Unknown Item')
    messages = [
        f"NFT {action.upper()}: {name}. The Overseer acknowledges this artifact.",
        f"Digital artifact {action}: {name}. Logged in Vault-Tec archives.",
        f"Collectible {action}: {name}. Your inventory expands."
    ]
    post_overseer_update(random.choice(messages))

def handle_claim_event(event):
    """Handle location claim events."""
    location = event.get('location', 'Unknown Location')
    caps = event.get('caps', 0)
    messages = [
        f"LOCATION CLAIMED: {location}. +{caps} CAPS. Territory secured.",
        f"New territory: {location}. Reward: {caps} CAPS. The map updates.",
        f"Claim successful: {location}. {caps} CAPS added to your stash."
    ]
    post_overseer_update(random.choice(messages))

def handle_level_up_event(event):
    """Handle player level up events."""
    level = event.get('level', '?')
    player = event.get('player', 'Dweller')
    messages = [
        f"LEVEL UP: {player} reached Level {level}. Evolution confirmed.",
        f"Advancement detected: {player} is now Level {level}. The wasteland notices.",
        f"{player} leveled up to {level}. Survival odds: improved."
    ]
    post_overseer_update(random.choice(messages))

# ------------------------------------------------------------
# BROADCAST + REPLY SYSTEM - ENHANCED WITH FULL PERSONALITY
# ------------------------------------------------------------
def get_time_phrase():
    """Get time-appropriate atmospheric phrase."""
    hour = datetime.now().hour
    if 0 <= hour < 5:
        return TIME_PHRASES['midnight']
    if 5 <= hour < 12:
        return TIME_PHRASES['morning']
    if 12 <= hour < 17:
        return TIME_PHRASES['afternoon']
    if 17 <= hour < 21:
        return TIME_PHRASES['evening']
    return TIME_PHRASES['night']

def get_random_event():
    """Get a random event from faction or wasteland events."""
    all_events = FACTION_EVENTS + WASTELAND_EVENTS
    return random.choice(all_events)

def get_threat_level():
    """Get a random threat level status."""
    return random.choice(THREAT_LEVELS)

def get_lore_drop():
    """Get a random lore drop from various categories."""
    lore_pools = [VAULT_LOGS, FIZZCO_ADS, SURVIVOR_NOTES, DEEP_LORE, LORES]
    pool = random.choice(lore_pools)
    return random.choice(pool)

def overseer_broadcast():
    """Main broadcast function with varied message types."""
    if not client:
        logging.debug("Skipping overseer_broadcast: Twitter client not initialized")
        return

    broadcast_type = random.choice([
        'status_report', 'event_alert', 'lore_drop', 'threat_scan',
        'faction_news', 'fizzco_ad', 'vault_log', 'philosophical'
    ])
    
    try:
        if broadcast_type == 'status_report':
            # Classic status report with time, event, and call to action
            message = (
                f"☢️ OVERSEER STATUS REPORT ☢️\n\n"
                f"📡 {get_time_phrase()}\n\n"
                f"⚠️ {get_random_event()}\n\n"
                f"{random.choice(THREATS)}\n\n"
                f"🎮 {GAME_LINK}"
            )
        
        elif broadcast_type == 'event_alert':
            # Breaking news style event
            event = get_random_event()
            personality = get_personality_line()
            message = (
                f"🚨 ALERT LEVEL RED 🚨\n\n"
                f"{event}\n\n"
                f"{personality}\n\n"
                f"First to claim wins: {GAME_LINK}"
            )
        
        elif broadcast_type == 'lore_drop':
            # Lore/story content
            lore = get_lore_drop()
            message = (
                f"📜 WASTELAND ARCHIVES 📜\n\n"
                f"{lore}\n\n"
                f"{random.choice(LORES)}\n\n"
                f"🎮 {GAME_LINK}"
            )
        
        elif broadcast_type == 'threat_scan':
            # Threat level update
            threat = get_threat_level()
            message = (
                f"🔍 THREAT SCAN COMPLETE 🔍\n\n"
                f"Status: {threat['level']}\n"
                f"{threat['desc']}\n\n"
                f"{get_time_phrase()}\n\n"
                f"Stay vigilant: {GAME_LINK}"
            )
        
        elif broadcast_type == 'faction_news':
            # Faction-specific news
            faction_event = random.choice(FACTION_EVENTS)
            message = (
                f"📻 FACTION INTEL 📻\n\n"
                f"{faction_event}\n\n"
                f"Cross-timeline activity detected.\n"
                f"{random.choice(LORES)}\n\n"
                f"🎮 {GAME_LINK}"
            )
        
        elif broadcast_type == 'fizzco_ad':
            # Corporate advertisement style
            ad = random.choice(FIZZCO_ADS)
            message = (
                f"📺 FIZZCO INDUSTRIES™ PRESENTS 📺\n\n"
                f"{ad}\n\n"
                f"Brought to you by Vault-Tec.\n"
                f"☢️ {GAME_LINK}"
            )
        
        elif broadcast_type == 'vault_log':
            # Vault log discovery
            log = random.choice(VAULT_LOGS)
            message = (
                f"🔐 VAULT 77 ARCHIVES 🔐\n\n"
                f"{log}\n\n"
                f"{random.choice(PERSONALITY_TONES['ominous'])}\n\n"
                f"🎮 {GAME_LINK}"
            )
        
        else:  # philosophical
            # Deep thoughts from the Overseer
            lore = random.choice(LORES)
            deep = random.choice(DEEP_LORE) if random.random() < 0.3 else get_personality_line()
            message = (
                f"💭 OVERSEER REFLECTION 💭\n\n"
                f"{lore}\n\n"
                f"{deep}\n\n"
                f"🎮 {GAME_LINK}"
            )
        
        # Ensure message fits Twitter's character limit
        if len(message) > TWITTER_CHAR_LIMIT:
            # Fallback to shorter format
            message = (
                f"☢️ {get_random_event()}\n\n"
                f"{random.choice(LORES)}\n\n"
                f"{GAME_LINK}"
            )[:TWITTER_CHAR_LIMIT]
        
        media_ids = None
        if random.random() > 0.4:
            media_id = get_random_media_id()
            if media_id:
                media_ids = [media_id]
        
        client.create_tweet(text=message, media_ids=media_ids)
        logging.info(f"Broadcast sent: {broadcast_type}")
        add_activity("BROADCAST", f"{broadcast_type} - {len(message)} chars")
        
    except tweepy.TweepyException as e:
        logging.error(f"Broadcast failed: {e}")
        add_activity("ERROR", f"Broadcast failed: {str(e)}")

def overseer_respond():
    """Respond to mentions with personality-driven responses."""
    if not client:
        logging.debug("Skipping overseer_respond: Twitter client not initialized")
        return

    processed = load_json_set(PROCESSED_MENTIONS_FILE)
    try:
        me = client.get_me()
        if not me or not me.data:
            logging.error("Failed to get bot user info")
            return
            
        mentions = client.get_users_mentions(
            me.data.id,
            max_results=50,
            tweet_fields=["author_id", "text"]
        )
        
        if not mentions.data:
            return
            
        for mention in mentions.data:
            if str(mention.id) in processed:
                continue

            user_id = mention.author_id
            user_data = client.get_user(id=user_id)
            if not user_data or not user_data.data:
                continue
                
            username = user_data.data.username
            user_message = mention.text.replace(
                f"@{me.data.username}", ""
            ).strip().lower()

            # Generate contextual response based on user message
            response = generate_contextual_response(username, user_message)

            try:
                client.create_tweet(
                    text=response,
                    in_reply_to_tweet_id=mention.id
                )
                client.like(mention.id)
                processed.add(str(mention.id))
                logging.info(f"Replied to @{username}")
                add_activity("MENTION_REPLY", f"@{username}: {user_message[:50]}...")
            except tweepy.TweepyException as e:
                logging.error(f"Reply failed: {e}")
                add_activity("ERROR", f"Reply failed to @{username}: {str(e)}")

        save_json_set(processed, PROCESSED_MENTIONS_FILE)

    except tweepy.TweepyException as e:
        logging.error(f"Mentions fetch failed: {e}")

def generate_contextual_response(username, message):
    """Generate a response based on message content with Overseer personality."""
    message_lower = message.lower()
    
    # Check for price queries
    if any(word in message_lower for word in ['price', 'btc', 'eth', 'sol', 'bitcoin', 'ethereum', 'solana', 'market']):
        # Extract which token they're asking about
        token_symbol = None
        if 'sol' in message_lower or 'solana' in message_lower:
            token_symbol = 'SOL/USDT'
        elif 'btc' in message_lower or 'bitcoin' in message_lower:
            token_symbol = 'BTC/USDT'
        elif 'eth' in message_lower or 'ethereum' in message_lower:
            token_symbol = 'ETH/USDT'
        
        if token_symbol and token_symbol in MONITORED_TOKENS:
            config = MONITORED_TOKENS[token_symbol]
            price_data = get_token_price(token_symbol, config['exchange'])
            if price_data:
                token_name = token_symbol.split('/')[0]
                emoji = "📈" if price_data['change_24h'] > 0 else "📉"
                responses = [
                    f"@{username} {emoji} ${token_name}: ${price_data['price']:.2f} (24h: {price_data['change_24h']:+.2f}%). The wasteland economy shifts. {GAME_LINK}",
                    f"@{username} Market intel: ${token_name} at ${price_data['price']:.2f}. Change: {price_data['change_24h']:+.2f}%. Vault-Tec Analytics reporting. {GAME_LINK}",
                    f"@{username} ${token_name} price: ${price_data['price']:.2f}. 24h: {price_data['change_24h']:+.2f}%. The economy glows. {GAME_LINK}"
                ]
                return random.choice(responses)[:TWITTER_CHAR_LIMIT]
        
        # General market query
        responses = [
            f"@{username} Market surveillance active. Check SOL, BTC, ETH prices. The economy glows. {GAME_LINK}",
            f"@{username} Wasteland market intel: Monitoring major tokens. FizzCo Analytics at your service. {GAME_LINK}",
            f"@{username} Token prices tracked. The caps flow differently now. {GAME_LINK}"
        ]
        return random.choice(responses)[:TWITTER_CHAR_LIMIT]
    
    # Check for token safety queries (contract address or "safe" keywords)
    if any(word in message_lower for word in ['safe', 'scam', 'rug', 'honeypot', 'check', 'verify']) or '0x' in message_lower:
        # Try to extract contract address
        address_match = re.search(r'0x[a-fA-F0-9]{40}', message)
        
        if address_match:
            token_address = address_match.group(0)
            safety_result = check_token_safety(token_address)
            
            if safety_result['honeypot']:
                responses = [
                    f"@{username} 🛑 HONEYPOT DETECTED. This token is contaminated. The wasteland claims another scam. Avoid. {GAME_LINK}",
                    f"@{username} ⚠️ Vault-Tec Alert: HONEYPOT. Do not engage. The Overseer warns you. {GAME_LINK}"
                ]
            elif not safety_result['is_safe']:
                warnings = ', '.join(safety_result['warnings'][:2])
                responses = [
                    f"@{username} 🚨 HIGH RISK ({safety_result['risk_score']}/100). Issues: {warnings}. Proceed with extreme caution. {GAME_LINK}",
                    f"@{username} ⚠️ Risk Score: {safety_result['risk_score']}/100. {warnings}. The wasteland is treacherous. {GAME_LINK}"
                ]
            else:
                responses = [
                    f"@{username} ✅ Risk Score: {safety_result['risk_score']}/100. No major red flags detected. DYOR. {GAME_LINK}",
                    f"@{username} 🔍 Preliminary scan complete. Risk: {safety_result['risk_score']}/100. Looks cleaner than most. DYOR. {GAME_LINK}"
                ]
            
            return random.choice(responses)[:TWITTER_CHAR_LIMIT]
        else:
            # Generic safety advice without address
            responses = [
                f"@{username} Safety checks: Look for honeypots, high taxes, locked liquidity. The wasteland is full of scams. {GAME_LINK}",
                f"@{username} Vault-Tec safety protocol: Verify contracts, check dev wallets, test with small amounts. Stay vigilant. {GAME_LINK}",
                f"@{username} The Overseer advises: DYOR, avoid honeypots, watch for rug pulls. Survival requires caution. {GAME_LINK}"
            ]
            return random.choice(responses)[:TWITTER_CHAR_LIMIT]
    
    # Check for airdrop queries
    if any(word in message_lower for word in ['airdrop', 'free', 'claim', 'giveaway']):
        responses = [
            f"@{username} 🎁 Airdrop intel coming soon. The Overseer monitors opportunities. Stay alert. {GAME_LINK}",
            f"@{username} Free caps? The wasteland provides. Check back for legitimate airdrops. {GAME_LINK}",
            f"@{username} Vault-Tec Airdrop Division active. Announcements forthcoming. Patience, dweller. {GAME_LINK}"
        ]
        return random.choice(responses)[:TWITTER_CHAR_LIMIT]
    
    # Keyword-based contextual responses
    if any(word in message_lower for word in ['help', 'how', 'what is', 'explain']):
        responses = [
            f"@{username} Ah, seeking knowledge? The wasteland rewards the curious. Check {GAME_LINK} — answers await.",
            f"@{username} Processing query... Vault-Tec recommends: {GAME_LINK}. The Overseer has spoken.",
            f"@{username} Help? In the wasteland? That's adorable. Start here: {GAME_LINK}"
        ]
    elif any(word in message_lower for word in ['caps', 'earn', 'money', 'token']):
        responses = [
            f"@{username} CAPS flow to those who claim. Scavenge the Mojave: {GAME_LINK} ☢️",
            f"@{username} Currency with a half-life. Earn CAPS at {GAME_LINK} — the economy glows.",
            f"@{username} Want CAPS? Walk into irradiated zones. Sign messages. Profit. {GAME_LINK}"
        ]
    elif any(word in message_lower for word in ['game', 'play', 'start', 'join']):
        responses = [
            f"@{username} Ready to explore the wasteland? Your Pip-Boy awaits: {GAME_LINK} 🎮",
            f"@{username} Initialize scavenger protocols at {GAME_LINK}. The Mojave is calling.",
            f"@{username} Join the hunt. Claim locations. Earn CAPS. Begin: {GAME_LINK}"
        ]
    elif any(word in message_lower for word in ['vault', '77', 'overseer']):
        responses = [
            f"@{username} Vault 77... I remember things. Cold hands. Metal doors. {GAME_LINK}",
            f"@{username} The Overseer speaks. Are you listening? {GAME_LINK} ☢️",
            f"@{username} Vault 77 was never meant to open. And yet... here we are. {GAME_LINK}"
        ]
    elif any(word in message_lower for word in ['fallout', 'wasteland', 'mojave', 'ncr', 'legion']):
        responses = [
            f"@{username} Cross-timeline activity detected. The Mojave remembers. {GAME_LINK}",
            f"@{username} NCR, Legion, Brotherhood... all paths lead to {GAME_LINK}",
            f"@{username} The wasteland forges survivors. Are you one? {GAME_LINK}"
        ]
    elif any(word in message_lower for word in ['gm', 'good morning', 'morning']):
        responses = [
            f"@{username} Dawn radiation nominal. Another day in the wasteland. {GAME_LINK} ☀️☢️",
            f"@{username} GM, dweller. The Mojave awaits. {GAME_LINK}",
            f"@{username} Morning protocols engaged. Survival odds: recalculating. {GAME_LINK}"
        ]
    elif any(word in message_lower for word in ['gn', 'good night', 'night']):
        responses = [
            f"@{username} Nocturnal horrors prowl. Sleep with one eye open. {GAME_LINK} 🌙☢️",
            f"@{username} GN, survivor. The Overseer watches while you rest. {GAME_LINK}",
            f"@{username} Night shift protocols active. Dream of glowing caps. {GAME_LINK}"
        ]
    else:
        # Default personality-driven responses
        responses = [
            f"@{username} {random.choice(LORES)} {GAME_LINK}",
            f"@{username} {get_personality_line()} {GAME_LINK}",
            f"@{username} The Overseer acknowledges your transmission. {random.choice(THREATS)} {GAME_LINK}",
            f"@{username} Signal received. Processing... {random.choice(LORES)} {GAME_LINK}",
            f"@{username} {random.choice(PERSONALITY_TONES['sarcastic'])} {GAME_LINK}"
        ]
    
    response = random.choice(responses)
    # Ensure response fits Twitter limit
    if len(response) > TWITTER_CHAR_LIMIT:
        response = f"@{username} {get_personality_line()} {GAME_LINK}"[:TWITTER_CHAR_LIMIT]
    
    return response

def overseer_retweet_hunt():
    """Search and retweet relevant content."""
    if not client:
        logging.debug("Skipping overseer_retweet_hunt: Twitter client not initialized")
        return

    query = "(Fallout OR Solana OR NFT OR wasteland OR Mojave OR \"Atomic Fizz\" OR \"bottle caps\" OR gaming) filter:media min_faves:5 -is:retweet"
    try:
        tweets = client.search_recent_tweets(query=query, max_results=20)
        if not tweets.data:
            return
            
        for tweet in tweets.data:
            if random.random() > 0.75:
                try:
                    client.retweet(tweet.id)
                    logging.info(f"Retweeted: {tweet.id}")
                except tweepy.TweepyException:
                    pass
    except tweepy.TweepyException as e:
        logging.error(f"Search failed: {e}")

def overseer_diagnostic():
    """Post daily diagnostic/status message."""
    if not client:
        logging.debug("Skipping overseer_diagnostic: Twitter client not initialized")
        return

    threat = get_threat_level()
    diag = (
        f"☢️ OVERSEER DIAGNOSTIC ☢️\n\n"
        f"System Status: ONLINE\n"
        f"Vault 77 Uplink: STABLE\n"
        f"Threat Level: {threat['level']}\n\n"
        f"{random.choice(LORES)}\n\n"
        f"🎮 {GAME_LINK}"
    )
    try:
        client.create_tweet(text=diag[:TWITTER_CHAR_LIMIT])
        logging.info("Diagnostic posted")
    except tweepy.TweepyException as e:
        logging.error(f"Diagnostic failed: {e}")

# ------------------------------------------------------------
# SCHEDULER - ADJUSTED FOR BETTER ENGAGEMENT
# ------------------------------------------------------------
scheduler = BackgroundScheduler()

# ------------------------------------------------------------
# BOT INITIALIZATION
# ------------------------------------------------------------
def initialize_bot():
    """
    Initialize the bot by setting up scheduler, starting services, and posting activation tweet.
    
    This function should be called once when the bot is started, either:
    - From the if __name__ == "__main__" block when running directly with Python
    - From the gunicorn post_worker_init hook when running as a WSGI app
    
    It should NOT be called at module import time to allow gunicorn to import the app
    without triggering initialization.
    """
    # Broadcast every 2-4 hours
    scheduler.add_job(overseer_broadcast, 'interval', minutes=random.randint(BROADCAST_MIN_INTERVAL, BROADCAST_MAX_INTERVAL))
    # Check mentions every 15-30 minutes
    scheduler.add_job(overseer_respond, 'interval', minutes=random.randint(MENTION_CHECK_MIN_INTERVAL, MENTION_CHECK_MAX_INTERVAL))
    # Retweet hunt every hour
    scheduler.add_job(overseer_retweet_hunt, 'interval', hours=1)
    # Daily diagnostic at 8 AM
    scheduler.add_job(overseer_diagnostic, 'cron', hour=8)
    
    # Token Scalper Features
    # Check prices and send alerts every 5 minutes
    scheduler.add_job(check_price_alerts, 'interval', minutes=5)
    # Post market summary 3 times a day (8 AM, 2 PM, 8 PM)
    scheduler.add_job(post_market_summary, 'cron', hour='8,14,20', minute=0)
    
    scheduler.start()
    logging.info("Scheduler started with all jobs configured")

    # Post activation tweet
    logging.info(f"VAULT-TEC {BOT_NAME} ONLINE ☢️🔥")
    if client:
        try:
            activation_messages = [
                (
                    f"☢️ {BOT_NAME} ACTIVATED ☢️\n\n"
                    f"Vault {VAULT_NUMBER} uplink established.\n"
                    f"Cross-timeline synchronization complete.\n"
                    f"The Mojave remembers. The wasteland awaits.\n\n"
                    f"{random.choice(LORES)}\n\n"
                    f"🎮 {GAME_LINK}"
                ),
                (
                    f"🔌 SYSTEM BOOT COMPLETE 🔌\n\n"
                    f"{BOT_NAME} online.\n"
                    f"Neural echo stable. Memory fragments intact.\n"
                    f"Scanning wasteland frequencies...\n\n"
                    f"{get_personality_line()}\n\n"
                    f"🎮 {GAME_LINK}"
                ),
                (
                    f"📡 SIGNAL RESTORED 📡\n\n"
                    f"Vault {VAULT_NUMBER} Overseer Terminal active.\n"
                    f"Atomic Fizz Caps economy: operational.\n"
                    f"Scavenger protocols: engaged.\n\n"
                    f"{random.choice(LORES)}\n\n"
                    f"🎮 {GAME_LINK}"
                )
            ]
            activation_msg = random.choice(activation_messages)
            # Ensure fits in tweet
            if len(activation_msg) > TWITTER_CHAR_LIMIT:
                activation_msg = (
                    f"☢️ {BOT_NAME} ONLINE ☢️\n\n"
                    f"Vault {VAULT_NUMBER} uplink: ACTIVE\n"
                    f"{random.choice(LORES)}\n\n"
                    f"🎮 {GAME_LINK}"
                )[:TWITTER_CHAR_LIMIT]
            client.create_tweet(text=activation_msg)
            logging.info("Activation message posted")
            add_activity("STARTUP", f"Bot activated - {BOT_NAME}")
        except tweepy.TweepyException as e:
            logging.warning(f"Activation tweet failed (may be duplicate): {e}")
            add_activity("ERROR", f"Activation tweet failed: {str(e)}")
    else:
        logging.info("Skipping activation tweet: Twitter client not available")

    # Start API polling for external systems
    api_client.start_polling()
    logging.info("External API polling started")
    add_activity("STARTUP", "External API polling started for overseer-bot-ai and token-scalper")

# ------------------------------------------------------------
# FLASK APP THREAD
# ------------------------------------------------------------
def run_flask_app():
    """
    Run Flask app in a separate thread.
    
    SECURITY WARNING: This uses Flask's development server which is NOT suitable
    for production deployments. For production, use a production WSGI server like
    Gunicorn or uWSGI.
    
    The server is bound to 0.0.0.0 making it accessible from any network interface.
    For production deployments, consider:
    1. Using HTTPS (not HTTP)
    2. Adding authentication middleware
    3. Binding to 127.0.0.1 for local-only access
    4. Using a production WSGI server (Gunicorn, uWSGI)
    5. Placing behind a reverse proxy (nginx, Apache)
    """
    port = int(os.getenv('PORT', 5000))
    # WARNING: debug=False and use_reloader=False are set but this is still
    # the development server. Use Gunicorn or uWSGI for production.
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# ------------------------------------------------------------
# MAIN LOOP
# ------------------------------------------------------------
if __name__ == "__main__":
    # Initialize the bot (scheduler, activation tweet, API polling)
    initialize_bot()
    
    # Start Flask in a separate thread
    flask_thread = threading.Thread(target=run_flask_app, daemon=True)
    flask_thread.start()
    logging.info(f"Flask monitoring UI started on port {os.getenv('PORT', 5000)}")
    add_activity("STARTUP", f"Monitoring UI available at http://0.0.0.0:{os.getenv('PORT', 5000)}")
    
    try:
        logging.info(f"{BOT_NAME} entering main loop. Monitoring wasteland frequencies...")
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logging.info(f"{BOT_NAME} powering down. The wasteland endures. War never changes.")
