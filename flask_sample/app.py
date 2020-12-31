"""
Starting of sensor data monitoring and analysis application -- 2020/10/01
"""
import json
import math
from flask import Flask, redirect, request
from jinja2 import Environment, PackageLoader, Markup, select_autoescape

app = Flask(__name__)
env = Environment(
    loader=PackageLoader(__name__, 'templates'),
    autoescape=select_autoescape(['html', 'xml'])
)

@app.route('/')
def root():
    template = env.get_template('landing.html')
    return template.render()

@app.route('/dashboard')
def dashboard():
    template = env.get_template('dashboard.html')
    return template.render()

@app.route('/Ooops')
def Ooops():
    template = env.get_template('Ooops.html')
    return template.render()

@app.route('/post_test', methods=['POST'])
def post_test():
    data = json.loads(request.data)
    value = data['value']

    # Prepare data to send in here.
    x = []
    y = []
    for i in range(100):
        # Sine value for example.
        curr_x = float(i / 10)
        x.append(curr_x)
        y.append(math.sin(curr_x) * value)
    
    return json.dumps({ 'x': x, 'y': y })

if __name__ == '__main__':
    app.run(debug=True)