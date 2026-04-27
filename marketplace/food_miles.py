import math

# Offline lookup — avoids hitting an external geocoding API on every page load.
# Covers Bristol and surrounding areas served by the marketplace.
POSTCODE_COORDS = {
    'BS1': (51.4545, -2.5879),
    'BS2': (51.4600, -2.5700),
    'BS3': (51.4400, -2.6000),
    'BS4': (51.4300, -2.5500),
    'BS5': (51.4600, -2.5400),
    'BS6': (51.4700, -2.6000),
    'BS7': (51.4800, -2.5800),
    'BS8': (51.4600, -2.6200),
    'BS9': (51.4900, -2.6300),
    'BS10': (51.5000, -2.6100),
    'BS11': (51.5000, -2.6700),
    'BS13': (51.4100, -2.6000),
    'BS14': (51.4000, -2.5600),
    'BS15': (51.4600, -2.5000),
    'BS16': (51.4900, -2.5000),
    'BS20': (51.4900, -2.7500),
    'BS21': (51.4300, -2.8500),
    'BS22': (51.3600, -2.9100),
    'BS23': (51.3400, -2.9700),
    'BS24': (51.3300, -2.9400),
    'BS25': (51.3300, -2.8500),
    'BS26': (51.2900, -2.8700),
    'BS27': (51.2800, -2.7800),
    'BS28': (51.2700, -2.7500),
    'BS29': (51.3300, -2.8000),
    'BS30': (51.4500, -2.4500),
    'BS31': (51.4200, -2.4900),
    'BS32': (51.5300, -2.5400),
    'BS34': (51.5200, -2.5600),
    'BS35': (51.5600, -2.5600),
    'BS36': (51.5100, -2.4900),
    'BS37': (51.5400, -2.4500),
    'BS39': (51.3400, -2.5800),
    'BS40': (51.3600, -2.6800),
    'BS41': (51.4000, -2.6700),
    'BS48': (51.4300, -2.7600),
    'BS49': (51.3800, -2.8100),
    'GL1': (51.8640, -2.2440),
    'GL2': (51.8400, -2.2600),
    'SN1': (51.5600, -1.7800),
    'SN2': (51.5700, -1.7900),
    'BA1': (51.3800, -2.3600),
    'BA2': (51.3500, -2.3600),
    'TA1': (51.0200, -3.1000),
    'SW1A': (51.5010, -0.1247),
    'SW1': (51.4975, -0.1357),
    'EC1': (51.5200, -0.1000),
    'W1': (51.5140, -0.1500),
}

BRISTOL_CENTRE = (51.4545, -2.5879)


def _get_coords(postcode):
    pc = postcode.upper().replace(' ', '')
    # Try longest prefix first (e.g. BS48, then BS4)
    for length in [4, 3, 2]:
        prefix = pc[:length]
        if prefix in POSTCODE_COORDS:
            return POSTCODE_COORDS[prefix]
    return None


def _haversine(lat1, lon1, lat2, lon2):
    R = 3958.8  # Earth's mean radius in miles — gives straight-line distance, not road distance
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return round(R * 2 * math.asin(math.sqrt(a)), 1)


def calculate_food_miles(postcode_from, postcode_to):
    coords_from = _get_coords(postcode_from)
    coords_to = _get_coords(postcode_to)
    if not coords_from or not coords_to:
        return None
    return _haversine(coords_from[0], coords_from[1], coords_to[0], coords_to[1])
