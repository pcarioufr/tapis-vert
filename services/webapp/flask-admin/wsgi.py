from app import init_admin_app

app = init_admin_app()

if __name__ == "__main__":
    # Admin app only accessible from localhost
    app.run(host="127.0.0.1", port=5001)
