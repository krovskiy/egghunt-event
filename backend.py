import base64
from hashlib import md5
from pathlib import Path

import dotenv
from flask import (
    Flask,
    Response,
    make_response,
    redirect,
    render_template,
    request,
)
from flask.json import jsonify
from requests import get, post

from db import DB

app = Flask(
    __name__, static_folder="./src", static_url_path="/", template_folder="./src"
)
FLASK_ROOT = app.root_path

CLIENT_ID = dotenv.dotenv_values(".env")["DISCORD_CLIENT_ID"]
CLIENT_SECRET = dotenv.dotenv_values(".env")["DISCORD_SECRET"]
REDIRECT_URI = dotenv.dotenv_values(".env")["REDIRECT_URI"]
CALLBACK_URI = "http://localhost:5000/callback/discord"


def verify_discord_token(access_token: str) -> tuple[bool, dict | None]:
    url = "https://discord.com/api/users/@me"
    headers = {"Authorization": f"Bearer {access_token}"}

    r = get(url, headers=headers)

    if r.status_code == 200:
        return True, r.json()  # token is valid → return user info
    return False, None  # token invalid or expired


def exchange_code(code: str) -> dict:
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": CALLBACK_URI,
    }

    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    response = post("https://discord.com/api/oauth2/token", data=data, headers=headers)
    return response.json()


@app.route("/login")
def login_redirect() -> Response:
    return redirect(
        REDIRECT_URI,
        302,
    )


@app.route("/callback/discord")
def auth() -> Response:
    resp = make_response(redirect("/"))
    token = exchange_code(request.args.get("code"))["access_token"]
    resp.set_cookie("discord_token", token)
    return resp

@app.route("/")
def index_static() -> str:
    return render_template("index.html")


@app.route("/rules")
def rules_static() -> str:
    return render_template("/rules/index.html")


@app.route("/create-egg")
def create_egg_static() -> str:
    return render_template("/create-egg/index.html")


@app.route("/my-eggs")
def my_eggs_static() -> str:
    return render_template("/my-eggs/index.html")


class TextureError(Exception):
    pass


def prepare_texture(base64_data: str) -> str:
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
        return texture_path.relative_to(FLASK_ROOT).as_posix()


@app.route("/api/list_eggs", methods=["GET"])
def list_eggs() -> tuple[Response, int]:
    with DB("db.db") as db:
        eggs = db.list_eggs()

    return jsonify([egg.model_dump(exclude={"egg_id"}) for egg in eggs]), 200


@app.route("/api/my_eggs", methods=["GET"])
def my_eggs() -> tuple[Response, int]:

    allowed, user_data = verify_discord_token(request.cookies.get("discord_token"))
    if not allowed:
        return jsonify({"error": "Invalid token"}), 401
    user_id = user_data["id"]

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


# added by dima;  adds a created egg to the db
@app.route("/api/create_egg", methods=["POST"])
def create_egg() -> tuple[Response, int]:
    data = request.json
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    user_id = data.get("user_id")
    name = data.get("name")
    hint = data.get("hint")
    texture = data.get("texture")
    max_redeems = data.get("max_redeems", 1)

    texture_path = prepare_texture(texture)

    if not all([user_id, name, hint, texture]):
        return jsonify({"error": "user_id, name, hint and texture are required"}), 400

    with DB("db.db") as db:
        success, egg_id = db.add_egg(
            name=name,
            hint=hint,
            author=user_id,
            texture=texture_path,
            max_redeems=max_redeems,
        )

    return jsonify({"success": success, "egg_id": egg_id}), 200


@app.route("/api/delete_egg/<egg_id>", methods=["DELETE"])
def delete_egg(egg_id: str) -> tuple[Response, int]:
    with DB("db.db") as db:
        db.delete_egg(egg_id)
    return jsonify({"success": True}), 200


@app.route("/api/like_egg", methods=["POST"])
def like_egg() -> tuple[Response, int]:
    data = request.json
    user_id = data.get("user_id")
    egg_id = data.get("egg_id")
    if not all([user_id, egg_id]):
        return jsonify({"error": "user_id and egg_id are required"}), 400

    with DB("db.db") as db:
        db.like_egg(user_id, egg_id)
        return jsonify({"success": True}), 200


@app.route("/api/dislike_egg", methods=["POST"])
def dislike_egg() -> tuple[Response, int]:
    data = request.json
    user_id = data.get("user_id")
    egg_id = data.get("egg_id")
    if not all([user_id, egg_id]):
        return jsonify({"error": "user_id and egg_id are required"}), 400

    with DB("db.db") as db:
        db.dislike_egg(user_id, egg_id)
        return jsonify({"success": True}), 200


if __name__ == "__main__":
    app.run(debug=True)  # noqa: S201
