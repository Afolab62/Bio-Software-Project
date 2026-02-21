# Directed Evolution Portal User Manual

## Purpose

This manual guides new users through the end-to-end workflow for running directed evolution analysis with this repository.

## Scope

The current repository contains analysis and integration scripts plus data outputs.  
Use this manual for data ingestion, sequence analysis outputs, activity scoring, and report generation.

## Prerequisites

1. Python 3.10+ environment
2. Required packages installed (at minimum: `pandas`, `numpy`)
3. Access to project repository files
4. Input experiment file in TSV or JSON format

## Input Data Requirements

The integration step expects these columns in the experimental dataset:

1. `Plasmid_Variant_Index`
2. `Directed_Evolution_Generation`
3. `DNA_Quantification_fg`
4. `Protein_Quantification_pg`
5. `Control` (boolean)

Sample data is available in:

- `data/sequences/DE_BSU_Pol_Batch_1.tsv`
- `data/sequences/DE_BSU_Pol_Batch_1.json`

## Workflow

### 1. Prepare Inputs

1. Place your experiment file in `data/sequences/` (or another known path).
2. Confirm required columns and data types are present.
3. Ensure control rows are correctly labeled (`Control == True`).

### 2. Run Sequence Analysis (Section 4.a Output)

The integration step expects a populated SQLite database with table `variant_sequences`.

If your branch includes a sequence-processing pipeline script, run it to produce:

1. Variant-level sequence analysis
2. Mutation-level records
3. SQLite database (commonly named `directed_evolution_analysis.db`)

Core analysis modules:

- `analysis/sequence_analyzer.py`
- `analysis/database_queries.py`

### 3. Run Integrated Activity Analysis (Section 4.b)

Use the integration script:

```bash
python analysis/integration_example.py
```

This script:

1. Loads sequence results from SQLite
2. Loads quantification data from TSV/JSON
3. Merges by variant index
4. Calculates activity score per variant
5. Exports integrated outputs

### 4. Generate Reports for Review (Section 4.c Preparation)

Use the query/report utility:

```bash
python analysis/database_queries.py
```

Expected report artifacts include:

1. `all_variants.csv`
2. `all_mutations.csv`
3. `generation_summary.csv`
4. `mutation_frequencies.csv`

### 5. Review Top Performers

Top performers are ranked by `activity_score` in integration outputs.  
Prioritize variants with strong activity and acceptable mutation profiles.

## Troubleshooting

1. Database not found
Cause: sequence-processing step not completed.
Fix: generate the SQLite database before running integration or report scripts.

2. Merge returns fewer rows than expected
Cause: `Plasmid_Variant_Index` does not match DB `variant_index`.
Fix: verify index values and data types.

3. Invalid activity scores
Cause: missing controls, zero/invalid protein measurements, or malformed numeric fields.
Fix: validate controls and quantification columns before analysis.

## Related Documentation

- `docs/activity-metric-and-qc.md`
- `analysis/README.md`
