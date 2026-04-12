import base64
import logging
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
    send_from_directory,
    session,
)
from flask.json import jsonify
from requests import get, post

from db import DB
from rate_limiter import rate_limit, get_rate_limiter  # NEW: Import rate limiter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

app = Flask(
    __name__, static_folder="./src/assets", static_url_path="/egghunt/assets", template_folder="./src"
)

from werkzeug.middleware.proxy_fix import ProxyFix

app.wsgi_app = ProxyFix(app.wsgi_app, x_prefix=1)
FLASK_ROOT = app.root_path

CLIENT_ID = dotenv.dotenv_values(".env")["DISCORD_CLIENT_ID"]
CLIENT_SECRET = dotenv.dotenv_values(".env")["DISCORD_SECRET"]
REDIRECT_URI = dotenv.dotenv_values(".env")["REDIRECT_URI"]
CALLBACK_URI = dotenv.dotenv_values(".env")["CALLBACK_URI"]


# store ttl and in session - DIMA
# i actually have no idea how good this is the way by using flask -> session
app.secret_key = dotenv.dotenv_values(".env")["SECRET_KEY"]

# ttl - temporary cache tuple, needs to be purged after it gets filled. TODO: add purge
_token_cache: dict[str, tuple[dict, float]] = {}
CACHE_TTL = 300
CACHE_MAX_SIZE = 1000  # FIX: prevent unbounded growth

# file prepare texture
ALLOWED_IMAGE_TYPES = {
    "png",
    "jpeg",
    "jpg",
    "gif",
    "webp",
}  # FIX: whitelist image types
MAX_TEXTURE_BYTES = 5 * 1024 * 1024
MAX_NAME_LEN = 60
MAX_HINT_LEN = 280
MAX_REWARD_LEN = 140
MAX_REDEEMS_LIMIT = 99
DEFAULT_AVATAR = "https://cdn.discordapp.com/embed/avatars/0.png"
REQUEST_TIMEOUT = 5
MAX_TEXTURE_REPEAT = 5
COOKIE_SECURE = dotenv.dotenv_values(".env").get("COOKIE_SECURE", "0") == "1"
BASE_PATH = "/egghunt"

