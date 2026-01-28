"""
Sequence utilities used by Part C (plasmid validation) and downstream analysis.

This module deliberately avoids heavy dependencies (e.g., Biopython) to keep the
coursework environment lightweight and reproducible. It provides:
- FASTA parsing for DNA and protein sequences
- DNA reverse complement
- DNA translation in a specified reading frame
- 6-frame translation (3 forward + 3 reverse frames)

Key robustness choices:
- Ambiguous DNA bases translate to 'X' (unknown amino acid) rather than raising.
  This mirrors real sequencing outputs where ambiguity codes are common and keeps
  the pipeline resilient.
- Translation uses a codon table dictionary (default: standard genetic code) so
  the caller can swap tables via JSON when needed.

Performance:
- Translation is linear in sequence length (O(n)).
"""


from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from .errors import FastaParseError, InvalidSequenceError


# Standard genetic code (DNA codons -> amino acids).
# We keep this as a constant so it's easy to reference and override.
CODON_TABLE: Dict[str, str] = {
    "TTT": "F", "TTC": "F", "TTA": "L", "TTG": "L",
    "TCT": "S", "TCC": "S", "TCA": "S", "TCG": "S",
    "TAT": "Y", "TAC": "Y", "TAA": "*", "TAG": "*",
    "TGT": "C", "TGC": "C", "TGA": "*", "TGG": "W",
    "CTT": "L", "CTC": "L", "CTA": "L", "CTG": "L",
    "CCT": "P", "CCC": "P", "CCA": "P", "CCG": "P",
    "CAT": "H", "CAC": "H", "CAA": "Q", "CAG": "Q",
    "CGT": "R", "CGC": "R", "CGA": "R", "CGG": "R",
    "ATT": "I", "ATC": "I", "ATA": "I", "ATG": "M",
    "ACT": "T", "ACC": "T", "ACA": "T", "ACG": "T",
    "AAT": "N", "AAC": "N", "AAA": "K", "AAG": "K",
    "AGT": "S", "AGC": "S", "AGA": "R", "AGG": "R",
    "GTT": "V", "GTC": "V", "GTA": "V", "GTG": "V",
    "GCT": "A", "GCC": "A", "GCA": "A", "GCG": "A",
    "GAT": "D", "GAC": "D", "GAA": "E", "GAG": "E",
    "GGT": "G", "GGC": "G", "GGA": "G", "GGG": "G",
}

# IUPAC DNA alphabet (includes ambiguous bases).
# We allow these because real sequencing/assembly often contains N/R/Y/etc.
IUPAC_DNA = set("ACGTRYSWKMBDHVN")

# Protein alphabet:
# - Standard 20 amino acids (A,C,D,E,F,G,H,I,K,L,M,N,P,Q,R,S,T,V,W,Y)
# - X = unknown/ambiguous AA
# - * = stop
# - U/O/B/Z/J appear in some resources; we accept them as "valid" characters.
PROTEIN_ALPHABET = set("ACDEFGHIKLMNPQRSTVWYXBZJUO*")


@dataclass(frozen=True)
class FastaRecord:
    header: str
    seq: str


def _read_fasta_records(text: str) -> List[FastaRecord]:
    """
    Parse FASTA text into records.

    Accepts:
    - Standard FASTA with one or multiple records.
    - "Raw sequence" with no header (treated as a single record).

    Raises:
    - FastaParseError if formatting is malformed.
    """
    if text is None:
        raise FastaParseError("FASTA input was None")

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        raise FastaParseError("FASTA input is empty")

    # If there are no headers at all, treat the whole thing as a raw sequence.
    if not any(ln.startswith(">") for ln in lines):
        return [FastaRecord(header="raw_sequence", seq="".join(lines))]

    records: List[FastaRecord] = []
    header = None
    seq_parts: List[str] = []

    for ln in lines:
        if ln.startswith(">"):
            # Commit previous record (if any)
            if header is not None:
                records.append(FastaRecord(header=header, seq="".join(seq_parts)))
            header = ln[1:].strip() or "unnamed_record"
            seq_parts = []
        else:
            if header is None:
                # Sequence before any header is not valid FASTA.
                raise FastaParseError("FASTA sequence line encountered before any header ('>')")
            seq_parts.append(ln)

    # Commit last record
    if header is not None:
        records.append(FastaRecord(header=header, seq="".join(seq_parts)))

    if not records:
        raise FastaParseError("No FASTA records found")

    return records


