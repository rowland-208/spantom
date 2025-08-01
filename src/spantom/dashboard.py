"""
Dashboard module for spantom visualization.

This module provides a web-based dashboard for viewing and analyzing
trace data stored in SQLite databases.
"""

try:
    import os
    import sqlite3

    import click
    import dash
    from dash import dcc, Input, Output, dash_table, State
    import dash_bootstrap_components as dbc
    import pandas as pd
    import plotly.express as px

    from spantom.spantom import DEFAULT_DB
except ImportError as e:
    missing_package = str(e).split("'")[1] if "'" in str(e) else "unknown"
    raise ImportError(
        f"Dashboard dependencies not installed. "
        f"Install with: pip install spantom[dashboard]\n"
        f"Missing package: {missing_package}"
    )


class SpantomApp:
    def __init__(self, db_path=DEFAULT_DB):
        self.db_path = db_path
        # Embed CSS directly in the app
        external_stylesheets = [dbc.themes.FLATLY]
        self.app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

        # Add custom CSS
        self.app.index_string = """
        <!DOCTYPE html>
        <html>
            <head>
                {%metas%}
                <title>{%title%}</title>
                {%favicon%}
                {%css%}
                <style>
                    /* General Body Styles */
                    body {
                        background-color: #f8f9fa; /* A light grey background */
                    }

                    /* Header Styles */
                    .header-title {
                        color: #2C3E50; /* Dark blue-grey from Flatly theme */
                        text-align: center;
                        font-weight: 300;
                        padding-top: 20px;
                    }

                    .header-subtitle {
                        text-align: center;
                        color: #7B8A8B; /* A muted grey */
                        margin-bottom: 20px;
                    }

                    /* Query Text Area */
                    .query-textarea {
                        width: 100%;
                        height: 120px;
                        font-family: 'Courier New', Courier, monospace;
                        font-size: 14px;
                        border-radius: 5px;
                        border: 1px solid #ced4da;
                        padding: 10px;
                        resize: vertical; /* Allow vertical resizing */
                    }

                    /* Add a subtle transition to interactive elements */
                    .btn:hover, .Select-control:hover {
                        opacity: 0.9;
                        transition: opacity 0.2s ease-in-out;
                    }
                </style>
            </head>
            <body>
                {%app_entry%}
                <footer>
                    {%config%}
                    {%scripts%}
                    {%renderer%}
                </footer>
            </body>
        </html>
        """

        self.setup_layout()
        self.setup_callbacks()

    def execute_query(self, query):
        """Execute SQL query and return pandas DataFrame"""
        try:
            if not os.path.exists(self.db_path):
                raise FileNotFoundError(f"Database file not found: {self.db_path}")
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query(query, conn)
            conn.close()
            return df, None
        except Exception as e:
            return None, str(e)

    def setup_layout(self):
        self.app.layout = dbc.Container(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            dcc.Textarea(
                                id="query-input",
                                value="SELECT * FROM spans LIMIT 100",
                                className="query-textarea",
                                placeholder="Enter your SQL query here...",
                            ),
                            width=12,
                        ),
                        dbc.Col(
                            dbc.Button(
                                "Execute",
                                id="execute-btn",
                                color="primary",
                                className="mt-2 w-100",
                            ),
                            width=12,
                        ),
                    ],
                    className="mb-4",
                ),
                dbc.Alert(
                    id="error-alert", is_open=False, duration=4000, color="danger"
                ),
                dash_table.DataTable(
                    id="data-table",
                    page_size=10,
                    style_table={"overflowX": "auto"},
                    style_header={
                        "backgroundColor": "#2C3E50",
                        "color": "white",
                        "fontWeight": "bold",
                        "border": "1px solid #2C3E50",
                    },
                    style_cell={
                        "padding": "10px",
                        "fontFamily": "sans-serif",
                        "border": "1px solid #dee2e6",
                    },
                    style_data_conditional=[
                        {
                            "if": {"row_index": "odd"},
                            "backgroundColor": "rgb(248, 248, 248)",
                        }
                    ],
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Label("Plot Type"),
                                dcc.Dropdown(
                                    id="plot-type",
                                    options=[
                                        {"label": "Scatter Plot", "value": "scatter"},
                                        {"label": "Line Plot", "value": "line"},
                                        {"label": "Histogram", "value": "histogram"},
                                    ],
                                    value="scatter",
                                ),
                            ],
                            md=3,
                        ),
                        dbc.Col(
                            [dbc.Label("X-axis"), dcc.Dropdown(id="x-dropdown")], md=3
                        ),
                        dbc.Col(
                            [dbc.Label("Y-axis"), dcc.Dropdown(id="y-dropdown")], md=3
                        ),
                        dbc.Col(
                            [
                                dbc.Label("Color By (Optional)"),
                                dcc.Dropdown(id="z-dropdown"),
                            ],
                            md=3,
                        ),
                    ],
                    className="mb-4",
                ),
                dbc.Spinner(dcc.Graph(id="plot-output"), color="primary"),
                dcc.Store(id="dataframe-store"),
            ],
            fluid=True,
            className="p-4",
        )

    def setup_callbacks(self):
        @self.app.callback(
            [
                Output("dataframe-store", "data"),
                Output("error-alert", "children"),
                Output("error-alert", "is_open"),
                Output("data-table", "data"),
                Output("data-table", "columns"),
                Output("x-dropdown", "options"),
                Output("y-dropdown", "options"),
                Output("z-dropdown", "options"),
                Output("x-dropdown", "value"),
                Output("y-dropdown", "value"),
                Output("z-dropdown", "value"),
            ],
            Input("execute-btn", "n_clicks"),
            State("query-input", "value"),
        )
        def update_data(n_clicks, query):
            if not query or not query.strip():
                return (
                    dash.no_update,
                    "Please enter a SQL query.",
                    True,
                    dash.no_update,
                    dash.no_update,
                    [],
                    [],
                    [],
                    None,
                    None,
                    None,
                )

            df, error = self.execute_query(query)

            if error:
                return (
                    None,
                    f"Query Error: {error}",
                    True,
                    [],
                    [],
                    [],
                    [],
                    [],
                    None,
                    None,
                    None,
                )

            if df is None or df.empty:
                return (
                    None,
                    "Query returned no results.",
                    True,
                    [],
                    [],
                    [],
                    [],
                    [],
                    None,
                    None,
                    None,
                )

            table_data = df.to_dict("records")
            table_columns = [{"name": i, "id": i} for i in df.columns]
            column_options = [{"label": col, "value": col} for col in df.columns]

            # Set default values
            x_default = "start" if "start" in df.columns else None
            y_default = "duration" if "duration" in df.columns else None
            z_default = "name" if "name" in df.columns else None

            return (
                df.to_dict("records"),
                "",
                False,
                table_data,
                table_columns,
                column_options,
                column_options,
                column_options,
                x_default,
                y_default,
                z_default,
            )

        @self.app.callback(
            Output("plot-output", "figure"),
            [
                Input("dataframe-store", "data"),
                Input("x-dropdown", "value"),
                Input("y-dropdown", "value"),
                Input("z-dropdown", "value"),
                Input("plot-type", "value"),
            ],
        )
        def update_plot(data, x_col, y_col, z_col, plot_type):
            fig = px.scatter(
                title="Select data and columns to generate a plot"
            ).update_layout(template="plotly_white")

            if not data or not x_col:
                return fig

            df = pd.DataFrame(data)

            try:
                if plot_type == "histogram":
                    fig = px.histogram(df, x=x_col, title=f"Histogram of {x_col}")
                else:
                    if not y_col:
                        return fig

                    plot_func = px.scatter if plot_type == "scatter" else px.line
                    title = f"{plot_type.capitalize()} Plot: {y_col} vs {x_col}"
                    fig = plot_func(df, x=x_col, y=y_col, color=z_col, title=title)

                fig.update_layout(
                    template="plotly_white",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                )
                return fig
            except Exception as e:
                return px.scatter(title=f"Plotting Error: {e}").update_layout(
                    template="plotly_white"
                )

    def run(self, debug=True):
        self.app.run(debug=debug)


@click.command()
@click.option("--db-path", default=DEFAULT_DB, help="Path to the SQLite database.")
@click.option("--debug", is_flag=True, default=False, help="Run in debug mode.")
def main(db_path, debug):
    """Launch the spantom dashboard for viewing trace data."""
    app = SpantomApp(db_path)
    app.run(debug=debug)


if __name__ == "__main__":
    main()
