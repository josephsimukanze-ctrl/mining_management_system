import requests
import logging
import socket
from django.conf import settings
from datetime import datetime

logger = logging.getLogger(__name__)

ZAMTEL_API_URL = "https://api.zamtel.zm/v1/sms/send"
ZAMTEL_API_KEY = getattr(settings, 'ZAMTEL_API_KEY', 'your-api-key-here')
ZAMTEL_SENDER_ID = "ZM-MINING"

# Optional: fallback DNS server
FALLBACK_DNS = "8.8.8.8"


def check_dns(hostname: str) -> bool:
    """
    Check if a hostname can be resolved.
    Uses fallback DNS if default resolution fails.
    """
    try:
        socket.gethostbyname(hostname)
        return True
    except socket.gaierror:
        logger.warning(f"DNS resolution failed for {hostname}, trying fallback DNS {FALLBACK_DNS}")
        try:
            import dns.resolver  # pip install dnspython
            resolver = dns.resolver.Resolver()
            resolver.nameservers = [FALLBACK_DNS]
            resolver.resolve(hostname)
            return True
        except Exception as e:
            logger.error(f"Fallback DNS also failed for {hostname}: {e}")
            return False


def send_sms(phone: str, message: str) -> bool:
    """
    Send SMS via Zamtel API
    Example phone format: +26097XXXXXXX
    """
    if not ZAMTEL_API_KEY or ZAMTEL_API_KEY == 'your-api-key-here':
        logger.warning("⚠️ Zamtel API key not set. SMS not sent.")
        return False

    if not check_dns("api.zamtel.zm"):
        logger.error("❌ Cannot resolve Zamtel API host. SMS not sent.")
        return False

    payload = {
        "api_key": ZAMTEL_API_KEY,
        "sender_id": ZAMTEL_SENDER_ID,
        "phone": phone,
        "message": message,
        "schedule_time": None
    }

    try:
        response = requests.post(ZAMTEL_API_URL, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get('status') == 'success':
            logger.info(f"✅ SMS sent to {phone}: {message}")
            return True
        logger.error(f"❌ SMS failed: {data}")
    except requests.exceptions.RequestException as e:
        logger.error(f"🔥 SMS sending exception: {str(e)}")

    return False
