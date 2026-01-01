from flask import Flask, request, jsonify
import psycopg2
import boto3
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

DB_CONFIG = {
    "host": "localhost",
    "database": "cloudvote",
    "user": "clouduser",
    "password": "votre_mot_de_passe"
}

AWS_REGION = "votre-region"
BUCKET = "cloudvote-logos"

s3 = boto3.client("s3", region_name=AWS_REGION)


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


@app.route("/projects", methods=["GET"])
def projects():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, name, logo_key FROM projects")
    rows = cur.fetchall()

    result = []
    for project_id, name, logo_key in rows:
        logo_url = None

        if logo_key:
            logo_url = s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": BUCKET, "Key": logo_key},
                ExpiresIn=3600
            )

        result.append({
            "id": project_id,
            "name": name,
            "logo_url": logo_url
        })

        result.append({
            "id": project_id,
            "name": name,
            "logo_url": logo_url
        })

    cur.close()
    conn.close()
    return jsonify(result)

# -------------------------

@app.route("/vote", methods=["POST"])
def vote():
    data = request.get_json()
    project_id = data.get("project_id")

    if not project_id:
        return jsonify({"error": "project_id manquant"}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO votes (project_id) VALUES (%s)",
        (project_id,)
    )
    conn.commit()

    cur.close()
    conn.close()

    return jsonify({"status": "vote enregistré"})

# -------------------------

@app.route("/results", methods=["GET"])
def results():
    """
    Agrégation DES VOTES dans le même service
    """
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT p.id, p.name, COUNT(v.id) AS total_votes
        FROM projects p
        LEFT JOIN votes v ON p.id = v.project_id
        GROUP BY p.id, p.name
        ORDER BY total_votes DESC
    """)

    rows = cur.fetchall()

    results = []
    for project_id, name, total_votes in rows:
        results.append({
            "project_id": project_id,
            "name": name,
            "votes": total_votes
        })

    cur.close()
    conn.close()

    return jsonify(results)

# =========================
# MAIN
# =========================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)