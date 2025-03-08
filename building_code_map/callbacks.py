from dash.dependencies import Input, Output, State
from dash import html
import dash_leaflet as dl
import json
import os
from .utils import compute_voronoi_polygons, clip_polygons_to_bounds

def register_callbacks(app):
    @app.callback(
        Output('active-layer-container', 'children'),
        [Input('code-toggle', 'value'),
         Input('show-unknown-toggle', 'value')],
        [State('map', 'bounds')]
    )
    def toggle_code_display(selected_code, show_unknown, bounds):
        """
        Toggle between displaying IRC and IECC codes on the map and control visibility of unknown pins
        """
        # We need to recreate the markers every time to ensure proper rendering
        markers, point_data = create_markers_for_code_type(selected_code, show_unknown)
        
        # Create Voronoi cells based on the same points
        voronoi_layer = None
        if point_data:
            # points format is [[lat, lon], ...]
            points = [pos for pos, _, _ in point_data]
            colors = [color for _, color, _ in point_data]
            opacities = [0.5 if code != 'Unknown' else 0.2 for _, _, code in point_data]
            
            # Use Colorado state bounds if map bounds aren't available yet
            map_bounds = bounds if bounds else [[-109.5, 37.0], [-102.0, 41.0]]
            
            # Calculate Voronoi polygons using map bounds
            voronoi_polygons = compute_voronoi_polygons(points, map_bounds)
            voronoi_polygons = clip_polygons_to_bounds(voronoi_polygons, map_bounds)
            
            # Create GeoJSON features for the Voronoi cells
            features = []
            for (polygon_coords, point_index) in voronoi_polygons:
                if point_index < len(colors):
                    color = colors[point_index]
                    opacity = opacities[point_index]
                    code = point_data[point_index][2]
                    
                    # Skip unknown codes if not showing them
                    if code == 'Unknown' and not show_unknown:
                        continue
                    
                    # Create GeoJSON feature
                    feature = {
                        'type': 'Feature',
                        'geometry': {
                            'type': 'Polygon',
                            'coordinates': [[list(coord) for coord in polygon_coords]]
                        },
                        'properties': {
                            'color': color,
                            'opacity': opacity,
                            'code': code
                        }
                    }
                    features.append(feature)
            
            # Create GeoJSON object
            geojson_data = {
                'type': 'FeatureCollection',
                'features': features
            }
            
            # Create the Voronoi layer
            color_to_hex = {
                'blue': '#2A81CB',
                'gold': '#FFD326',
                'red': '#CB2B3E',
                'green': '#2AAD27',
                'orange': '#CB8427',
                'yellow': '#CAC428',
                'violet': '#9C2BCB',
                'grey': '#7B7B7B',
                'black': '#3D3D3D'
            }
            
            voronoi_layer = dl.GeoJSON(
                data=geojson_data,
                id='voronoi-layer',
                options={
                    'style': lambda feature: {
                        'color': color_to_hex.get(feature['properties']['color'], '#000000'),
                        'weight': 1,
                        'opacity': 0.8,
                        'fillColor': color_to_hex.get(feature['properties']['color'], '#000000'),
                        'fillOpacity': feature['properties']['opacity'],
                        'dashArray': '3' if feature['properties']['code'] == 'Unknown' else '0'
                    }
                }
            )
        
        # Create markers layer
        markers_layer = dl.LayerGroup(
            id=f'{selected_code}-markers-layer',
            children=markers
        )
        
        # Create a group for both layers - Voronoi on bottom, markers on top
        layers = [voronoi_layer, markers_layer] if voronoi_layer else [markers_layer]
        
        return dl.LayerGroup(
            id=f'{selected_code}-layer',
            children=layers
        )

