from flask import Flask, request, jsonify

app = Flask(__name__)
feed_data = []

@app.route('/')
def home():
    return jsonify({"status": "Feed server running", "routes": ["/feed", "/feed/update"]})

@app.route('/feed', methods=['GET'])
def get_feed():
    return jsonify(feed_data)

@app.route('/feed/update', methods=['POST'])
def update_feed():
    global feed_data
    try:
        new_data = request.get_json()
        if isinstance(new_data, list):
            feed_data.extend(new_data)
        else:
            feed_data.append(new_data)
        feed_data[:] = feed_data[-500:]  # zachowaj ostatnie 500 rekordów
        return jsonify({"status": "ok", "count": len(feed_data)})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