_leaderboard_cache: dict[str, tuple[dict, float]] = {"data": None, "expires": 0}

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
    try:
        r = get(
            "https://discord.com/api/users/@me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=REQUEST_TIMEOUT,
        )
    except Exception as e:
        logger.error(f"Failed to connect to Discord API: {e}")
        return False, None

    # store that shit in token cache
    if r.status_code == 200:
        user_data = r.json()
        # FIX: evict before inserting to cap cache size
        if len(_token_cache) >= CACHE_MAX_SIZE:
            _evict_expired_tokens()
        _token_cache[access_token] = (user_data, now + CACHE_TTL)
        return True, user_data

    logger.warning(f"Discord API returned status {r.status_code}: {r.text}")
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

    try:
        response = post(
            "https://discord.com/api/oauth2/token",
            data=data,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
    except Exception as e:
        logger.error(f"Failed to connect to Discord token exchange: {e}")
        return None

    # FIX: return None on OAuth errors instead of raising KeyError later
    payload = response.json()
    if "access_token" not in payload:
        logger.warning(f"Discord token exchange failed: {payload}")
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
        return redirect(f"{BASE_PATH}/login", 302)

    # FIX: handle failed exchange gracefully
    token_data = exchange_code(code)
    if not token_data:
        logger.error("OAuth code exchange failed")
        return redirect(f"{BASE_PATH}/login?error=oauth_failed", 302)

    token = token_data["access_token"]

    ok, user_data = verify_discord_token(token)
    if not ok or user_data is None:
        logger.error("Failed to verify Discord token after exchange")
        return redirect(f"{BASE_PATH}/login?error=token_invalid", 302)

    # FIX: clear any stale session before setting new user
    session.clear()
    session["user"] = user_data
    logger.info(f"User logged in: {user_data.get('username')} ({user_data.get('id')})")

    resp = make_response(redirect(f"{BASE_PATH}/"))
    resp.set_cookie(
        "discord_token", token, httponly=True, samesite="Lax", secure=COOKIE_SECURE
    )
    return resp


@app.route("/")
def index_static() -> str:
    return render_template("index.html")


@app.route("/rules")
def rules_static() -> str:
    return render_template("/rules/index.html")


@app.route("/create-egg")
def create_egg_static() -> str:
    allowed, _ = get_current_user(request)
    if not allowed:
        return redirect(f"{BASE_PATH}/login", 302)
    edit_id = request.args.get("edit")
    return render_template("/create-egg/index.html", edit_id=edit_id)


@app.route("/my-eggs")
def my_eggs_static() -> str:
    allowed, _ = get_current_user(request)
    if not allowed:
        return redirect(f"{BASE_PATH}/login", 302)
    return render_template("/my-eggs/index.html")


@app.route("/leaderboard")
def leaderboard_static() -> str:
    return render_template("/leaderboard/index.html")


@app.route("/textures/<path:filename>")
def texture_file(filename: str) -> Response:
    texture_dir = Path(FLASK_ROOT) / "src" / "textures"
    return send_from_directory(texture_dir, filename)


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

        texture_path = (
            texture_dir / f"{texture_hash}.{texture_type}"
        )  # path creation in case there is not
        texture_path.write_bytes(texture_data)
    except Exception as e:
        msg = f"Failed to prepare texture: {e}"
        raise TextureError(msg) from e
    else:
        return texture_path.relative_to(Path(FLASK_ROOT) / "src").as_posix()


def _normalize_text(
    value: object, field_name: str, max_len: int, allow_empty: bool = False
) -> tuple[str | None, str | None]:
    if value is None:
        return None, f"{field_name} is required"
    if not isinstance(value, str):
        return None, f"{field_name} must be a string"

    text = value.strip()
    if not text and not allow_empty:
        return None, f"{field_name} is required"
    if len(text) > max_len:
        return None, f"{field_name} is too long (max {max_len} chars)"
    if "<" in text or ">" in text:
        return None, f"{field_name} contains invalid characters"
    if "\x00" in text:
        return None, f"{field_name} contains invalid characters"

    return text, None


def _parse_max_redeems(value: object) -> tuple[int | None, str | None]:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None, "max_redeems must be a number"

    if parsed < 1:
        return None, "max_redeems must be at least 1"
    if parsed > MAX_REDEEMS_LIMIT:
        return None, f"max_redeems must be at most {MAX_REDEEMS_LIMIT}"

    return parsed, None


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item for item in value.split(",") if item]


def _avatar_url(user_id: str | None, avatar_hash: str | None) -> str:
    if not user_id or not avatar_hash:
        return DEFAULT_AVATAR
    ext = "gif" if avatar_hash.startswith("a_") else "png"
    return f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.{ext}"

def get_leaderboard_cached(limit: int = 5, ttl: int = 60) -> dict:
    """Cache leaderboard results for TTL seconds."""
    now = time.time()
    
    # Return cached result if still fresh
    if (
        _leaderboard_cache["data"] is not None
        and now < _leaderboard_cache["expires"]
    ):
        return _leaderboard_cache["data"]
    
    # Recompute (your logic here)
    likes_by_author: dict[str, int] = {}
    redeemed_by_user: dict[str, int] = {}
    user_meta: dict[str, dict[str, str]] = {}
    
    with DB("db.db") as db:
        rows = db.get_leaderboard_source()
    
    for author_id, author, author_avatar, liked_users, redeemed_users in rows:
        if author_id:
            user_meta[author_id] = {
                "name": author or "Unknown",
                "avatar": _avatar_url(author_id, author_avatar),
            }
        
        like_count = len(_split_csv(liked_users))
        if author_id:
            likes_by_author[author_id] = likes_by_author.get(author_id, 0) + like_count
        
        for user_id in _split_csv(redeemed_users):
            redeemed_by_user[user_id] = redeemed_by_user.get(user_id, 0) + 1
    
    top_likes = sorted(likes_by_author.items(), key=lambda x: x[1], reverse=True)[:limit]
    top_redeems = sorted(redeemed_by_user.items(), key=lambda x: x[1], reverse=True)[:limit]
    
    likes_payload = [
        {
            "user_id": uid,
            "name": user_meta.get(uid, {}).get("name", uid),
            "avatar": user_meta.get(uid, {}).get("avatar", DEFAULT_AVATAR),
            "total": total,
        }
        for uid, total in top_likes
    ]
    
    redeems_payload = [
        {
            "user_id": uid,
            "name": user_meta.get(uid, {}).get("name", uid),
            "avatar": user_meta.get(uid, {}).get("avatar", DEFAULT_AVATAR),
            "total": total,
        }
        for uid, total in top_redeems
    ]
    
    result = {
        "top_likes": likes_payload,
        "top_redeems": redeems_payload,
    }
    
    _leaderboard_cache["data"] = result
    _leaderboard_cache["expires"] = now + ttl
    return result


