from flask import Flask, jsonify, request
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.database import add_user, get_users


app = Flask(__name__)


@app.route("/users", methods=["GET"])
def get_users_route():

    users = get_users()

    return jsonify({
        "service": "user",
        "message": "User service is working",
        "users": users
    })


@app.route("/users", methods=["POST"])
def create_user():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):

        return jsonify({
            "error": "Request body must be a JSON object"
        }), 400

    name = data.get("name")
    email = data.get("email")

    if not isinstance(name, str) or not name.strip():

        return jsonify({
            "error": "name is required"
        }), 400

    if not isinstance(email, str) or not email.strip():

        return jsonify({
            "error": "email is required"
        }), 400

    user_id = add_user(
        name=name.strip(),
        email=email.strip()
    )

    return jsonify({
        "service": "user",
        "message": "User created",
        "id": user_id,
        "name": name.strip(),
        "email": email.strip(),
        "received": data,
        "received_header": request.headers.get("X-Test-Header")
    }), 201


if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5001
    )