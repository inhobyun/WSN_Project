# WSN_Project

## How to setup virtual environment

Setup **venv**.

```bash
python -m venv ./env
```

Install all dependencies. (Install module stuffs after activating **venv**)

```bash
pip install -r requirements.txt
```

## How to run

Activate **venv**.

```bash
source ./env/bin/activate
```

or in Windows:

```cmd
\env\Scripts\activate.bat
```

And then, run server.

```bash
python app.py
```

## Check out these documents

- Web framework: Flask 
    - https://flask.palletsprojects.com/en/1.1.x/quickstart/
- Web page template rendering: Jinja2
    - https://jinja.palletsprojects.com/en/2.11.x/
- JavaScript Chart: D3.js
    - https://www.d3-graph-gallery.com/graph/line_basic.html
- Serving Flask-based Apps: Gunicorn & nginx
    - https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-gunicorn-and-nginx-on-ubuntu-18-04
