__all__ = ["build_regex", "AND", "OR", "NOT"]


import re


def build_regex(e: list[str]|str) -> str:
    """ Conjunct regex expressions; i.e., `"<expr1>|<expr2>|..."`. """
    if isinstance(e, str):
        e = [e]
    _e = []
    for expr in e:
        expr = expr.strip()
        if expr:
            _e.append(re.escape(expr.lower()))
    if len(_e) == 1:
        return _e[0]
    return "|".join(_e)


def AND(e: list[str]) -> str:
    """ Conjunct search expressions; i.e., `"<expr1> AND <expr2> AND ..."`. """
    for i in range(len(e)):
        if any(op in e[i] for op in ["AND", "OR", "NOT"]):
            if len(e) > 1:
                e[i] = f"({e[i]})"
        elif " " in e[i]:
            e[i] = f"\"{e[i]}\""
    if len(e) == 1:
        return e[0]
    return " AND ".join(e)


def OR(e: list[str]) -> str:
    """ Disjunct search expressions; i.e., `"<expr1> OR <expr2> OR ..."`. """
    for i, expr in enumerate(e):
        if any(op in expr for op in ["AND", "OR", "NOT"]):
            if len(e) > 1:
                e[i] = f"({expr})"
        elif " " in expr:
            e[i] = f"\"{expr}\""
    if len(e) == 1:
        return e[0]
    return " OR ".join(e)


def NOT(e: str) -> str:
    """ Negate a search expression; i.e., `"NOT <expression>"`. """
    if any(op in e for op in ["AND", "OR", "NOT"]):
        e = f"({e})"
    elif " " in e:
        e = f"\"{e}\""
    return f"NOT {e}"
