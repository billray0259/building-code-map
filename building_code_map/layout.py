import os
import dash_bootstrap_components as dbc
import dash_leaflet as dl
import json
import re  # Add regex for name cleaning
from dash import dcc, html
from dash.dependencies import Input, Output
from shapely.geometry import Point, shape
# Fix the import error - handle different Shapely versions
try:
    # For Shapely 2.0+
    from shapely.errors import GEOSException
except ImportError:
    try:
        # Alternative location in some versions
        from shapely.errors import TopologyException as GEOSException
    except ImportError:
        # Very old versions
        from shapely.topology import TopologyException as GEOSException
import logging
import copy
from .config import GEOJSON_FILENAME

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Set up logging to print to console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


def create_layout():
    # Compute the absolute path to the geojson file
    base_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    
    polygon_geojson_path = 'data/tl_2024_08_place/tl_2024_08_place.geojson'
    with open(os.path.join(base_path, polygon_geojson_path)) as f:
        polygons = json.load(f)
    
    # Load points geojson data
    point_geojson_path = os.path.join(base_path, 'data', GEOJSON_FILENAME)
    with open(point_geojson_path) as f:
        points = json.load(f)

    # Collect all unique codes (both IRC and IECC) into a single set
    all_codes = set()
    
    # Add codes from points geojson
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
    
    # Create a color map for all codes with simple colors that match available marker colors
    available_colors = ['blue', 'gold', 'red', 'green', 'orange', 'yellow', 'violet', 'black'][::-1]
    
    # Create a consistent color mapping for all codes
    color_mapping = {}
    for i, code in enumerate(sorted(all_codes)):
        color_index = i % len(available_colors)
        color_mapping[code] = available_colors[color_index]
    
    # Make sure "Unknown" is always grey
    color_mapping["Unknown"] = "grey"
    
    # Create color to hex map for legend display
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
    
    # Store both marker sets (IRC and IECC) as separate layer groups
    irc_markers = []
    iecc_markers = []
    
    # Function to normalize place names for comparison
    def normalize_name(name):
        if not name:
            return ""
        # Remove characters like [*] and ? and convert to lowercase
        cleaned_name = re.sub(r'\[.*?\]|\?', '', str(name)).strip().lower()
        return cleaned_name
    
    # Process each feature from the GeoJSON
    for feature in points['features']:
        if 'geometry' in feature and feature['geometry']['type'] == 'Point':
            props = feature['properties']
            
            # Get codes
            irc_code = props.get('irc', 'Unknown')
            iecc_code = props.get('iecc', 'Unknown')
            
            # Convert numeric codes to strings for comparison
            if isinstance(irc_code, (int, float)):
                irc_code = str(irc_code)
            if isinstance(iecc_code, (int, float)):
                iecc_code = str(iecc_code)
                
            coordinates = feature['geometry']['coordinates']
            
            # Extract original coordinates
            orig_x, orig_y = coordinates[0], coordinates[1]
            
            # Apply the correct transformation: "Longitude sign fixed"
            # Convert from GeoJSON [lon, lat] to Leaflet [lat, lon] and fix longitude sign
            position = [orig_y, -abs(orig_x)]
            
            tooltip_text = props.get('name', 'Unnamed Point')
            name = props.get('name', 'Unnamed Point')
            
            # Create a unique ID base for this popup
            popup_id_base = f"popup-{name.lower().replace(' ', '-')}"
            
            # Create popup content template
            popup_content_template = html.Div([
                html.H4(name),
                html.P(f"Government: {props.get('government', 'N/A')}"),
                html.P(f"County: {props.get('county', 'N/A')}"),
                html.P(f"IRC: {irc_code}"),
                html.P(f"IECC: {iecc_code}"),
                html.P([
                    html.A("Website", href=props.get('website', '#'), target="_blank")
                ])
            ])
            
            # Create IRC marker with color based on IRC code
            irc_color = color_mapping.get(irc_code, "grey")
            irc_icon = {
                'iconUrl': f'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-{irc_color}.png',
                'shadowUrl': 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.0.0/images/marker-shadow.png',
                'iconSize': [25, 41],
                'iconAnchor': [12, 41],
                'popupAnchor': [1, -34],
                'shadowSize': [41, 41]
            }
            
            irc_marker = dl.Marker(
                position=position,
                icon=irc_icon,
                children=[
                    dl.Tooltip(tooltip_text),
                    dl.Popup(html.Div([popup_content_template], id=f"{popup_id_base}-irc"))
                ]
            )
            irc_markers.append(irc_marker)
            
            # Create IECC marker with color based on IECC code
            iecc_color = color_mapping.get(iecc_code, "grey")
            iecc_icon = {
                'iconUrl': f'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-{iecc_color}.png',
                'shadowUrl': 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.0.0/images/marker-shadow.png',
                'iconSize': [25, 41],
                'iconAnchor': [12, 41],
                'popupAnchor': [1, -34],
                'shadowSize': [41, 41]
            }
            
            iecc_marker = dl.Marker(
                position=position,
                icon=iecc_icon,
                children=[
                    dl.Tooltip(tooltip_text),
                    dl.Popup(html.Div([popup_content_template], id=f"{popup_id_base}-iecc"))
                ]
            )
            iecc_markers.append(iecc_marker)
    
    # Extract normalized point names for matching with polygons
    point_name_mapping = {}
    for feature in points['features']:
        if 'properties' in feature:
            raw_name = feature['properties'].get('name', '')
            normalized_name = normalize_name(raw_name)
            point_name_mapping[normalized_name] = raw_name
    
    # Match polygons to points by name
    polygon_point_counts = {}
    polygon_point_names = {}  # Track names of points in each polygon
    
    # Process each polygon to find matching points by name
    for feature in polygons['features']:
        if 'properties' in feature:
            polygon_id = feature['properties'].get('GEOID', '')
            polygon_name = feature['properties'].get('NAME', '')
            polygon_namelsad = feature['properties'].get('NAMELSAD', '')  # Also try NAMELSAD
            normalized_polygon_name = normalize_name(polygon_name)
            normalized_polygon_namelsad = normalize_name(polygon_namelsad)
            
            # Initialize counts and name lists
            polygon_point_counts[polygon_id] = 0
            polygon_point_names[polygon_id] = []
            
            # First try matching on NAME
            if normalized_polygon_name in point_name_mapping:
                original_point_name = point_name_mapping[normalized_polygon_name]
                polygon_point_counts[polygon_id] += 1
                polygon_point_names[polygon_id].append(original_point_name)
                logger.info(f"Matched '{original_point_name}' to polygon '{polygon_name}' (ID: {polygon_id})")
            # If no match with NAME, try NAMELSAD
            elif normalized_polygon_namelsad in point_name_mapping:
                original_point_name = point_name_mapping[normalized_polygon_namelsad]
                polygon_point_counts[polygon_id] += 1
                polygon_point_names[polygon_id].append(original_point_name)
                logger.info(f"Matched '{original_point_name}' to polygon '{polygon_namelsad}' (ID: {polygon_id})")
    
    # Create a deep copy of the polygons GeoJSON to modify
    styled_polygons = copy.deepcopy(polygons)
    
    # Create individual polygon layers
    polygon_layers = []
    
    for feature in styled_polygons['features']:
        if 'properties' in feature and 'geometry' in feature:
            polygon_id = feature['properties'].get('GEOID', None)
            point_count = polygon_point_counts.get(polygon_id, 0)
            point_names = polygon_point_names.get(polygon_id, [])
            
            # Get city name from polygon properties
            city_name = feature['properties'].get('NAME', 'Unknown Area')
            
            # Determine fill color based on matched points
            fill_color = color_to_hex.get('grey')  # Default to Unknown/grey color
            
            # If we have matched points, look up their codes and colors
            if point_count > 0:
                # Find the point in the original points data that matches our polygon
                for point_feature in points['features']:
                    if point_feature.get('properties', {}).get('name', '') in point_names:
                        # Get the IRC code (could use IECC as well depending on requirements)
                        irc_code = point_feature.get('properties', {}).get('irc', 'Unknown')
                        # Convert numeric codes to strings
                        if isinstance(irc_code, (int, float)):
                            irc_code = str(irc_code)
                        # Get the color for this code
                        color_name = color_mapping.get(irc_code, 'grey')
                        fill_color = color_to_hex.get(color_name, color_to_hex.get('grey'))
                        # Just use the first match for now
                        break
            
            # Define style based on point count and matched color
            style = {
                'weight': 2,
                'opacity': 0.7,
                'color': '#4A4A4A',
                'fillOpacity': 0.4,
                'fillColor': fill_color
            }
            
            # Create single-feature GeoJSON
            single_feature_geojson = {
                "type": "FeatureCollection",
                "features": [feature]
            }
            
            # Create tooltip content with list of points
            if point_count > 0:
                tooltip_content = f"{city_name}: {point_count} {'location' if point_count == 1 else 'locations'}"
                popup_content = html.Div([
                    html.H5(f"{city_name}"),
                    html.P(f"{point_count} {'location' if point_count == 1 else 'locations'}:"),
                    html.Ul([html.Li(name) for name in point_names])
                ])
            else:
                tooltip_content = f"{city_name}: No data"
                popup_content = html.Div([
                    html.H5(f"{city_name}"),
                    html.P("No building code data available")
                ])
            
            # Create individual polygon layer
            polygon = dl.GeoJSON(
                data=single_feature_geojson,
                id=f'polygon-{polygon_id}',
                style=style,
                hoverStyle=dict(weight=3, color='#666', dashArray=''),
                children=[
                    dl.Tooltip(tooltip_content),
                    dl.Popup(popup_content)
                ]
            )
            
            polygon_layers.append(polygon)
    
    # Create a layer group with all polygon layers
    polygon_layer = dl.LayerGroup(
        id='polygon-layer',
        children=polygon_layers
    )
    
    # Create layer groups for IRC and IECC markers
    irc_layer = dl.LayerGroup(
        id='irc-layer',
        children=irc_markers
    )
    
    iecc_layer = dl.LayerGroup(
        id='iecc-layer',
        children=iecc_markers
    )
    
    # Create a single, unified legend for all codes
    legend_items = [
        html.Div([
            html.Span(style={'backgroundColor': color_to_hex[color_mapping[code]], 'display': 'inline-block',
                             'width': '15px', 'height': '15px', 'marginRight': '5px'}),
            html.Span(code)
        ], style={'padding': '5px'})
        for code in sorted(all_codes)
    ]
    
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                # Control panel with fixed width
                dbc.Card([
                    dbc.CardHeader(html.H4("Building Code Adoption in Colorado", className="mb-0")),
                    dbc.CardBody([
                        # Controls section
                        dbc.Row([
                            dbc.Col([
                                html.Label("Select Building Code Type:"),
                                dbc.RadioItems(
                                    id='code-toggle',
                                    options=[
                                        {'label': 'IRC (Residential)', 'value': 'irc'},
                                        {'label': 'IECC (Energy)', 'value': 'iecc'},
                                        {'label': 'Combined Code Mode', 'value': 'combined'},
                                    ],
                                    value='irc',  # Default to IRC
                                    inline=True,
                                    className="mb-3"
                                ),
                            ], md=6),
                            dbc.Col([
                                html.Label("Display Options:"),
                                dbc.Checkbox(
                                    id='show-unknown-toggle',
                                    label="Show Unknown Codes",
                                    value=False,  # Default to showing unknown codes
                                    className="mb-0 mt-2"
                                ),
                                dbc.Checkbox(
                                    id='pin-toggle',
                                    label="Show Pins",
                                    value=True,  # Default to showing pins
                                    className="mb-3 mt-2"
                                )
                            ], md=6),
                        ]),
                        # Legend section updated
                        html.Hr(),
                        html.H6("Legend:"),
                        html.Div(id="legend-div", style={'display': 'flex', 'flexWrap': 'wrap'})
                    ])
                ], className="shadow-sm", style={'position': 'absolute', 'top': '10px', 'left': '10px', 
                                                 'zIndex': 1000, 'width': '400px', 'maxWidth': '90%'})
            ], width=12, style={'padding': 0}),
        ], style={'margin': '0', 'padding': '0'}),
        
        # Map takes full page
        dbc.Row([
            dbc.Col([
                dl.Map(
                    id='map',
                    style={'width': '100vw', 'height': '100vh'},
                    center=[39.0, -105.5],  # Center on Colorado
                    zoom=7,  # Show the entire state
                    zoomControl=False,  # Disable default zoom control
                    children=[
                        dl.TileLayer(),
                        polygon_layer,  # Add polygon layer before markers
                        html.Div(id='active-layer-container'),  # This container will hold active layer
                        # Add custom positioned zoom control
                        dl.ZoomControl(position="bottomright")
                    ],
                    # Track bounds for Voronoi calculations
                    bounds=[[-109.5, 37.0], [-102.0, 41.0]]  # Colorado's approximate bounds
                )
            ], width=12, style={'padding': 0})
        ], style={'margin': '0', 'padding': '0'})
    ], fluid=True, style={'margin': '0', 'padding': '0'})