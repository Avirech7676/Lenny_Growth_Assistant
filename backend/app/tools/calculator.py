"""Safe Mathematical & Business Metrics Calculator Tool using AST evaluation."""

import ast
import operator
import math
import time
from typing import Dict, Any

from app.tools.base import Tool, ToolResult

# Safe mathematical operators
OPERATORS = {
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
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "cagr": lambda start, end, periods: ((end / start) ** (1 / periods)) - 1 if start > 0 and periods > 0 else 0.0,
    "ice": lambda impact, confidence, ease: round((impact + confidence + ease) / 3.0, 2),
    "rice": lambda reach, impact, confidence, effort: round((reach * impact * (confidence / 100.0)) / effort, 2) if effort > 0 else 0.0,
    "cac_payback": lambda cac, arpu, margin: round(cac / (arpu * (margin / 100.0)), 2) if arpu > 0 and margin > 0 else 0.0,
    "ltv": lambda arpu, margin, churn: round((arpu * (margin / 100.0)) / churn, 2) if churn > 0 else 0.0,
}


def safe_eval(node):
    """Recursively evaluate an AST expression using only whitelisted operators and functions."""
    if isinstance(node, ast.Expression):
        return safe_eval(node.body)
    elif isinstance(node, ast.Constant):
        return node.value
    elif isinstance(node, ast.BinOp):
        left = safe_eval(node.left)
        right = safe_eval(node.right)
        op_type = type(node.op)
        if op_type in OPERATORS:
            return OPERATORS[op_type](left, right)
        raise ValueError(f"Unsupported binary operator: {op_type.__name__}")
    elif isinstance(node, ast.UnaryOp):
        operand = safe_eval(node.operand)
        op_type = type(node.op)
        if op_type in OPERATORS:
            return OPERATORS[op_type](operand)
        raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
    elif isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in SAFE_FUNCTIONS:
            args = [safe_eval(arg) for arg in node.args]
            return SAFE_FUNCTIONS[node.func.id](*args)
        raise ValueError(f"Function call '{ast.unparse(node.func)}' is not permitted.")
    else:
        raise ValueError(f"Unsupported expression element: {type(node).__name__}")


class CalculatorTool(Tool):
    name = "calculator"
    description = (
        "Execute precision mathematical calculations, percentages, and business metrics "
        "(CAGR, ICE score, RICE, CAC payback, LTV). Evaluates safely via an AST compiler."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "Mathematical expression (e.g., '(45000 / 12) * 0.85', 'ice(9, 8, 7)', 'cagr(100, 250, 3)').",
            }
        },
        "required": ["expression"],
    }
    timeout_seconds = 5.0

    async def execute(self, expression: str, **kwargs) -> ToolResult:
        t0 = time.perf_counter()
        try:
            clean_expr = expression.strip().rstrip(";")
            tree = ast.parse(clean_expr, mode="eval")
            result = safe_eval(tree)
            duration_ms = (time.perf_counter() - t0) * 1000

            return ToolResult(
                tool_name=self.name,
                status="success",
                input_params={"expression": expression},
                output=result,
                metadata={"type": type(result).__name__, "raw_expression": expression},
                duration_ms=duration_ms,
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status="error",
                input_params={"expression": expression},
                output="",
                error_message=f"Calculation error: {str(e)}",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
