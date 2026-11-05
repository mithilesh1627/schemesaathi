"""Unit Tests for Pure Deterministic AST Evaluator.

Covers:
- All approved operators: ==, !=, >, >=, <, <=, in, and, or, not, var
- 3-valued Kleene logic rules
- Unapproved and malformed operators
- Variable resolution with aliases and dot-notation
- Case-insensitivity for string categorical attributes
"""

from src.modules.eligibility.domain.ast_evaluator import (
    evaluate_ast_node,
)
from src.modules.eligibility.domain.enums import RuleOutcome


class TestAstEvaluatorOperators:
    """Tests for individual JSON-Logic AST operators."""

    def test_var_resolution_direct(self) -> None:
        ctx = {"social_category": "ST", "annual_family_income_inr": 200000}
        res = evaluate_ast_node({"var": "social_category"}, ctx)
        assert res.outcome == RuleOutcome.PASS
        assert res.value == "ST"

    def test_var_resolution_alias(self) -> None:
        ctx = {"annual_family_income_inr": 150000}
        res = evaluate_ast_node({"var": "income"}, ctx)
        assert res.outcome == RuleOutcome.PASS
        assert res.value == 150000

    def test_var_resolution_dotted_path(self) -> None:
        ctx = {"financial": {"annual_family_income_inr": 180000}}
        res = evaluate_ast_node({"var": "financial.annual_family_income_inr"}, ctx)
        assert res.outcome == RuleOutcome.PASS
        assert res.value == 180000

    def test_var_resolution_missing_returns_unknown(self) -> None:
        ctx = {"social_category": "ST"}
        res = evaluate_ast_node({"var": "annual_family_income_inr"}, ctx)
        assert res.outcome == RuleOutcome.UNKNOWN
        assert "annual_family_income_inr" in res.missing_fields

    def test_equality_operator_passes_and_fails(self) -> None:
        ctx = {"domicile_state": "MANIPUR"}
        # Pass
        res_pass = evaluate_ast_node({"==": [{"var": "domicile_state"}, "MANIPUR"]}, ctx)
        assert res_pass.outcome == RuleOutcome.PASS
        assert res_pass.value is True

        # Case-insensitive string match
        res_ci = evaluate_ast_node({"==": [{"var": "domicile_state"}, "manipur"]}, ctx)
        assert res_ci.outcome == RuleOutcome.PASS

        # Fail
        res_fail = evaluate_ast_node({"==": [{"var": "domicile_state"}, "ASSAM"]}, ctx)
        assert res_fail.outcome == RuleOutcome.FAIL
        assert res_fail.value is False

    def test_equality_with_unknown_operand_returns_unknown(self) -> None:
        ctx: dict[str, object] = {}
        res = evaluate_ast_node({"==": [{"var": "domicile_state"}, "MANIPUR"]}, ctx)
        assert res.outcome == RuleOutcome.UNKNOWN
        assert "domicile_state" in res.missing_fields

    def test_inequality_operator(self) -> None:
        ctx = {"social_category": "GENERAL"}
        res = evaluate_ast_node({"!=": [{"var": "social_category"}, "ST"]}, ctx)
        assert res.outcome == RuleOutcome.PASS

        res_same = evaluate_ast_node({"!=": [{"var": "social_category"}, "GENERAL"]}, ctx)
        assert res_same.outcome == RuleOutcome.FAIL

    def test_numeric_comparisons(self) -> None:
        ctx = {"income": 250000, "marks": 60.0}

        # <= (exact boundary and lower)
        assert (
            evaluate_ast_node({"<=": [{"var": "income"}, 250000]}, ctx).outcome == RuleOutcome.PASS
        )
        assert (
            evaluate_ast_node({"<=": [{"var": "income"}, 300000]}, ctx).outcome == RuleOutcome.PASS
        )
        assert (
            evaluate_ast_node({"<=": [{"var": "income"}, 249999]}, ctx).outcome == RuleOutcome.FAIL
        )

        # <
        assert (
            evaluate_ast_node({"<": [{"var": "income"}, 250001]}, ctx).outcome == RuleOutcome.PASS
        )
        assert (
            evaluate_ast_node({"<": [{"var": "income"}, 250000]}, ctx).outcome == RuleOutcome.FAIL
        )

        # >=
        assert evaluate_ast_node({">=": [{"var": "marks"}, 60.0]}, ctx).outcome == RuleOutcome.PASS
        assert evaluate_ast_node({">=": [{"var": "marks"}, 59.9]}, ctx).outcome == RuleOutcome.PASS
        assert evaluate_ast_node({">=": [{"var": "marks"}, 60.1]}, ctx).outcome == RuleOutcome.FAIL

        # >
        assert evaluate_ast_node({">": [{"var": "marks"}, 59.9]}, ctx).outcome == RuleOutcome.PASS
        assert evaluate_ast_node({">": [{"var": "marks"}, 60.0]}, ctx).outcome == RuleOutcome.FAIL

    def test_membership_in_operator(self) -> None:
        ctx = {"category": "OBC", "course": "UNDERGRADUATE"}
        # List membership
        ast_in = {"in": [{"var": "category"}, ["SC", "ST", "OBC"]]}
        assert evaluate_ast_node(ast_in, ctx).outcome == RuleOutcome.PASS

        ast_not_in = {"in": [{"var": "category"}, ["SC", "ST"]]}
        assert evaluate_ast_node(ast_not_in, ctx).outcome == RuleOutcome.FAIL

        # String substring membership
        ast_str_in = {"in": ["MANIPUR", "NORTH_EAST_MANIPUR_STATE"]}
        assert evaluate_ast_node(ast_str_in, ctx).outcome == RuleOutcome.PASS


