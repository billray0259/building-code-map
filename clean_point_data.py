import json
import re

file = 'data/gracy_3-9.geojson'

with open(file) as f:
    data = json.load(f)
    
    
def clean_strings(data):
    if isinstance(data, dict):
        for key, value in data.items():
            if key == 'website':
                continue
            if isinstance(value, str):
                new_value = value.replace('?', '')
                new_value = re.sub(r'\[.*?\]', '', new_value)
                data[key] = new_value
            else:
                clean_strings(value)
    elif isinstance(data, list):
        for item in data:
            clean_strings(item)
    return data

cleaned_data = clean_strings(data)

with open('data/cleaned_gracy_3-9.geojson', 'w') as f:
    json.dump(cleaned_data, f, indent=4)