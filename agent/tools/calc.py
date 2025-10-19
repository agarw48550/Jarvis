import ast
import operator as op


# Supported operators for safe evaluation
_OPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.FloorDiv: op.floordiv,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
    ast.USub: op.neg,
    ast.UAdd: op.pos,
}

_CONSTS = {
    "pi": 3.141592653589793,
    "e": 2.718281828459045,
}


def _eval(node):
    if isinstance(node, ast.Num):  # type: ignore[attr-defined]
        return node.n
    if hasattr(ast, "Constant") and isinstance(node, ast.Constant):  # py3.8+
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("Only numbers are allowed.")
    if isinstance(node, ast.BinOp):
        left = _eval(node.left)
        right = _eval(node.right)
        op_type = type(node.op)
        if op_type in _OPS:
            return _OPS[op_type](left, right)
        raise ValueError("Unsupported operator.")
    if isinstance(node, ast.UnaryOp):
        operand = _eval(node.operand)
        op_type = type(node.op)
        if op_type in _OPS:
            return _OPS[op_type](operand)
        raise ValueError("Unsupported unary operator.")
    if isinstance(node, ast.Name):
        name = node.id.lower()
        if name in _CONSTS:
            return _CONSTS[name]
        raise ValueError("Unknown name: " + name)
    if isinstance(node, ast.Expr):
        return _eval(node.value)
    raise ValueError("Unsupported expression.")


def calculate(expr: str) -> str:
    """Safely evaluate a basic arithmetic expression.
    Supports + - * / // % **, parentheses, and constants pi, e.
    """
    if not expr or not isinstance(expr, str):
        return "Missing expression."
    try:
        tree = ast.parse(expr, mode="eval")
        result = _eval(tree.body)
        # Pretty formatting: avoid trailing .0 for ints
        if isinstance(result, float) and result.is_integer():
            return str(int(result))
        return str(result)
    except Exception:
        return "I couldn't calculate that."
