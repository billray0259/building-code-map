# dash_app/layout.py

import dash_bootstrap_components as dbc
import dash_leaflet as dl
import json
from shapely.geometry import shape
from dash import dcc
from .naiop_challenge_map import get_geojson

def create_layout():
    
    geojson = get_geojson()
    
    geojson_layer = []
    centroids = []
    latitudes = []
    longitudes = []
    
    for feature in geojson['features']:
        feature_component = dl.GeoJSON(
            data=feature,
            children=dl.Tooltip(content=feature['properties']['description'])
        )
        if 'icon' in feature['properties']:
            feature_component = dl.Marker(
                position=[feature['geometry']['coordinates'][1], feature['geometry']['coordinates'][0]],
                children=[
                    dl.Tooltip(content=feature['properties']['name']),
                    dl.Popup(content=feature['properties']['description'])
                ],
                icon=feature['properties']['icon']
            )
        geojson_layer.append(
            feature_component
        )
        geom = shape(feature['geometry'])
        centroids.append(geom.centroid)
        bounds = geom.bounds
        longitudes.extend([bounds[0], bounds[2]])
        latitudes.extend([bounds[1], bounds[3]])
    
    avg_lat = sum(centroid.y for centroid in centroids) / len(centroids)
    avg_lon = sum(centroid.x for centroid in centroids) / len(centroids)
    
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dl.Map(id='map', style={'width': '100vw', 'height': '100vh'}, center=[39.8575144983084, -104.97617052195768], zoom=12, children=[
                    dl.TileLayer(),
                    dl.LayerGroup(id='geojson-layer', children=geojson_layer)
                ])
            ])
        ], style={'margin': '0', 'padding': '0'})
    ], fluid=True, style={'margin': '0', 'padding': '0'})