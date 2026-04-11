import base64
import time
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
    session,
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


# store ttl and in session - DIMA
# i actually have no idea how good this is the way by using flask -> session
app.secret_key = dotenv.dotenv_values(".env")["SECRET_KEY"]

# ttl - temporary cache tuple, needs to be purged after it gets filled. TODO: add purge
_token_cache: dict[str, tuple[dict, float]] = {}
CACHE_TTL = 300
CACHE_MAX_SIZE = 1000  # FIX: prevent unbounded growth

# file prepare texture
ALLOWED_IMAGE_TYPES = {"png", "jpeg", "jpg", "gif", "webp"}  # FIX: whitelist image types
MAX_TEXTURE_BYTES = 5 * 1024 * 1024

def _evict_expired_tokens() -> None:
    """FIX: sweep expired entries instead of only evicting on hit."""
    now = time.time()
    expired = [k for k, (_, exp) in _token_cache.items() if now >= exp]
    for k in expired:
        del _token_cache[k]

def verify_discord_token(access_token: str) -> tuple[bool, dict | None]:
    now = time.time()

    # return cached result if still fresh or somethin
    if access_token in _token_cache:
        user_data, expires_at = _token_cache[access_token]
        if now < expires_at:
            return True, user_data
        del _token_cache[access_token]

    # otherwise hit discord
    r = get("https://discord.com/api/users/@me",
            headers={"Authorization": f"Bearer {access_token}"})

    # store that shit in token cache
    if r.status_code == 200:
        user_data = r.json()
        # FIX: evict before inserting to cap cache size
        if len(_token_cache) >= CACHE_MAX_SIZE:
            _evict_expired_tokens()
        _token_cache[access_token] = (user_data, now + CACHE_TTL)
        print(_token_cache)
        return True, user_data

    return False, None

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
    # FIX: return None on OAuth errors instead of raising KeyError later
    payload = response.json()
    if "access_token" not in payload:
        return None
    return payload


# replace verify_discord_token because it is too slow with this. short - stores token in session
def get_current_user(req) -> tuple[bool, dict | None]:
    # FIX: actually use the session cache so it isn't dead code
    if "user" in session:
        return True, session["user"]
    token = req.cookies.get("discord_token")
    if not token:
        return False, None
    ok, user_data = verify_discord_token(token)
    if ok:
        session["user"] = user_data
    return ok, user_data

@app.route("/login")
def login_redirect() -> Response:
    return redirect(
        REDIRECT_URI,
        302,
    )


@app.route("/callback/discord")
def auth() -> Response:
    code = request.args.get("code")
    if not code:
        return redirect("/login", 302)
 
    # FIX: handle failed exchange gracefully
    token_data = exchange_code(code)
    if not token_data:
        return redirect("/login?error=oauth_failed", 302)
 
    token = token_data["access_token"]
 
    ok, user_data = verify_discord_token(token)
    if not ok or user_data is None:
        return redirect("/login?error=token_invalid", 302)
 
    # FIX: clear any stale session before setting new user
    session.clear()
    session["user"] = user_data
 
    resp = make_response(redirect("/"))
    resp.set_cookie("discord_token", token, httponly=True, samesite="Lax")
    return resp

@app.route("/")
def index_static() -> str:
    return render_template("index.html")


@app.route("/rules")
def rules_static() -> str:
    return render_template("/rules/index.html")


@app.route("/create-egg")
def create_egg_static() -> str:
    edit_id = request.args.get("edit")
    return render_template("/create-egg/index.html", edit_id=edit_id)


@app.route("/my-eggs")
def my_eggs_static() -> str:
    return render_template("/my-eggs/index.html")


class TextureError(Exception):
    pass

