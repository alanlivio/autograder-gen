# Advanced algorithms with runtime errors - demonstrates RUNTIME ERROR during execution

# Wrong signature defaults
def complex_calculation(input_data, algorithm='wrong', precision=5, debug=None):  # FAILED: Wrong defaults
    return "wrong result"

# Runtime error during execution
def handle_edge_cases(data):
    # This will cause RUNTIME ERROR when called with []
    return data[0]  # IndexError when data is empty list

# Wrong signature
def main_algorithm(wrong_param):  # FAILED: Wrong parameter name and count
    raise ValueError("This function always fails")  # RUNTIME ERROR during execution

# Missing expected output format
def run_comprehensive_tests():
    print("Wrong output format")  # FAILED: Output doesn't match expected
