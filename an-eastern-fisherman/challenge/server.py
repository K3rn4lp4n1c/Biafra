from flask import Flask, jsonify, make_response, render_template, request, send_from_directory, url_for, g, session
from flask_login import LoginManager, login_user, login_required, UserMixin, current_user
from flask_session import Session
from werkzeug.utils import secure_filename
from functools import wraps
from pathlib import Path

import os
import json
import py7zr
import logging
import secrets

from helpers.compile import compile_code
from helpers.auth import verify_credentials, gen_enc_path, enc_req, dec_req, issue_shop_token, validate_shop_token, clear_shop_token
from helpers.shop import make_shops, req_product_details, put_product_out_for_delivery, deliver_product, inform_shop_of_delivery

BASE_DIR = Path('/home')
FLAG_PRODUCT = {
    "id": "prd_f786ee3f04cca064",
    "name": "Pflueger Bull Dog Fishing Hook",
    "vendorSku": "PBD-2139",
    "price": 8900,
    "currency": "USD",
    "desc": "Perfect find for any fisherman",
    "HiveCTF": os.getenv("FLAG", "CTF{REDACTED}"),
    "stock": 1
}
ASSETS_DIR = BASE_DIR / "assets"
if not ASSETS_DIR.is_dir(): ASSETS_DIR.mkdir(parents=True, exist_ok=True)
EXECUTABLE = "an-eastern-fisherman"

HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", 80))

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "views"),
    static_folder=str(BASE_DIR / "static"),
)
login_manager = LoginManager()
login_manager.init_app(app)

app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = False
app.config["ENCRYPTED_PATH"] = gen_enc_path()
app.config["SECRET_KEY"] = secrets.token_hex(32)
app.config["AES_KEY"] = secrets.token_hex(16)
app.config["ATTEMPT_LIMIT"] = 2

Session(app)

class User(UserMixin):
    def __init__(self, username: str):
        self.id = username
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

@login_manager.unauthorized_handler
def unauthorized():
    return jsonify({"error": "Unauthorized. Authentication required."}), 401

SHOPS: dict[str, dict[str, str|list[dict[str, str]]]] = make_shops(BASE_DIR, FLAG_PRODUCT)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
app.logger.setLevel(logging.INFO)

