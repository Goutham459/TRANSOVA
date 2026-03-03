"""
================================================================================
BOOKINGS UTILITIES MODULE
================================================================================
This module contains shared utility functions used across the bookings application.
All functions are documented with clear explanations of their purpose and usage.

Usage:
    from bookings.utils import calculate_booking_price, get_distance_haversine
================================================================================
"""

import math
import logging
import requests
from typing import Optional, Tuple, Dict, Any
from django.conf import settings

# ============================================================================
# LOGGER CONFIGURATION
# ============================================================================
# Get logger instance for debugging and error tracking
logger = logging.getLogger(__name__)


# ============================================================================
# DISTANCE CALCULATION FUNCTIONS
# ============================================================================

def get_distance_haversine(
    pickup_lat: float, 
    pickup_lng: float, 
    drop_lat: float, 
    drop_lng: float
) -> float:
    """
    Calculate the distance between two GPS coordinates using the Haversine formula.
    
    The Haversine formula determines the great-circle distance between two points
    on a sphere (Earth) given their longitudes and latitudes. This is more accurate
    than simple Euclidean distance for geographic coordinates.
    
    Args:
        pickup_lat: Latitude of pickup location (decimal degrees)
        pickup_lng: Longitude of pickup location (decimal degrees)
        drop_lat: Latitude of drop location (decimal degrees)
        drop_lng: Longitude of drop location (decimal degrees)
    
    Returns:
        float: Distance in kilometers between the two points
    
    Example:
        >>> get_distance_haversine(40.7128, -74.0060, 34.0522, -118.2437)
        3939.29  # Distance from New York to Los Angeles
    
    Note:
        - Earth radius (R) is approximately 6,371 km
        - Coordinates can be positive (North/East) or negative (South/West)
        - Results are accurate to within 0.5% for most practical distances
    """
    # Earth's radius in kilometers - this is the average radius accounting for
    # Earth's slightly oblate spheroid shape
    EARTH_RADIUS_KM = 6371
    
    # Convert degrees to radians - trigonometric functions require radians
    # Formula: radians = degrees * (π / 180)
    lat1_rad = math.radians(pickup_lat)
    lat2_rad = math.radians(drop_lat)
    delta_lat = math.radians(drop_lat - pickup_lat)
    delta_lng = math.radians(drop_lng - pickup_lng)
    
    # Haversine formula implementation:
    # a = sin²(Δlat/2) + cos(lat1) * cos(lat2) * sin²(Δlng/2)
    # c = 2 * atan2(√a, √(1-a))
    # distance = R * c
    
    a = (math.sin(delta_lat / 2) ** 2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * 
         math.sin(delta_lng / 2) ** 2)
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = EARTH_RADIUS_KM * c
    
    return distance


# ============================================================================
# PRICE CALCULATION FUNCTIONS
# ============================================================================

def calculate_booking_price(
    distance_km: float,
    base_rate: Optional[float] = None,
    load_multiplier: float = 1.0,
    include_commission: bool = True
) -> float:
    """
    Calculate the total price for a booking based on distance and other factors.
    
    This function computes the booking price using the following formula:
    1. Base price (minimum fixed charge) + (distance × rate per km)
    2. Multiply by load type multiplier (e.g., heavier loads cost more)
    3. Add platform commission (optional)
    
    Args:
        distance_km: Distance traveled in kilometers
        base_rate: Price per kilometer (defaults to settings.BASE_RATE_CUSTOMER)
        load_multiplier: Multiplier based on load type (1.0 = standard)
        include_commission: Whether to add platform commission
    
    Returns:
        float: Total calculated price rounded to 2 decimal places
    
    Example:
        >>> calculate_booking_price(100, 2.0, 1.0, True)
        210.0  # (100 * 2.0) * 1.05 = 210.0
    
    Pricing Logic:
        - Base Rate: Per-kilometer charge (configured in settings)
        - Load Multiplier: Varies by cargo type (sand=1.0, cement=1.3, steel=1.5)
        - Commission: Platform fee (default 5%, configured in settings)
    """
    # Use default base rate from settings if not provided
    if base_rate is None:
        base_rate = getattr(settings, 'BASE_RATE_CUSTOMER', 2.0)
    
    # Get commission rate from settings (default 5% if not set)
    commission_rate = getattr(settings, 'COMMISSION_RATE', 0.05)
    
    # Step 1: Calculate base price = distance × rate per km
    base_price = distance_km * base_rate
    
    # Step 2: Apply load type multiplier (heavier/more expensive cargo)
    price_with_load = base_price * load_multiplier
    
    # Step 3: Add platform commission (optional - can be disabled)
    if include_commission:
        total_price = price_with_load * (1 + commission_rate)
    else:
        total_price = price_with_load
    
    # Round to 2 decimal places for currency
    return round(total_price, 2)


