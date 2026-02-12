"""
Example Skill Functions
Shows how to create tools that Jarvis can use.
"""


def example_greeting(name: str) -> str:
    """Say hello to someone by name.
    
    Args:
        name: The name of the person to greet
    
    Returns:
        A friendly greeting
    """
    return f"Hello, {name}! 👋 This is an example skill greeting."


def example_math(expression: str) -> str:
    """Evaluate a simple math expression safely.
    
    Args:
        expression: A math expression like '2 + 3 * 4'
    
    Returns:
        The result of the calculation
    """
    # Only allow safe math operations
    allowed = set('0123456789+-*/.() ')
    if not all(c in allowed for c in expression):
        return "⚠️ Invalid characters in expression. Only numbers and +, -, *, /, (, ) are allowed."
    
    try:
        result = eval(expression)  # Safe because we validated input
        return f"🔢 {expression} = {result}"
    except Exception as e:
        return f"⚠️ Math error: {e}"
