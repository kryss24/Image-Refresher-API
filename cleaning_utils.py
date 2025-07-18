import json


SAMPLE_DATA_FILE = "output.json"

def filter_json_object(obj: dict, allowed_keys: list[str]) -> dict:
    """
    Keeps only top-level keys specified in allowed_keys.
    If a value is a nested dict, it is preserved as-is.
    """
    return {k: v for k, v in obj.items() if k in allowed_keys}

# Step 1: Load the JSON file
with open(SAMPLE_DATA_FILE, "r") as infile:
    data = json.load(infile)

# Step 2: Define which keys to keep
allowed_keys = ["text", "user", "processed_images", "price", "location"]

# Step 3: Apply the filter
if isinstance(data, list):
    # For a list of JSON objects
    filtered_data = [filter_json_object(obj, allowed_keys) for obj in data]
else:
    # For a single JSON object
    filtered_data = filter_json_object(data, allowed_keys)

# Step 4: Save the result back to a new file
with open("removed_irrelevant_keys_output.json", "w") as outfile:
    json.dump(filtered_data, outfile, indent=4)

print("Filtered JSON saved to filtered_output.json")



# 