from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import threading
from flask_cors import CORS  # NEW

app = Flask(__name__)
CORS(app, resources={r"/feed*": {"origins": "*"}})  # NEW

# Uwaga: jeśli używasz Gunicorna na Renderze, wymuś jeden worker:
# Var: WEB_CONCURRENCY=1  (inaczej każdy worker ma swój własny latest_data)

app = Flask(__name__)
CORS(app)

_latest_data = []
_lock = threading.Lock()

def _is_non_empty_str(v):
    return isinstance(v, str) and v.strip() != ""

def _is_number(v):
    try:
        float(v)
        return True
    except (TypeError, ValueError):
        return False

def _clean_payload(payload):
    """
    payload -> list[{instrument, price, status:"LIVE"}] bez duplikatów/śmieci.
    Zasady:
      - instrument: niepusty string, różny od "HEARTBEAT" (case-insens)
      - price: liczba (z close lub price, jeśli ktoś już przemapował)
      - status: zawsze "LIVE"
    """
    if not isinstance(payload, list):
        raise ValueError("Body must be a JSON array")

    items = {}
    for x in payload:
        if not isinstance(x, dict):
            continue

        instr = x.get("instrument") or x.get("symbol")  # ewentualny alias
        if not _is_non_empty_str(instr):
            continue
        instr = instr.strip()
        if instr.upper() == "HEARTBEAT":
            continue

        # akceptuj close albo price; preferuj close gdy jest
        raw_price = x.get("close", x.get("price", None))
        if not _is_number(raw_price):
            continue
        price = float(raw_price)

        items[instr] = {"instrument": instr, "price": price, "status": "LIVE"}

    # zwróć posortowane po instrumencie (stabilna kolejność do diffów)
    return [items[k] for k in sorted(items.keys())]

@app.route("/feed", methods=["GET", "OPTIONS"])
def get_feed():
    with _lock:
        # zwracaj snapshot – nic poza trzema polami
        return jsonify(_latest_data)

@app.route("/feed/update", methods=["POST", "OPTIONS"])
def update_feed():
    replace = request.args.get("replace") == "1"

    # Nie używaj force=True – odrzuć złe Content-Type i nie-JSON
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    try:
        payload = request.get_json(silent=False)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    try:
        cleaned = _clean_payload(payload)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    if replace:
        with _lock:
            _latest_data.clear()
            _latest_data.extend(cleaned)
    else:
        # merge po instrument (ostatni wygrywa)
        with _lock:
            index = {x["instrument"]: i for i, x in enumerate(_latest_data)}
            for r in cleaned:
                i = index.get(r["instrument"])
                if i is None:
                    _latest_data.append(r)
                else:
                    _latest_data[i] = r

    return jsonify({"status": "updated", "updated": len(cleaned), "total": len(_latest_data)})

@app.after_request
def add_cors_headers(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return resp

if __name__ == "__main__":
    # Dev-only. Na Renderze nie uruchamiać app.run (Gunicorn ładuje app)
    port = int(os.environ.get("PORT", 8080))
    print(f"🔧 Running Flask dev server locally on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=True, threaded=True)

  
