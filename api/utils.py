import re
import requests
import whois
import phonenumbers
from datetime import datetime

def get_phone_number_type_description(num_type_code):
    type_map = {
        phonenumbers.PhoneNumberType.FIXED_LINE: "Fixed Line",
        phonenumbers.PhoneNumberType.MOBILE: "Mobile",
        phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE: "Fixed Line or Mobile",
        phonenumbers.PhoneNumberType.TOLL_FREE: "Toll Free",
        phonenumbers.PhoneNumberType.PREMIUM_RATE: "Premium Rate",
        phonenumbers.PhoneNumberType.SHARED_COST: "Shared Cost",
        phonenumbers.PhoneNumberType.VOIP: "VoIP",
        phonenumbers.PhoneNumberType.PERSONAL_NUMBER: "Personal Number",
        phonenumbers.PhoneNumberType.PAGER: "Pager",
        phonenumbers.PhoneNumberType.UAN: "UAN",
        phonenumbers.PhoneNumberType.VOICEMAIL: "Voicemail",
        phonenumbers.PhoneNumberType.UNKNOWN: "Unknown"
    }
    return type_map.get(num_type_code, "Unknown")

def custom_slugify(text):
    if not text:
        return ""

    text = text.lower()

    text = text.replace("https://", "").replace("http://", "").replace("www.", "")

    tr_map = {
        'ş': 's', 'ı': 'i', 'ğ': 'g', 'ü': 'u', 'ö': 'o', 'ç': 'c',
        'Ş': 's', 'I': 'i', 'Ğ': 'g', 'Ü': 'u', 'Ö': 'o', 'Ç': 'c', 'İ': 'i'
    }
    for tr_char, en_char in tr_map.items():
        text = text.replace(tr_char, en_char)

    text = re.sub(r'[^a-z0-9]+', '-', text)

    text = text.strip('-')

    return text

def verify_address_osm(address_string):
    """
    Verifies an address using OpenStreetMap (Nominatim).
    """
    if not address_string:
        return False
        
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': address_string,
            'format': 'json',
            'limit': 1
        }
        headers = {
            'User-Agent': 'VGetit-App/1.0'  # Required by Nominatim Policy
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        return len(data) > 0
        
    except Exception as e:
        print(f"OSM verification failed: {e}")
        return False

def get_whois_details(domain):
    """
    Fetches WHOIS details for a domain.
    """
    try:
        # Clean domain if it's a URL
        domain = domain.lower().replace("https://", "").replace("http://", "").replace("www.", "")
        
        w = whois.whois(domain)
        
        # Handle different return types (list vs string vs datetime)
        reg_date = w.creation_date
        if isinstance(reg_date, list):
            reg_date = reg_date[0]
            
        origin = w.country
        if isinstance(origin, list):
            origin = origin[0]

        # Extract status (sometimes a list)
        status = w.status
        if isinstance(status, list):
            status = ", ".join(status[:3]) # Limit length
            
        return {
            'registration_date': reg_date,
            'origin_country': origin,
            'legal_status': status
        }
    except Exception as e:
        print(f"WHOIS lookup failed: {e}")
        return {}
