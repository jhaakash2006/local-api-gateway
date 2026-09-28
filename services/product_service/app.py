from flask import Flask, jsonify, request
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.database import add_product, get_products


app = Flask(__name__)


@app.route("/products", methods=["GET"])
def get_products_route():

    products = get_products()

    return jsonify({
        "service": "product",
        "message": "Product service is working",
        "products": products
    })


@app.route("/products", methods=["POST"])
def create_product():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):

        return jsonify({
            "error": "Request body must be a JSON object"
        }), 400

    name = data.get("name")
    price = data.get("price")

    if not isinstance(name, str) or not name.strip():

        return jsonify({
            "error": "name is required"
        }), 400

    if not isinstance(price, (int, float)) or isinstance(price, bool):

        return jsonify({
            "error": "price must be a number"
        }), 400

    if price < 0:

        return jsonify({
            "error": "price cannot be negative"
        }), 400

    product_id = add_product(
        name=name.strip(),
        price=float(price)
    )

    return jsonify({
        "service": "product",
        "message": "Product created",
        "id": product_id,
        "name": name.strip(),
        "price": float(price)
    }), 201


if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5003
    )