@app.route("/api/list_eggs", methods=["GET"])
def list_eggs() -> tuple[Response, int]:
    allowed, user_data = get_current_user(request)
    user_id = user_data["id"] if allowed and user_data else None

    limit = request.args.get("limit", type=int)
    offset = request.args.get("offset", default=0, type=int)

    with DB("db.db") as db:
        eggs = db.list_eggs()
        if limit is not None:
            eggs = eggs[offset : offset + limit]
        redeemed_ids = set()
        if user_id:
            redeemed = db.get_user_eggs(user_id)
            redeemed_ids = {egg.egg_id for egg in redeemed}

    payload = []
    for egg in eggs:
        data = egg.model_dump(exclude={"salted_hash"})
        data["redeemed_by_me"] = egg.egg_id in redeemed_ids
        payload.append(data)

    return jsonify(payload), 200


@app.route("/api/list_eggs_by_feedback", methods=["GET"])
def list_eggs_by_feedback() -> tuple[Response, int]:
    allowed, user_data = get_current_user(request)
    user_id = user_data["id"] if allowed and user_data else None

    limit = request.args.get("limit", type=int)
    offset = request.args.get("offset", default=0, type=int)

    with DB("db.db") as db:
        results = db.list_eggs_by_feedback(limit=limit, offset=offset)
        redeemed_ids = set()
        if user_id:
            redeemed = db.get_user_eggs(user_id)
            redeemed_ids = {egg.egg_id for egg in redeemed}

    payload = []
    for row in results:
        egg = row["egg"]
        data = egg.model_dump()
        data["redeemed_by_me"] = egg.egg_id in redeemed_ids
        data["likes"] = row["like_count"]
        data["dislikes"] = row["dislike_count"]
        payload.append(data)

    return jsonify(payload), 200

@app.route("/api/leaderboard", methods=["GET"])
def leaderboard() -> tuple[Response, int]:
    limit = request.args.get("limit", default=5, type=int)
    return jsonify(get_leaderboard_cached(limit=limit)), 200


@app.route("/api/my_eggs", methods=["GET"])
@rate_limit(limit=60)  # NEW: 60 requests per minute per user
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
@rate_limit(limit=60)  # NEW: 60 requests per minute per user
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
@rate_limit(limit=60)  # NEW: 60 requests per minute per user
def egg_detail(egg_id: str) -> tuple[Response, int]:

    allowed, user_data = get_current_user(request)
    if not allowed:
        return jsonify({"error": "Invalid token"}), 401
    user_id = user_data["id"]

    with DB("db.db") as db:
        egg = db.get_egg(egg_id)
        if not egg:
            return jsonify({"error": "Egg not found"}), 404

    if egg.author_id != user_id:
        return jsonify({"error": "Forbidden"}), 403

    return jsonify(egg.model_dump()), 200


@app.route("/api/redeem_egg", methods=["POST"])
@rate_limit(limit=30)  # NEW: 30 requests per minute per user (DB state change)
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
        if not db.get_created_eggs(user_id):
            return jsonify({"error": "Create at least one egg before redeeming."}), 403
        if not db.get_egg(egg_id):
            return jsonify({"error": "Egg not found"}), 404
        success = db.redeem_egg(user_id, egg_id)
        if success:
            e = db.get_egg(egg_id)
            response["egg"] = e.model_dump()
        response["success"] = success
    return jsonify(response), 200