def log_req(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        client = request.headers.get("X-Forwarded-For", request.remote_addr)
        app.logger.info(f"-> {request.method} {request.full_path} from {client} {app.config['AES_KEY']}")
        resp = make_response(f(*args, **kwargs))
        app.logger.info(f"<- {resp.status_code} {request.path}")
        return resp
    return wrapper

def encrypted_api(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if app.config["ATTEMPT_LIMIT"] <= 0:
            app.logger.warning("Attempt limit reached. Rejecting request.")
            return jsonify({"error": "Too many invalid attempts. Please try again later."}), 429
        try:
            req = request.get_json(silent=True) or {}
            payload = req.get("payload")
            data = dec_req(app.config["AES_KEY"], payload) if payload else None
            if data is None and request.method in ("POST", "PUT"):
                app.config["ATTEMPT_LIMIT"] -= 1
                app.logger.warning(f"Missing or Invalid encrypted payload - {req}")
                return jsonify({"error": "Invalid payload"}), 400
            g.data = data

            result = f(*args, **kwargs)
            resp = make_response(result)
            if resp.is_json:
                data = resp.get_json()
                resp.set_data(json.dumps({"payload": enc_req(app.config["AES_KEY"], data)}))
                resp.mimetype = "application/json"
            return resp
        except (ValueError, KeyError, json.JSONDecodeError) as e:
            app.config["ATTEMPT_LIMIT"] -= 1
            app.logger.warning(f"Error processing encrypted API request: {app.config['AES_KEY']} {e}")
            return jsonify({"error": "Invalid payload format"}), 400
        except Exception as e:
            app.logger.error(f"Unexpected error in encrypted API: {e}")
            return jsonify({"error": "Internal server error"}), 500
    return wrapper
            
@app.route("/<path:path>/gnip", methods=["GET","OPTIONS"])
@encrypted_api
def health(path):
    if request.method == "GET":
        return "", 404
    if path != app.config.get("ENCRYPTED_PATH", ""):
        return "", 404
    return "", 204

@app.get("/<path:path>")
@log_req
@login_required
@encrypted_api
def hidden_index(path):
    if path != app.config.get("ENCRYPTED_PATH", ""):
        return jsonify({"error": "Not found"}), 404
    products: list[dict[str, str]] = []
    for shop in SHOPS.values():
        for product in shop["products"]:
            if isinstance(product, dict) and all(k in product for k in ("id", "name", "desc")):
                products.append({"id":product["id"],"name":product["name"],"desc": product["desc"],})
    if not hasattr(current_user, "username"):
        return jsonify({"error": "User information is missing. Please log in again."}), 400
    msg = f"""Welcome to the marketplace ,{current_user.username}!
    Send a request with the id of the product you want to buy, and we will take care of the rest.
    Here are the products available for purchase:"""
    return jsonify({"message":msg,"products": products}), 200

@app.post("/<path:path>")
@log_req
@login_required
@encrypted_api
def request_for_product(path):
    if path != app.config.get("ENCRYPTED_PATH", ""):
        return jsonify({"error": "Not found"}), 404

    data = g.get("data", {})
    if not data or not isinstance(data, dict):
        return jsonify({"error": "Invalid or missing payload"}), 400

    productId = data.get("id", "")
    if not isinstance(productId, str) or not productId:
        return jsonify({"error": "Invalid or missing id parameter"}), 400

    hit = req_product_details(SHOPS, productId)
    if not hit:
        return jsonify({"error": "product not found"}), 404

    shop_id = hit["shopId"]

    token = issue_shop_token(session, shop_id, productId)

    endpoint = data.get("endpoint", "")
    if not hasattr(current_user, "username"):
        return jsonify({"error": "User information is missing. Please log in again."}), 400
    
    message = ""
    if isinstance(endpoint, str) and endpoint:
        if inform_shop_of_delivery(endpoint, current_user.username, productId, token):
            message = f"""Shop is not trusted, but we have informed them of your order.
            The ETA is currently unknown. Try visiting our trusted shops for a better experience."""
        else:
            message = f"""Failed to inform the untrusted shop at {endpoint}.
            If you had not specify a shop, we would have informed our trusted shops instead."""
    else:
        p = put_product_out_for_delivery(SHOPS,shop_id,productId,current_user.username,token,)
        if not p:
            return jsonify({"error": "Product not found or already out for delivery"}), 404
        endpoint = url_for("deliver", shopId=shop_id, productId=productId)
        message = f"""Product order was successful. We will deliver in 100 days!
        Bear with us and do not go to the shop directly, as they may not recognize you."""

    return jsonify({ "message": message, "url": endpoint, "shopToken": token }), 200

@app.post("/shop/<shopId>/<productId>")
@log_req
@login_required
def deliver(shopId, productId):
    data = request.get_json(silent=True) or {}
    shop_token = data.get("shopToken", "")

    if not validate_shop_token(session, shopId, productId, shop_token):
        return jsonify({"error": "Invalid shop token"}), 403
    if not hasattr(current_user, "username"):
        return jsonify({"error": "User information is missing. Please log in again."}), 400
    item = deliver_product(
        SHOPS,
        shopId,
        productId,
        current_user.username,
        shop_token,
    )
    if not item: return jsonify({"error": "Delivery not found"}), 404

    clear_shop_token(session, shopId, productId)
    return jsonify(item), 200
    
@app.post("/<path:path>/nigol")
@log_req
@encrypted_api
def login(path):
    if path != app.config.get("ENCRYPTED_PATH", ""):
        return jsonify({"error": "Not found"}), 404
    data = g.get("data", {})
    if not data or not isinstance(data, dict):
        app.logger.warning(f"Login attempt with invalid payload - {data}")
        return jsonify({"error": "Invalid payload"}), 400
    username = data.get("username", "")
    password = data.get("password", "")
    if not isinstance(username, str) or not username:
        return jsonify({"error": "A valid username is required"}), 400
    if not isinstance(password, str) or not password:
        return jsonify({"error": "A valid password is required"}), 400
    credentials_file = ASSETS_DIR / "users.csv"
    if not credentials_file.is_file():
        return jsonify({"error": "Server misconfiguration"}), 500
    authorized = verify_credentials(f"{credentials_file}", username, password)
    if authorized is None:
        return jsonify({"error": f"User was not found in {credentials_file}"}), 404
    if not authorized:
        return jsonify({"error": "Invalid password"}), 403
    login_user(User(username))
    return jsonify({"message": "Login successful. Try visiting the marketplace now"}), 200
    

@app.get("/")
@log_req
def index(): return render_template("index.html")

@app.post("/")
@log_req
def download():
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({"error": "Invalid payload"}), 400
    filetype = data.get("filetype", "")
    if not isinstance(filetype, str) or not filetype:
        return jsonify({"error": "Invalid filename"}), 400
    file_path = ASSETS_DIR.joinpath(secure_filename(EXECUTABLE))
    filename = data.get("filename", EXECUTABLE)
    if not file_path.is_file():
        if filetype in ("linux", "windows"):
            base_url = request.url_root.rstrip("/")
            enc_path = app.config.get("ENCRYPTED_PATH", "")
            if not enc_path or not isinstance(enc_path, str):
                return jsonify({"error": "Server misconfiguration"}), 500
            secret_key = app.config.get("AES_KEY", "")
            if not secret_key or not isinstance(secret_key, str):
                return jsonify({"error": "Server misconfiguration"}), 500
            if not compile_code(enc_path, secret_key, base_url):
                return jsonify({"error": "Compilation failed"}), 500
        else:
            return jsonify({"error": f"File was not found"}), 404
    return send_from_directory(ASSETS_DIR, filename, as_attachment=True)

if __name__ == "__main__":
    password = os.getenv("ASSETS_PASSWORD")
    if password is None: raise RuntimeError("ASSETS_PASSWORD environment variable is not set.")
    with py7zr.SevenZipFile(BASE_DIR / "assets.7z", mode='r', password=password) as archive:
        archive.extractall(path=ASSETS_DIR)
    app.run(host=HOST, port=PORT)