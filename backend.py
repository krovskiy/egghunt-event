from flask import Flask, request
from flask.json import jsonify

from db import DB
app = Flask(__name__)


@app.route("/api/list_eggs")
def list_eggs():
    with DB("db.db") as db:
        eggs = db.list_eggs()

    return jsonify([egg.model_dump(exclude={"egg_id"}) for egg in eggs]),200


@app.route("/api/user/<user_id>/my_eggs")
def my_eggs(user_id):
    with DB("db.db") as db:
        eggs = db.get_user_eggs(user_id)

    return jsonify([egg.model_dump(exclude={"egg_id"}) for egg in eggs]),200

@app.route("/api/redeem_egg")
def redeem_egg():
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


if __name__ == "__main__":
    app.run(debug=True)