import pandas as pd
import json

# Load CSV data using pandas
csv_file_path = '/home/bill/dev/school/holt-research/building-code-map/data/denver-metro.csv'
df = pd.read_csv(csv_file_path, encoding='latin1')

# Create dictionary from DataFrame
csv_data = {}
for _, row in df.iterrows():
    municipality = row['Municipality[1]'].strip()
    csv_data[municipality] = {
        'irc': row['Adopted IRC'],
        'iecc': row['Adopted IECC']
    }

# Load GeoJSON data
geojson_file_path = '/home/bill/dev/school/holt-research/building-code-map/data/gracy_3-3.geojson'
with open(geojson_file_path, mode='r', encoding='latin1') as geojsonfile:
    geojson_data = json.load(geojsonfile)

# Update GeoJSON data with IRC and IECC codes from CSV
for feature in geojson_data['features']:
    name = feature['properties']['name'].strip()
    if name in csv_data:
        feature['properties']['irc'] = int(csv_data[name]['irc']) if pd.notna(csv_data[name]['irc']) else "Unknown"
        feature['properties']['iecc'] = int(csv_data[name]['iecc']) if pd.notna(csv_data[name]['iecc']) else "Unknown"

# Save updated GeoJSON data to a new file
updated_geojson_file_path = '/home/bill/dev/school/holt-research/building-code-map/data/gracy_3-9.geojson'
with open(updated_geojson_file_path, mode='w', encoding='latin1') as updated_geojsonfile:
    json.dump(geojson_data, updated_geojsonfile, indent=2)
