from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

import requests

from app.services.mutation_analysis import (
    clean_dna,
    clean_protein,
    extract_gene_from_plasmid,
    find_wt_gene_call,
    translate_dna,
)

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VALIDATION_CACHE = _PROJECT_ROOT / "instance" / "validation_cache"
_UNIPROT_FASTA_URL = "https://rest.uniprot.org/uniprotkb/{accession}.fasta"
_UNIPROT_JSON_URL = "https://rest.uniprot.org/uniprotkb/{accession}.json"


class UniProtError(RuntimeError):
    """Raised when a UniProt lookup fails."""


def _cache_key(accession: str, plasmid_fasta_text: str, fetch_features: bool) -> str:
    digest = hashlib.sha1()
    digest.update(accession.strip().upper().encode("utf-8"))
    digest.update(b"|")
    digest.update(plasmid_fasta_text.encode("utf-8"))
    digest.update(b"|")
    digest.update(b"1" if fetch_features else b"0")
    return digest.hexdigest()


def _cache_path(cache_dir: Path, key: str) -> Path:
    return cache_dir / f"{key}.json"


def _read_validation_cache(cache_dir: Path, key: str) -> dict[str, Any] | None:
    try:
        path = _cache_path(cache_dir, key)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_validation_cache(cache_dir: Path, key: str, data: dict[str, Any]) -> None:
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        _cache_path(cache_dir, key).write_text(json.dumps(data), encoding="utf-8")
    except Exception:
        logger.debug("Could not write staging validation cache", exc_info=True)


def _parse_fasta_sequence(text: str, *, sequence_type: str) -> str:
    if not text or not text.strip():
        raise ValueError("FASTA input cannot be empty.")

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if lines and lines[0].startswith(">"):
        lines = lines[1:]

    sequence = "".join(lines) if lines else text
    if sequence_type == "dna":
        cleaned = clean_dna(sequence)
    elif sequence_type == "protein":
        cleaned = clean_protein(sequence).replace("*", "")
    else:
        raise ValueError(f"Unsupported sequence_type: {sequence_type}")

    if not cleaned:
        raise ValueError(f"Could not parse a valid {sequence_type} sequence from FASTA input.")
    return cleaned


def fetch_uniprot_fasta(accession: str) -> str:
    accession = accession.strip().upper()
    if not accession:
        raise UniProtError("A UniProt accession is required.")

    response = requests.get(_UNIPROT_FASTA_URL.format(accession=accession), timeout=20)
    if response.status_code == 404:
        raise UniProtError(f"Accession {accession} was not found.")
    if not response.ok:
        raise UniProtError(f"FASTA request failed with HTTP {response.status_code}.")
    return response.text


def fetch_uniprot_features_json(accession: str) -> list[dict[str, Any]]:
    accession = accession.strip().upper()
    response = requests.get(_UNIPROT_JSON_URL.format(accession=accession), timeout=20)
    if response.status_code == 404:
        raise UniProtError(f"Accession {accession} was not found.")
    if not response.ok:
        raise UniProtError(f"Feature request failed with HTTP {response.status_code}.")

    payload = response.json()
    features: list[dict[str, Any]] = []
    for feature in payload.get("features") or []:
        location = feature.get("location") or {}
        start = (location.get("start") or {}).get("value")
        end = (location.get("end") or {}).get("value")
        features.append(
            {
                "type": feature.get("type"),
                "description": feature.get("description"),
                "start": int(start) if start is not None else None,
                "end": int(end) if end is not None else None,
            }
        )
    return features


def _build_validation(plasmid_dna: str, wt_protein: str) -> dict[str, Any]:
    wt_protein_clean = clean_protein(wt_protein).replace("*", "")
    try:
        gene_call = find_wt_gene_call(plasmid_dna, wt_protein_clean)
    except Exception as exc:
        return {
            "is_valid": False,
            "match_type": "not_found",
            "message": str(exc),
        }

    gene_seq = extract_gene_from_plasmid(plasmid_dna, gene_call)
    translated = clean_protein(translate_dna(gene_seq)).replace("*", "")
    is_valid = translated == wt_protein_clean

    return {
        "is_valid": is_valid,
        "match_type": "exact" if is_valid else "mismatch",
        "message": (
            "The plasmid encodes the expected wild-type protein."
            if is_valid
            else "A coding region was found, but the translated protein does not match UniProt."
        ),
        "gene_nt_len": len(gene_seq),
        "protein_len": len(translated),
        "start_nt": int(gene_call["start_nt"]),
        "frame": int(gene_call["frame"]),
        "strand": str(gene_call["strand"]),
        "wraps_origin": bool(gene_call["wraps_origin"]),
    }


def stage_experiment_validate_plasmid(
    accession: str,
    plasmid_fasta_text: str,
    fetch_features: bool = True,
) -> dict[str, Any]:
    """
    Fetch the UniProt WT sequence, parse the submitted plasmid FASTA, and
    validate that the plasmid contains a coding region matching the WT protein.
    """
    normalized_accession = accession.strip().upper()
    result: dict[str, Any] = {
        "accession": normalized_accession,
        "wt_protein": None,
        "wt_plasmid_seq": None,
        "features": None,
        "validation": None,
        "error": None,
    }

    cache_key = _cache_key(normalized_accession, plasmid_fasta_text, fetch_features)
    cached = _read_validation_cache(DEFAULT_VALIDATION_CACHE, cache_key)
    if cached is not None:
        return cached

    try:
        wt_fasta = fetch_uniprot_fasta(normalized_accession)
        wt_protein = _parse_fasta_sequence(wt_fasta, sequence_type="protein")
        plasmid_dna = _parse_fasta_sequence(plasmid_fasta_text, sequence_type="dna")

        result["wt_protein"] = wt_protein
        result["wt_plasmid_seq"] = plasmid_dna
        result["features"] = (
            fetch_uniprot_features_json(normalized_accession) if fetch_features else []
        )
        result["validation"] = _build_validation(plasmid_dna, wt_protein)

    except UniProtError as exc:
        result["error"] = f"UniProt error: {exc}"
    except Exception as exc:
        result["error"] = f"Unexpected error: {exc}"

    _write_validation_cache(DEFAULT_VALIDATION_CACHE, cache_key, result)
    return result


__all__ = [
    "UniProtError",
    "fetch_uniprot_fasta",
    "fetch_uniprot_features_json",
    "stage_experiment_validate_plasmid",
]
