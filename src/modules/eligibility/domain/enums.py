"""Domain Enums for Deterministic Eligibility Evaluation."""

import enum


class RuleOutcome(enum.StrEnum):
    """Outcome of a single deterministic eligibility rule check."""

    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class EvaluationOutcome(enum.StrEnum):
    """Aggregate statutory eligibility outcome for a scheme."""

    ELIGIBLE = "ELIGIBLE"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"
    UNKNOWN = "UNKNOWN"