def parse_fasta_dna(text: str, *, allow_multiple: bool = False) -> str:
    """
    Parse a DNA FASTA into a single uppercase sequence.

    Why we default to *single-record only*:
    - The plasmid upload should represent one construct.
    - Multi-record input (e.g., several plasmids) should be rejected with a clear message
      instead of quietly choosing one.

    Set allow_multiple=True if you deliberately want "first record wins".
    """
    records = _read_fasta_records(text)

    if len(records) > 1 and not allow_multiple:
        raise FastaParseError(
            f"DNA FASTA contains {len(records)} records (expected 1). "
            "Please upload a single plasmid sequence."
        )

    seq = records[0].seq.upper().replace(" ", "")
    if not seq:
        raise InvalidSequenceError("DNA sequence is empty after parsing FASTA")

    # Validate IUPAC alphabet; this prevents subtle downstream bugs.
    bad = {c for c in seq if c not in IUPAC_DNA}
    if bad:
        sample = "".join(sorted(list(bad)))[:20]
        raise InvalidSequenceError(f"DNA sequence contains invalid characters: {sample}")

    return seq


def parse_fasta_protein(text: str, *, allow_multiple: bool = False) -> str:
    """
    Parse a protein FASTA into a single uppercase sequence.

    Why validation matters:
    - UniProt sequences should be clean, but user-supplied FASTA may contain unusual characters.
    - Failing early avoids confusing downstream 'no match' errors caused by bad input.
    """
    records = _read_fasta_records(text)

    if len(records) > 1 and not allow_multiple:
        raise FastaParseError(
            f"Protein FASTA contains {len(records)} records (expected 1). "
            "Please upload a single WT protein sequence."
        )

    seq = records[0].seq.upper().replace(" ", "")
    if not seq:
        raise InvalidSequenceError("Protein sequence is empty after parsing FASTA")

    bad = {c for c in seq if c not in PROTEIN_ALPHABET}
    if bad:
        sample = "".join(sorted(list(bad)))[:20]
        raise InvalidSequenceError(f"Protein sequence contains invalid characters: {sample}")

    return seq


def reverse_complement(dna: str) -> str:
    """Reverse-complement a DNA sequence (IUPAC-safe for common ambiguity letters)."""
    comp = {
        "A": "T", "C": "G", "G": "C", "T": "A",
        "R": "Y", "Y": "R", "S": "S", "W": "W",
        "K": "M", "M": "K", "B": "V", "V": "B",
        "D": "H", "H": "D", "N": "N",
    }
    return "".join(comp.get(b, "N") for b in reversed(dna.upper()))


def translate_dna(dna: str, *, frame: int = 0, codon_table: Dict[str, str] = CODON_TABLE) -> str:
    """
    Translate DNA -> protein for a given frame.

    Notes:
    - We translate every complete codon and keep '*' in the output.
    - Any codon containing ambiguous bases returns 'X' rather than failing.
      This matches real-world sequencing ambiguity and keeps the pipeline robust.
    """
    dna = dna.upper()
    # Defensive programming: callers may pass codon_table=None.
    # Default back to the standard genetic code to avoid crashes.
    if codon_table is None:
        codon_table = CODON_TABLE
    aa = []
    for i in range(frame, len(dna) - 2, 3):
        codon = dna[i:i + 3]
        if any(c not in "ACGT" for c in codon):
            aa.append("X")
        else:
            aa.append(codon_table.get(codon, "X"))
    return "".join(aa)

    # Defensive programming: allow callers to omit codon table.
    if codon_table is None:
        codon_table = CODON_TABLE
def translate_six_frames(dna: str, *, codon_table: Dict[str, str] = CODON_TABLE) -> Dict[str, str]:
    """
    Translate a DNA sequence in all 6 reading frames (+0/+1/+2 and -0/-1/-2).

    Why this matters scientifically:
    - Plasmids can encode the gene on either strand.
    - The reading frame is not guaranteed unless annotated.

    The validator searches across these 6 translations to find the WT protein.
    """
    dna = dna.upper()
    rc = reverse_complement(dna)

    return {
        "+0": translate_dna(dna, frame=0, codon_table=codon_table),
        "+1": translate_dna(dna, frame=1, codon_table=codon_table),
        "+2": translate_dna(dna, frame=2, codon_table=codon_table),
        "-0": translate_dna(rc, frame=0, codon_table=codon_table),
        "-1": translate_dna(rc, frame=1, codon_table=codon_table),
        "-2": translate_dna(rc, frame=2, codon_table=codon_table),
    }
