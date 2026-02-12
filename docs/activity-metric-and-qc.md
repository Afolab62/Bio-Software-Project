# Unifying Activity Metric and Quality Control

## Purpose

This document defines the currently implemented unifying activity metric and the quality control (QC) checks used in the integration pipeline.

Implementation reference: `analysis/integration_example.py`

## Data Inputs

Required fields per record:

1. `Directed_Evolution_Generation`
2. `DNA_Quantification_fg`
3. `Protein_Quantification_pg`
4. `Control`
5. `Plasmid_Variant_Index`

Merged with sequence analysis results via:

- `variant_sequences.variant_index` (database)
- `Plasmid_Variant_Index` (experimental data)

## Unifying Activity Metric (Implemented)

For each non-control variant:

1. Compute generation-specific control baselines.
`baseline_dna = mean(DNA_Quantification_fg of controls in same generation)`
`baseline_protein = mean(Protein_Quantification_pg of controls in same generation)`
2. Normalize yields.
`norm_dna = variant_dna / baseline_dna`
`norm_protein = variant_protein / baseline_protein`
3. Compute activity score.
`activity_score = norm_dna / norm_protein` if `norm_protein > 0`
`activity_score = 0` otherwise

For control rows:

- `activity_score = 1.0`

## Baseline Fallback Rule

If a generation has no control rows, the implementation falls back to global control means:

1. `baseline_dna = mean(DNA_Quantification_fg across all controls)`
2. `baseline_protein = mean(Protein_Quantification_pg across all controls)`

## QC Implementations in Current Pipeline

### 1. Control/Variant Separation

Rows are split into:

1. Controls: `Control == True`
2. Variants: `Control == False`

This ensures baseline estimates are derived from controls only.

### 2. Generation-Specific Baselines

Baselines are computed per directed evolution generation to reduce cross-generation drift effects.

### 3. Merge Integrity Constraint

The merge uses an inner join on variant index fields.  
Only rows with valid matches in both sequence and experimental datasets proceed to scoring.

### 4. Division Safety Guard

If normalized protein denominator is not positive, score is set to `0` to avoid invalid division.

### 5. Control Anchoring

Controls are assigned score `1.0` as baseline anchors for interpretation and plotting.

## Notes on Formula Text vs Code

A docstring comment in the script includes:

- `Activity Score = (DNA_yield - baseline_DNA) / (Protein_yield - baseline_protein)`

The implemented code uses ratio-of-ratios normalization:

- `activity_score = (DNA / baseline_DNA) / (Protein / baseline_protein)`

For reproducibility, treat the code implementation as the authoritative method unless the team intentionally changes it.

## Recommended Additional QC (Not Yet Implemented)

1. Explicit missing-value checks with row-level exclusion logs
2. Outlier policy (IQR or robust z-score) for control baselines
3. Minimum controls per generation threshold
4. Confidence intervals or bootstrap uncertainty for activity scores
5. Validation report that lists dropped rows and reasons