def prepare_texture(base64_data: str) -> str:
    try:
        texture_parts = base64_data.split(";base64,")
        if len(texture_parts) != 2:
            raise ValueError("Invalid base64 data URI format")
 
        raw_type = texture_parts[0].split("image/")[-1].lower().strip()
 
        # FIX: whitelist allowed image types to prevent arbitrary file uploads
        if raw_type not in ALLOWED_IMAGE_TYPES:
            raise ValueError(f"Unsupported image type: {raw_type!r}")

        # normalize jpeg
        texture_type = "jpg" if raw_type == "jpeg" else raw_type
        texture_data = base64.b64decode(texture_parts[1])
        if len(texture_data) > MAX_TEXTURE_BYTES:
            raise ValueError("Texture exceeds maximum allowed size (ALLOCATED 5 MB)")
        texture_hash = md5(texture_data).hexdigest()  # noqa: S324
        texture_dir = Path(FLASK_ROOT) / "src" / "textures"
        texture_dir.mkdir(parents=True, exist_ok=True)

        texture_path = texture_dir / f"{texture_hash}.{texture_type}"  # path creation in case there is not
        texture_path.write_bytes(texture_data)
    except Exception as e:
        msg = f"Failed to prepare texture: {e}"
        raise TextureError(msg) from e
    else:
        return texture_path.relative_to(Path(FLASK_ROOT) / "src").as_posix()


@app.route("/api/list_eggs", methods=["GET"])
def list_eggs() -> tuple[Response, int]:
    with DB("db.db") as db:
        eggs = db.list_eggs()

    return jsonify([egg.model_dump(exclude={"egg_id"}) for egg in eggs]), 200


@app.route("/api/my_eggs", methods=["GET"])
def my_eggs() -> tuple[Response, int]:

    # FIX: use get_current_user so session cache is respected
    allowed, user_data = get_current_user(request)
    if not allowed:
        return jsonify({"error": "Invalid token"}), 401
    user_id = user_data["id"]
 
    with DB("db.db") as db:
        eggs = db.get_user_eggs(user_id)
    return jsonify([egg.model_dump(exclude={"egg_id"}) for egg in eggs]), 200

# routes for created_eggs by USER by dima
@app.route("/api/created_eggs", methods=["GET"])
def created_eggs() -> tuple[Response, int]:

    allowed, user_data = get_current_user(request)
    if not allowed:
        return jsonify({"error": "Invalid token"}), 401
    user_id = user_data["id"]

    with DB("db.db") as db:
        eggs = db.get_created_eggs(user_id)

    return jsonify([egg.model_dump() for egg in eggs]), 200

# loads egg for EDIT
@app.route("/api/egg/<egg_id>", methods=["GET"])
def egg_detail(egg_id: str) -> tuple[Response, int]:

    allowed, user_data = get_current_user(request)
    if not allowed:
        return jsonify({"error": "Invalid token"}), 401
    user_id = user_data["id"]

    with DB("db.db") as db:
        egg = db.get_egg(egg_id)

    if egg.author_id != user_id:
        return jsonify({"error": "Forbidden"}), 403

    return jsonify(egg.model_dump()), 200


@app.route("/api/redeem_egg", methods=["POST"])
def redeem_egg() -> tuple[Response, int]:
    # FIX: authenticate the request; reject user_id from the body
    allowed, user_data = get_current_user(request)
    if not allowed:
        return jsonify({"error": "Invalid token"}), 401
 
    egg_id = request.json.get("egg_id")
    if not egg_id:
        return jsonify({"error": "egg_id is required"}), 400
 
    # FIX: use the verified identity, not a client-supplied user_id
    user_id = user_data["id"]

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
    # FIX: require authentication; don't trust user_id from the body
    allowed, user_data = get_current_user(request)
    if not allowed:
        return jsonify({"error": "Invalid token"}), 401
    

    data = request.json
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    name = data.get("name")
    hint = data.get("hint")
    texture = data.get("texture")
    max_redeems = data.get("max_redeems", 1)
    texture_size = data.get("textureSize", 0)
 
    # FIX: extract author info from verified Discord token
    user_id = user_data["id"]
    author_name = user_data.get("username", "Unknown")
    author_avatar = user_data.get("avatar", "")

    if not all([user_id, name, hint, texture]):
        return jsonify({"error": "name, hint and texture are required"}), 400

    # FIX: file written before the check above ^
    try:
        texture_path = prepare_texture(texture)
    except TextureError as e:
        return jsonify({"error": str(e)}), 400
    
    with DB("db.db") as db:
        success, egg_id = db.add_egg(
            name=name,
            hint=hint,
            author_id=user_id,
            author=author_name,
            author_avatar=author_avatar,
            texture=texture_path,
            max_redeems=max_redeems,
            textureSize=texture_size,
        )

    return jsonify({"success": success, "egg_id": egg_id}), 200

