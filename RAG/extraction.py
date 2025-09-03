import re

def extract_metadata(text):
    # Price
    price_matches = re.findall(r"\$?(\d{3,4})", text)
    price_min = min(map(int, price_matches)) if price_matches else None
    price_max = max(map(int, price_matches)) if price_matches else None

    # Beds/Baths
    beds = None
    baths = None
    bed_match = re.search(r"(\d+)\s*bed", text.lower())
    bath_match = re.search(r"(\d+)\s*bath", text.lower())
    if bed_match:
        beds = int(bed_match.group(1))
    if bath_match:
        baths = int(bath_match.group(1))

    # Location (very rough: look for "Athens", "UGA", etc.)
    location = None
    loc_match = re.search(r"Athens, GA|UGA|Downtown", text, re.IGNORECASE)
    if loc_match:
        location = loc_match.group(0)

    return price_min, price_max, beds, baths, location
