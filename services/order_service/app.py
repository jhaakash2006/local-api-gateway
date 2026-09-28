from flask import Flask, jsonify, request
import time
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.database import add_order, get_orders


app = Flask(__name__)


@app.route("/orders", methods=["GET"])
def get_orders_route():

    orders = get_orders()

    return jsonify({
        "service": "order",
        "message": "Order service is working",
        "orders": orders
    })


@app.route("/orders", methods=["POST"])
def create_order():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):

        return jsonify({
            "error": "Request body must be a JSON object"
        }), 400

    user_id = data.get("user_id")
    product_name = data.get("product_name")
    quantity = data.get("quantity")

    if not isinstance(user_id, int) or isinstance(user_id, bool):

        return jsonify({
            "error": "user_id must be an integer"
        }), 400

    if not isinstance(product_name, str) or not product_name.strip():

        return jsonify({
            "error": "product_name is required"
        }), 400

    if not isinstance(quantity, int) or isinstance(quantity, bool):

        return jsonify({
            "error": "quantity must be an integer"
        }), 400

    if quantity < 1:

        return jsonify({
            "error": "quantity must be greater than 0"
        }), 400

    order_id = add_order(
        user_id=user_id,
        product_name=product_name.strip(),
        quantity=quantity
    )

    return jsonify({
        "service": "order",
        "message": "Order created",
        "id": order_id,
        "user_id": user_id,
        "product_name": product_name.strip(),
        "quantity": quantity
    }), 201


@app.route("/slow-orders", methods=["GET"])
def slow_orders():

    time.sleep(5)

    return jsonify({
        "service": "order",
        "message": "Slow order service is working"
    })


if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5002
    )