def calculate_admin_booking_price(
    distance_km: float,
    base_price: Optional[float] = None,
    rate_per_km: Optional[float] = None,
    load_multiplier: float = 1.0
) -> float:
    """
    Calculate booking price using admin pricing configuration.
    
    This function uses the admin-side pricing model which includes:
    - A base fixed price (operational overhead)
    - Distance-based rate per kilometer
    - Load type multiplier
    
    Args:
        distance_km: Distance in kilometers
        base_price: Fixed base price (defaults to settings.BASE_PRICE = 50)
        rate_per_km: Rate per km (defaults to settings.RATE_PER_KM = 10)
        load_multiplier: Multiplier for load type
    
    Returns:
        float: Total price rounded to 2 decimal places
    
    Example:
        >>> calculate_admin_booking_price(100, 50, 10, 1.0)
        1050.0  # (50 + 100 * 10) * 1.0 = 1050.0
    
    Note:
        This is used for admin-facing bookings with different pricing
        than customer-facing bookings.
    """
    # Use default values from settings
    if base_price is None:
        base_price = getattr(settings, 'BASE_PRICE', 50)
    if rate_per_km is None:
        rate_per_km = getattr(settings, 'RATE_PER_KM', 10)
    
    # Formula: (BASE_PRICE + distance_km * RATE_PER_KM) * load_multiplier
    total_price = (base_price + distance_km * rate_per_km) * load_multiplier
    
    return round(total_price, 2)


# ============================================================================
# CURRENCY DETECTION FUNCTIONS
# ============================================================================

def detect_user_currency() -> str:
    """
    Detect user's currency based on their IP address.
    
    This function calls an external API to determine the user's location
    and returns the appropriate currency code. Falls back to USD if
    the API call fails.
    
    Returns:
        str: Currency code (default: 'USD')
    
    API Used:
        ipapi.co - Free IP geolocation API
    
    Note:
        - Makes external API call (may be slow - consider caching)
        - Falls back to USD if API is unavailable
        - In production, consider implementing caching
    """
    default_currency = getattr(settings, 'DEFAULT_CURRENCY', 'USD')
    api_url = getattr(settings, 'CURRENCY_API_URL', 'https://ipapi.co/json/')
    
    try:
        # Make API request with timeout to prevent hanging
        response = requests.get(api_url, timeout=5)
        response.raise_for_status()  # Raise exception for HTTP errors
        
        data = response.json()
        currency = data.get('currency', default_currency)
        
        logger.info(f"Currency detected: {currency}")
        return currency
    
    except requests.RequestException as e:
        # Log error but don't crash - use default currency
        logger.warning(f"Currency API failed: {e}. Using default: {default_currency}")
        return default_currency
    
    except (ValueError, KeyError) as e:
        # Handle JSON parsing errors
        logger.warning(f"Currency API parse error: {e}. Using default: {default_currency}")
        return default_currency


def format_price(amount: float, currency: str = 'USD') -> str:
    """
    Format a price amount with currency symbol.
    
    Args:
        amount: Numerical amount to format
        currency: Currency code (default: 'USD')
    
    Returns:
        str: Formatted price string (e.g., "$100.00 USD")
    
    Example:
        >>> format_price(100.50, 'USD')
        '$100.50 USD'
    """
    currency_symbols = {
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'INR': '₹',
        'JPY': '¥',
    }
    
    symbol = currency_symbols.get(currency.upper(), currency.upper() + ' ')
    return f"{symbol}{amount:,.2f} {currency}"


# ============================================================================
# VALIDATION HELPER FUNCTIONS
# ============================================================================

