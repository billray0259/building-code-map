import shapefile
import json
import os

# Check if the necessary files are present
shapefile_path = "data/tl_2024_08_place/tl_2024_08_place.shp"
dbf_path = shapefile_path.replace(".shp", ".dbf")

if not os.path.exists(shapefile_path) or not os.path.exists(dbf_path):
    raise FileNotFoundError("Required shapefile components (.shp and .dbf) are missing.")

# Read the shapefile
reader = shapefile.Reader(shapefile_path)
fields = [field[0] for field in reader.fields[1:]]  # Skip the DeletionFlag field
records = reader.records()
shapes = reader.shapes()

# Convert to GeoJSON format
geojson = {
    "type": "FeatureCollection",
    "features": []
}


for record, shape in zip(records, shapes):
    # Convert shapefile shape type number to GeoJSON type string
    shape_type = {
        1: "Point",
        3: "LineString",
        5: "Polygon",
        8: "MultiPoint",
        11: "PointZ",
        13: "LineStringZ",
        15: "PolygonZ",
        18: "MultiPointZ",
        21: "PointM",
        23: "LineStringM",
        25: "PolygonM",
        28: "MultiPointM",
        31: "MultiPatch"
    }.get(shape.shapeType, "Unknown")
    
    # Format coordinates based on shape type
    # Store points as lon, lat (instead of default lat, lon)
    coords = [(point[0], point[1]) for point in shape.points]
    if shape_type == "Polygon" or shape_type == "PolygonZ" or shape_type == "PolygonM":
        # For polygons, we need to group by parts
        parts = shape.parts
        parts.append(len(shape.points))
        coords = []
        for i in range(len(parts) - 1):
            coords.append([(point[0], point[1]) for point in shape.points[parts[i]:parts[i+1]]])
    
    feature = {
        "type": "Feature",
        "geometry": {
            "type": shape_type,
            "coordinates": coords
        },
        "properties": {field: value for field, value in zip(fields, record)}
    }
    geojson["features"].append(feature)

# Save to GeoJSON file with same base name as input
output_geojson = os.path.splitext(shapefile_path)[0] + ".geojson"
with open(output_geojson, "w") as geojson_file:
    json.dump(geojson, geojson_file, indent=4)
print(f"Saved to {output_geojson}")
