import base64

from flask import Flask, jsonify, request
from playwright.sync_api import Error, TimeoutError as PlaywrightTimeoutError, sync_playwright

app = Flask(__name__)

_playwright = None
_browser = None


def get_browser():
    global _playwright, _browser
    if _browser is not None:
        try:
            connected = _browser.is_connected()
        except Exception:
            connected = False
        if not connected:
            _browser = None

    if _browser is None:
        if _playwright is None:
            _playwright = sync_playwright().start()
        try:
            _browser = _playwright.chromium.launch(headless=True)
        except Exception:
            try:
                _playwright.stop()
            except Exception:
                pass
            _playwright = sync_playwright().start()
            _browser = _playwright.chromium.launch(headless=True)

    return _browser


def _error_message(exc: BaseException) -> str:
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
    if not url or not isinstance(url, str):
        return jsonify({"success": False, "error": "Missing or invalid 'url' field"}), 400

    url = url.strip()
    if not url:
        return jsonify({"success": False, "error": "Missing or invalid 'url' field"}), 400

    page = None
    try:
        browser = get_browser()
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=60_000)
        image_bytes = page.screenshot(type="png", full_page=True)
    except PlaywrightTimeoutError as e:
        return jsonify({"success": False, "error": f"Page load timed out: {_error_message(e)}"}), 502
    except Error as e:
        return jsonify({"success": False, "error": _error_message(e)}), 502
    except OSError as e:
        return jsonify({"success": False, "error": f"Unreachable or failed to connect: {_error_message(e)}"}), 502
    except Exception as e:
        return jsonify({"success": False, "error": _error_message(e)}), 500
    finally:
        if page is not None:
            page.close()

    b64 = base64.b64encode(image_bytes).decode("ascii")
    return jsonify({"image": b64, "success": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
