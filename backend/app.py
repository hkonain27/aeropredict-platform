from flask import Flask
from routes.health import health_bp

app = Flask(__name__)

def create_app():
    app = Flask(__name__)
    app.register_blueprint(health_bp)
    return app


app = create_app()

@app.route("/health")
def health():
    return {"status": "ok"}

@app.route("/")
def index():
    return {"message": "Welcome to the Flask API!"}

if __name__ == "__main__":
    app.run(debug=True)