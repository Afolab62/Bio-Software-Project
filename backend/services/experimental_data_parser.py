"""
Service for parsing experimental data files (TSV/JSON) and validating them.
Based on requirements 3a, 3b, and 3c from the briefing.
"""

import pandas as pd
import io
from typing import Dict, List, Tuple, Optional, Any


# Essential fields required in the data
ESSENTIAL_FIELDS = {
    "plasmid_variant_index": float,
    "parent_plasmid_variant": float,
    "generation": int,
    "assembled_dna_sequence": str,
    "dna_yield": float,
    "protein_yield": float,
    "is_control": bool
}

# Column name synonyms for flexible parsing
COLUMN_SYNONYMS = {
    "plasmid_variant_index": [
        "variant_index", "plasmid_id", "plasmid_variant_index",
        "variant_id", "index"
    ],
    "parent_plasmid_variant": [
        "parent_variant", "parent_id", "parent_plasmid_variant",
        "parent", "parent_index"
    ],
    "generation": [
        "generation", "directed_evolution_generation", 
        "evolution_generation", "gen"
    ],
    "assembled_dna_sequence": [
        "dna_sequence", "sequence", "assembled_sequence",
        "assembled_dna_sequence", "plasmid_sequence"
    ],
    "dna_yield": [
        "dna_quantification_fg", "dna_qty_fg", "dna_yield",
        "dna_concentration_fg", "dna_quantification"
    ],
    "protein_yield": [
        "protein_quantification_pg", "protein_qty_pg", "protein_yield",
        "protein_concentration_pg", "protein_quantification"
    ],
    "is_control": [
        "control", "is_control", "control_sample", "iscontrol"
    ]
}


def clean_column_name(col: str) -> str:
    """Normalize column names to lowercase with underscores"""
    return col.strip().lower().replace(" ", "_").replace("-", "_")


def build_synonym_map(synonyms: Dict[str, List[str]]) -> Dict[str, str]:
    """Build reverse lookup: synonym -> canonical name"""
    synonym_map = {}
    for canonical, variants in synonyms.items():
        for variant in variants:
            synonym_map[clean_column_name(variant)] = canonical
    return synonym_map