@app.route("/redeem_egg/<salted_hash>")
@rate_limit(limit=30)  # NEW: 30 requests per minute per user
def redeem_egg_public(salted_hash: str) -> Response:
    """Redeem an egg via its public salted hash and redirect to /my_eggs."""
    allowed, user_data = get_current_user(request)
    if not allowed:
        return redirect(f"{BASE_PATH}/login", 302)

    user_id = user_data["id"]

    try:
        with DB("db.db") as db:
            if not db.get_created_eggs(user_id):
                return redirect(f"{BASE_PATH}/my-eggs?error=must_create", 302)
            egg = db.get_egg_by_hash(salted_hash)
            if not egg:
                return redirect(f"{BASE_PATH}/my-eggs?error=invalid_egg", 302)
            success = db.redeem_egg(user_id, egg.egg_id)
    except Exception as exc:
        logger.exception(f"Redeem failed for user {user_id} with hash {salted_hash}")
        return redirect(f"{BASE_PATH}/my-eggs?error=invalid_egg", 302)

    if success:
        logger.info(f"User {user_id} successfully redeemed egg with hash {salted_hash}")
        return redirect(f"{BASE_PATH}/my-eggs?redeemed=true", 302)
    logger.warning(f"User {user_id} failed to redeem egg with hash {salted_hash}")
    return redirect(f"{BASE_PATH}/my-eggs?error=redeem_failed", 302)


# added by dima;  adds a created egg to the db
@app.route("/api/create_egg", methods=["POST"])
@rate_limit(limit=20)  # NEW: 20 requests per minute per user (file upload + DB write)
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
    texture_size = data.get("textureSize", 1)
    reward = data.get("reward", "")

    # FIX: extract author info from verified Discord token
    user_id = user_data["id"]
    author_name = user_data.get("username", "Unknown")
    author_avatar = user_data.get("avatar", "")

    if not all([user_id, name, hint, texture]):
        return jsonify({"error": "name, hint and texture are required"}), 400

    name, name_error = _normalize_text(name, "name", MAX_NAME_LEN)
    if name_error:
        return jsonify({"error": name_error}), 400

    hint, hint_error = _normalize_text(hint, "hint", MAX_HINT_LEN)
    if hint_error:
        return jsonify({"error": hint_error}), 400

    reward, reward_error = _normalize_text(
        reward, "reward", MAX_REWARD_LEN, allow_empty=True
    )
    if reward_error:
        return jsonify({"error": reward_error}), 400

    max_redeems, max_redeems_error = _parse_max_redeems(max_redeems)
    if max_redeems_error:
        return jsonify({"error": max_redeems_error}), 400

    try:
        texture_size = int(texture_size)
    except (TypeError, ValueError):
        return jsonify({"error": "textureSize must be a number"}), 400
    if texture_size < 1 or texture_size > MAX_TEXTURE_REPEAT:
        return jsonify(
            {"error": f"textureSize must be between 1 and {MAX_TEXTURE_REPEAT}"}
        ), 400

    # FIX: file written before the check above ^
    try:
        texture_path = prepare_texture(texture)
    except TextureError as e:
        return jsonify({"error": str(e)}), 400

    with DB("db.db") as db:
        created_eggs = db.get_created_eggs(user_id)
        if len(created_eggs) >= 10:
            return jsonify(
                {"error": f"Maximum of 10 eggs per user allowed"}
            ), 403
        success, egg_id = db.add_egg(
            name=name,
            hint=hint,
            author_id=user_id,
            author=author_name,
            author_avatar=author_avatar,
            texture=texture_path,
            max_redeems=max_redeems,
            textureSize=texture_size,
            reward=reward,
        )

    return jsonify({"success": success, "egg_id": egg_id}), 200


