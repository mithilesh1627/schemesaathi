"""Deterministic JSON-Logic Abstract Syntax Tree (AST) Evaluator.

This module implements a pure, deterministic 3-valued Kleene logic evaluator for
statutory eligibility rules. It requires zero network calls, zero LLMs, and zero
vector embeddings.

Evaluator Invariant:
    Outcome is strictly one of:
    - PASS: statutory rule satisfied.
    - FAIL: statutory rule unsatisfied.
    - UNKNOWN: missing student profile attribute or malformed/unsupported rule.
"""

from dataclasses import dataclass
from typing import Any

from src.modules.eligibility.domain.enums import RuleOutcome


class UnsupportedOperatorError(Exception):
    """Raised when an AST contains an unapproved operator."""


SUPPORTED_OPERATORS: frozenset[str] = frozenset(
    {"==", "!=", ">", ">=", "<", "<=", "in", "and", "or", "not", "var"}
)

# Standard canonical field aliases for student context
_FIELD_ALIASES: dict[str, str] = {
    "income": "annual_family_income_inr",
    "annual_income_inr": "annual_family_income_inr",
    "annual_income": "annual_family_income_inr",
    "family_income": "annual_family_income_inr",
    "financial.annual_family_income_inr": "annual_family_income_inr",
    "category": "social_category",
    "demographics.social_category": "social_category",
    "caste": "social_category",
    "domicile": "domicile_state",
    "demographics.domicile_state": "domicile_state",
    "state": "domicile_state",
    "marks": "marks_percent",
    "percentage": "marks_percent",
    "academic.marks_percent": "marks_percent",
    "course": "course_level",
    "academic.course_level": "course_level",
    "gender": "gender",
    "demographics.gender": "gender",
    "disability": "is_disability",
    "is_disabled": "is_disability",
    "displaced": "is_displaced",
    "is_conflict_displaced": "is_displaced",
}


@dataclass(frozen=True)
class NodeEvaluationResult:
    """Evaluation result for an individual AST node or sub-tree."""

    outcome: RuleOutcome
    value: Any = None
    missing_fields: tuple[str, ...] = ()
    error: str | None = None
    reasons: tuple[str, ...] = ()


def _resolve_context_variable(
    var_path: str, context: dict[str, Any]
) -> tuple[RuleOutcome, Any, str | None]:
    """Resolve a variable reference against student context, supporting dot notation and aliases."""
    if not isinstance(var_path, str) or not var_path.strip():
        return RuleOutcome.UNKNOWN, None, "empty_variable_name"

    clean_path = var_path.strip()

    # 1. Direct key match
    if clean_path in context:
        val = context[clean_path]
        if val is not None:
            return RuleOutcome.PASS, val, None
        return RuleOutcome.UNKNOWN, None, clean_path

    # 2. Canonical alias match
    canonical_key = _FIELD_ALIASES.get(clean_path)
    if canonical_key and canonical_key in context:
        val = context[canonical_key]
        if val is not None:
            return RuleOutcome.PASS, val, None
        return RuleOutcome.UNKNOWN, None, canonical_key

    # 3. Dotted dictionary traversal (e.g. "financial.annual_family_income_inr")
    if "." in clean_path:
        parts = clean_path.split(".")
        curr: Any = context
        for part in parts:
            if isinstance(curr, dict) and part in curr:
                curr = curr[part]
            else:
                curr = None
                break
        if curr is not None:
            return RuleOutcome.PASS, curr, None

    # Not found or value is None -> UNKNOWN
    reported_key = canonical_key if canonical_key else clean_path
    return RuleOutcome.UNKNOWN, None, reported_key