# route to update an egg with new information by dima
@app.route("/api/update_egg/<egg_id>", methods=["PUT"])
def update_egg(egg_id: str) -> tuple[Response, int]:

    allowed, user_data = get_current_user(request)
    if not allowed:
        return jsonify({"error": "Invalid token"}), 401
    user_id = user_data["id"]

    data = request.json
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    name = data.get("name")
    hint = data.get("hint")
    max_redeems = data.get("max_redeems", 1)
    texture_size = data.get("textureSize", 0)
    texture = data.get("texture")

    if not all([name, hint]):
        return jsonify({"error": "name and hint are required"}), 400

    with DB("db.db") as db:
        egg = db.get_egg(egg_id)
        if egg.author_id != user_id:
            return jsonify({"error": "Forbidden"}), 403

        # FIX: resolve texture path if provided
        texture_path = texture if texture else egg.texture
        if texture:
            try:
                texture_path = prepare_texture(texture)
            except TextureError as e:
                return jsonify({"error": str(e)}), 400

        author_name = user_data.get("username", egg.author)
        author_avatar = user_data.get("avatar", egg.author_avatar)

        success = db.update_egg(
            egg_id=egg_id,
            name=name,
            hint=hint,
            author_id=user_id,
            author=author_name,
            author_avatar=author_avatar,
            max_redeems=max_redeems,
            texture=texture_path,
            textureSize=texture_size,
        )

    return jsonify({"success": success, "egg_id": egg_id}), 200


@app.route("/api/delete_egg/<egg_id>", methods=["DELETE"])
def delete_egg(egg_id: str) -> tuple[Response, int]:
    allowed, user_data = get_current_user(request)
    if not allowed:
        return jsonify({"error": "Invalid token"}), 401
    user_id = user_data["id"]
 
    with DB("db.db") as db:
        egg = db.get_egg(egg_id)
        if egg.author_id != user_id:
            return jsonify({"error": "Forbidden"}), 403
        db.delete_egg(egg_id)
 
    return jsonify({"success": True}), 200


@app.route("/api/like_egg", methods=["POST"])
def like_egg() -> tuple[Response, int]:
    allowed, user_data = get_current_user(request)
    if not allowed:
        return jsonify({"error": "Invalid token"}), 401
 
    data = request.json
    egg_id = data.get("egg_id")
    if not egg_id:
        return jsonify({"error": "egg_id is required"}), 400
 
    user_id = user_data["id"]
    with DB("db.db") as db:
        db.like_egg(user_id, egg_id)
    return jsonify({"success": True}), 200


@app.route("/api/dislike_egg", methods=["POST"])
def dislike_egg() -> tuple[Response, int]:
    # FIX: use authenticated identity
    allowed, user_data = get_current_user(request)
    if not allowed:
        return jsonify({"error": "Invalid token"}), 401
 
    data = request.json
    egg_id = data.get("egg_id")
    if not egg_id:
        return jsonify({"error": "egg_id is required"}), 400
 
    user_id = user_data["id"]
    with DB("db.db") as db:
        db.dislike_egg(user_id, egg_id)
    return jsonify({"success": True}), 200


# add by dima, log in function -> returns: image, username, global_name FOR TESTING
@app.route("/api/me")
def me() -> tuple[Response, int]:

    token = request.cookies.get("discord_token")
    if not token:
        return jsonify({"error": "No token"}), 401

    allowed, user_data = get_current_user(request)

    if not allowed:
        return jsonify({"error": "Invalid token"}), 401

    return jsonify({
        "id": user_data["id"],
        "username": user_data["username"],
        "global_name": user_data.get("global_name"),
        "avatar": user_data["avatar"]
    }), 200

@app.route("/logout")
def logout():
    # FIX: clear the server-side session as well as the cookie
    session.clear()
    resp = make_response(redirect("/"))
    resp.set_cookie("discord_token", "", expires=0, path="/")
    return resp

if __name__ == "__main__":
    app.run(debug=True)  # noqa: S201
