from app import create_app, init_db


def main():
    app = create_app("testing")
    with app.app_context():
        init_db()
    client = app.test_client()
    response = client.post(
        "/register",
        json={
            "username": "testuser",
            "email": "testuser@example.com",
            "password": "test-password",
        },
    )
    print(response.status_code, response.get_json())


if __name__ == "__main__":
    main()
