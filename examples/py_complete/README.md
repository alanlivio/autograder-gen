# py_complete

This folder contains a config conver all testing categories covered. It has the following content.

```bash
py_complete/
├── config.json                 # Main configuration file
├── README.md                   # documentation
└── solutions/                  # Passing submission files
    ├── basic_operations.py       # I/O and basic operations
    ├── math_functions.py         # Simple math functions
    ├── data_processing.py        # Advanced data manipulation
    └── advanced_algorithms.py    # Complex algorithms
└── failing_solutions/          # Failing submission files
    ├── basic_operations.py      # RUNTIME ERROR (syntax error)
    ├── math_functions.py        # FAILED (wrong function signatures)
    ├── data_processing.py       # FAILED (wrong default values and function outputs)
    └── advanced_algorithms.py   # RUNTIME ERROR and FAILED (mixed errors)
```

Usage Instructions:

```bash
python autograder_gen/cli.py --config examples/py_complete/config.json
```

Web Interface:

- Upload this config to see all form fields
- Demonstrates complete UI functionality

## Testing Categories Covered

### File Existence Tests

Verify

- Required files are submitted

Examples:

- Files Tested: `basic_operations.py`, `math_functions.py`, `data_processing.py`

### Output Comparison Tests

Verify:

- Program output against expected results
  - Input simulation
  - Exact output matching
  - Automatic newline handling for Python `print()` statements

### Basic Signature Check Tests

Verify:

- Parameter count and names

Examples:

- `add_numbers(a, b)` - Simple two-parameter function
- `multiply(x, y)` - Alternative parameter names

Json:

### Advanced Signature Check Tests

Verify:

- Parameter count and names
- Default value checking (numeric, boolean, string)
- Mixed parameter types
Examples:
- `process_data(data, threshold=0.5, normalize=True)`
- `filter_values(values, min_val=0, max_val=100, inclusive=True)`
- `complex_calculation(input_data, algorithm='default', precision=2, debug=False)`

### Simple Function Tests

Verify:

- Test function execution with various inputs

Examples:

- Basic arithmetic: `add_numbers(2, 3)` => `5`
- Multiplication: `multiply(3, 4)` => `12`

### Edge Case Testing

Verify:

- Test handling of unusual inputs

Examples:

- Empty lists: `[]` → `None`

## Scoring Distribution

- File Existence: 5 points (2+2+1)
- Output Comparison: 15 points (8+7)
- Signature Checks: 26 points (4+4+6+5+7)
- Function Tests: 37 points (8+7+12+10)
- Edge Case Testing: 15 points
- Mixed Testing: 28 points (2+6+12+8)
- Total: 100 points (optimized from 206)

## Visibility Levels Demonstrated

| Level | Purpose | When Shown |
|-----------|-------------|----------------|
| `visible` | Immediate feedback | Always visible to students |
| `hidden` | Grading only | Never shown to students |
| `after_due_date` | Post-deadline | Revealed after assignment deadline |
| `after_published` | Final results | Shown when grades are published |

## Time Limits Configured

- File existence: 5 seconds (fast checks)
- Simple functions: 10-30 seconds
- Complex algorithms: 60-120 seconds
- Global limit: 600 seconds (10 minutes total)
