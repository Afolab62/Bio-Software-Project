"""
Staging routes: UniProt accession + plasmid FASTA upload + validation.
"""
from flask import Blueprint, jsonify, render_template, request

from app.services.staging import stage_experiment_validate_plasmid

staging_bp = Blueprint("staging", __name__, url_prefix="/staging")


def _get_plasmid_fasta_from_request() -> str:
    """Extract plasmid FASTA text from textarea or uploaded file."""
    plasmid_fasta = request.form.get("plasmid_fasta", "").strip()
    uploaded = request.files.get("plasmid_file")
    if uploaded and uploaded.filename:
        plasmid_fasta = uploaded.read().decode("utf-8")
    return plasmid_fasta


@staging_bp.get("/")
def staging_form():
    """Render the staging form."""
    return render_template("staging.html", result=None, accession="", plasmid_fasta="", fetch_features=True)


@staging_bp.post("/")
def staging_submit():
    """Handle staging submission and render results."""
    accession = request.form.get("accession", "").strip()
    fetch_features = bool(request.form.get("fetch_features"))

    plasmid_fasta = _get_plasmid_fasta_from_request()

    if not accession or not plasmid_fasta:
        result = {"error": "Please provide a UniProt accession and plasmid FASTA (paste or upload)."}
        return render_template(
            "staging.html",
            result=result,
            accession=accession,
            plasmid_fasta=plasmid_fasta,
            fetch_features=fetch_features,
        )

    # Core staging call: UniProt fetch + FASTA parsing + validation
    result = stage_experiment_validate_plasmid(
        accession=accession,
        plasmid_fasta_text=plasmid_fasta,
        fetch_features=fetch_features,
    )

    return render_template(
        "staging.html",
        result=result,
        accession=accession,
        plasmid_fasta=plasmid_fasta,
        fetch_features=fetch_features,
    )


@staging_bp.post("/api/staging")
def staging_api():
    """
    JSON API endpoint for staging.
    Expects: {accession, plasmid_fasta, fetch_features?}
    """
    data = request.get_json(silent=True) or {}
    accession = str(data.get("accession", "")).strip()
    plasmid_fasta = str(data.get("plasmid_fasta", "")).strip()
    fetch_features = bool(data.get("fetch_features", True))

    if not accession or not plasmid_fasta:
        return jsonify({"error": "accession and plasmid_fasta are required"}), 400

    result = stage_experiment_validate_plasmid(
        accession=accession,
        plasmid_fasta_text=plasmid_fasta,
        fetch_features=fetch_features,
    )
    return jsonify(result), 200
