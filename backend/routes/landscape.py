import uuid
from flask import Blueprint, request, jsonify, session
from database import db
from models.experiment import VariantData
from services.landscape_service import compute_fitness_landscape

landscape_bp = Blueprint('landscape', __name__, url_prefix='/api/experiments')


def require_auth():
    user_id = session.get('user_id')
    if not user_id:
        return None
    return user_id


@landscape_bp.route('/<experiment_id>/landscape', methods=['GET'])
def get_fitness_landscape(experiment_id: str):
    """
    Compute and return a 3D fitness landscape for an experiment.
    Query params:
        method: "pca" (default) | "tsne" | "umap"
        resolution: grid resolution integer (default 50)
    """
    user_id = require_auth()
    if not user_id:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401

    try:
        method = request.args.get('method', 'pca').lower()
        resolution = min(int(request.args.get('resolution', 50)), 100)

        if method not in ('pca', 'tsne', 'umap'):
            return jsonify({'success': False, 'error': 'method must be pca, tsne, or umap'}), 400

        exp_uuid = uuid.UUID(experiment_id)

        # Only use variants that have been sequence-analysed and passed QC
        variants = (
            db.query(VariantData)
            .filter_by(experiment_id=exp_uuid, qc_status='passed', is_control=False)
            .filter(VariantData.protein_sequence.isnot(None))
            .filter(VariantData.activity_score.isnot(None))
            .all()
        )

        if len(variants) < 3:
            return jsonify({
                'success': False,
                'error': f'Need at least 3 analysed variants (found {len(variants)}). '
                         'Run sequence analysis first.'
            }), 422

        sequences = [v.protein_sequence for v in variants]
        activity_scores = [v.activity_score for v in variants]
        variant_ids = [str(v.id) for v in variants]

        landscape = compute_fitness_landscape(
            sequences=sequences,
            activity_scores=activity_scores,
            method=method,
            grid_resolution=resolution,
        )
        landscape['variant_ids'] = variant_ids

        return jsonify({'success': True, **landscape}), 200

    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 422
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Landscape computation failed: {str(e)}'}), 500
