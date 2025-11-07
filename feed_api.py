from flask import Flask, request, jsonify
from flask_cors import CORS
import os

# Render deployment guard: jeśli aplikacja jest uruchamiana pod Gunicornem na Render,
# zmienna środowiskowa RENDER=true i nie chcemy startować wbudowanego serwera dev.
if os.environ.get("RENDER", "") == "true":
  # Gunicorn załaduje obiekt 'app'; brak potrzeby uruchamiania app.run()
  pass

app = Flask(__name__)
# Szerokie zezwolenie CORS dla wszystkich origin (publiczny feed)
CORS(app)

latest_data = []

@app.route("/feed", methods=["GET", "OPTIONS"])
def get_feed():
    return jsonify(latest_data)

@app.route("/feed/update", methods=["POST", "OPTIONS"])
def update_feed():
    global latest_data
    latest_data = request.get_json(force=True)
    return {"status": "updated", "records": len(latest_data)}

@app.after_request
def add_cors_headers(resp):
  # Explicit CORS headers (flask-cors already adds them, but we reinforce to be safe)
  resp.headers["Access-Control-Allow-Origin"] = "*"
  resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
  resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
  return resp

if __name__ == "__main__":
  port = int(os.environ.get("PORT", 8080))
  print(f"🔧 Running Flask dev server locally on port {port}...")
  app.run(host="0.0.0.0", port=port, debug=True)
  
