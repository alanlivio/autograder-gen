# Data processing with wrong default values - demonstrates FAILED default validation

# Wrong default values
def process_data(data, threshold=0.8, normalize=False):  # FAILED: Wrong defaults
    return {"processed": True}

def filter_values(values, min_val=10, max_val=50, inclusive=False):  # FAILED: Wrong defaults
    return [v for v in values if min_val <= v <= max_val]

# Wrong function output - demonstrates FAILED function test
def calculate_statistics(data):
    return {"mean": 999, "median": 999, "std": 999}  # FAILED: Wrong output

def transform_data(data):
    return {"wrong": "format"}  # FAILED: Wrong output format
