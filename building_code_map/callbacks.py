from dash.dependencies import Input, Output, State
from dash import html
import dash_leaflet as dl
import json
import os
from .utils import compute_voronoi_polygons, clip_polygons_to_bounds
from collections import Counter
from .config import GEOJSON_FILENAME

def register_callbacks(app):
    @app.callback(
        Output('active-layer-container', 'children'),
        [Input('code-toggle', 'value'),
         Input('show-unknown-toggle', 'value'),
         Input('pin-toggle', 'value')],  # Removed combined-mode-toggle
        [State('map', 'bounds')]
    )
    def toggle_code_display(selected_code, show_unknown, pin_toggle, bounds):
        """
        Toggle between displaying IRC, IECC, or combined codes on the map and control visibility of unknown pins
        """
        if selected_code == "combined":
            markers, point_data = create_markers_for_combined_mode(show_unknown)
        else:
            markers, point_data = create_markers_for_code_type(selected_code, show_unknown)
        
        # NEW: If pins are toggled off, clear the markers list while preserving point_data for Voronoi if needed.
        if not pin_toggle:
            markers = []
        
        # We need to recreate the markers every time to ensure proper rendering
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
        
        # Create markers layer (updated to remove combined_mode variable)
        markers_layer = dl.LayerGroup(
            id=f'{selected_code}-markers-layer',  # Previously used combined_mode variable
            children=markers
        )
        
        # Create a group for both layers and use selected_code to form the layer id
        layers = [voronoi_layer, markers_layer] if voronoi_layer else [markers_layer]
        
        return dl.LayerGroup(
            id=f'{selected_code}-layer',  # Updated to use selected_code only
            children=layers
        )
    
    @app.callback(
        Output('polygon-layer', 'children'),
        [Input('code-toggle', 'value'),
         Input('show-unknown-toggle', 'value')]  # Removed combined-mode-toggle
    )
    def update_polygon_colors(selected_code, show_unknown):
        import os, json
        from collections import Counter
        base_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        point_geojson_path = os.path.join(base_path, 'data', GEOJSON_FILENAME)
        with open(point_geojson_path) as f:
            points = json.load(f)
        polygon_geojson_path = os.path.join(base_path, 'data/tl_2024_08_place/tl_2024_08_place.geojson')
        with open(polygon_geojson_path) as f:
            polygons = json.load(f)
        # Color to hex mapping remains constant
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
        # Build mapping from polygon IDs to matching point names (based on normalized names)
        polygon_point_names = {}
        def normalize_name(name):
            import re
            return re.sub(r'\[.*?\]|\?', '', str(name)).strip().lower() if name else ""
        point_name_mapping = {}
        for feature in points['features']:
            if 'properties' in feature:
                raw_name = feature['properties'].get('name', '')
                normalized = normalize_name(raw_name)
                point_name_mapping[normalized] = raw_name
        for feature in polygons['features']:
            if 'properties' in feature:
                polygon_id = feature['properties'].get('GEOID', '')
                polygon_name = feature['properties'].get('NAME', '')
                polygon_namelsad = feature['properties'].get('NAMELSAD', '')
                normalized1 = normalize_name(polygon_name)
                normalized2 = normalize_name(polygon_namelsad)
                polygon_point_names[polygon_id] = []
                if normalized1 in point_name_mapping:
                    polygon_point_names[polygon_id].append(point_name_mapping[normalized1])
                elif normalized2 in point_name_mapping:
                    polygon_point_names[polygon_id].append(point_name_mapping[normalized2])
        updated_polygon_layers = []
        if selected_code == "combined":
            # Build global combined mapping from point name to combined key
            combined_keys = []
            point_name_to_combined = {}
            for feature in points['features']:
                if feature.get('geometry', {}).get('type') == 'Point' and 'properties' in feature:
                    props = feature['properties']
                    irc = props.get('irc', 'Unknown')
                    iecc = props.get('iecc', 'Unknown')
                    if isinstance(irc, (int, float)):
                        irc = str(irc)
                    if isinstance(iecc, (int, float)):
                        iecc = str(iecc)
                    # NEW: Only use ("Other", "Other") if both codes are Unknown
                    if irc == 'Unknown' and iecc == 'Unknown':
                        key = ("Other", "Other")
                    else:
                        key = (irc, iecc)
                    if key == ("Other", "Other") and not show_unknown:
                        continue
                    combined_keys.append(key)
                    point_name = props.get('name', '')
                    point_name_to_combined[point_name] = key
            # Determine top combined classes (limited to available colors)
            available_colors = ['blue', 'gold', 'red', 'green', 'orange', 'yellow', 'violet', 'black']
            counter = Counter(combined_keys)
            top_classes = {k for k, _ in counter.most_common(len(available_colors))}
            # ---- Modified sorting: order by IECC then IRC (both descending) ----
            sorted_top = sorted(
                top_classes,
                key=lambda k: ((int(k[1]) if k[1].isdigit() else -1), (int(k[0]) if k[0].isdigit() else -1)),
                reverse=True
            )
            class_color_mapping = {cls: available_colors[i] for i, cls in enumerate(sorted_top)}
            # For each polygon, use the first matched point's combined key if available
            for feature in polygons['features']:
                if 'properties' in feature and 'geometry' in feature:
                    polygon_id = feature['properties'].get('GEOID', None)
                    point_names = polygon_point_names.get(polygon_id, [])
                    # NEW: Skip polygon if no matching points and show_unknown is unchecked
                    if not show_unknown and len(point_names) == 0:
                        continue
                    city_name = feature['properties'].get('NAME', 'Unknown Area')
                    fill_color = color_to_hex.get('grey')
                    for name in point_names:
                        key = point_name_to_combined.get(name)
                        # NEW: If key not in mapping, reassign to ("Other", "Other")
                        if key not in class_color_mapping:
                            key = ("Other", "Other")
                        if key and key in class_color_mapping:
                            color_name = class_color_mapping.get(key) or "black"
                            fill_color = color_to_hex.get(color_name, color_to_hex.get('grey'))
                            break
                    single_feature_geojson = {"type": "FeatureCollection", "features": [feature]}
                    tooltip_content = f"{city_name}: {len(point_names)} location{'s' if len(point_names)!=1 else ''}"
                    popup_content = html.Div([
                        html.H5(f"{city_name}"),
                        html.P(f"{len(point_names)} location{'s' if len(point_names)!=1 else ''}:"),
                        html.Ul([html.Li(n) for n in point_names])
                    ])
                    polygon = dl.GeoJSON(
                        data=single_feature_geojson,
                        id=f'polygon-{polygon_id}',
                        style={'weight': 2, 'opacity': 0.7, 'color': '#4A4A4A',
                               'fillOpacity': 0.4, 'fillColor': fill_color},
                        hoverStyle=dict(weight=3, color='#666', dashArray=''),
                        children=[dl.Tooltip(tooltip_content), dl.Popup(popup_content)]
                    )
                    updated_polygon_layers.append(polygon)
        else:
            # Use single code logic (existing behavior)
            from .callbacks import collect_all_codes, create_color_mapping  # if needed adjust import
            all_codes = collect_all_codes(points)
            color_mapping = create_color_mapping(all_codes)
            for feature in polygons['features']:
                if 'properties' in feature and 'geometry' in feature:
                    polygon_id = feature['properties'].get('GEOID', None)
                    point_names = polygon_point_names.get(polygon_id, [])
                    # NEW: Skip polygon if no matching points and show_unknown is unchecked
                    if not show_unknown and len(point_names) == 0:
                        continue
                    city_name = feature['properties'].get('NAME', 'Unknown Area')
                    fill_color = color_to_hex.get('grey')
                    code_value = 'Unknown'
                    # Use first matched point's single code from the selected type
                    # (Note: here selected_code determines which code is used)
                    point_name_to_code = {}
                    for feat in points['features']:
                        if 'properties' in feat:
                            name = feat.get('properties', {}).get('name', '')
                            code_val = feat.get('properties', {}).get(selected_code.lower(), 'Unknown')
                            if isinstance(code_val, (int, float)):
                                code_val = str(code_val)
                            point_name_to_code[name] = code_val
                    for name in point_names:
                        code_value = point_name_to_code.get(name, 'Unknown')
                        if code_value != 'Unknown' or show_unknown:
                            c_name = color_mapping.get(code_value, 'grey')
                            fill_color = color_to_hex.get(c_name, color_to_hex.get('grey'))
                            break
                    # Skip polygon if code is unknown and show_unknown False
                    if code_value == 'Unknown' and not show_unknown:
                        continue
                    single_feature_geojson = {"type": "FeatureCollection", "features": [feature]}
                    tooltip_content = f"{city_name}: {len(point_names)} location{'s' if len(point_names)!=1 else ''}"
                    code_info = f"{selected_code.upper()}: {code_value}"
                    popup_content = html.Div([
                        html.H5(f"{city_name}"),
                        html.P(code_info),
                        html.P(f"{len(point_names)} location{'s' if len(point_names)!=1 else ''}:"),
                        html.Ul([html.Li(n) for n in point_names])
                    ])
                    polygon = dl.GeoJSON(
                        data=single_feature_geojson,
                        id=f'polygon-{polygon_id}',
                        style={'weight': 2, 'opacity': 0.7, 'color': '#4A4A4A',
                               'fillOpacity': 0.4, 'fillColor': fill_color},
                        hoverStyle=dict(weight=3, color='#666', dashArray=''),
                        children=[dl.Tooltip(tooltip_content), dl.Popup(popup_content)]
                    )
                    updated_polygon_layers.append(polygon)
        return updated_polygon_layers

    @app.callback(
        Output("legend-div", "children"),
        [Input("code-toggle", 'value'),
         Input("show-unknown-toggle", 'value')]  # Removed combined-mode-toggle
    )
    def update_legend(selected_code, show_unknown):
        import os, json
        from collections import Counter
        base_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        point_geojson_path = os.path.join(base_path, "data", GEOJSON_FILENAME)
        with open(point_geojson_path) as f:
            points = json.load(f)
        # Define available colors and hex mapping
        available_colors = ['blue', 'gold', 'red', 'green', 'orange', 'yellow', 'violet', 'black']
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
        if selected_code == "combined":
            # Build combined keys frequency
            combined_keys = []
            for feature in points["features"]:
                if feature.get("geometry", {}).get("type") == "Point":
                    props = feature.get("properties", {})
                    irc = props.get("irc", "Unknown")
                    iecc = props.get("iecc", "Unknown")
                    if isinstance(irc, (int, float)): irc = str(irc)
                    if isinstance(iecc, (int, float)): iecc = str(iecc)
                    # NEW: Only assign ("Other","Other") if both are Unknown
                    if irc == "Unknown" and iecc == "Unknown":
                        key = ("Other", "Other")
                    else:
                        key = (irc, iecc)
                    if key == ("Other", "Other") and not show_unknown:
                        continue
                    combined_keys.append(key)
            counter = Counter(combined_keys)
            top_classes = {k for k, _ in counter.most_common(len(available_colors))}
            # ---- Modified sorting: order by IECC then IRC (both descending) ----
            sorted_top = sorted(
                top_classes,
                key=lambda k: ((int(k[1]) if k[1].isdigit() else -1), (int(k[0]) if k[0].isdigit() else -1)),
                reverse=True
            )
            # Map each combined class to a color from available_colors
            class_color_mapping = {cls: available_colors[i] for i, cls in enumerate(sorted_top)}
            legend_items = [
                html.Div([
                    html.Span(
                        style={
                            "backgroundColor": color_to_hex.get(class_color_mapping[cls], "#000000"),
                            "display": "inline-block",
                            "width": "15px",
                            "height": "15px",
                            "marginRight": "5px"
                        }
                    ),
                    html.Span(f"IRC {cls[0]} / IECC {cls[1]} ({counter[cls]})")
                ], style={"padding": "5px"}) for cls in sorted_top
            ]
        else:
            # Build legend for individual codes
            all_codes = set()
            for feature in points["features"]:
                props = feature.get("properties", {})
                irc = props.get("irc")
                iecc = props.get("iecc")
                if isinstance(irc, (int, float)): irc = str(irc)
                if isinstance(iecc, (int, float)): iecc = str(iecc)
                if irc not in [None, "Unknown"]:
                    all_codes.add(irc)
                if iecc not in [None, "Unknown"]:
                    all_codes.add(iecc)
            all_codes.add("Unknown")
            sorted_codes = sorted(all_codes)
            # Use color mapping as in create_color_mapping
            rev_colors = available_colors[::-1]
            color_mapping = {}
            for i, code in enumerate(sorted_codes):
                color_mapping[code] = rev_colors[i % len(available_colors)]
            color_mapping["Unknown"] = "grey"
            legend_items = [
                html.Div([
                    html.Span(
                        style={
                            "backgroundColor": color_to_hex.get(color_mapping[code], "#000000"),
                            "display": "inline-block",
                            "width": "15px",
                            "height": "15px",
                            "marginRight": "5px"
                        }
                    ),
                    html.Span(f"{code}")
                ], style={"padding": "5px"}) for code in sorted_codes
            ]
        return legend_items

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
    point_geojson_path = os.path.join(base_path, 'data', GEOJSON_FILENAME)
    with open(point_geojson_path) as f:
        points = json.load(f)
    
    # NEW: Clean name fields from points
    import re
    for feature in points['features']:
        if 'properties' in feature and 'name' in feature['properties']:
            feature['properties']['name'] = re.sub(r'\[.*?\]|\?', '', feature['properties']['name']).strip()
    
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

