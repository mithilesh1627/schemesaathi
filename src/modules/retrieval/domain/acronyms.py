"""Domain Acronyms Dictionary and Expansion Engine from M0 Official Source Inventory."""

import re

# Audited domain acronym mapping strictly derived from M0 statutory documents
OFFICIAL_ACRONYMS: dict[str, str] = {
    "OTR": "One Time Registration",
    "NSP": "National Scholarship Portal",
    "AISHE": "All India Survey on Higher Education",
    "NPCI": "National Payments Corporation of India",
    "CMCSRS": "Chief Minister's College Students Rehabilitation Scheme",
    "Face RD": "Aadhaar Face Registered Device",
    "DBT": "Direct Benefit Transfer",
    "PFMS": "Public Financial Management System",
    "MoTA": "Ministry of Tribal Affairs",
    "MoSJE": "Ministry of Social Justice and Empowerment",
    "DUHE": "Directorate of University and Higher Education",
}


def expand_query_acronyms(query: str) -> tuple[str, list[str]]:
    """Expand recognized scholarship domain acronyms within the search query.

    Returns:
        tuple of (expanded_query, list_of_expanded_acronyms).
    """
    expanded_terms: list[str] = []
    text = query

    for acronym, full_term in OFFICIAL_ACRONYMS.items():
        # Match acronym as a standalone word (case-insensitive for standard terms, exact for mixed case like Face RD)
        pattern = rf"\b{re.escape(acronym)}\b"
        if re.search(pattern, text, re.IGNORECASE):
            expanded_terms.append(f"{acronym} ({full_term})")
            # If the full term is not already in the query, append it to maximize lexical & dense recall
            if full_term.lower() not in text.lower():
                text = f"{text} {full_term}"

    return text.strip(), expanded_terms
