from flask import Blueprint, request, jsonify, session
from services.experiment_service import experiment_service
from services.experimental_data_parser import parser
from services.activity_calculator import activity_calculator
from services.sequence_analyzer import sequence_analyzer
from models.experiment import Experiment, VariantData, Mutation
from database import db
from sqlalchemy.orm import joinedload
import pandas as pd
import uuid
import math
import threading


def clean_dict_for_json(obj):
    """Convert NaN/Inf values to None for JSON serialization"""
    if isinstance(obj, dict):
        return {k: clean_dict_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_dict_for_json(item) for item in obj]
    elif isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj


experiments_bp = Blueprint('experiments', __name__, url_prefix='/api/experiments')


def require_auth():
    """Check if user is authenticated"""
    user_id = session.get('user_id')
    if not user_id:
        return None
    return user_id


@experiments_bp.route('', methods=['POST'])
def create_experiment():
    """Create a new experiment"""
    user_id = require_auth()
    if not user_id:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        data = request.get_json()
        
        name = data.get('name', '').strip()
        protein_accession = data.get('proteinAccession', '').strip()
        plasmid_sequence = data.get('plasmidSequence', '').strip()
        plasmid_name = data.get('plasmidName', '').strip() or None
        fetch_features = data.get('fetchFeatures', True)
        
        if not name or not protein_accession or not plasmid_sequence:
            return jsonify({
                'success': False,
                'error': 'Name, protein accession, and plasmid sequence are required'
            }), 400
        
        experiment, error = experiment_service.create_experiment(
            user_id=user_id,
            name=name,
            protein_accession=protein_accession,
            plasmid_sequence=plasmid_sequence,
            plasmid_name=plasmid_name,
            fetch_features=fetch_features
        )
        
        if error:
            return jsonify({'success': False, 'error': error}), 400
        
        # Build response with validation summary for frontend
        experiment_dict = experiment.to_dict(include_sequences=True)
        
        return jsonify({
            'success': True,
            'experiment': experiment_dict,
            'validation': {
                'isValid': experiment.validation_status == 'valid',
                'message': experiment.validation_message
            }
        }), 201
        
    except Exception as e:
        return jsonify({'success': False, 'error': 'Server error'}), 500


