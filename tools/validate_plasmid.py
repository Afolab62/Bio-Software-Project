import argparse
import json
import logging
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, Optional

from app.services.sequence_tools import parse_fasta_dna, parse_fasta_protein, CODON_TABLE
from app.services.plasmid_validation import find_wt_in_plasmid
from app.services.errors import DirectedEvolutionPortalError


def _load_codon_table_json(path: str) -> dict:
    """
    Load a codon table from JSON.

    Expected format:
      {"TTT":"F", ..., "TAA":"*", "TAG":"*", "TGA":"*"}
    Strict validation prevents silent translation mistakes.
    """
    data = json.loads(Path(path).read_text())
    if not isinstance(data, dict):
        raise ValueError("codon_table_json must be a JSON object mapping codon->AA")

    table = {}
    for k, v in data.items():
        if not isinstance(k, str) or len(k) != 3 or any(c not in "ACGT" for c in k.upper()):
            raise ValueError(f"Invalid codon key: {k!r} (expected 3 letters A/C/G/T)")
        if not isinstance(v, str) or len(v) != 1:
            raise ValueError(f"Invalid amino acid value for {k!r}: {v!r} (expected single character)")
        table[k.upper()] = v.upper()

    if "ATG" not in table:
        raise ValueError("Codon table missing ATG (start codon)")

    return table


def _build_report(*, call_obj: Any, accession: Optional[str], plasmid_len: int, params: Dict[str, Any],
                  codon_table_source: str, timing_s: float) -> Dict[str, Any]:
    """
    Versioned, structured output envelope.

    Why:
    - Makes outputs stable across future refactors (schema_version).
    - Records analysis parameters for reproducibility (critical for assessment).
    - Carries diagnostics/warnings in a consistent location.
    """
    call = call_obj.__dict__
    return {
        "schema_version": "1.0",
        "inputs": {
            "uniprot_accession": accession,
            "plasmid_length_nt": plasmid_len,
            "codon_table_source": codon_table_source,
        },
        "params": params,
        "timing_seconds": round(timing_s, 6),
        "validation": call,
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Validate that a WT protein sequence is encoded in a (circular) plasmid DNA FASTA."
    )
    ap.add_argument("--plasmid_fasta", required=True, help="Path to plasmid DNA FASTA")
    ap.add_argument("--wt_protein_fasta", required=True, help="Path to WT protein FASTA")

    # Robustness parameters (tunable without code edits)
    ap.add_argument("--min_wt_len", type=int, default=30, help="Minimum WT protein length (aa)")
    ap.add_argument("--min_identity", type=float, default=0.95, help="Fuzzy substitution identity threshold")
    ap.add_argument("--align_min_identity", type=float, default=0.90, help="Alignment identity threshold")
    ap.add_argument("--align_min_coverage", type=float, default=0.95, help="Alignment WT-coverage threshold")

    # Performance guards: prevents pathological O(n*m) alignment runs by default
    ap.add_argument("--max_align_wt_len", type=int, default=2000, help="Skip alignment if WT is longer than this (unless allow_slow_alignment)")
    ap.add_argument("--max_align_plasmid_len", type=int, default=200000, help="Skip alignment if plasmid is longer than this (unless allow_slow_alignment)")
    ap.add_argument("--allow_slow_alignment", action="store_true", help="Allow alignment even if max lengths exceeded")

    # Codon table handling
    ap.add_argument("--codon_table_json", default=None, help="Optional path to JSON codon table mapping (overrides standard).")

    # Output controls
    ap.add_argument("--save_report", default=None, help="Optional path to save the full report JSON (recommended for assessment evidence).")
    ap.add_argument("--legacy_output", action="store_true", help="Print only the raw validation dict (no report envelope).")

    # Logging
    ap.add_argument("--log_level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    args = ap.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level))
    log = logging.getLogger("validate_plasmid")

    try:
        t0 = perf_counter()

        plasmid_text = Path(args.plasmid_fasta).read_text()
        wt_text = Path(args.wt_protein_fasta).read_text()

        plasmid_dna = parse_fasta_dna(plasmid_text)
        wt_protein = parse_fasta_protein(wt_text)

        codon_table = CODON_TABLE
        codon_table_source = "standard"
        if args.codon_table_json:
            codon_table = _load_codon_table_json(args.codon_table_json)
            codon_table_source = f"json:{args.codon_table_json}"

        # Run validation (service layer) — all heavy logic stays in services for testability.
        call = find_wt_in_plasmid(
            plasmid_dna,
            wt_protein,
            min_wt_len=args.min_wt_len,
            min_identity=args.min_identity,
            align_min_identity=args.align_min_identity,
            align_min_coverage=args.align_min_coverage,
            codon_table=codon_table,
            max_align_wt_len=args.max_align_wt_len,
            max_align_plasmid_len=args.max_align_plasmid_len,
            allow_slow_alignment=args.allow_slow_alignment,
            enable_plausibility_warnings=True,
        )

        timing = perf_counter() - t0

        params = {
            "min_wt_len": args.min_wt_len,
            "min_identity": args.min_identity,
            "align_min_identity": args.align_min_identity,
            "align_min_coverage": args.align_min_coverage,
            "max_align_wt_len": args.max_align_wt_len,
            "max_align_plasmid_len": args.max_align_plasmid_len,
            "allow_slow_alignment": bool(args.allow_slow_alignment),
        }

        report = _build_report(
            call_obj=call,
            accession=None,
            plasmid_len=len(plasmid_dna),
            params=params,
            codon_table_source=codon_table_source,
            timing_s=timing,
        )

        if args.save_report:
            Path(args.save_report).parent.mkdir(parents=True, exist_ok=True)
            Path(args.save_report).write_text(json.dumps(report, indent=2, default=str))
            log.info("Saved report to %s", args.save_report)

        # Print output
        if args.legacy_output:
            print(json.dumps(call.__dict__, indent=2, default=str))
        else:
            print(json.dumps(report, indent=2, default=str))

    except DirectedEvolutionPortalError as e:
        # Clean, user-facing failure (ideal for web UI too)
        err = {"error": str(e), "schema_version": "1.0"}
        print(json.dumps(err, indent=2))
        raise SystemExit(2)
    except Exception as e:
        # Unexpected error: still print a structured payload so failures are diagnosable
        err = {"error": f"Unexpected error: {e}", "schema_version": "1.0"}
        print(json.dumps(err, indent=2))
        raise SystemExit(3)


if __name__ == "__main__":
    main()
