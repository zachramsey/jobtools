import re
from .uni2ascii import uni2ascii


STATES = [", ak", ", al", ", ar", ", az", ", ca", ", co", ", ct", ", dc", ", de", ", fl",
          ", ga", ", hi", ", ia", ", id", ", il", ", in", ", ks", ", ky", ", la", ", ma",
          ", md", ", me", ", mi", ", mn", ", mo", ", ms", ", mt", ", nc", ", nd", ", ne",
          ", nh", ", nj", ", nm", ", nv", ", ny", ", oh", ", ok", ", or", ", pa", ", ri",
          ", sc", ", sd", ", tn", ", tx", ", ut", ", va", ", vt", ", wa", ", wi", ", wv", ", wy" ]

# SECTION_REGEXES: list[tuple[str, str]] = [
#     ("13|EEO/DEI", r"\b(?:equal\s+(?:opportunity|employment)|eeo|de[i&]i|diversity|inclusion|affirmative action|accommodations?|commitment|statement|promise)\b"),
#     ("11|Legal", r"\b(?:screenings?|clearance|secret|background check|export control|visas?|sponsorships?|comply|disclaimers?|drug|unincorporated|federal|citizenship|fraud(s|ulent)?|notices?|disclosures?|conditions?|rights|at\-will|union|veterans?|citizen|exempt(?:ion)?|(?:candidates?|applicants?).*?privacy)\b"),
#     ("12|Hiring", r"\b(?:apply|applications?|applicants?|submit|resumes?|referr(?:ed|als?)|recruit(?:ing|ers?)?|hire|hiring|contact|email|interviews?|trial|posting)\b"),
#     ("02|Responsibilities", r"\b(?:responsibilit(?:y|ies)|responsible|duties|you(?:.*)(?:be\s+(?:doing|work(ing)? on)|do(?:ing)?|build|own|achieve|get to)|day in the life|day|functions?|daily|activities|Accountabilities)\b"),
#     ("05|Additional", r"\b(?:additional|other)\s+(?:requirements?|qualifications?|skills?|abilities?)\b"),
#     ("06|Physical", r"\b(?:(?:physical|medical|health|ehs|environmental)\s+(?:qualifications?|requirements?|abilit(?:y|ies)?|demands?))\b"),
#     ("04|Preferred", r"\b(?:prefer\w*|desir\w*|(?:nice|good|helpful)[-\s]?to[-\s]?haves?|(?:like|love) (?:to see|it if you)|stand out|you (?:also|are)|not required|don\'t need|plus(es)?|fit|extra credit|look(ing)? for|at least one|one or more)\b"),
#     ("03|Required", r"\b(?:basic|skills\s+required|must[-\s]?haves?|need to (?:see|have)|(?:you|'ll|\s+will)\s+(?:bring|need|have|possess)|should have|expect you to|we need)\b"),
#     ("08|Compensation", r"(?:\b(?:salary|pay|compensation|benefits?|perks|site ranges|'ll (?:enjoy|get)|offer|retirement|rewards?|what we bring)\b|\$)"),
#     ("07|Location", r"\b(?:locations?|work arrangements?|remote(?:ly)?|onsite|hybrid|ability to commute|relocate|relocation|usa|united states|where|flexib\w*|on[-\s]?site|Region|Country|City)\b"),
#     ("07|Location", r"(?:" + "|".join([re.escape(state) for state in STATES]) + r")\b"),
#     ("09|Details", r"\b(?:shift|(?:job|employment|work(er)?|position|time|career) (?:category|area)|type|temporary|regular|(full|part)[-\s]?time|hour(?:s|ly)|seasonal|contract(or)?|intern(ship)?|duration|travel|schedule(s|d|ing)?|environment|start)\b"),
#     ("01|Description", r"\b(?:overview|description|the (?:job|role|position)|summary|details|information|opportunity|notes?|expect|introduction|attributes|who you are|work with|your expertise)\b"),
#     ("10|About", r"\b(about|company|team|we |mission|culture|why|join|get to know|working (?:here|at|for)|values|business|life at|department)\b"),
#     ("02|Responsibilities", r"\b(?:roles?|you will|impact)\b"),
#     ("04|Preferred", r"\b(?:bonus|skills?|competenc(?:e|y|ies)|abilit(?:y|ies)?|knowledge|background|credentials?|ideal(?:ly)?|match|apart)\b"),
#     ("03|Required", r"\b(?:qualifications?|required|requirements?|essential|needed|academic|education)\b"),
# ]
# SECTION_REGEXES: list[tuple[str, str]] = [
#     ("ADMINISTRATIVE", r"\b(?:equal|eeo|de&?i|diversity|inclusion|affirmative action|accommodations?|security|clearance|background (?:check|investigation)|export control|visas?|sponsorships?|comply|disclaimers?|drug|federal|citizenship|exempt(?:ions?)?|fraud(?:ulent)?|notices?|disclosures?|conditions?|rights?|at[-\s]?will|union|veterans?|submit|referr(?:ed|als?)|recruit(?:ing|ers?)?|contact|email|interviews?|posting)\b"),
#     ("COMPENSATION", r"\$|\b(?:salary|pay|compensation|benefits?|perks|retirement|rewards?|what we offer)\b"),
#     ("DETAILS", r"\b(?:shift|(?:job|employment|work(er)?|position|time|career) (?:categor(?:y|ies)|areas?|types?)|(full|part)[-\s]?time|hour(?:s|ly)|intern(ship)?|duration|travel|schedule(s|d|ing)?)\b"),
#     ("DESCRIPTION", r"\b(?:overview|description|summary|the (?:job|role|position))\b"),
#     ("RESPONSIBILITY", r"\b(?:responsib(?:le|ility|ilities)|duties|you(?:'ll| will)? .*?(?:do(?:ing)?|work(ing)? on|build(?:ing)?|achieve|get to|impact)|day in the life|accountabilities)\b"),
#     ("PREFERRED", r"\b(?:prefer(?:red)|desired|(?:nice|good)[-\s]?to[-\s]?haves?|(?:to|you) stand out|we look for|bonus points|extra credit)\b"),
#     ("REQUIRED", r"\b(?:qualifications?|require(?:d|ments?)|must[-\s]?haves?|need to (?:see|have|succeed)|you(?:'ll| will)? (?:bring|need)|competencies|credentials|academic|education)\b"),
# ]
SECTION_REGEXES: list[tuple[str, str]] = [
    ("TRAVEL", r"\b(?:travel|work flexibility)\b"),
    ("NOTICE", r"\b(?:equal (?:opportunit(?:y|ies)|employ(?:ment|ee))|eeoc?|eoe|accommodations?|accessibility|candidate data|privacy polic(?:y|ies)|notices?|discl(?:aimer|osure)s?|(?:our|culture) commitment|commit(?:ted|ment)(?: to)|disabilit(?:y|ies)|discrimination|veterans?|inclusi(?:ve|on)|diversity|recruit(?:ing|ment|ers)|unsolicited|agencies|fair chance|los angeles county|county of los angeles|drug|your rights?|fraud(?:ulent)|statements|recent awards)\b"),
    ("PROCESS", r"\b(?:appl(?:y(?:ing)?|ication)|interview|expression of interest|(?:u\.s\.|multiple|number of) positions)\b"),
    ("COMPENSATION", r"\$|\b(?:salary|pay|compensation|benefits?|perks?|rewards?|we offer|in it for you|retirement|pto|stipend|time[-\s]off|company vehicle|relocat(?:e|ion)|you(?:'ed|'ll| will) (?:love|like))\b"),
    ("COMPANY", r"\b(?:nyse|nasdaq|about (?:(?:the|our) (?:company|team|organization|group)|us)|our (?:values|culture|purpose)|(?:<!your )mission|who we are|why join|join us|company overview|team description)\b"),
    ("CLASSIFICATION", r"(?:\A(?:job|business|career|functional) (?:area|family|level|segment|unit|stream)|\b(?:(?:sub)?category|reports? to|division))\b"),
    ("ELIGIBILITY", r"\b(?:eligibility|screenings?|clearances?|citizenship|(?:work|employment) authorization|ead|visa|sponsorship|(?:eligibility|special) requirements?|itar|export control(?:led)?|conditions of (?:employ|appoint)ment|e\-verify|foreign national)\b"),
    ("IDENTIFIER", r"\b(?:(?:job|req(?:uisition)?|position) (?:id|code|number)|\#.+)\b"),
    ("MODEL", r"\b(?:remote(?:ly)?|(?:work(?:place)?|job) (?:model|mode|schedules?|arrangement|options?)|flexible working|schedule for this position|workplace type|hybrid|onsite|commute|type|shift|duration|hour(?:s|ly)|flsa)\b"),
    ("ENVIRONMENT", r"\b(?:work(?:ing)? environment|work(?:ing) conditions|physical demands)\b"),
    ("PREFERRED", r"\b(?:prefer(?:red|ences?)?|desir(?:ed|able)|(?:nice|good)(?:[-\s]?to[-\s]?| if you )haves?|(?:to|you) stand out|sets? you apart|bonus|extra credit|accelerators|competitive edge|even better|keywords)\b"),
    ("REQUIRED", r"\b(?:require(?:d|ments?)|qualifications?|must[-\s]?haves?|need to (?:see|have|succeed)|you(?:'ll| will)? (?:bring|need|have)|must have|compentenc(?:y|ies)|mandatory|minimum|basic)\b|\bmin\.\s"),
    ("QUALIFICATIONS", r"\b(?:skills?|abilit(?:y|ies)?|knowledge|background|credentials?|academic|education|certifications?|experience|expertise|proficienc(?:y|ies)|we(?:'re| are)? (?:look(?:ing)? for|seeking)|who you are|the person|tech stack|collaboration|we value|competencies|ideal candidate)\b"),
    ("RESPONSIBILITIES", r"\b(?:(?:responsib|accountab)(?:le|ility|ilities)|duties|you will|will you do|you'll .*?(?:do(?:ing)?|work(ing)? on|build(?:ing)?|achieve|get to|gain|grow|learn)|impact|your mission|day in the life|(?:essential|job) functions|\d0 days|purpose|the challenge|percentage of time|projects?)\b"),
    ("DESCRIPTION", r"\b(?:description|summary|overview|introduction|role|opportunity|position)\b"),
    ("TITLE", r"\b(?:title|develop(?:er|ment)|engineer(?:ing))\b"),
    ("DETAILS", r"\b(?:(?:other|additional|general)(?: important)? information|details|logistics|recruiter)\b"),
    ("COMPANY", r"\b(?:about \w+|compan(?:y|ies)|department|team|organization|employer|program|missions?|culture|values|who (?:are we|we are|will you)|our (?:vision|people)|working with us|learn more|what we(?: do|\'re doing))\b"),
    ("LOCATION", r"\b(?:locations?|city|state|province|\, [A-Z]{2})\b"),
    ("DESCRIPTION", r"\b(?:job|work)\b"),
    ("DATE", r"\b(?:date|posted on)\b"),
    ("NOTES", r"\b(?:notes?)\b"),
    ("LINK", r"\b(?:https?|www)\b"),
]
PATTERNS: list[tuple[str, re.Pattern]] = [
    (label, re.compile(rx, re.IGNORECASE)) for label, rx in SECTION_REGEXES
]

