"""Tests for the calculator tool — safe expression evaluation."""

import pytest

from src.tools.calculator import safe_evaluate


class TestSafeEvaluate:
    """Test the safe_evaluate function."""

    def test_basic_addition(self) -> None:
        assert safe_evaluate("2 + 3") == 5.0

    def test_basic_subtraction(self) -> None:
        assert safe_evaluate("10 - 4") == 6.0

    def test_basic_multiplication(self) -> None:
        assert safe_evaluate("3 * 7") == 21.0

    def test_basic_division(self) -> None:
        assert safe_evaluate("10 / 4") == 2.5

    def test_floor_division(self) -> None:
        assert safe_evaluate("10 // 3") == 3.0

    def test_modulo(self) -> None:
        assert safe_evaluate("10 % 3") == 1.0

    def test_power(self) -> None:
        assert safe_evaluate("2 ** 10") == 1024.0

    def test_negative_number(self) -> None:
        assert safe_evaluate("-5 + 3") == -2.0

    def test_complex_expression(self) -> None:
        assert safe_evaluate("(2 + 3) * 4 - 1") == 19.0

    def test_nested_parentheses(self) -> None:
        assert safe_evaluate("((2 + 3) * (4 - 1))") == 15.0

    def test_sqrt_function(self) -> None:
        assert safe_evaluate("sqrt(16)") == 4.0

    def test_abs_function(self) -> None:
        assert safe_evaluate("abs(-42)") == 42.0

    def test_pi_constant(self) -> None:
        result = safe_evaluate("pi")
        assert abs(result - 3.14159265) < 0.0001

    def test_e_constant(self) -> None:
        result = safe_evaluate("e")
        assert abs(result - 2.71828182) < 0.0001

    def test_invalid_expression(self) -> None:
        with pytest.raises(ValueError, match="Invalid expression"):
            safe_evaluate("not a math expression")

    def test_unsupported_function(self) -> None:
        with pytest.raises(ValueError, match="Unsupported"):
            safe_evaluate("__import__('os').system('ls')")

    def test_division_by_zero(self) -> None:
        with pytest.raises(ZeroDivisionError):
            safe_evaluate("1 / 0")