def evaluate_ast_node(node: Any, context: dict[str, Any]) -> NodeEvaluationResult:
    """Evaluate a single JSON-Logic AST node against context using 3-valued Kleene logic."""
    # 1. Primitive literal values
    if node is None:
        return NodeEvaluationResult(outcome=RuleOutcome.UNKNOWN, error="AST node is null")

    if isinstance(node, (bool, int, float, str)):
        return NodeEvaluationResult(outcome=RuleOutcome.PASS, value=node)

    if isinstance(node, list):
        # Bare list of expressions
        return NodeEvaluationResult(outcome=RuleOutcome.PASS, value=node)

    if not isinstance(node, dict):
        return NodeEvaluationResult(
            outcome=RuleOutcome.UNKNOWN,
            error=f"Malformed AST node: expected dict, got {type(node).__name__}",
        )

    # 2. Operator dictionary: must have exactly 1 operator key
    if len(node) != 1:
        return NodeEvaluationResult(
            outcome=RuleOutcome.UNKNOWN,
            error=f"Malformed AST node: expected exactly 1 operator, got {len(node)}",
        )

    op, raw_args = next(iter(node.items()))

    if op not in SUPPORTED_OPERATORS:
        return NodeEvaluationResult(
            outcome=RuleOutcome.UNKNOWN,
            error=f"Unsupported AST operator: '{op}'. Supported operators: {sorted(SUPPORTED_OPERATORS)}",
        )

    # 3. Dispatch to operator handler
    if op == "var":
        var_name = raw_args[0] if isinstance(raw_args, (list, tuple)) and raw_args else raw_args
        outcome, val, missing_key = _resolve_context_variable(str(var_name), context)
        if outcome == RuleOutcome.PASS:
            return NodeEvaluationResult(outcome=RuleOutcome.PASS, value=val)
        return NodeEvaluationResult(
            outcome=RuleOutcome.UNKNOWN,
            missing_fields=(missing_key,) if missing_key else (),
            error=f"Profile is missing required field '{missing_key}'",
        )

    if op in ("==", "!=", ">", ">=", "<", "<="):
        if not isinstance(raw_args, (list, tuple)) or len(raw_args) != 2:
            return NodeEvaluationResult(
                outcome=RuleOutcome.UNKNOWN,
                error=f"Operator '{op}' requires exactly 2 operands, got {raw_args}",
            )

        left_res = evaluate_ast_node(raw_args[0], context)
        right_res = evaluate_ast_node(raw_args[1], context)

        # Kleene logic: if any operand is unknown, the comparison is unknown
        if left_res.outcome == RuleOutcome.UNKNOWN or right_res.outcome == RuleOutcome.UNKNOWN:
            combined_missing = left_res.missing_fields + right_res.missing_fields
            combined_err = left_res.error or right_res.error
            return NodeEvaluationResult(
                outcome=RuleOutcome.UNKNOWN,
                missing_fields=combined_missing,
                error=combined_err,
            )

        left_val = left_res.value
        right_val = right_res.value

        if op == "==":
            # Case-insensitive equality for strings
            if isinstance(left_val, str) and isinstance(right_val, str):
                passed = left_val.strip().upper() == right_val.strip().upper()
            else:
                passed = left_val == right_val
            return NodeEvaluationResult(
                outcome=RuleOutcome.PASS if passed else RuleOutcome.FAIL,
                value=passed,
                reasons=() if passed else (f"Value '{left_val}' does not equal '{right_val}'",),
            )

        if op == "!=":
            if isinstance(left_val, str) and isinstance(right_val, str):
                passed = left_val.strip().upper() != right_val.strip().upper()
            else:
                passed = left_val != right_val
            return NodeEvaluationResult(
                outcome=RuleOutcome.PASS if passed else RuleOutcome.FAIL,
                value=passed,
                reasons=() if passed else (f"Value '{left_val}' equals '{right_val}'",),
            )

        # Numeric comparisons: >, >=, <, <=
        try:
            l_num = float(left_val)
            r_num = float(right_val)
        except (TypeError, ValueError) as num_err:
            return NodeEvaluationResult(
                outcome=RuleOutcome.UNKNOWN,
                error=f"Cannot compare non-numeric operands '{left_val}' and '{right_val}' for '{op}': {num_err}",
            )

        if op == ">":
            passed = l_num > r_num
            reason = f"{l_num} is not greater than {r_num}"
        elif op == ">=":
            passed = l_num >= r_num
            reason = f"{l_num} is less than required minimum {r_num}"
        elif op == "<":
            passed = l_num < r_num
            reason = f"{l_num} is not less than {r_num}"
        elif op == "<=":
            passed = l_num <= r_num
            reason = f"{l_num} exceeds ceiling of {r_num}"
        else:
            passed = False
            reason = "Unknown comparison"

        return NodeEvaluationResult(
            outcome=RuleOutcome.PASS if passed else RuleOutcome.FAIL,
            value=passed,
            reasons=() if passed else (reason,),
        )

    if op == "in":
        if not isinstance(raw_args, (list, tuple)) or len(raw_args) != 2:
            return NodeEvaluationResult(
                outcome=RuleOutcome.UNKNOWN,
                error=f"Operator 'in' requires [item, container], got {raw_args}",
            )

        item_res = evaluate_ast_node(raw_args[0], context)
        container_res = evaluate_ast_node(raw_args[1], context)

        if item_res.outcome == RuleOutcome.UNKNOWN or container_res.outcome == RuleOutcome.UNKNOWN:
            return NodeEvaluationResult(
                outcome=RuleOutcome.UNKNOWN,
                missing_fields=item_res.missing_fields + container_res.missing_fields,
                error=item_res.error or container_res.error,
            )

        item_val = item_res.value
        container_val = container_res.value

        if isinstance(container_val, (list, tuple, set)):
            # Normalize strings for comparison
            if isinstance(item_val, str):
                normalized_container = [
                    elem.strip().upper() if isinstance(elem, str) else elem
                    for elem in container_val
                ]
                passed = item_val.strip().upper() in normalized_container
            else:
                passed = item_val in container_val
        elif isinstance(container_val, str):
            passed = str(item_val).upper() in container_val.upper()
        else:
            return NodeEvaluationResult(
                outcome=RuleOutcome.UNKNOWN,
                error=f"Operator 'in' container must be list or string, got {type(container_val).__name__}",
            )

        return NodeEvaluationResult(
            outcome=RuleOutcome.PASS if passed else RuleOutcome.FAIL,
            value=passed,
            reasons=() if passed else (f"'{item_val}' not found in eligible list {container_val}",),
        )

    if op == "and":
        if not isinstance(raw_args, list):
            return NodeEvaluationResult(
                outcome=RuleOutcome.UNKNOWN,
                error=f"Operator 'and' requires list of sub-expressions, got {type(raw_args).__name__}",
            )

        child_results = [evaluate_ast_node(child, context) for child in raw_args]

        # In Kleene 3-valued AND:
        # If ANY child is FAIL -> overall is FAIL
        # Else if ANY child is UNKNOWN -> overall is UNKNOWN
        # Else (all PASS) -> overall is PASS
        failing_children = [c for c in child_results if c.outcome == RuleOutcome.FAIL]
        if failing_children:
            all_reasons: list[str] = []
            for fc in failing_children:
                all_reasons.extend(fc.reasons)
            return NodeEvaluationResult(
                outcome=RuleOutcome.FAIL,
                value=False,
                reasons=tuple(all_reasons),
            )

        unknown_children = [c for c in child_results if c.outcome == RuleOutcome.UNKNOWN]
        if unknown_children:
            missing_set: list[str] = []
            errs: list[str] = []
            for uc in unknown_children:
                for mf in uc.missing_fields:
                    if mf not in missing_set:
                        missing_set.append(mf)
                if uc.error and uc.error not in errs:
                    errs.append(uc.error)
            return NodeEvaluationResult(
                outcome=RuleOutcome.UNKNOWN,
                missing_fields=tuple(missing_set),
                error="; ".join(errs) if errs else None,
            )

        return NodeEvaluationResult(outcome=RuleOutcome.PASS, value=True)

    if op == "or":
        if not isinstance(raw_args, list):
            return NodeEvaluationResult(
                outcome=RuleOutcome.UNKNOWN,
                error=f"Operator 'or' requires list of sub-expressions, got {type(raw_args).__name__}",
            )

        child_results = [evaluate_ast_node(child, context) for child in raw_args]

        # In Kleene 3-valued OR:
        # If ANY child is PASS -> overall is PASS
        # Else if ALL children are FAIL -> overall is FAIL
        # Else -> UNKNOWN
        passing_children = [c for c in child_results if c.outcome == RuleOutcome.PASS]
        if passing_children:
            return NodeEvaluationResult(outcome=RuleOutcome.PASS, value=True)

        unknown_children = [c for c in child_results if c.outcome == RuleOutcome.UNKNOWN]
        if not unknown_children:
            # All must be FAIL
            all_reasons = []
            for fc in child_results:
                all_reasons.extend(fc.reasons)
            return NodeEvaluationResult(
                outcome=RuleOutcome.FAIL,
                value=False,
                reasons=tuple(all_reasons),
            )

        missing_set = []
        for uc in unknown_children:
            for mf in uc.missing_fields:
                if mf not in missing_set:
                    missing_set.append(mf)
        return NodeEvaluationResult(
            outcome=RuleOutcome.UNKNOWN,
            missing_fields=tuple(missing_set),
            error="None of the OR branches passed and some are unknown",
        )

    if op == "not":
        expr = raw_args[0] if isinstance(raw_args, list) and raw_args else raw_args
        child_res = evaluate_ast_node(expr, context)
        if child_res.outcome == RuleOutcome.UNKNOWN:
            return child_res
        if child_res.outcome == RuleOutcome.PASS:
            return NodeEvaluationResult(
                outcome=RuleOutcome.FAIL,
                value=False,
                reasons=("Negation condition evaluated to false",),
            )
        return NodeEvaluationResult(outcome=RuleOutcome.PASS, value=True)

    return NodeEvaluationResult(
        outcome=RuleOutcome.UNKNOWN,
        error=f"Unhandled operator '{op}'",
    )
