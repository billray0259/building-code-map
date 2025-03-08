# dash_app/app.py

import dash
import dash_bootstrap_components as dbc
from flask import Flask

from .layout import create_layout
from .callbacks import register_callbacks

def create_dash_app(server: Flask, url_base_pathname: str = "/"):
    """
    Factory function to create a Dash application.
    """
    app = dash.Dash(
        __name__,
        server=server,
        url_base_pathname=url_base_pathname,
        external_stylesheets=[dbc.themes.BOOTSTRAP],
        suppress_callback_exceptions=True
    )

    # Set the layout
    app.layout = create_layout()

    # Register all callbacks
    register_callbacks(app)

    return app
