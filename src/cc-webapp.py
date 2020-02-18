#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_table
from dash.dependencies import Input, Output, State
import psycopg2 as pg
import pandas as pd

# Get passwords from environment variables
jdbc_password = os.environ['POSTGRES_PASSWORD']
jdbc_user = os.environ['POSTGRES_USER']
jdbc_host = os.environ['POSTGRES_DNS']

# table schema
column_names = ['host_name','country_code',
                'cookie_keyword','page_count']
col1, col2, col3, col4= column_names
table_name = r"cookie_table"

conn = pg.connect(host= jdbc_host,
                dbname="cookie_consent", user=jdbc_user, password=jdbc_password)

cur = conn.cursor()

# get list of country codes
cur.execute("""SELECT DISTINCT country_name FROM cookie_table;""")
country_name = cur.fetchall()
c = [i[0] for i in country_name]
c = c[2:]

# query for each country
def query(value):
    """
    Do query base on country name
    :param value: country name
    """
#    print(value)
    c_name = "'{value}'".format(value=value)
    cur.execute("""SELECT ROUND(100.0*(SUM
    (CASE WHEN {col3}!='None' 
    AND country_name={c_name} THEN 1 ELSE 0 END)::DECIMAL
    /COUNT({col1})),1) 
    AS percent_total 
    FROM cookie_consent;
    """.format(col1=col1,col3=col3,c_name=c_name))
    
    percent = float((cur.fetchall())[0][0])
    return [percent,100-percent]

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.layout =html.Div([
        html.Div(id = "centering_div",
    style={'text-align':'center'},
    children=[

        html.Div(id = "maindiv",
            className="mt-2",
            style={'width': '80%','max-width': '1600px','display': 'inline-block'},
            children=[

            html.H1(children='Cookie Consent'),

            html.Div(children='''
                Who complies with Privacy Act
                ''',
                style={'font-size':'18px'}
                )])]),
    html.Div([
        dcc.Dropdown(
            id='demo-dropdown',
            options=\
            [{'label': i, 'value': i} for i in c],
                    value='United States'
     
    ),
    html.Div(id='dd-output-container')
])

])

@app.callback(Output('dd-output-container', 'children'),
              [Input('demo-dropdown', 'value')])
def display_content(value):
    """
    generate pie chart
    """
    print(value)
    data = [
        {
            'values': query(value),
            'type': 'pie',
            'labels':['Yes','No']
        },
    ]

    return html.Div([
            
        dcc.Graph(
            id='graph',
            figure={
                'data': data,
                'layout': {
#                        'title':'Percentage of websites that comply with law',
                    'margin': {
                        'l': 30,'r': 0,'b': 30,'t': 30
                    },
                    'legend': {'x': 0, 'y': 1},
                    
                }
            }
        )
    ])

if __name__ == '__main__':
    app.run_server(host='0.0.0.0',port="8050")
    # app.run_server(debug=True)#,
