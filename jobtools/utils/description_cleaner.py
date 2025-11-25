__all__ = ["clean_description"]


import re
from .uni2ascii import uni2ascii


def clean_description(md: str) -> str:
    """ Clean and standardize markdown text of job description. """
    # Convert to ASCII characters
    md = uni2ascii(md)
    md = md.encode("ascii", "ignore").decode("ascii", "ignore")
    
    # Remove escape symbols
    md = md.replace("\\", "")
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
    pat = r" *([,.!?:;])"
    md = re.sub(pat, r"\1", md)
    # Ensure space after comma unless between digits
    pat = r"(?<!\d)\, *(?!\d)"
    md = re.sub(pat, r", ", md)
    # # Ensure space after other punctuation
    # pat = r"(\S)([!?;] *)(\S)"
    # md = re.sub(pat, r"\1\2 \3", md)

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
    pat = r"\: *(_+)"
    md = re.sub(pat, r"\1:", md)
    # Remove Non-header lines with leading "#"
    pat = r"^\s*(#+)([^\s#].+?)\s*$"
    md = re.sub(pat, r"", md, flags=re.MULTILINE)
    # Standardize existing headers to L3
    pat = r"\s*\#{1,6}\s+"
    md = re.sub(pat, r"\n### ", md)

    # Make header from [ __{h}__ {t} ]
    pat = r"^(?!\s*\* )\s*_+(.+?)_+(?!,)\:?\s+(.+?)\s*$"
    rep = r"\n### \1\n\n\2\n"
    md = re.sub(pat, rep, md, flags=re.MULTILINE)
    # Make header from [ __{h} : {t}__ ]
    pat = r"^(?!\s*\* )\s*_+(.+?)\:\s+(.+?)_+\s*$"
    rep = r"\n### \1\n\n\2\n"
    md = re.sub(pat, rep, md, flags=re.MULTILINE)
    # Make header from [ {h} : {t} ]
    pat = r"^(?!\s*\* )\s*(.{3,}?)\:\s+(.+?)\s*$"
    rep = r"\n### \1\n\n\2\n"
    md = re.sub(pat, rep, md, flags=re.MULTILINE)
    # Make header from [ __{header}__ : ]
    pat = r"^\s*_{2,}(.+?)_{2,}\:?\s*$"
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

    # Remove empty headers
    pat = r"^###\s*$"
    md = re.sub(pat, r"", md, flags=re.MULTILINE)
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