def clean_description(md: str) -> str:
    """ Clean and standardize markdown text of job description. """
    # Convert to ASCII characters
    md = uni2ascii(md)
    md = md.encode("ascii", "ignore").decode("ascii", "ignore")
    
    # Remove newlines within paragraphs
    md = re.sub(r"(?<=\S) *\n +(?=\S)", r" ", md)
    # Remove excess spaces
    md = re.sub(r" {2,}", r" ", md)
    # Remove excess bullet markers
    md = re.sub(r"(\* ){2,}", r"* ", md)
    # Remove leading spaces
    md = re.sub(r"^ ", r"", md, flags=re.MULTILINE)
    # Remove trailing spaces
    md = re.sub(r" $", r"", md, flags=re.MULTILINE)
    # Remove excess vertical whitespace
    md = re.sub(r"\n{3,}", r"\n\n", md)

    # Remove space before punctuation
    pat = r" ([,.!?:;])"
    md = re.sub(pat, r"\1", md)
    # Ensure space after comma unless between digits
    pat = r"(?<!\d)\, *(?!\d)"
    md = re.sub(pat, r", ", md)
    # Ensure space after other punctuation
    pat = r"(\S)([!?:;] *)(\S)"
    md = re.sub(pat, r"\1\2 \3", md)

    # Merge adjacent bold-italic markers
    pat = r"(?<=\S)___([ \t]*)___(?=\S)"
    md = re.sub(pat, r"\1", md)
    # Merge adjacent bold markers
    pat = r"(?<=\S)__([ \t]*)__(?=\S)"
    md = re.sub(pat, r"\1", md)
    # # Merge adjacent italic markers
    # pat = r"(?<=[^\s_])_([ \t]*)_(?=[^\s_])"
    # md = re.sub(pat, r"\1", md)

    # Move trailing colons to outside of emphasis
    pat = r" ?\: ?(_+)"
    md = re.sub(pat, r"\1:", md)
    # Remove Non-header lines with leading "#"
    pat = r"^\s*(#+)([^\s#].+?)\s*$"
    md = re.sub(pat, r"", md, flags=re.MULTILINE)
    # Standardize existing headers to L3
    pat = r"\s*\#{1,6}\s+"
    md = re.sub(pat, r"\n### ", md)

    # Make header from [ __{h}__ {t} ]
    pat = r"^(?!\s*\* )\s*_+(.+?)_+\s*(.+?)\s*$"
    rep = r"\n### \1\n\n\2\n"
    md = re.sub(pat, rep, md, flags=re.MULTILINE)
    # Make header from [ __{h} : {t}__ ]
    pat = r"^(?!\s*\* )\s*_+(.+?)\s*\:\s*(.+?)_+\s*$"
    rep = r"\n### \1\n\n\2\n"
    md = re.sub(pat, rep, md, flags=re.MULTILINE)
    # Make header from [ {h} : {t} ]
    pat = r"^(?!\s*\* )\s*(.{3,}?)\s*\:\s*(.+?)\s*$"
    rep = r"\n### \1\n\n\2\n"
    md = re.sub(pat, rep, md, flags=re.MULTILINE)
    # Make header from [ __{header}__ : ]
    pat = r"^\s*_{2,}(.+?)_{2,}\s*\:?\s*$"
    rep = r"\n### \1\n\n"
    md = re.sub(pat, rep, md, flags=re.MULTILINE)
    # Make header from [ {HEADER} ]
    pat = r"^\s*([A-Z][A-Z?!.,;\-\s]{3,})\s*$"
    rep = r"\n### \1\n\n"
    md = re.sub(pat, rep, md, flags=re.MULTILINE)
    
    # Make header from line immediately preceding bullet points
    pat = r"^(?!\s*\* )(.+?)\s*\n(\s*\* .+?)"
    rep = r"\n### \1\n\n\2"
    md = re.sub(pat, rep, md, flags=re.MULTILINE)
    # Make header from next populated line after bullet points
    pat = r"(\s*\* .+?)\n+(?!\s*\* )(.+?)\s*$"
    rep = r"\1\n\n### \2"
    md = re.sub(pat, rep, md, flags=re.MULTILINE)

    # Consolidate multiple header markers
    md = re.sub(r"(### )+", r"### ", md)
    # Remove emphasis markers, colons, and periods from headers
    pat = r"^\s*\#\#\#\s*_{2,}?(.+?)_{2,}?[:.?! \t]*$"
    md = re.sub(pat, r"### \1", md, flags=re.MULTILINE)
    # All-caps headers to title case
    pat = r"^(?:### )([A-Z][A-Z\s]{3,})$"
    md = re.sub(pat, lambda m: "### " + m.group(1).title(), md, flags=re.MULTILINE)

    # Remove escape symbols
    md = md.replace("\\", "")
    # Remove lines with few characters
    pat = r"^\s*(.{1,5})\s*$"
    md = re.sub(pat, r"", md, flags=re.MULTILINE)
    # Remove seperator lines
    pat = r"^\s*[\-\=\_\+\*\~]{3,}\s*$"
    md = re.sub(pat, r"", md, flags=re.MULTILINE)
    # Ensure no empty lines between bullet points
    pat = r"\n+(\t*\* .+?)$"
    md = re.sub(pat, r"\n\1", md, flags=re.MULTILINE)
    # Ensure exactly one blank line before and after headers
    pat = r"\n### (.+?)\n"
    md = re.sub(pat, r"\n\n### \1\n\n", md)
    # Remove remaining formatting markers
    md = re.sub(r"_+", r"", md)
    # Remove excess vertical whitespace
    md = re.sub(r"\n{3,}", r"\n\n", md)

    return md


def extract_headers(md: str) -> list[str]:
    """ Extract header lines from cleaned markdown text. """
    headers = []
    for line in md.splitlines():
        if "###" in line:
            headers.append(line.replace("###", "").strip())
    return headers


def get_label(header: str) -> str:
    """ Find best-matching label for a given header line. """
    header = header.replace("###", "").strip()
    for lbl, ptrn in PATTERNS:
        if re.search(ptrn, header):
            return lbl
    return ""


def format_mapping(values: list[str], labels: list[str]) -> str:
    """ Generate formatted "{label} | {header}" strings for debugging. """
    return "\n".join(f"{lbl:>16} | {val}" for val, lbl in zip(values, labels))


def generate_header_debug_str(md: str) -> str:
    """ Generate formatted "{label} | {header}" strings for debugging. """
    headers = extract_headers(md)
    labels = [get_label(hdr) for hdr in headers]
    return format_mapping(headers, labels)


def split_sections(md: str) -> list[tuple[str, str]]:
    """ Split cleaned markdown text into sections based on headers.

    Parameters
    ----------
    desc : str
        Cleaned markdown text of job description.

    Returns
    -------
    sections : list[tuple[str, str]]
        List of (header, section text) tuples.
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
    