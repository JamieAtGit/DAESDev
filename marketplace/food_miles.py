import pgeocode


def calculate_food_miles(postcode_from, postcode_to):
    """
    Calculate the distance in miles between two UK postcodes.
    Returns None if either postcode is invalid.
    """
    try:
        nomi = pgeocode.Nominatim('gb')
        dist = pgeocode.GeoDistance('gb')
        loc_from = nomi.query_postal_code(postcode_from.replace(' ', ''))
        loc_to = nomi.query_postal_code(postcode_to.replace(' ', ''))

        if loc_from.empty or loc_to.empty:
            return None

        km = dist.query_postal_code(
            postcode_from.replace(' ', ''),
            postcode_to.replace(' ', '')
        )
        if km is None:
            return None
        miles = round(km * 0.621371, 1)
        return miles
    except Exception:
        return None