def validate_booking_data(data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate booking form data before processing.
    
    Performs basic validation checks on booking data to ensure
    all required fields are present and valid.
    
    Args:
        data: Dictionary containing booking form data
    
    Returns:
        Tuple of (is_valid: bool, error_message: str)
    
    Validation Rules:
        - customer_name: Required, max 100 characters
        - pickup_location: Required
        - drop_location: Required
        - distance_km: Must be positive number
        - booking_date: Required, must be valid date
    """
    required_fields = [
        'customer_name', 'pickup_location', 'drop_location', 
        'distance_km', 'booking_date'
    ]
    
    # Check required fields
    for field in required_fields:
        if field not in data or not data[field]:
            return False, f"Missing required field: {field}"
    
    # Validate distance is positive
    try:
        distance = float(data['distance_km'])
        if distance <= 0:
            return False, "Distance must be a positive number"
        if distance > 10000:  # Max 10,000 km (around the world)
            return False, "Distance seems unrealistic. Please verify."
    except (ValueError, TypeError):
        return False, "Invalid distance value"
    
    # Validate customer name length
    if len(data['customer_name']) > 100:
        return False, "Customer name is too long (max 100 characters)"
    
    return True, ""


def validate_coordinates(lat: float, lng: float) -> bool:
    """
    Validate GPS coordinates are within valid ranges.
    
    Args:
        lat: Latitude (-90 to 90)
        lng: Longitude (-180 to 180)
    
    Returns:
        bool: True if coordinates are valid
    """
    try:
        lat = float(lat)
        lng = float(lng)
        
        # Latitude must be between -90 and 90 degrees
        if not -90 <= lat <= 90:
            return False
        
        # Longitude must be between -180 and 180 degrees
        if not -180 <= lng <= 180:
            return False
        
        return True
    
    except (ValueError, TypeError):
        return False


# ============================================================================
# PAYMENT HELPER FUNCTIONS
# ============================================================================

def detect_card_type(card_number: str) -> str:
    """
    Detect the card type based on the card number prefix.
    
    Args:
        card_number: Credit/debit card number (may contain spaces)
    
    Returns:
        str: Card type ('Visa', 'Mastercard', 'Amex', 'Unknown')
    
    Card Number Patterns:
        - Visa: Starts with 4
        - Mastercard: Starts with 51-55 or 2221-2720
        - Amex: Starts with 34 or 37
        - Discover: Starts with 6011, 65, 644-649
    """
    # Remove spaces and dashes
    card_clean = card_number.replace(' ', '').replace('-', '')
    
    if not card_clean:
        return 'Unknown'
    
    # Check first digit(s) to determine card type
    if card_clean.startswith('4'):
        return 'Visa'
    elif card_clean.startswith(('51', '52', '53', '54', '55')):
        return 'Mastercard'
    elif card_clean.startswith(('34', '37')):
        return 'Amex'
    elif card_clean.startswith(('6011', '65')) or card_clean[:3] in [str(i) for i in range(644, 650)]:
        return 'Discover'
    else:
        return 'Unknown'


def mask_card_number(card_number: str) -> str:
    """
    Mask card number showing only last 4 digits.
    
    Args:
        card_number: Full card number
    
    Returns:
        str: Masked card number (e.g., "****1234")
    """
    card_clean = card_number.replace(' ', '').replace('-', '')
    
    if len(card_clean) < 4:
        return '****'
    
    return f"****{card_clean[-4:]}"


# ============================================================================
# SESSION HELPER FUNCTIONS
# ============================================================================

def generate_otp() -> int:
    """
    Generate a random 6-digit OTP for verification.
    
    Returns:
        int: Random number between 100000 and 999999
    """
    import random
    return random.randint(100000, 999999)


def store_otp_in_session(request, otp: int, key: str = 'otp') -> None:
    """
    Store OTP in session with timestamp for validation.
    
    Args:
        request: Django HTTP request object
        otp: One-time password to store
        key: Session key to use
    """
    import datetime
    
    session_key = getattr(settings, f'SESSION_{key.upper()}_KEY', key)
    request.session[session_key] = otp
    request.session[f'{session_key}_created'] = datetime.datetime.now().timestamp()
    
    # Mark session as modified to ensure it's saved
    request.session.modified = True


def validate_session_otp(request, entered_otp: int, key: str = 'otp') -> Tuple[bool, str]:
    """
    Validate OTP from session with expiry check.
    
    Args:
        request: Django HTTP request object
        entered_otp: OTP entered by user
        key: Session key to check
    
    Returns:
        Tuple of (is_valid: bool, message: str)
    """
    import datetime
    
    session_key = getattr(settings, f'SESSION_{key.upper()}_KEY', key)
    session_otp = request.session.get(session_key)
    created_timestamp = request.session.get(f'{session_key}_created')
    
    # Check if OTP exists
    if not session_otp:
        return False, "OTP not found or expired. Please request a new one."
    
    # Check if OTP matches
    if str(entered_otp) != str(session_otp):
        return False, "Invalid OTP. Please try again."
    
    # Check if OTP has expired (default 10 minutes)
    validity_minutes = getattr(settings, 'OTP_VALIDITY_MINUTES', 10)
    
    if created_timestamp:
        created_time = datetime.datetime.fromtimestamp(created_timestamp)
        elapsed = datetime.datetime.now() - created_time
        
        if elapsed.total_seconds() > (validity_minutes * 60):
            # Clear the expired OTP
            request.session.pop(session_key, None)
            request.session.pop(f'{session_key}_created', None)
            return False, f"OTP has expired. Please request a new one (valid for {validity_minutes} minutes)."
    
    return True, "OTP validated successfully"


# ============================================================================
# EXPORT STATEMENTS
# ============================================================================
# These are the main functions that should be imported from this module
__all__ = [
    # Distance calculation
    'get_distance_haversine',
    
    # Price calculation
    'calculate_booking_price',
    'calculate_admin_booking_price',
    'format_price',
    
    # Currency
    'detect_user_currency',
    
    # Validation
    'validate_booking_data',
    'validate_coordinates',
    
    # Payment helpers
    'detect_card_type',
    'mask_card_number',
    
    # OTP helpers
    'generate_otp',
    'store_otp_in_session',
    'validate_session_otp',
]

