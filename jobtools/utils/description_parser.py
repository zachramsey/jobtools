__all__ = [
    "get_label",
    "parse_description",
]

import re

STATES = [", ak", ", al", ", ar", ", az", ", ca", ", co", ", ct", ", dc", ", de", ", fl",
          ", ga", ", hi", ", ia", ", id", ", il", ", in", ", ks", ", ky", ", la", ", ma",
          ", md", ", me", ", mi", ", mn", ", mo", ", ms", ", mt", ", nc", ", nd", ", ne",
          ", nh", ", nj", ", nm", ", nv", ", ny", ", oh", ", ok", ", or", ", pa", ", ri",
          ", sc", ", sd", ", tn", ", tx", ", ut", ", va", ", vt", ", wa", ", wi", ", wv", ", wy" ]

SECTION_REGEXES: list[tuple[str, str]] = [
    ("TRAVEL", r"\b(?:travel|work flexibility)\b"),
    ("NOTICE", r"\b(?:equal (?:opportunit(?:y|ies)|employ(?:ment|ee))|eeoc?|eoe|accommodations?|accessibility|candidate data|privacy polic(?:y|ies)|notices?|discl(?:aimer|osure)s?|(?:our|culture) commitment|commit(?:ted|ment)(?: to)|disabilit(?:y|ies)|discrimination|veterans?|inclusi(?:ve|on)|diversity|recruit(?:ing|ment|ers)|unsolicited|agencies|fair chance|los angeles county|county of los angeles|drug|your rights?|fraud(?:ulent)|statements|recent awards)\b"),   # noqa: E501
    ("PROCESS", r"\b(?:appl(?:y(?:ing)?|ication)|interview|expression of interest|(?:u\.s\.|multiple|number of) positions)\b"), # noqa: E501
    ("COMPENSATION", r"\$|\b(?:salary|pay|compensation|benefits?|perks?|rewards?|we offer|in it for you|retirement|pto|stipend|time[-\s]off|company vehicle|relocat(?:e|ion)|you(?:'ed|'ll| will) (?:love|like))\b"),   # noqa: E501
    ("COMPANY", r"\b(?:nyse|nasdaq|about (?:(?:the|our) (?:company|team|organization|group)|us)|our (?:values|culture|purpose)|(?:<!your )mission|who we are|why join|join us|company overview|team description)\b"),   # noqa: E501
    ("CLASSIFICATION", r"(?:\A(?:job|business|career|functional) (?:area|family|level|segment|unit|stream)|\b(?:(?:sub)?category|reports? to|division))\b"),    # noqa: E501
    ("ELIGIBILITY", r"\b(?:eligibility|screenings?|clearances?|citizenship|(?:work|employment) authorization|ead|visa|sponsorship|(?:eligibility|special) requirements?|itar|export control(?:led)?|conditions of (?:employ|appoint)ment|e\-verify|foreign national)\b"),   # noqa: E501
    ("IDENTIFIER", r"\b(?:(?:job|req(?:uisition)?|position) (?:id|code|number)|\#.+)\b"),
    ("MODEL", r"\b(?:remote(?:ly)?|(?:work(?:place)?|job) (?:model|mode|schedules?|arrangement|options?)|flexible working|schedule for this position|workplace type|hybrid|onsite|commute|type|shift|duration|hour(?:s|ly)|flsa)\b"),   # noqa: E501
    ("ENVIRONMENT", r"\b(?:work(?:ing)? environment|work(?:ing) conditions|physical demands)\b"),
    ("PREFERRED", r"\b(?:prefer(?:red|ences?)?|desir(?:ed|able)|(?:nice|good)(?:[-\s]?to[-\s]?| if you )haves?|(?:to|you) stand out|sets? you apart|bonus|extra credit|accelerators|competitive edge|even better|keywords)\b"), # noqa: E501
    ("REQUIRED", r"\b(?:require(?:d|ments?)|qualifications?|must[-\s]?haves?|need to (?:see|have|succeed)|you(?:'ll| will)? (?:bring|need|have)|must have|compentenc(?:y|ies)|mandatory|minimum|basic)\b|\bmin\.\s"),   # noqa: E501
    ("QUALIFICATIONS", r"\b(?:skills?|abilit(?:y|ies)?|knowledge|background|credentials?|academic|education|certifications?|experience|expertise|proficienc(?:y|ies)|we(?:'re| are)? (?:look(?:ing)? for|seeking)|who you are|the person|tech stack|collaboration|we value|competencies|ideal candidate)\b"),   # noqa: E501
    ("RESPONSIBILITIES", r"\b(?:(?:responsib|accountab)(?:le|ility|ilities)|duties|you will|will you do|you'll .*?(?:do(?:ing)?|work(ing)? on|build(?:ing)?|achieve|get to|gain|grow|learn)|impact|your mission|day in the life|(?:essential|job) functions|\d0 days|purpose|the challenge|percentage of time|projects?)\b"),   # noqa: E501
    ("DESCRIPTION", r"\b(?:description|summary|overview|introduction|role|opportunity|position)\b"),
    ("TITLE", r"\b(?:title|develop(?:er|ment)|engineer(?:ing))\b"),
    ("DETAILS", r"\b(?:(?:other|additional|general)(?: important)? information|details|logistics|recruiter)\b"),
    ("COMPANY", r"\b(?:about \w+|compan(?:y|ies)|department|team|organization|employer|program|missions?|culture|values|who (?:are we|we are|will you)|our (?:vision|people)|working with us|learn more|what we(?: do|\'re doing))\b"),     # noqa: E501
    ("LOCATION", r"\b(?:locations?|city|state|province|\, [A-Z]{2})\b"),
    ("DESCRIPTION", r"\b(?:job|work)\b"),
    ("DATE", r"\b(?:date|posted on)\b"),
    ("NOTES", r"\b(?:notes?)\b"),
    ("LINK", r"\b(?:https?|www)\b"),
]

