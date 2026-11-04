import time

from flask import Flask, jsonify

app = Flask(__name__)


@app.get("/eggs")
def eggs():
    time.sleep(1)
    return jsonify({"item": "eggs"})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=False, use_reloader=False)
