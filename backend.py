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

@app.route("/rules")
def rules_static():
    return render_template("/rules/index.html")

@app.route("/create-egg")
def create_egg_static():
    return render_template("/create-egg/index.html")

@app.route("/my-eggs")
def my_eggs_static():
    return render_template("/my-eggs/index.html")


@app.route("/api/list_eggs")
def list_eggs():
    with DB("db.db") as db:
        eggs = db.list_eggs()

    return jsonify([egg.model_dump(
        #exclude={"egg_id"}
        ) for egg in eggs]),200


@app.route("/api/user/<user_id>/my_eggs")
def my_eggs(user_id):
    with DB("db.db") as db:
        eggs = db.get_user_eggs(user_id)

    return jsonify([egg.model_dump(
        #exclude={"egg_id"}
        ) for egg in eggs]),200

@app.route("/api/redeem_egg", methods=['POST'])
def redeem_egg() -> tuple[Response, int]:

    egg_id = request.json.get("egg_id")
    user_id = request.json.get("user_id")

    response = {
        "success": False,
    }
    with DB("db.db") as db:
        success = db.redeem_egg(user_id,egg_id)
        if success:
            e = db.get_egg(egg_id)
            response['egg'] = e.model_dump()
        response['success'] = success
    return response,200


# added by dima;  adds a created egg to the db
@app.route("/api/create_egg", methods=['POST'])
def create_egg():
    data = request.json
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    user_id = data.get("user_id")
    name = data.get("name")
    hint = data.get("hint")
    texture = data.get("texture", "").encode()
    max_redeems = data.get("max_redeems", 1)

    if not all([user_id, name, hint, texture]):
        return jsonify({"error": "user_id, name, hint and texture are required"}), 400

    with DB("db.db") as db:
        success, egg_id = db.add_egg(
            name=name,
            hint=hint,
            author=user_id,
            texture=texture,
            max_redeems=max_redeems,
        )
    
    return jsonify({"success": success, "egg_id": egg_id}), 200


if __name__ == "__main__":
    app.run(debug=True)