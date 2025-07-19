from app import init_public_app

app = init_public_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