@experiments_bp.route('', methods=['GET'])
def list_experiments():
    """Get all experiments for the current user"""
    user_id = require_auth()
    if not user_id:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        limit = min(int(request.args.get('limit', 100)), 100)
        offset = int(request.args.get('offset', 0))
        
        experiments = experiment_service.get_experiments_by_user(user_id, limit=limit, offset=offset)
        
        return jsonify({
            'success': True,
            'experiments': [exp.to_dict() for exp in experiments]
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': 'Server error'}), 500


@experiments_bp.route('/<experiment_id>', methods=['GET'])
def get_experiment(experiment_id: str):
    """Get a single experiment by ID with its variants"""
    user_id = require_auth()
    if not user_id:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        experiment = experiment_service.get_experiment_by_id(experiment_id, user_id)
        
        if not experiment:
            return jsonify({'success': False, 'error': 'Experiment not found'}), 404
        
        # Get variants for this experiment - convert string ID to UUID
        # Limit variants and exclude mutations for performance
        try:
            exp_uuid = uuid.UUID(experiment_id) if isinstance(experiment_id, str) else experiment_id
            limit = min(int(request.args.get('limit', 1000)), 5000)  # Default 1000, max 5000
            
            variants = db.query(VariantData).filter_by(
                experiment_id=exp_uuid
            ).order_by(
                VariantData.generation.asc(),
                VariantData.activity_score.desc().nullslast()
            ).limit(limit).all()
            
            print(f"Loaded {len(variants)} variants for experiment {experiment_id}")
        except Exception as e:
            print(f"Error fetching variants: {e}")
            variants = []
        
        return jsonify({
            'success': True,
            'experiment': experiment.to_dict(include_sequences=True),
            'variants': [v.to_dict(include_mutations=False) for v in variants]
        }), 200
        
    except Exception as e:
        print(f"Error in get_experiment: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': 'Server error'}), 500


@experiments_bp.route('/<experiment_id>', methods=['PATCH'])
def update_experiment(experiment_id: str):
    """Update experiment metadata"""
    user_id = require_auth()
    if not user_id:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        data = request.get_json()
        
        name = data.get('name')
        plasmid_name = data.get('plasmidName')
        
        experiment = experiment_service.update_experiment(
            experiment_id=experiment_id,
            user_id=user_id,
            name=name,
            plasmid_name=plasmid_name
        )
        
        if not experiment:
            return jsonify({'success': False, 'error': 'Experiment not found'}), 404
        
        return jsonify({
            'success': True,
            'experiment': experiment.to_dict(include_sequences=True)
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': 'Server error'}), 500


@experiments_bp.route('/<experiment_id>', methods=['DELETE'])
def delete_experiment(experiment_id: str):
    """Delete an experiment"""
    user_id = require_auth()
    if not user_id:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        success = experiment_service.delete_experiment(experiment_id, user_id)
        
        if not success:
            return jsonify({'success': False, 'error': 'Experiment not found'}), 404
        
        return jsonify({'success': True, 'message': 'Experiment deleted'}), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': 'Server error'}), 500


@experiments_bp.route('/<experiment_id>/upload-data', methods=['POST'])
def upload_experimental_data(experiment_id: str):
    """
    Upload and process experimental data (TSV/JSON) for an experiment.
    Handles parsing, QC, sequence analysis, and activity score calculation.
    """
    user_id = require_auth()
    if not user_id:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        # Get experiment and verify ownership
        experiment = experiment_service.get_experiment_by_id(experiment_id, user_id)
        if not experiment:
            return jsonify({'success': False, 'error': 'Experiment not found'}), 404
        
        # Extract data we need from experiment (before closing session)
        exp_id = experiment.id
        wt_protein_seq = experiment.wt_protein_sequence
        plasmid_seq = experiment.plasmid_sequence
        
        # Get request data
        data = request.get_json()
        file_content = data.get('data', '')
        file_format = data.get('format', 'tsv').lower()
        
        if not file_content:
            return jsonify({'success': False, 'error': 'No file content provided'}), 400
        
        # Step 1: Parse and validate file
        print(f"Step 1: Parsing {file_format} file...")
        try:
            valid_df, control_df, rejected_df, parse_summary = parser.process_file(
                file_content, 
                file_format
            )
            print(f"Parsed: {parse_summary['valid_rows']} valid, {parse_summary['control_rows']} controls, {parse_summary['rejected_rows']} rejected")
        except ValueError as e:
            print(f"Parse error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 400
        
        if valid_df.empty:
            return jsonify({
                'success': False, 
                'error': 'All rows failed QC validation',
                'rejected': parse_summary['rejected_details']
            }), 400
        
        # Step 2: Calculate activity scores (using both valid variants and controls)
        print("Step 2: Calculating activity scores...")
        try:
            # Combine valid variants with controls for activity calculation
            combined_df = pd.concat([valid_df, control_df], ignore_index=True) if not control_df.empty else valid_df
            # Calculate scores for the combined dataset
            scored_df = activity_calculator.calculate_activity_scores(combined_df)
            
            # Separate controls and variants after scoring
            control_scored_df = scored_df[scored_df['is_control'] == True].copy() if not control_df.empty else pd.DataFrame()
            valid_df = scored_df[scored_df['is_control'] == False].copy()
            
            print(f"Activity scores calculated for {len(valid_df)} variants and {len(control_scored_df)} controls")
        except ValueError as e:
            print(f"Activity calculation error: {e}")
            return jsonify({'success': False, 'error': f'Activity calculation failed: {str(e)}'}), 400
        
        # Step 3: Prepare records — sequence analysis runs separately via /analyze-sequences
        print("Step 3: Preparing records (sequence analysis deferred to /analyze-sequences)...")
        analyzed_variants = valid_df.to_dict('records')
        analyzed_controls = control_scored_df.to_dict('records') if not control_scored_df.empty else []

        
        # Step 4: Store in database in batches to avoid timeout
        # Store both variants AND controls so Gen 0 controls are available for mutation analysis
        print(f"Step 4: Storing {len(analyzed_variants)} variants and {len(analyzed_controls)} controls in database...")
        stored_count = 0
        metadata_columns = parse_summary['metadata_columns']
        BATCH_SIZE = 50  # Commit every 50 variants to avoid long transactions
        
        # Combine variants and controls for storage
        all_records = analyzed_variants + analyzed_controls
        
        for idx, variant_data in enumerate(all_records):
            # Create variant record
            variant = VariantData(
                experiment_id=exp_id,
                plasmid_variant_index=variant_data['plasmid_variant_index'],
                parent_plasmid_variant=variant_data.get('parent_plasmid_variant'),
                generation=int(variant_data['generation']),
                assembled_dna_sequence=variant_data['assembled_dna_sequence'],
                dna_yield=variant_data['dna_yield'],
                protein_yield=variant_data['protein_yield'],
                is_control=variant_data['is_control'],
                protein_sequence=variant_data.get('protein_sequence'),
                activity_score=variant_data.get('activity_score'),
                qc_status='passed',
                qc_message=None
            )
            
            # Store extra metadata
            if metadata_columns:
                metadata = {col: variant_data.get(col) for col in metadata_columns if col in variant_data}
                variant.extra_metadata = metadata
            
            # Store mutations using relationship (SQLAlchemy will handle variant_id)
            for mut in variant_data.get('mutations', []):
                mutation = Mutation(
                    position=mut['position'],
                    wild_type=mut['wild_type'],
                    mutant=mut['mutant'],
                    mutation_type=mut['type'],
                    generation_introduced=variant_data['generation']  # Simplified
                )
                variant.mutations.append(mutation)
            
            db.add(variant)
            stored_count += 1
            
            # Commit in batches to avoid long-running transactions
            if (idx + 1) % BATCH_SIZE == 0:
                db.commit()
                print(f"  Committed batch: {stored_count}/{len(all_records)} records")
        
        # Final commit for remaining items
        db.commit()
        print(f"Database commit successful. Stored {len(analyzed_variants)} variants + {len(analyzed_controls)} controls = {stored_count} total records.")
        
        # Step 5: Calculate statistics for response
        print("Step 5: Generating statistics...")
        generation_stats = activity_calculator.get_generation_statistics(valid_df)
        
        # Build response
        stats_list = generation_stats.to_dict('records') if not generation_stats.empty else []
        stats_list = clean_dict_for_json(stats_list)
        
        response = {
            'success': True,
            'parsed': parse_summary['total_rows'],
            'processed': stored_count,
            'variants': len(analyzed_variants),
            'controls': len(analyzed_controls),
            'passedQC': parse_summary['valid_rows'],
            'failedQC': parse_summary['rejected_rows'],
            'errors': [
                {
                    'row': r['qc_row_number'],
                    'message': r['qc_error_reason']
                }
                for r in parse_summary['rejected_details']
            ][:20],  # Limit to first 20 errors
            'warnings': [],
            'generationStats': stats_list
        }
        
        print(f"Upload completed successfully! Returning response.")
        return jsonify(response), 200
        
    except Exception as e:
        db.rollback()
        print(f"Error in upload_experimental_data: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': 'Server error during data processing'}), 500


@experiments_bp.route('/<experiment_id>/variants', methods=['GET'])
def get_experiment_variants(experiment_id: str):
    """Get all variant data for an experiment"""
    user_id = require_auth()
    if not user_id:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        # Verify experiment ownership
        experiment = experiment_service.get_experiment_by_id(experiment_id, user_id)
        if not experiment:
            return jsonify({'success': False, 'error': 'Experiment not found'}), 404
        
        # Get variants with optional pagination
        exp_uuid = uuid.UUID(experiment_id) if isinstance(experiment_id, str) else experiment_id
        limit = min(int(request.args.get('limit', 1000)), 5000)  # Default 1000, max 5000
        include_mutations = request.args.get('include_mutations', 'false').lower() == 'true'
        
        variants = db.query(VariantData).filter_by(
            experiment_id=exp_uuid
        ).order_by(
            VariantData.generation.asc(),
            VariantData.activity_score.desc().nullslast()
        ).limit(limit).all()
        
        return jsonify({
            'success': True,
            'variants': [v.to_dict(include_mutations=include_mutations) for v in variants]
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': 'Server error'}), 500


@experiments_bp.route('/<experiment_id>/top-performers', methods=['GET'])
def get_top_performers(experiment_id: str):
    """Get top performing variants by activity score"""
    user_id = require_auth()
    if not user_id:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        # Verify experiment ownership
        experiment = experiment_service.get_experiment_by_id(experiment_id, user_id)
        if not experiment:
            return jsonify({'success': False, 'error': 'Experiment not found'}), 404
        
        # Get top performers
        limit = min(int(request.args.get('limit', 10)), 50)
        include_mutations = request.args.get('include_mutations', 'true').lower() == 'true'
        
        exp_uuid = uuid.UUID(experiment_id) if isinstance(experiment_id, str) else experiment_id
        
        query = db.query(VariantData)
        if include_mutations:
            query = query.options(joinedload(VariantData.mutations))
        
        variants = query.filter_by(
            experiment_id=exp_uuid,
            is_control=False
        ).filter(
            VariantData.activity_score.isnot(None)
        ).order_by(
            VariantData.activity_score.desc()
        ).limit(limit).all()
        
        return jsonify({
            'success': True,
            'topPerformers': [v.to_dict(include_sequences=True, include_mutations=include_mutations) for v in variants]
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': 'Server error'}), 500


@experiments_bp.route('/<experiment_id>/statistics', methods=['GET'])
def get_experiment_statistics(experiment_id: str):
    """Get statistical summary of experiment data"""
    user_id = require_auth()
    if not user_id:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        # Verify experiment ownership
        experiment = experiment_service.get_experiment_by_id(experiment_id, user_id)
        if not experiment:
            return jsonify({'success': False, 'error': 'Experiment not found'}), 404
        
        # Get all variants for this experiment
        exp_uuid = uuid.UUID(experiment_id) if isinstance(experiment_id, str) else experiment_id
        variants = db.query(VariantData).filter_by(
            experiment_id=exp_uuid
        ).all()
        
        if not variants:
            return jsonify({
                'success': True,
                'statistics': {
                    'totalVariants': 0,
                    'passedQC': 0,
                    'failedQC': 0,
                    'generations': []
                }
            }), 200
        
        # Convert to DataFrame for analysis
        variants_data = []
        for v in variants:
            variants_data.append({
                'generation': v.generation,
                'activity_score': v.activity_score,
                'is_control': v.is_control,
                'qc_status': v.qc_status
            })
        
        df = pd.DataFrame(variants_data)
        
        # Calculate generation statistics
        generation_stats = activity_calculator.get_generation_statistics(df)
        stats_list = generation_stats.to_dict('records') if not generation_stats.empty else []
        stats_list = clean_dict_for_json(stats_list)
        
        return jsonify({
            'success': True,
            'statistics': {
                'totalVariants': len(variants),
                'passedQC': len([v for v in variants if v.qc_status == 'passed']),
                'failedQC': len([v for v in variants if v.qc_status == 'failed']),
                'generationStats': stats_list
            }
        }), 200
        
    except Exception as e:
        print(f"Error in get_experiment_statistics: {str(e)}")
        return jsonify({'success': False, 'error': 'Server error'}), 500


def _set_analysis_status(exp_id, status: str, message: str):
    """Helper to update experiment analysis status safely."""
    try:
        experiment = db.query(Experiment).filter_by(id=exp_id).first()
        if experiment:
            experiment.analysis_status = status
            experiment.analysis_message = message
            db.commit()
    except Exception as e:
        print(f"Could not update analysis status: {e}")
        db.rollback()


def _run_analysis_background(app, exp_id, wt_protein_seq: str, plasmid_seq: str):
    """
    Runs in a background thread. Uses app context so the DB session works correctly.
    The HTTP response has already been returned before this runs.
    """
    with app.app_context():
        try:
            print(f"[BG] Starting sequence analysis for {exp_id}...")

            all_data = db.query(VariantData).filter_by(experiment_id=exp_id).all()
            if not all_data:
                _set_analysis_status(exp_id, 'failed', 'No data found to analyze')
                return

            controls = [v for v in all_data if v.is_control and v.generation == 0]
            variants = [v for v in all_data if not v.is_control]
            print(f"[BG] {len(variants)} variants, {len(controls)} Gen-0 controls")

            # Use Gen-0 control plasmid as WT reference if available
            if controls:
                print("[BG] Using Generation 0 control as WT reference...")
                ref_plasmid = controls[0].assembled_dna_sequence
            else:
                print("[BG] No Gen-0 controls found — using experiment plasmid as reference")
                ref_plasmid = plasmid_seq

            variants_data = [
                {'id': str(v.id), 'assembled_dna_sequence': v.assembled_dna_sequence, 'generation': v.generation}
                for v in variants
            ]

            print("[BG] Running sequence analyzer...")
            analyzed = sequence_analyzer.analyze_variant_batch(
                variants_data, wt_protein_seq, ref_plasmid
            )
            print(f"[BG] Analysis complete for {len(analyzed)} variants")

            BATCH_SIZE = 50
            updated_count = 0

            for idx, result in enumerate(analyzed):
                variant = db.query(VariantData).filter_by(
                    id=uuid.UUID(result['id'])
                ).first()

                if variant:
                    variant.protein_sequence = result.get('protein_sequence')

                    # Delete existing mutations then insert fresh ones
                    db.query(Mutation).filter_by(variant_id=variant.id).delete()

                    for mut in result.get('mutations', []):
                        db.add(Mutation(
                            variant_id=variant.id,
                            position=mut['position'],
                            wild_type=mut['wild_type'],
                            mutant=mut['mutant'],
                            wt_codon=mut.get('wt_codon'),
                            mut_codon=mut.get('mut_codon'),
                            mut_aa=mut.get('mut_aa'),
                            mutation_type=mut.get('type', 'non-synonymous'),
                            generation_introduced=variant.generation
                        ))

                    updated_count += 1

                    if (idx + 1) % BATCH_SIZE == 0:
                        db.commit()
                        print(f"[BG] Committed {updated_count}/{len(analyzed)} variants")

            db.commit()
            print(f"[BG] Database update complete: {updated_count} variants updated")
            _set_analysis_status(exp_id, 'completed', f'Successfully analyzed {updated_count} variants')

        except Exception as e:
            import traceback
            traceback.print_exc()
            db.rollback()
            _set_analysis_status(exp_id, 'failed', f'Analysis failed: {str(e)}')


@experiments_bp.route('/<experiment_id>/analyze-sequences', methods=['POST'])
def analyze_sequences(experiment_id: str):
    """
    Kick off background sequence analysis. Returns 200 immediately.
    Poll GET /<experiment_id> to check analysis_status field.
    """
    user_id = require_auth()
    if not user_id:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401

    try:
        experiment = experiment_service.get_experiment_by_id(experiment_id, user_id)
        if not experiment:
            return jsonify({'success': False, 'error': 'Experiment not found'}), 404

        if experiment.analysis_status == 'analyzing':
            return jsonify({'success': False, 'error': 'Analysis already in progress'}), 409

        exp_id = experiment.id
        wt_protein_seq = experiment.wt_protein_sequence
        plasmid_seq = experiment.plasmid_sequence

        # Set status synchronously before spawning thread
        experiment.analysis_status = 'analyzing'
        experiment.analysis_message = 'Analysis queued...'
        db.commit()

        # Spawn background thread — HTTP response returns immediately
        from flask import current_app
        app = current_app._get_current_object()

        thread = threading.Thread(
            target=_run_analysis_background,
            args=(app, exp_id, wt_protein_seq, plasmid_seq),
            daemon=True
        )
        thread.start()

        return jsonify({
            'success': True,
            'message': 'Sequence analysis started',
            'status': 'analyzing'
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        db.rollback()
        return jsonify({'success': False, 'error': f'Failed to start analysis: {str(e)}'}), 500
