import os

from app import create_app

app = create_app(service="users")


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=int(os.environ.get("PORT", "5001")),
        debug=False,
        use_reloader=False,
    )
