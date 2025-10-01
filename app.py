# app.py
import os
from flask import Flask, request, jsonify, send_from_directory, redirect, url_for
from werkzeug.utils import secure_filename
import esg_pipeline as pipeline

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
ALLOWED_EXTENSIONS = {"pdf"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__, static_folder="static", static_url_path="")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# Serve UI
@app.route("/")
def index():
    return app.send_static_file("index.html")

# Upload endpoint
@app.route("/api/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"success": False, "message": "No file part"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "message": "No selected file"}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(save_path)
        return jsonify({"success": True, "filename": filename, "path": save_path})
    return jsonify({"success": False, "message": "Invalid file type"}), 400

# Analyze endpoint - processes only the provided uploaded file
@app.route("/api/analyze", methods=["POST"])
def analyze_file():
    data = request.get_json() or {}
    filename = data.get("filename")
    company_name = data.get("company_name")  # optional: override company name
    if not filename:
        return jsonify({"success": False, "message": "filename required"}), 400
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    if not os.path.exists(file_path):
        return jsonify({"success": False, "message": "file not found"}), 404

    # run pipeline for single report (this loads the model if needed)
    records_df, summary_df = pipeline.process_single_report(file_path, company_name=company_name)
    # Note: process_single_report writes to CSVs internally
    return jsonify({
        "success": True,
        "processed_file": filename,
        "num_records": int(len(records_df)) if records_df is not None else 0
    })

# Companies list
@app.route("/api/companies", methods=["GET"])
def companies():
    companies = pipeline.list_companies()
    return jsonify({"companies": companies})

# Company snapshot
@app.route("/api/company/<company_name>", methods=["GET"])
def company_snapshot(company_name):
    data = pipeline.get_company_snapshot(company_name)
    return jsonify(data)

# Comparative data (summary)
@app.route("/api/comparative", methods=["GET"])
def comparative():
    data = pipeline.get_comparative_all()
    return jsonify({"data": data})

# Download CSVs for manual inspection
@app.route("/api/download/<which>", methods=["GET"])
def download(which):
    base = os.path.dirname(__file__)
    if which == "explorer":
        path = pipeline.EXPLORER_CSV
    elif which == "summary":
        path = pipeline.SUMMARY_CSV
    else:
        return jsonify({"success": False, "message": "invalid file"}), 400
    if not os.path.exists(path):
        return jsonify({"success": False, "message": "file does not exist"}), 404
    return send_from_directory(os.path.dirname(path), os.path.basename(path), as_attachment=True)

if __name__ == "__main__":
    print("Starting server on http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
