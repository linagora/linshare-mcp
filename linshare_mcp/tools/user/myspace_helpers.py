
import requests
from ...config import LINSHARE_USER_URL
from ...utils.logging import logger
from ...utils.auth import auth_manager
from datetime import datetime, timedelta, timezone

def _get_share_expiration_policy():
    """Fetch SHARE_EXPIRATION functionality configuration."""
    if not LINSHARE_USER_URL or not auth_manager.is_logged_in():
        return None
    
    try:
        url = f"{LINSHARE_USER_URL}/functionalities"
        response = requests.get(url, headers=auth_manager.get_user_header(), timeout=10)
        response.raise_for_status()
        data = response.json()
        
        for func in data:
            if func.get('identifier') == "SHARE_EXPIRATION":
                return func
    except Exception as e:
        logger.warning(f"Failed to fetch functionalities: {e}")
    
    return None

def _calculate_expiration_timestamp(value: int, unit: str) -> int:
    """Calculate expiration timestamp (ms) based on value and unit."""
    now = datetime.now(timezone.utc)
    delta = None
    
    if not isinstance(value, (int, float)):
        return None
        
    u = unit.upper()
    # Support both singular and plural
    if u in ("DAY", "DAYS"):
        delta = timedelta(days=value)
    elif u in ("WEEK", "WEEKS"):
        delta = timedelta(weeks=value)
    elif u in ("MONTH", "MONTHS"):
        delta = timedelta(days=value * 30) # Approximate
    elif u in ("YEAR", "YEARS"):
        delta = timedelta(days=value * 365) # Approximate
    elif u in ("HOUR", "HOURS"):
        delta = timedelta(hours=value)
    elif u in ("MINUTE", "MINUTES"):
        delta = timedelta(minutes=value)
        
    if delta:
        return int((now + delta).timestamp() * 1000)
    return int((now + timedelta(days=value)).timestamp() * 1000) # Default fallback

def _validate_expiration_range(target_date_ms: int, func_config: dict) -> tuple[bool, str]:
    """Validate if target date is within min/max range from now using full config."""
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    diff_ms = target_date_ms - now_ms
    
    # Validation for past dates
    if diff_ms < 0:
        return False, "Expiration date cannot be in the past."
    
    def to_ms(val, u):
        if val is None or u is None: return None
        u = u.upper()
        if u in ("DAY", "DAYS"): return val * 24 * 3600 * 1000
        if u in ("WEEK", "WEEKS"): return val * 7 * 24 * 3600 * 1000
        if u in ("MONTH", "MONTHS"): return val * 30 * 24 * 3600 * 1000
        if u in ("YEAR", "YEARS"): return val * 365 * 24 * 3600 * 1000
        if u in ("HOUR", "HOURS"): return val * 3600 * 1000
        if u in ("MINUTE", "MINUTES"): return val * 60 * 1000
        return val * 24 * 3600 * 1000 # Default days

    # Check for min
    min_val = func_config.get('minValue') or func_config.get('min')
    min_unit = func_config.get('minUnit') or func_config.get('unit', 'DAY')
    min_ms = to_ms(min_val, min_unit)

    # Check for max
    max_val = func_config.get('maxValue') or func_config.get('max')
    max_unit = func_config.get('maxUnit') or func_config.get('unit', 'DAY')
    max_ms = to_ms(max_val, max_unit)
    
    if min_ms is not None and diff_ms < min_ms:
        return False, f"Expiration is too short. Minimum is {min_val} {min_unit}."
    if max_ms is not None and diff_ms > max_ms:
        return False, f"Expiration is too long. Maximum is {max_val} {max_unit}."
        
    return True, ""
