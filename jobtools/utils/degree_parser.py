__all__ = ["parse_degrees"]


import re


# _hs_pat = re.compile(
#     r'''
#     \b(?:
#         high[\s-]?school|       # High School
#         g\.?e\.?d\.?|           # GED
#         gen\.?ed\.?|            # Gen Ed (General Education)
#         secondary\s?school|     # Secondary School
#         secondary\s?education   # Secondary Education
#     )\b
#     ''',
#     re.VERBOSE | re.IGNORECASE
# )


# _aa_pat = re.compile(
#     r'''
#     \b(?:
#         a\.?a\.?|               # AA
#         a\.s\.|                 # A.S.
#         a\.?a\.?s\.?|           # AAS
#         (?:aa|aas|ba|bs)\s+as|              # AA/AAS/BA/BS + AS
#         as\s+(?:aa|aas|ba|bs)|              # AS + AA/AAS/BA/BS
#         as\s+(?:degree|cert|program|level)  # AS + degree/cert/program/level
#     )\b
#     ''',
#     re.VERBOSE | re.IGNORECASE
# )


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


def parse_degrees(text: str) -> tuple[bool, bool, bool]:
    """ Parse text for degree requirements.

    Parameters
    ----------
    text : str
        Input text to parse.

    Returns
    -------
    tuple[bool, bool, bool]
        Tuple indicating presence of (bachelor, master, doctorate) degrees.
    """
    # Handle "BS/MS" cases
    clean_text = text.replace('/', ' ')
    # Check each degree level
    has_bachelor = bool(_ba_pat.search(clean_text))
    has_master = bool(_ma_pat.search(clean_text))
    has_doctorate = bool(_phd_pat.search(clean_text))
    return has_bachelor, has_master, has_doctorate