PATTERNS: list[tuple[str, re.Pattern]] = [
    (label, re.compile(rx, re.IGNORECASE))
    for label, rx in SECTION_REGEXES
]


def extract_headers(md: str) -> list[str]:
    """Extract header lines from cleaned markdown text."""
    headers = []
    for line in md.splitlines():
        if "###" in line:
            headers.append(line.replace("###", "").strip())
    return headers


def get_label(header: str) -> str:
    """Find best-matching label for a given header line."""
    header = header.replace("###", "").strip()
    for lbl, ptrn in PATTERNS:
        if re.search(ptrn, header):
            return lbl
    return ""


def format_mapping(values: list[str], labels: list[str]) -> str:
    """Generate formatted "{label} | {header}" strings for debugging."""
    return "\n".join(f"{lbl:>16} | {val}" for val, lbl in zip(values, labels))


def generate_header_debug_str(md: str) -> str:
    """Generate formatted "{label} | {header}" strings for debugging."""
    headers = extract_headers(md)
    labels = [get_label(hdr) for hdr in headers]
    return format_mapping(headers, labels)


def generate_description_debug_str(md: str) -> str:
    """Generate formatted description sections for debugging."""
    output = ""
    for line in md.splitlines():
        if "###" in line:
            output += f"{get_label(line):>16} | {line}\n"
        else:
            output += f"{'':>16} | {line}\n"
    return output


def parse_description(md: str) -> list[tuple[str, str]]:
    """Parse cleaned markdown description into sections.

    Parameters
    ----------
    md : str
        Cleaned markdown text of job description.

    Returns
    -------
    list[tuple[str, str]]
        List of (header, content) tuples for each section.

    Notes
    -----
    See `utils::clean_description` for requisite cleaning function.
    """
    sections = []
    curr_header = ""
    curr_text = ""
    for line in md.splitlines(keepends=True):
        if "###" in line:
            # Save previous section
            if curr_header or curr_text:
                sections.append((curr_header.strip(), curr_text.strip()))
            # Start new section
            curr_header = line
            curr_text = ""
        else:
            curr_text += line
    # Save final section
    if curr_header or curr_text:
        sections.append((curr_header.strip(), curr_text.strip()))
    return sections
