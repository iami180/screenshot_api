import base64
import subprocess
import tempfile
import os
from flask import Flask, jsonify, request

app = Flask(__name__)

def _error_message(exc):
    text = str(exc).strip()
    if not text:
        return type(exc).__name__
    return text.split("\n", 1)[0].strip()

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/", methods=["POST"])
def screenshot():
    if not request.is_json:
        return jsonify({"success": False, "error": "Request body must be JSON"}), 400

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"success": False, "error": "Invalid JSON body"}), 400

    url = data.get("url")
    if not url or not isinstance(url, str) or not url.strip():
        return jsonify({"success": False, "error": "Missing or invalid 'url' field"}), 400

    url = url.strip()

    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            tmp_path = f.name

        result = subprocess.run([
            "chromium", "--headless", "--no-sandbox",
            "--disable-gpu", "--disable-dev-shm-usage",
            f"--screenshot={tmp_path}",
            "--window-size=1280,800",
            url
        ], capture_output=True, timeout=30)

        if result.returncode != 0:
            return jsonify({"success": False, "error": "Failed to capture screenshot"}), 502

        with open(tmp_path, "rb") as f:
            image_bytes = f.read()

        os.unlink(tmp_path)
        b64 = base64.b64encode(image_bytes).decode("ascii")
        return jsonify({"image": b64, "success": True})

    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "error": "Page load timed out"}), 502
    except Exception as e:
        return jsonify({"success": False, "error": _error_message(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
