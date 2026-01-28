from __future__ import annotations

"""
UniProt client (Part C support)

What this module does:
- Fetch WT protein FASTA for a UniProt accession.
- (Optional) Fetch UniProt "features" annotations (JSON).
- Provide lightweight caching and clear, user-friendly error messages.

Why this exists:
- Part C needs a reliable source of WT protein sequence for validation.
- Coursework pipelines should be reproducible and resilient to transient network issues.
"""

from dataclasses import dataclass
from hashlib import sha1
from pathlib import Path
from typing import Any, Optional
import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


# ----------------------------- Exceptions -----------------------------

class UniProtError(Exception):
    """Base error for UniProt client failures."""


class UniProtNotFound(UniProtError):
    """Accession invalid or not found (typically 400/404)."""


class UniProtNetworkError(UniProtError):
    """Network/HTTP errors that are not simple not-found."""


# ----------------------------- Data model -----------------------------

@dataclass(frozen=True)
class UniProtRecord:
    accession: str
    fasta_text: str
    features: Optional[list[dict[str, Any]]] = None


# ----------------------------- Constants -----------------------------

UNIPROT_BASE = "https://rest.uniprot.org/uniprotkb"

# Disk cache lives under Flask's conventional instance/ folder.
# This is safe to ignore in git and keeps repeated runs fast.
DEFAULT_CACHE_DIR = Path("instance") / "uniprot_cache"
DEFAULT_CACHE_TTL_S = 24 * 3600  # 24 hours


# ----------------------------- Cache helpers -----------------------------

def _cache_key(url: str, accept: str) -> str:
    h = sha1()
    h.update(url.encode("utf-8"))
    h.update(b"|")
    h.update(accept.encode("utf-8"))
    return h.hexdigest()


def _cache_paths(cache_dir: Path, key: str) -> tuple[Path, Path]:
    # Store body + tiny metadata so we can expire old entries safely.
    body_path = cache_dir / f"{key}.body"
    meta_path = cache_dir / f"{key}.meta.json"
    return body_path, meta_path


def _read_cache(cache_dir: Path, url: str, accept: str, ttl_s: float) -> Optional[str]:
    try:
        key = _cache_key(url, accept)
        body_path, meta_path = _cache_paths(cache_dir, key)
        if not body_path.exists() or not meta_path.exists():
            return None
        meta = json.loads(meta_path.read_text())
        ts = float(meta.get("ts", 0.0))
        if (time.time() - ts) > ttl_s:
            return None
        return body_path.read_text()
    except Exception:
        # Cache is strictly best-effort; never fail the workflow due to cache issues.
        return None


def _write_cache(cache_dir: Path, url: str, accept: str, text: str) -> None:
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        key = _cache_key(url, accept)
        body_path, meta_path = _cache_paths(cache_dir, key)
        body_path.write_text(text)
        meta_path.write_text(json.dumps({"ts": time.time(), "url": url, "accept": accept}))
    except Exception:
        # Best-effort only.
        return


# ----------------------------- HTTP core -----------------------------

def _http_get(
    url: str,
    *,
    accept: str,
    timeout_s: float,
    accession: Optional[str] = None,
    use_cache: bool = True,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    cache_ttl_s: float = DEFAULT_CACHE_TTL_S,
) -> str:
    """
    HTTP GET wrapper with:
    - optional caching
    - consistent UniProt error mapping

    B2/B3 note:
    We optionally include the accession in the error message so the UI can show:
      "UniProt accession not found or invalid: <ACC>"
    instead of exposing raw UniProt URLs/status lines.
    """
    if use_cache:
        cached = _read_cache(cache_dir, url, accept, ttl_s=cache_ttl_s)
        if cached is not None:
            return cached

    req = Request(url, headers={"Accept": accept, "User-Agent": "Directed-Evolution-Portal/1.0"})

    try:
        with urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read()
            # UniProt responses are UTF-8.
            text = raw.decode("utf-8", errors="replace")
    except HTTPError as e:
        # UniProt returns:
        # - 400 for malformed accessions
        # - 404 for not found
        if e.code in (400, 404):
            msg = "UniProt accession not found or invalid."
            if accession:
                msg = f"UniProt accession not found or invalid: {accession}"
            raise UniProtNotFound(msg) from e

        raise UniProtNetworkError(f"UniProt HTTP error {e.code}.") from e
    except (URLError, TimeoutError) as e:
        raise UniProtNetworkError("UniProt network error (timeout or connection failure).") from e

    if use_cache:
        _write_cache(cache_dir, url, accept, text)

    return text


# ----------------------------- Public API -----------------------------

def fetch_uniprot_fasta(accession: str, timeout_s: float = 10.0, use_cache: bool = True) -> str:
    """
    Fetch UniProt FASTA text for an accession.

    Returns FASTA text (header + sequence lines). Downstream code can parse it using
    parse_fasta_protein() in sequence_tools.
    """
    acc = accession.strip()
    url = f"{UNIPROT_BASE}/{acc}.fasta"
    return _http_get(url, accept="text/plain", timeout_s=timeout_s, accession=acc, use_cache=use_cache)


def fetch_uniprot_features_json(accession: str, timeout_s: float = 10.0, use_cache: bool = True) -> list[dict[str, Any]]:
    """
    Fetch UniProt JSON and extract the 'features' list (if present).

    Notes:
    - UniProt entries vary in annotation richness; features may be empty.
    - We return raw feature dicts to keep this layer general; filtering can be done later.
    """
    acc = accession.strip()
    url = f"{UNIPROT_BASE}/{acc}.json"
    text = _http_get(url, accept="application/json", timeout_s=timeout_s, accession=acc, use_cache=use_cache)
    data = json.loads(text)
    return list(data.get("features", []))


def fetch_uniprot_record(accession: str, *, fetch_features: bool = True, timeout_s: float = 10.0,
                         use_cache: bool = True) -> UniProtRecord:
    """
    Convenience wrapper to fetch FASTA and (optionally) features together.
    """
    fasta = fetch_uniprot_fasta(accession, timeout_s=timeout_s, use_cache=use_cache)
    features = fetch_uniprot_features_json(accession, timeout_s=timeout_s, use_cache=use_cache) if fetch_features else None
    return UniProtRecord(accession=accession.strip(), fasta_text=fasta, features=features)