class TestKleeneThreeValuedLogic:
    """Tests for 3-valued Kleene logic: PASS, FAIL, UNKNOWN."""

    def test_and_short_circuits_to_fail_even_with_unknown(self) -> None:
        # If income exceeds ceiling (FAIL), the outcome is FAIL even if category is missing (UNKNOWN)
        ctx = {"income": 500000}  # category is missing
        ast = {
            "and": [
                {"<=": [{"var": "income"}, 250000]},  # FAIL
                {"in": [{"var": "category"}, ["ST"]]},  # UNKNOWN
            ]
        }
        res = evaluate_ast_node(ast, ctx)
        assert res.outcome == RuleOutcome.FAIL
        assert res.value is False

    def test_and_returns_unknown_when_no_failure_but_missing_field(self) -> None:
        # Income passes, but category is missing -> UNKNOWN
        ctx = {"income": 200000}
        ast = {
            "and": [
                {"<=": [{"var": "income"}, 250000]},  # PASS
                {"in": [{"var": "category"}, ["ST"]]},  # UNKNOWN
            ]
        }
        res = evaluate_ast_node(ast, ctx)
        assert res.outcome == RuleOutcome.UNKNOWN
        assert "social_category" in res.missing_fields

    def test_and_returns_pass_when_all_pass(self) -> None:
        ctx = {"income": 200000, "category": "ST"}
        ast = {
            "and": [
                {"<=": [{"var": "income"}, 250000]},
                {"in": [{"var": "category"}, ["ST"]]},
            ]
        }
        res = evaluate_ast_node(ast, ctx)
        assert res.outcome == RuleOutcome.PASS
        assert res.value is True

    def test_or_resolves_to_pass_even_with_unknown(self) -> None:
        # If one branch PASS, OR evaluates to PASS regardless of missing data in other branch
        ctx = {"is_displaced": True}
        ast = {
            "or": [
                {"==": [{"var": "is_displaced"}, True]},  # PASS
                {"<=": [{"var": "income"}, 250000]},  # UNKNOWN
            ]
        }
        res = evaluate_ast_node(ast, ctx)
        assert res.outcome == RuleOutcome.PASS
        assert res.value is True

    def test_or_returns_unknown_when_no_pass_and_some_unknown(self) -> None:
        ctx = {"is_displaced": False}
        ast = {
            "or": [
                {"==": [{"var": "is_displaced"}, True]},  # FAIL
                {"<=": [{"var": "income"}, 250000]},  # UNKNOWN
            ]
        }
        res = evaluate_ast_node(ast, ctx)
        assert res.outcome == RuleOutcome.UNKNOWN

    def test_not_operator(self) -> None:
        ctx = {"category": "GENERAL"}
        # NOT(PASS) -> FAIL
        assert (
            evaluate_ast_node({"not": [{"==": [{"var": "category"}, "GENERAL"]}]}, ctx).outcome
            == RuleOutcome.FAIL
        )
        # NOT(FAIL) -> PASS
        assert (
            evaluate_ast_node({"not": [{"==": [{"var": "category"}, "ST"]}]}, ctx).outcome
            == RuleOutcome.PASS
        )
        # NOT(UNKNOWN) -> UNKNOWN
        assert (
            evaluate_ast_node({"not": [{"==": [{"var": "missing_var"}, "ST"]}]}, ctx).outcome
            == RuleOutcome.UNKNOWN
        )


class TestMalformationsAndUnapprovedOperators:
    """Security and correctness tests for invalid, unapproved, or corrupted AST."""

    def test_unapproved_operator_returns_unknown_with_error(self) -> None:
        ctx = {"income": 100000}
        # 'fuzzy_like' is outside approved set
        ast = {"fuzzy_like": [{"var": "income"}, 100000]}
        res = evaluate_ast_node(ast, ctx)
        assert res.outcome == RuleOutcome.UNKNOWN
        assert res.error is not None
        assert "Unsupported AST operator: 'fuzzy_like'" in res.error

    def test_malformed_multiple_keys_in_node(self) -> None:
        ctx = {"income": 100000}
        ast = {"==": [1, 1], ">=": [2, 2]}
        res = evaluate_ast_node(ast, ctx)
        assert res.outcome == RuleOutcome.UNKNOWN
        assert "expected exactly 1 operator" in (res.error or "")

    def test_null_ast_node_returns_unknown(self) -> None:
        res = evaluate_ast_node(None, {})
        assert res.outcome == RuleOutcome.UNKNOWN

    def test_invalid_comparison_types(self) -> None:
        ctx = {"name": "TestStudent"}
        # Comparing string to number with >
        ast = {">": [{"var": "name"}, 50000]}
        res = evaluate_ast_node(ast, ctx)
        assert res.outcome == RuleOutcome.UNKNOWN
        assert "Cannot compare non-numeric operands" in (res.error or "")
