# Math functions with wrong signatures - demonstrates FAILED signature checks

# Wrong parameter names (should be a, b)
def add_numbers(x, y):  # FAILED: Parameter names don't match expected
    return x + y

# Missing parameter (should be x, y)
def multiply(x):  # FAILED: Wrong parameter count
    return x * 2
