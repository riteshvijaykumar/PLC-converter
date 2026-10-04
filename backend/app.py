"""
Flask API for the AI-Assisted Bidirectional PLC Program Conversion System.

Run with:
    cd backend
    pip install -r requirements.txt
    python app.py

Then open frontend/index.html in a browser (it calls this API at
http://localhost:5000).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # allow `import ir`, `import parsers`, ...

from flask import Flask, jsonify, request, send_from_directory

from converters.siemens_to_ab import convert_siemens_to_ab
from converters.ab_to_siemens import convert_ab_to_siemens
from validators.syntax import validate_syntax

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")


@app.after_request
def add_cors_headers(response):
    # Minimal manual CORS so the static frontend (opened separately, or
    # served from a different port) can call this API without extra
    # dependencies. Use flask-cors instead for a production deployment.
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/convert", methods=["POST"])
def convert():
    data = request.get_json(force=True, silent=True) or {}
    source = data.get("source", "")
    source_vendor = (data.get("source_vendor") or "").strip().lower()
    target_vendor = (data.get("target_vendor") or "").strip().lower()
    program_name = data.get("program_name", "Program1")

    if not source.strip():
        return jsonify({"error": "No source code provided."}), 400

    if source_vendor.startswith("siem") and target_vendor.startswith(("rock", "ab", "allen")):
        result = convert_siemens_to_ab(source, program_name)
    elif source_vendor.startswith(("rock", "ab", "allen")) and target_vendor.startswith("siem"):
        result = convert_ab_to_siemens(source, program_name)
    else:
        return jsonify({
            "error": "Unsupported vendor pair. Use source_vendor='Siemens', "
                     "target_vendor='Rockwell' (or vice versa)."
        }), 400

    return jsonify(result)


@app.route("/validate", methods=["POST"])
def validate():
    data = request.get_json(force=True, silent=True) or {}
    code = data.get("code", "")
    vendor = data.get("vendor", "Siemens")
    return jsonify(validate_syntax(code, vendor))


if __name__ == "__main__":
    app.run(debug=True, port=5000)