def create_markers_for_code_type(code_type, show_unknown=True):
    """
    Create markers for the selected code type (IRC or IECC)
    
    Parameters:
    code_type (str): The type of code to display ('irc' or 'iecc')
    show_unknown (bool): Whether to show pins with 'Unknown' codes
    
    Returns:
    tuple: (markers_list, point_data)
    where point_data is a list of tuples (position, color, code)
    """
    # Load points geojson data
    base_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    point_geojson_path = os.path.join(base_path, 'data', 'gracy_3-3.geojson')
    with open(point_geojson_path) as f:
        points = json.load(f)
    
    # Create color mapping
    all_codes = collect_all_codes(points)
    color_mapping = create_color_mapping(all_codes)
    
    # Create markers list and point data
    markers = []
    point_data = []  # List of (position, color, code) tuples
    
    # Process each feature from the GeoJSON
    for feature in points['features']:
        if 'geometry' in feature and feature['geometry']['type'] == 'Point':
            props = feature['properties']
            
            # Get the specific code based on type (IRC or IECC)
            code_value = props.get(code_type.lower(), 'Unknown')
            
            # Convert numeric code to string for comparison
            if isinstance(code_value, (int, float)):
                code_value = str(code_value)
                
            # Skip unknown codes if show_unknown is False
            if code_value == 'Unknown' and not show_unknown:
                continue
                
            coordinates = feature['geometry']['coordinates']
            
            # Extract original coordinates
            orig_x, orig_y = coordinates[0], coordinates[1]
            
            # Apply the correct transformation: "Longitude sign fixed"
            # Convert from GeoJSON [lon, lat] to Leaflet [lat, lon] and fix longitude sign
            position = [orig_y, -abs(orig_x)]
            
            tooltip_text = props.get('name', 'Unnamed Point')
            name = props.get('name', 'Unnamed Point')
            
            # Get color based on code value
            marker_color = color_mapping.get(code_value, "grey")
            
            # Store point data for Voronoi calculation
            point_data.append((position, marker_color, code_value))
            
            # Create icon
            icon = {
                'iconUrl': f'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-{marker_color}.png',
                'shadowUrl': 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.0.0/images/marker-shadow.png',
                'iconSize': [25, 41],
                'iconAnchor': [12, 41],
                'popupAnchor': [1, -34],
                'shadowSize': [41, 41]
            }
            
            # Create popup content
            irc_code = props.get('irc', 'Unknown')
            if isinstance(irc_code, (int, float)):
                irc_code = str(irc_code)
                
            iecc_code = props.get('iecc', 'Unknown')
            if isinstance(iecc_code, (int, float)):
                iecc_code = str(iecc_code)
                
            popup_content = html.Div([
                html.H4(name),
                html.P(f"Government: {props.get('government', 'N/A')}"),
                html.P(f"County: {props.get('county', 'N/A')}"),
                html.P(f"IRC: {irc_code}"),
                html.P(f"IECC: {iecc_code}"),
                html.P([
                    html.A("Website", href=props.get('website', '#'), target="_blank")
                ])
            ], id=f"popup-{name.lower().replace(' ', '-')}")
            
            # Create marker
            marker = dl.Marker(
                position=position,
                icon=icon,
                children=[
                    dl.Tooltip(tooltip_text),
                    dl.Popup(popup_content)
                ]
            )
            markers.append(marker)
    
    return markers, point_data

def collect_all_codes(points):
    """Collect all unique codes from the GeoJSON data"""
    all_codes = set()
    
    for feature in points['features']:
        props = feature.get('properties', {})
        irc_code = props.get('irc')
        iecc_code = props.get('iecc')
        
        # Handle IRC codes
        if isinstance(irc_code, (int, float)) and str(irc_code) != "Unknown":
            all_codes.add(str(irc_code))
        elif isinstance(irc_code, str) and irc_code != "Unknown":
            all_codes.add(irc_code)
            
        # Handle IECC codes
        if isinstance(iecc_code, (int, float)) and str(iecc_code) != "Unknown":
            all_codes.add(str(iecc_code))
        elif isinstance(iecc_code, str) and iecc_code != "Unknown":
            all_codes.add(iecc_code)
    
    # Add "Unknown" as a special case
    all_codes.add("Unknown")
    
    return all_codes

def create_color_mapping(all_codes):
    """Create a mapping of codes to colors"""
    available_colors = ['blue', 'gold', 'red', 'green', 'orange', 'yellow', 'violet', 'black'][::-1]
    
    color_mapping = {}
    for i, code in enumerate(sorted(all_codes)):
        color_index = i % len(available_colors)
        color_mapping[code] = available_colors[color_index]
    
    # Make sure "Unknown" is always grey
    color_mapping["Unknown"] = "grey"
    
    return color_mapping