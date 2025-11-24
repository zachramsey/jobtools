__all__ = ["build_regex", "AND", "OR", "NOT"]


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
