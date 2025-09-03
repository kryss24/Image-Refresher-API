import json
import re



def extract_location(text):
    # 1. Full street address
    address_match = re.search(r'\d{1,5}\s[\w\s]+,\s*\w+,\s*[A-Z]{2}\s*\d{5}', text)
    if address_match:
        return address_match.group(0)

    # 2. Apartment / Complex names (capitalized words with optional "The")
    complex_match = re.search(r'(?:The\s)?[A-Z][A-Za-z0-9&\-\']+(?:\s[A-Z][A-Za-z0-9&\-\']+){0,4}', text)
    if complex_match:
        return complex_match.group(0)

    # 3. City / University mentions
    city_uni_match = re.search(r'(Tallahassee|Athens|Tampa|College Town|FSU|UGA|USF)', text, re.IGNORECASE)
    if city_uni_match:
        return city_uni_match.group(0)

    return None

def extract_metadata(text):
    bedrooms, bathrooms, location, min_price, max_price = None, None, None, None, None

    # Bedrooms
    br_match = re.search(r'(\d+)\s*(?:BR|Bed|Beds|Bedroom|Bedrooms)', text, re.IGNORECASE)
    if br_match:
        bedrooms = int(br_match.group(1))

    # Bathrooms
    ba_match = re.search(r'(\d+(\.\d+)?)\s*(?:BA|Bath|Baths|Bathroom|Bathrooms)', text, re.IGNORECASE)
    if ba_match:
        bathrooms = float(ba_match.group(1))

    # Location extraction
    location = extract_location(text)

    # Prices
    prices = re.findall(r'\$([0-9]+(?:,[0-9]{3})*(?:\.\d{1,2})?)', text)
    prices = [float(p.replace(",", "")) for p in prices]
    if prices:
        if len(prices) == 1:
            min_price = 0
            max_price = prices[0]
        else:
            min_price = min(prices)
            max_price = max(prices)

    return  min_price, max_price,bedrooms, bathrooms, location