class ExperimentalDataParser:
    """Parser for experimental data files with flexible column mapping"""
    
    def __init__(self):
        self.synonym_map = build_synonym_map(COLUMN_SYNONYMS)
        self.essential_field_names = list(ESSENTIAL_FIELDS.keys())
    
    def parse_file(self, file_content: str, file_format: str) -> pd.DataFrame:
        """
        Parse TSV or JSON file content into a DataFrame
        
        Args:
            file_content: String content of the file
            file_format: Either 'tsv' or 'json'
        
        Returns:
            Parsed DataFrame
        
        Raises:
            ValueError: If format is unsupported or parsing fails
        """
        try:
            if file_format.lower() in ['tsv', 'txt']:
                df = pd.read_csv(io.StringIO(file_content), sep='\t')
            elif file_format.lower() == 'json':
                df = pd.read_json(io.StringIO(file_content))
            else:
                raise ValueError(f"Unsupported file format: {file_format}")
            
            if df.empty:
                raise ValueError("File contains no data")
            
            return df
        except Exception as e:
            raise ValueError(f"Failed to parse file: {str(e)}")
    
    def map_columns(self, df_columns: List[str]) -> Tuple[Dict[str, str], List[str]]:
        """
        Map DataFrame columns to canonical field names
        
        Args:
            df_columns: List of column names from the DataFrame
        
        Returns:
            Tuple of (column_mapping dict, list of missing essential fields)
        """
        # Track original -> cleaned -> canonical mappings
        original_to_clean = {c: clean_column_name(c) for c in df_columns}
        clean_to_original = {v: k for k, v in original_to_clean.items()}
        cleaned_cols = list(clean_to_original.keys())
        
        # Auto-map using synonyms
        mapping = {}
        used_cleaned = set()
        
        for cleaned_col in cleaned_cols:
            if cleaned_col in self.synonym_map:
                canonical = self.synonym_map[cleaned_col]
                if canonical not in mapping.values():  # Avoid duplicates
                    mapping[cleaned_col] = canonical
                    used_cleaned.add(cleaned_col)
        
        # Left-to-right assignment for remaining fields
        remaining_cleaned = [c for c in cleaned_cols if c not in used_cleaned]
        already_assigned = set(mapping.values())
        remaining_fields = [f for f in self.essential_field_names if f not in already_assigned]
        
        for col, field in zip(remaining_cleaned, remaining_fields):
            mapping[col] = field
        
        # Convert back to original column names
        final_mapping = {clean_to_original[k]: v for k, v in mapping.items()}
        
        # Check for missing fields
        mapped_fields = set(mapping.values())
        missing_fields = [f for f in self.essential_field_names if f not in mapped_fields]
        
        return final_mapping, missing_fields
    
    def coerce_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Convert DataFrame columns to expected types
        
        Args:
            df: DataFrame with canonical column names
        
        Returns:
            DataFrame with coerced types
        """
        df = df.copy()
        
        for col, dtype in ESSENTIAL_FIELDS.items():
            if col not in df.columns:
                continue
            
            if dtype == float:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            elif dtype == int:
                df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')
            elif dtype == bool:
                # Handle various boolean representations
                df[col] = df[col].map(
                    {1: True, 0: False, "1": True, "0": False,
                     "true": True, "false": False,
                     "True": True, "False": False,
                     True: True, False: False}
                )
            elif dtype == str:
                df[col] = df[col].astype(str)
        
        return df
    
    def validate_row(self, row: pd.Series) -> List[str]:
        """
        Validate a single row for QC
        
        Args:
            row: DataFrame row as Series
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        # Check for missing essential fields
        for field in self.essential_field_names:
            if pd.isna(row.get(field)):
                errors.append(f"Missing value for {field}")
        
        # Biological/logical validation rules
        if pd.notna(row.get("generation")) and row["generation"] < 0:
            errors.append("Generation cannot be negative")
        
        if pd.notna(row.get("dna_yield")) and row["dna_yield"] < 0:
            errors.append("DNA yield cannot be negative")
        
        if pd.notna(row.get("protein_yield")) and row["protein_yield"] < 0:
            errors.append("Protein yield cannot be negative")
        
        if row.get("is_control") not in [True, False]:
            errors.append("is_control must be boolean")
        
        # DNA sequence validation
        seq = row.get("assembled_dna_sequence")
        if isinstance(seq, str) and seq:
            if not set(seq.upper()).issubset(set("ATCGN")):  # Allow N for ambiguous bases
                errors.append("DNA sequence contains invalid characters")
        
        return errors
    
    def process_file(
        self, 
        file_content: str, 
        file_format: str
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
        """
        Complete processing pipeline for experimental data file
        
        Args:
            file_content: String content of the file
            file_format: Either 'tsv' or 'json'
        
        Returns:
            Tuple of (valid_df, control_df, rejected_df, summary_dict)
            - valid_df: DataFrame with non-control rows that passed QC
            - control_df: DataFrame with control variants (used for baseline calculation)
            - rejected_df: DataFrame with rows that failed QC
            - summary_dict: Statistics about parsing
        
        Raises:
            ValueError: If file cannot be parsed or essential fields are missing
        """
        # Parse file
        df = self.parse_file(file_content, file_format)
        
        # Map columns
        column_mapping, missing_fields = self.map_columns(df.columns.tolist())
        
        if missing_fields:
            raise ValueError(
                f"Missing essential fields: {', '.join(missing_fields)}. "
                f"Cannot proceed without these columns."
            )
        
        # Rename columns to canonical names
        df = df.rename(columns=column_mapping)
        
        # Identify extra metadata columns
        metadata_columns = [c for c in df.columns if c not in self.essential_field_names]
        
        # Coerce types
        df = self.coerce_types(df)
        
        # Validate each row
        valid_rows = []
        rejected_rows = []
        control_rows = []
        
        for idx, row in df.iterrows():
            errors = self.validate_row(row)
            
            if errors:
                row_dict = row.to_dict()
                row_dict['qc_error_reason'] = "; ".join(errors)
                row_dict['qc_row_number'] = idx + 2  # +2 for header and 1-based indexing
                rejected_rows.append(row_dict)
            else:
                row_dict = row.to_dict()
                # Separate controls from valid variants
                if row.get('is_control') is True:
                    control_rows.append(row_dict)
                else:
                    valid_rows.append(row_dict)
        
        valid_df = pd.DataFrame(valid_rows)  # Non-control variants only
        rejected_df = pd.DataFrame(rejected_rows)  # Actual QC failures only
        control_df = pd.DataFrame(control_rows)  # Controls for internal use
        
        # Build summary
        summary = {
            'total_rows': len(df),
            'valid_rows': len(valid_df),
            'rejected_rows': len(rejected_df),
            'control_rows': len(control_df),
            'column_mapping': column_mapping,
            'metadata_columns': metadata_columns,
            'rejected_details': rejected_rows
        }
        
        return valid_df, control_df, rejected_df, summary


# Singleton instance
parser = ExperimentalDataParser()
