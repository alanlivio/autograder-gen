# data_processing.py - WRONG DEFAULT VALUES

def process_data(data, threshold=0.8, normalize=False):  # Wrong defaults: should be 0.5, True
    return {"processed": True}

def filter_values(values, min_val=10, max_val=50):  # Wrong: missing inclusive param and wrong defaults
    return [v for v in values if min_val <= v <= max_val]

def calculate_statistics(data):
    mean = sum(data) / len(data)
    return f"{{'mean': {mean}, 'median': {mean}, 'std': 1.58}}"

def transform_data(data):
    if isinstance(data, dict):
        return {k: v * 2 for k, v in data.items()}
    return data