def create_markers_for_combined_mode(show_unknown=True):
    """
    Create markers using a combined key (IRC, IECC) and classify markers based on the combination.
    Only the top classes (by frequency) limited to the number of available colors are rendered.
    
    Returns:
         tuple: (markers_list, point_data)
         where point_data is a list of tuples (position, color, combined_key)
    """
    base_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    point_geojson_path = os.path.join(base_path, 'data', GEOJSON_FILENAME)
    with open(point_geojson_path) as f:
        points = json.load(f)
    
    # NEW: Clean name fields from points
    import re
    for feature in points['features']:
        if 'properties' in feature and 'name' in feature['properties']:
            feature['properties']['name'] = re.sub(r'\[.*?\]|\?', '', feature['properties']['name']).strip()
    
    markers = []
    point_data = []
    combined_keys = []
    items = []  # Temporarily store (feature, combined_key)
    
    # First pass to gather all combined keys and frequency
    for feature in points['features']:
        if 'geometry' in feature and feature['geometry']['type'] == 'Point':
            props = feature['properties']
            irc_code = props.get('irc', 'Unknown')
            iecc_code = props.get('iecc', 'Unknown')
            if isinstance(irc_code, (int, float)):
                irc_code = str(irc_code)
            if isinstance(iecc_code, (int, float)):
                iecc_code = str(iecc_code)
            # NEW: Use ("Other","Other") only if both codes are Unknown
            if irc_code == 'Unknown' and iecc_code == 'Unknown':
                key = ("Unknown", "Unknown")
            else:
                key = (irc_code, iecc_code)
            # Skip if both are Unknown and show_unknown is False
            if key == ("Unknown", "Unknown") and not show_unknown:
                continue
            combined_keys.append(key)
            items.append((feature, key))
    
    # Count frequency and select top classes (limited to available colors)
    available_colors = ['blue', 'gold', 'red', 'green', 'orange', 'yellow', 'violet', 'black']
    counter = Counter(combined_keys)
    top_classes = {k for k, _ in counter.most_common(len(available_colors))}
    # ---- Modified sorting: order by IECC then IRC (both descending) ----
    sorted_top = sorted(
        top_classes,
        key=lambda k: ((int(k[1]) if k[1].isdigit() else -1), (int(k[0]) if k[0].isdigit() else -1)),
        reverse=True
    )
    class_color_mapping = {cls: available_colors[i] for i, cls in enumerate(sorted_top)}
    
    # Second pass: for features not in top classes, reassign key to ("Other", "Other")
    for feature, combined_key in items:
        if combined_key not in class_color_mapping:
            combined_key = ("Other", "Other")
        props = feature['properties']
        # Get both codes for popup display
        irc_code = props.get('irc', 'Unknown')
        iecc_code = props.get('iecc', 'Unknown')
        if isinstance(irc_code, (int, float)):
            irc_code = str(irc_code)
        if isinstance(iecc_code, (int, float)):
            iecc_code = str(iecc_code)
        coordinates = feature['geometry']['coordinates']
        orig_x, orig_y = coordinates[0], coordinates[1]
        position = [orig_y, -abs(orig_x)]
        tooltip_text = props.get('name', 'Unnamed Point')
        name = props.get('name', 'Unnamed Point')
        # Use fallback "black" if no color is returned
        marker_color = class_color_mapping.get(combined_key) or "black"
        point_data.append((position, marker_color, f"{irc_code}-{iecc_code}"))
        icon = {
            'iconUrl': f'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-{marker_color}.png',
            'shadowUrl': 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.0.0/images/marker-shadow.png',
            'iconSize': [25, 41],
            'iconAnchor': [12, 41],
            'popupAnchor': [1, -34],
            'shadowSize': [41, 41]
        }
        popup_content = html.Div([
            html.H4(name),
            html.P(f"Government: {props.get('government', 'N/A')}"),
            html.P(f"County: {props.get('county', 'N/A')}"),
            html.P(f"IRC: {irc_code}"),
            html.P(f"IECC: {iecc_code}"),
            html.P([html.A("Website", href=props.get('website', '#'), target="_blank")])
        ], id=f"popup-{name.lower().replace(' ', '-')}" )
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