from flask import Flask, jsonify, request, send_from_directory


app = Flask(__name__, static_folder=".", static_url_path="")


@app.get("/")
def index():
    return send_from_directory(".", "index.html")


@app.get("/results")
def results():
    return send_from_directory(".", "results.html")


@app.get("/check")
def check():
    return send_from_directory(".", "check.html")


@app.post("/search")
def search():
    data = request.form.to_dict(flat=True)
    data["filing_types"] = request.form.getlist("filing_types")
    return jsonify(data)


if __name__ == "__main__":
    app.run(debug=True)
