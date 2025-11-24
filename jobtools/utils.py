import logging


class JTLogger:
    formatter = logging.Formatter(
        "{asctime} | {name:^8} | {levelname:^8} | {message}",
        datefmt="%H:%M:%S",
        style="{"
    )

    def __init__(self):
        self.logger = logging.getLogger("JobTools")

    def configure(self, level):
        self.set_level(level)
        self._add_handler()
        self.logger.propagate = False

    def debug(self, message):
        self.logger.debug(f"{message}")

    def info(self, message):
        self.logger.info(f"{message}")

    def warning(self, message):
        self.logger.warning(f"{message}")
    
    def set_level(self, level):
        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if level in levels:
            self.logger.setLevel(level)

    def _add_handler(self):
        sh = logging.StreamHandler()
        sh.setFormatter(self.formatter)
        self.logger.addHandler(sh)

        # Remove duplicate handlers
        if len(self.logger.handlers) > 1:
            self.logger.handlers = [self.logger.handlers[0]]

    @staticmethod
    def conform_format(logger_name: str):
        """ Set JTLogger format for an existing logger by name. """
        logger = logging.getLogger(logger_name)
        for h in logger.handlers:
            if isinstance(h, logging.StreamHandler):
                h.setFormatter(JTLogger.formatter)
                break


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


def build_regex(terms: list[str]|str) -> str:
    """ Conjunct regex expressions; i.e., `"<term1>|<term2>|..."`. """
    if isinstance(terms, str):
        return terms
    if len(terms) == 0:
        return ""
    for i, term in enumerate(terms):
        if " " in term:
            terms[i] = f"\'{term}\'"
    if len(terms) == 1:
        return terms[0]
    return "|".join(terms)


def AND(expressions: list[str]) -> str:
    """ Conjunct search expressions; i.e., `"<expr1> AND <expr2> AND ..."`. """
    for i in range(len(expressions)):
        if any(op in expressions[i] for op in ["AND", "OR", "NOT"]):
            if len(expressions) > 1:
                expressions[i] = f"({expressions[i]})"
        elif " " in expressions[i]:
            expressions[i] = f"\"{expressions[i]}\""
    if len(expressions) == 1:
        return expressions[0]
    return " AND ".join(expressions)


def OR(expressions: list[str]) -> str:
    """ Disjunct search expressions; i.e., `"<expr1> OR <expr2> OR ..."`. """
    for i, term in enumerate(expressions):
        if any(op in term for op in ["AND", "OR", "NOT"]):
            if len(expressions) > 1:
                expressions[i] = f"({term})"
        elif " " in term:
            expressions[i] = f"\"{term}\""
    if len(expressions) == 1:
        return expressions[0]
    return " OR ".join(expressions)


def NOT(expression: str) -> str:
    """ Negate a search expression; i.e., `"NOT <expression>"`. """
    if any(op in expression for op in ["AND", "OR", "NOT"]):
        expression = f"({expression})"
    elif " " in expression:
        expression = f"\"{expression}\""
    return f"NOT {expression}"

