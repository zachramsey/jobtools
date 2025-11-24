__all__ = ["parse_location"]

# Mapping of US state names to their 2-letter abbreviations
NAME_TO_ABBR = {
    "alaska": "ak", "alabama": "al", "arkansas": "ar", "arizona": "az",
    "california": "ca", "colorado": "co", "connecticut": "ct",
    "district of columbia": "dc", "delaware": "de", "florida": "fl",
    "georgia": "ga", "hawaii": "hi", "iowa": "ia", "idaho": "id",
    "illinois": "il", "indiana": "in", "kansas": "ks", "kentucky": "ky",
    "louisiana": "la", "massachusetts": "ma", "maryland": "md", "maine": "me",
    "michigan": "mi", "minnesota": "mn", "missouri": "mo", "mississippi": "ms",
    "montana": "mt", "north carolina": "nc", "north dakota": "nd",
    "nebraska": "ne", "new hampshire": "nh", "new jersey": "nj",
    "new mexico": "nm", "nevada": "nv", "new york": "ny", "ohio": "oh",
    "oklahoma": "ok", "oregon": "or", "pennsylvania": "pa",
    "rhode island": "ri", "south carolina": "sc", "south dakota": "sd",
    "tennessee": "tn", "texas": "tx", "utah": "ut", "virginia": "va",
    "vermont": "vt", "washington": "wa", "wisconsin": "wi",
    "west virginia": "wv", "wyoming": "wy"
}
STATE_LOOKUP = set(NAME_TO_ABBR.keys()).union(set(NAME_TO_ABBR.values()))
US_LOOKUP = set(["us", "usa", "united states", "united states of america"])


def parse_location(loc: str) -> tuple:
    """ Parse location string into (`"<city>"`, `"<state>"`, `"<city>, <state>"`) tuple. """
    if not isinstance(loc, str):
        return "", "", ""
    parts = [p.strip() for p in loc.split(",")]
    city, state = "", ""
    if len(parts) == 1:
        # Single part; could be city or state
        part0_lower = parts[0].lower()
        if part0_lower in STATE_LOOKUP:
            state = NAME_TO_ABBR.get(part0_lower, part0_lower).upper()
        elif part0_lower not in US_LOOKUP:
            city = part0_lower.title()
    elif len(parts) == 2:
        # Two parts; could be "City, State" or "State, Country"
        part0_raw, part1_lower = parts[0], parts[1].lower()
        if part1_lower in US_LOOKUP:
            if part0_raw.lower() in STATE_LOOKUP:
                part0_lower = part0_raw.lower()
                state = NAME_TO_ABBR.get(part0_lower, part0_lower).upper()
            else:
                city = part0_raw.title()
        elif part1_lower in STATE_LOOKUP:
            city = part0_raw.title()
            state = NAME_TO_ABBR.get(part1_lower, part1_lower).upper()
    elif len(parts) == 3:
        # Three parts; assume "City, State, Country"
        city = parts[0].title()
        state_part = parts[1].lower()
        state = NAME_TO_ABBR.get(state_part, state_part).upper()
    location = ", ".join(filter(None, [city, state]))
    return city, state, location