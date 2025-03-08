import json


with open('data/counties.json') as f:
    counties = json.load(f)

updated = {
    "type": "FeatureCollection",
    "features": []
}

for feature in counties['features']:
    geometry = feature['geometry']
    updated_geometry = {
        "type": "Polygon",
        "coordinates": [geometry['coordinates']]
    }
    updated['features'].append({
        "type": "Feature",
        "geometry": updated_geometry,
        "properties": feature['properties']
    })


with open('data/counties_updated.json', 'w') as f:
    json.dump(updated, f, indent=4)