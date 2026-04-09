import base64
from hashlib import md5
from pathlib import Path

import dotenv
from flask import Flask, request, Response, render_template
from flask.json import jsonify

from db import DB
app = Flask(__name__, static_folder='./src', static_url_path='/', template_folder='./src')


@app.route("/")
def index_static():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)  # noqa: 