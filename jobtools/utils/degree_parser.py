__all__ = ["parse_degrees"]


import re

_ba_pat = re.compile(
    r'''
        \b(?:
            b\.?a\.?|               # BA
            b\.?s\.?|               # BS
            b\.?sc\.?|              # BSc
            b\.?s\.?e\.?|           # BSE
            b\.?eng\.?|             # BEng
            b\.?b\.?a\.?|           # BBA
            bfa|bit|                # Other Bachelors
            bachelor\'?s?|          # Bachelor, Bachelors, Bachelor's
            undergrad(?:uate)?|     # Undergrad, Undergraduate
            four-year\s+degree|     # four-year degree
            4-year\s+degree|        # 4-year degree
            university\s+degree|    # University degree
            degree\s+in\s+\w+       # Degree in [field]
        )\b
    ''',
    re.VERBOSE | re.IGNORECASE
)

_ma_pat = re.compile(
    r'''
        \b(?:
            m\.?a\.?|               # MA
            m\.?s\.?|               # MS
            m\.?b\.?a\.?|           # MBA
            m\.?sc\.?|              # MSc
            m\.?s\.?e\.?|           # MSE
            m\.?eng\.?|             # MEng
            mph|mcs|mfa|            # Other Masters
            master\'?s?|            # Master, Masters, Master's
            graduate\s+degree|      # "Graduate degree" usually implies Masters+
            advanced\s+degree|      # "Advanced degree"
            post-?graduate          # Post-graduate
        )\b
    ''',
    re.VERBOSE | re.IGNORECASE
)

_phd_pat = re.compile(
    r'''
        \b(?:
            ph\.?d\.?|              # PhD, Ph.D.
            doctor(?:ate|al)|       # Doctorate, Doctoral
            jd|md|edd|dphil         # Professional doctorates
        )\b
    ''',
    re.VERBOSE | re.IGNORECASE
)

LEVEL_MAP = {
    0: "No Degree",
    1: "Bachelor's",
    2: "Master's",
    3: "Doctorate"
}

def parse_degrees(self, text: str) -> set[int]:
    """ Parse input text for degree mentions.

    Parameters
    ----------
    text : str
        Input text to parse.

    Returns
    -------
    set[int]
        Set of degree levels found (1: Bachelor's, 2: Master's, 3: Doctorate).
    """
    # Handle "BS/MS" cases
    clean_text = text.replace('/', ' ')
    # Check each degree level
    found_levels = set()
    if _phd_pat.search(clean_text):
        found_levels.add(3)
    if _ma_pat.search(clean_text):
        found_levels.add(2)
    if _ba_pat.search(clean_text):
        found_levels.add(1)
    return found_levels
