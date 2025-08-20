# Comprehensive Sample

This folder contains a complete demonstration of all autograder-gen functionality.

## Contents

```
comprehensive_sample/
├── comprehensive_sample_config.json    # Main configuration file
├── COMPREHENSIVE_CONFIG_README.md      # Detailed documentation
├── overview.md                         # This file
└── solutions/                          # Sample solution files
    ├── basic_operations.py             # I/O and basic operations
    ├── math_functions.py               # Simple math functions
    ├── data_processing.py              # Advanced data manipulation
    └── advanced_algorithms.py          # Complex algorithms
```

## Usage

**Test the configuration**:

   ```bash
   cd comprehensive_sample
   python ../cli/main.py --config comprehensive_sample_config.json --validate-only
   ```

**Generate autograder**:

   ```bash
   python ../cli/main.py --config comprehensive_sample_config.json
   ```

**View in web interface**:

* Start web server: `python -m web.app`
* Upload `comprehensive_sample_config.json`
* Explore all form fields and functionality

**Solutions**

* **Passing Solutions**: Located in `solutions/` directory - designed to pass all test cases
* **Failing Solutions**: Located in `failing_solutions/` directory - demonstrate different failure types:
  * `basic_operations.py`: **RUNTIME ERROR** (syntax error)
  * `math_functions.py`: **FAILED** (wrong function signatures)
  * `data_processing.py`: **FAILED** (wrong default values and function outputs)
  * `advanced_algorithms.py`: **RUNTIME ERROR** and **FAILED** (mixed errors)

## `comprehensive_sample_config.json`

## **Testing Categories Covered**

* **File Existence Tests**
  * **Purpose**: Verify required files are submitted
  * **Files Tested**: `basic_operations.py`, `math_functions.py`, `data_processing.py`
  * **Visibility**: Mix of visible, hidden tests

* **Output Comparison Tests**

  * **Purpose**: Test program output against expected results
  * **Features**:
  * Input simulation
  * Exact output matching
  * Automatic newline handling for Python `print()` statements
  * **Test Cases**: Multiple input/output scenarios with different visibility levels

* **Basic Signature Check Tests**

  * **Purpose**: Validate function signatures without defaults
  * **Examples**:
  * `add_numbers(a, b)` - Simple two-parameter function
  * `multiply(x, y)` - Alternative parameter names
  * **Validation**: Parameter count and names
  * **4. Advanced Signature Check Tests**

* **Purpose**: signature validation with default parameters

  * **Examples**:
    * `process_data(data, threshold=0.5, normalize=True)`
    * `filter_values(values, min_val=0, max_val=100, inclusive=True)`
    * `complex_calculation(input_data, algorithm='default', precision=2, debug=False)`
  * **Validation**:
    * Parameter count matching
    * Parameter name validation
    * Default value checking (numeric, boolean, string)
    * Mixed parameter types

* **Simple Function Tests**

  * **Purpose**: Test function execution with various inputs
  * **Examples**:
    * Basic arithmetic: `add_numbers(2, 3)` → `5`
    * Multiplication: `multiply(3, 4)` → `12`
  * **Optimization**: Each function test has exactly **1 test case** for focused validation

* **Advanced Function Tests with Keywords**

  * **Purpose**: Complex function testing with keyword arguments
  * **Features**:
    * Positional arguments
    * Keyword arguments
    * Mixed argument types
    * Complex return values (dictionaries, lists)
    * JSON string validation
  * **Optimization**: Each function test has exactly **1 test case** for streamlined testing

* **Edge Case Testing**

  * **Purpose**: Test handling of unusual inputs
  * **Cases**:
    * Empty lists: `[]` → `None`
  * **Optimization**: Focused on essential edge case validation with **1 test case**
  * **Clean testing**: Removed problematic test cases that generated warnings

* **Mixed Testing Scenarios**

  * **Purpose**: Combine multiple test types for comprehensive validation
  * **Flow**: File existence → Signature check → Function test → Output comparison
  * **Real-world simulation** of complete assignment grading
  * **Optimization**: Each function test has exactly **1 test case** for efficient validation

* **Time Limits Configured**

  * **File existence**: 5 seconds (fast checks)
  * **Simple functions**: 10-30 seconds
  * **Complex algorithms**: 60-120 seconds
  * **Global limit**: 600 seconds (10 minutes total)

## **Scoring Distribution**

* **File Existence**: 5 points (2+2+1)
* **Output Comparison**: 15 points (8+7)
* **Signature Checks**: 26 points (4+4+6+5+7)
* **Function Tests**: 37 points (8+7+12+10)
* **Edge Case Testing**: 15 points
* **Mixed Testing**: 28 points (2+6+12+8)
* **Total**: **100 points** (optimized from 206)

## **Advanced Features**

**Signature Validation Capabilities**

```python
# Basic validation
"expected_parameters": "a, b"

# With defaults
"expected_parameters": "data, threshold=0.5, normalize=True"

# Complex mixed types
"expected_parameters": "input_data, algorithm='default', precision=2, debug=False"
```

**Function Testing Scenarios**

```json
{
  "args": [[1, 2, 3, 4, 5]],
  "expected": "{'mean': 3.0, 'median': 3.0, 'std': 1.58}"
}
```

**Note**: Each function test now contains exactly **1 test case** for optimized performance and clarity.
