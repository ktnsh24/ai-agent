"""Calculator tool — safe mathematical expression evaluator."""

from __future__ import annotations

import ast
import logging
import math
import operator

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Safe operations allowed in expressions
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

SAFE_FUNCTIONS = {
    "sqrt": math.sqrt,
    "abs": abs,
    "round": round,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "pi": math.pi,
    "e": math.e,
}


def _safe_eval(node: ast.AST) -> float:
    """Safely evaluate an AST node — only allows arithmetic operations."""
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    elif isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise ValueError(f"Unsupported constant: {node.value}")
    elif isinstance(node, ast.BinOp):
        op = SAFE_OPERATORS.get(type(node.op))
        if op is None:
            raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        return op(left, right)
    elif isinstance(node, ast.UnaryOp):
        op = SAFE_OPERATORS.get(type(node.op))
        if op is None:
            raise ValueError(f"Unsupported unary operator: {type(node.op).__name__}")
        return op(_safe_eval(node.operand))
    elif isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in SAFE_FUNCTIONS:
            func = SAFE_FUNCTIONS[node.func.id]
            if callable(func):
                args = [_safe_eval(arg) for arg in node.args]
                return float(func(*args))
            return float(func)  # Constants like pi, e
        raise ValueError(f"Unsupported function: {getattr(node.func, 'id', 'unknown')}")
    elif isinstance(node, ast.Name):
        if node.id in SAFE_FUNCTIONS:
            val = SAFE_FUNCTIONS[node.id]
            if not callable(val):
                return float(val)
        raise ValueError(f"Unsupported variable: {node.id}")
    else:
        raise ValueError(f"Unsupported expression type: {type(node).__name__}")


def safe_evaluate(expression: str) -> float:
    """Safely evaluate a mathematical expression string.

    Args:
        expression: A mathematical expression (e.g., "2 + 3 * 4", "sqrt(16)")

    Returns:
        The numeric result.

    Raises:
        ValueError: If the expression contains unsupported operations.
    """
    try:
        tree = ast.parse(expression, mode="eval")
        return _safe_eval(tree)
    except (SyntaxError, TypeError) as e:
        raise ValueError(f"Invalid expression: {expression}") from e


def create_calculator_tool():
    """Factory: create the calculator tool."""

    @tool
    def calculator(expression: str) -> str:
        """Perform a mathematical calculation safely.

        Supports: +, -, *, /, //, %, **, sqrt(), abs(), round(),
        sin(), cos(), tan(), log(), log10(), pi, e.

        Args:
            expression: A mathematical expression to evaluate.

        Returns:
            The result as a string.
        """
        try:
            result = safe_evaluate(expression)
            # Format nicely
            if result == int(result):
                return str(int(result))
            return f"{result:.6f}".rstrip("0").rstrip(".")
        except ValueError as e:
            return f"Error: {str(e)}"
        except ZeroDivisionError:
            return "Error: Division by zero"
        except OverflowError:
            return "Error: Result too large"

    return calculator
