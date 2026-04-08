import base64
from hashlib import md5
from pathlib import Path

import dotenv
from flask import Flask, request, Response
from flask.json import jsonify

from db import DB

DEFAULT_MAX_REDEEMS = str(dotenv.dotenv_values(".env")["DEFAULT_MAX_REDEEMS"])

app = Flask(__name__, static_folder="./textures")


class TextureError(Exception):
    pass


def prepare_texture(base64_data: str) -> Path:
    try:
        texture_parts = base64_data.split(";base64,")
        texture_type = texture_parts[0].split("image/")[-1]
        texture_data = base64.b64decode(texture_parts[1])
        texture_hash = md5(texture_data).hexdigest()  # noqa: S324
        texture_path = Path("textures") / f"{texture_hash}.{texture_type}"
        texture_path.write_bytes(texture_data)
    except Exception as e:
        msg = f"Failed to prepare texture: {e}"
        raise TextureError(msg) from e
    else:
        return texture_path


@app.route("/api/create_egg", methods=["POST"])
def create_egg() -> tuple[Response, int]:
    egg_name = request.json.get("egg_name")
    egg_hint = request.json.get("egg_hint")
    egg_author = request.json.get("egg_author")
    egg_texture = request.json.get("egg_texture")  # base64 encoded image
    user_id = request.json.get("user_id")
    max_redeems = request.json.get("max_redeems", DEFAULT_MAX_REDEEMS)

    if not egg_name or not egg_hint or not egg_texture:
        return jsonify({"error": "Missing required fields"}), 418

    if not egg_author and user_id:
        egg_author = user_id
    else:
        return jsonify({"error": "Missing an author or user_id"}), 418

    texture_path = prepare_texture(egg_texture)

    with DB("db.db") as db:
        success, egg_id = db.add_egg(
            name=egg_name,
            hint=egg_hint,
            author=egg_author,
            texture=str(texture_path.relative_to(".")),
            max_redeems=max_redeems,
        )

    return jsonify({"success": success, "egg_id": egg_id}), 200 if success else 400


@app.route("/api/list_eggs", methods=["GET"])
def list_eggs() -> tuple[Response, int]:
    with DB("db.db") as db:
        eggs = db.list_eggs()

    return jsonify([egg.model_dump(exclude={"egg_id"}) for egg in eggs]), 200


@app.route("/api/user/<user_id>/my_eggs", methods=["GET"])
def my_eggs(user_id: str) -> tuple[Response, int]:
    with DB("db.db") as db:
        eggs = db.get_user_eggs(user_id)

    return jsonify([egg.model_dump(exclude={"egg_id"}) for egg in eggs]), 200


@app.route("/api/redeem_egg", methods=["POST"])
def redeem_egg() -> tuple[Response, int]:
    egg_id = request.json.get("egg_id")
    user_id = request.json.get("user_id")
    response = {
        "success": False,
    }
    with DB("db.db") as db:
        success = db.redeem_egg(user_id, egg_id)
        if success:
            e = db.get_egg(egg_id)
            response["egg"] = e.model_dump()
        response["success"] = success
    return jsonify(response), 200


if __name__ == "__main__":
    app.run(debug=True)  # noqa: S201
