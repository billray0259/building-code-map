import numpy as np
from scipy.spatial import Voronoi
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon
import pyproj
from shapely.ops import transform
from functools import partial

def compute_voronoi_polygons(points, bounds=None):
    """
    Compute Voronoi polygons for a set of points
    
    Parameters:
    points (list): List of [lat, lon] points
    bounds (list, optional): Map bounds as [[min_lat, min_lon], [max_lat, max_lon]] (Leaflet format)
                            or [min_lon, min_lat, max_lon, max_lat] (direct format)
    
    Returns:
    list: List of polygons with format [(polygon_coords, point_index), ...]
    """
    # Convert points to numpy array for scipy, with x=lon, y=lat
    # We need to flip lat and lon since scipy expects [x, y]
    points_array = np.array([[point[1], point[0]] for point in points])
    
    # Process bounds based on format
    if bounds:
        # Handle Leaflet format: [[min_lat, min_lon], [max_lat, max_lon]]
        if isinstance(bounds[0], (list, tuple)) and len(bounds) == 2:
            min_lat, min_lon = bounds[0]
            max_lat, max_lon = bounds[1]
        # Handle direct format: [min_lon, min_lat, max_lon, max_lat]
        elif len(bounds) == 4:
            min_lon, min_lat, max_lon, max_lat = bounds
        else:
            # Default bounds for Colorado if format is invalid
            min_lon, min_lat = -109.5, 37.0
            max_lon, max_lat = -102.0, 41.0
            
        # Add far points at corners to bound the Voronoi diagram
        far_points = np.array([
            [min_lon - 10, min_lat - 10],
            [min_lon - 10, max_lat + 10],
            [max_lon + 10, min_lat - 10],
            [max_lon + 10, max_lat + 10]
        ])
        # Combine the points with the far points
        points_array = np.vstack([points_array, far_points])
    
    # Compute Voronoi diagram
    vor = Voronoi(points_array)
    
    # Extract polygons
    regions = []
    for i, point_index in enumerate(vor.point_region[:len(points)]):  # Only use original points, not far points
        region = vor.regions[point_index]
        if -1 not in region and len(region) > 0:  # Skip regions that contain a point at infinity
            polygon = [vor.vertices[i] for i in region]
            if len(polygon) >= 3:  # Need at least 3 vertices for a polygon
                # Flip back to [lat, lon] for leaflet
                polygon_coords = [(float(vertex[1]), float(vertex[0])) for vertex in polygon]
                regions.append((polygon_coords, i))
    
    return regions

def clip_polygons_to_bounds(polygons, bounds):
    """
    Clip Voronoi polygons to map bounds
    
    Parameters:
    polygons (list): List of (polygon_coords, point_index) tuples
    bounds (list): Map bounds as [[min_lat, min_lon], [max_lat, max_lon]] (Leaflet format)
                  or [min_lon, min_lat, max_lon, max_lat] (direct format)
    
    Returns:
    list: List of clipped polygons with format [(polygon_coords, point_index), ...]
    """
    # Process bounds based on format
    if isinstance(bounds[0], (list, tuple)) and len(bounds) == 2:
        min_lat, min_lon = bounds[0]
        max_lat, max_lon = bounds[1]
    elif len(bounds) == 4:
        min_lon, min_lat, max_lon, max_lat = bounds
    else:
        # Default bounds for Colorado if format is invalid
        min_lon, min_lat = -109.5, 37.0
        max_lon, max_lat = -102.0, 41.0
    
    # Create a GeoDataFrame for the polygons
    geometries = []
    indices = []
    for polygon_coords, point_index in polygons:
        # Convert to Shapely polygon (Leaflet format is already [lat, lon], need to swap to [lon, lat] for Shapely)
        shapely_coords = [(lon, lat) for lat, lon in polygon_coords]
        if len(shapely_coords) >= 3:  # Need at least 3 vertices for a polygon
            try:
                geom = Polygon(shapely_coords)
                if geom.is_valid:
                    geometries.append(geom)
                    indices.append(point_index)
            except:
                pass
    
    if not geometries:
        return []
    
    gdf = gpd.GeoDataFrame({'geometry': geometries, 'index': indices})
    
    # Create a bounding box polygon
    bound_box = Polygon([
        (min_lon, min_lat),
        (min_lon, max_lat),
        (max_lon, max_lat),
        (max_lon, min_lat)
    ])
    
    # Clip the polygons
    clipped = gdf.copy()
    clipped['geometry'] = gdf.intersection(bound_box)
    
    # Extract clipped polygons
    clipped_polygons = []
    for idx, row in clipped.iterrows():
        geometry = row['geometry']
        point_index = row['index']
        
        if geometry.is_empty:
            continue
        
        if isinstance(geometry, Polygon):
            # Convert back to Leaflet format [lat, lon]
            coords = [(float(lat), float(lon)) for lon, lat in geometry.exterior.coords]
            clipped_polygons.append((coords, point_index))
        elif isinstance(geometry, MultiPolygon):
            for poly in geometry.geoms:
                coords = [(float(lat), float(lon)) for lon, lat in poly.exterior.coords]
                clipped_polygons.append((coords, point_index))
    
    return clipped_polygons
