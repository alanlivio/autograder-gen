#!/usr/bin/env python3
"""
Math Functions Module - RUNTIME EXCEPTION VERSION
This version causes runtime exceptions during function execution - RUNTIME ERROR
"""

def add_numbers(a, b):
    """Add two numbers - but crashes at runtime."""
    # This will cause a runtime error
    result = a + b
    undefined_variable.some_method()  # NameError - undefined variable
    return result

def multiply(x, y):
    """Multiply two numbers - but crashes with division by zero."""
    temp = x * y
    crash = temp / 0  # ZeroDivisionError
    return crash