# route to update an egg with new information by dima
@app.route("/api/update_egg/<egg_id>", methods=["PUT"])
@rate_limit(limit=30)  # NEW: 30 requests per minute per user (file processing)
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
    texture_size = data.get("textureSize")
    texture = data.get("texture")
    reward = data.get("reward", "")

    if not all([name, hint]):
        return jsonify({"error": "name and hint are required"}), 400

    name, name_error = _normalize_text(name, "name", MAX_NAME_LEN)
    if name_error:
        return jsonify({"error": name_error}), 400

    hint, hint_error = _normalize_text(hint, "hint", MAX_HINT_LEN)
    if hint_error:
        return jsonify({"error": hint_error}), 400

    reward, reward_error = _normalize_text(
        reward, "reward", MAX_REWARD_LEN, allow_empty=True
    )
    if reward_error:
        return jsonify({"error": reward_error}), 400

    max_redeems, max_redeems_error = _parse_max_redeems(max_redeems)
    if max_redeems_error:
        return jsonify({"error": max_redeems_error}), 400

    with DB("db.db") as db:
        egg = db.get_egg(egg_id)
        if not egg:
            return jsonify({"error": "Egg not found"}), 404
        old_texture = egg.texture
        if egg.author_id != user_id:
            return jsonify({"error": "Forbidden"}), 403

        if texture_size is None:
            texture_size = egg.textureSize
        else:
            try:
                texture_size = int(texture_size)
            except (TypeError, ValueError):
                return jsonify({"error": "textureSize must be a number"}), 400
            if texture_size < 1 or texture_size > MAX_TEXTURE_REPEAT:
                return jsonify(
                    {"error": f"textureSize must be between 1 and {MAX_TEXTURE_REPEAT}"}
                ), 400

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
            reward=reward,
        )
        # FIX remove old textures after new one is applied
        if (
            success
            and texture
            and old_texture != texture_path
            and db.count_texture_usage(old_texture) == 0
        ):
            try:
                old_path = Path(FLASK_ROOT) / "src" / old_texture
                if old_path.exists():
                    old_path.unlink()
            except Exception as e:
                logger.warning(f"Warning: couldn't delete old texture {old_texture}: {e}")

    return jsonify({"success": success, "egg_id": egg_id}), 200


@app.route("/api/delete_egg/<egg_id>", methods=["DELETE"])
@rate_limit(limit=40)  # NEW: 40 requests per minute per user (file cleanup)
def delete_egg(egg_id: str) -> tuple[Response, int]:
    allowed, user_data = get_current_user(request)
    if not allowed:
        return jsonify({"error": "Invalid token"}), 401
    user_id = user_data["id"]

    with DB("db.db") as db:
        egg = db.get_egg(egg_id)
        if not egg:
            return jsonify({"error": "Egg not found"}), 404
        if egg.author_id != user_id:
            return jsonify({"error": "Forbidden"}), 403
        db.delete_egg(egg_id)

        if egg.texture and db.count_texture_usage(egg.texture) == 0:
            try:
                texture_path = Path(FLASK_ROOT) / "src" / egg.texture
                if texture_path.exists():
                    texture_path.unlink()
            except Exception as e:
                logger.warning(f"Warning: couldn't delete texture {egg.texture}: {e}")

    return jsonify({"success": True}), 200


@app.route("/api/like_egg", methods=["POST"])
@rate_limit(limit=60)  # NEW: 60 requests per minute per user (prevent spam)
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
@rate_limit(limit=60)  # NEW: 60 requests per minute per user (prevent spam)
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

    return jsonify(
        {
            "id": user_data["id"],
            "username": user_data["username"],
            "global_name": user_data.get("global_name"),
            "avatar": user_data["avatar"],
        }
    ), 200


@app.route("/logout")
def logout():
    # FIX: clear the server-side session as well as the cookie
    session.clear()
    resp = make_response(redirect(f"{BASE_PATH}/"))
    resp.set_cookie("discord_token", "", expires=0, path="/")
    return resp


# NEW: Periodic cleanup of rate limiter cache
@app.before_request
def cleanup_rate_limiter_cache():
    """Clean up expired rate limit entries periodically (every hour)."""
    if not hasattr(cleanup_rate_limiter_cache, 'last_cleanup'):
        cleanup_rate_limiter_cache.last_cleanup = time.time()
    
    now = time.time()
    if now - cleanup_rate_limiter_cache.last_cleanup > 3600:  # Every hour
        limiter = get_rate_limiter()
        limiter.cleanup(max_age=3600)
        cleanup_rate_limiter_cache.last_cleanup = now


@app.after_request
def set_cache_headers(response: Response) -> Response:
    """Set HTTP cache headers for static assets and immutable textures."""
    if request.path.startswith('/textures/'):
        response.cache_control.max_age = 86400 * 30  
        response.cache_control.public = True

    elif request.path.startswith('/assets/'):
        response.cache_control.max_age = 86400  
    return response


if __name__ == "__main__":
    app.run(debug=True)  # noqa: S201