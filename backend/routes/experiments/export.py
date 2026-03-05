"""
Data export and visualisation routes.

Routes registered here:
  GET  /api/experiments/<experiment_id>/mutations/export
  GET  /api/experiments/<experiment_id>/plots/activity-distribution

Provenance (activity-distribution plot)
----------------------------------------
The violin plot endpoint is derived from
``to_integrate/activity_score_distribution_plot.py``.

Key changes from the original
------------------------------
* **Data source** – Original read rows directly from SQLite using
  ``sqlite3.connect()``.  This version queries the SQLAlchemy ORM
  (PostgreSQL), so the same rendering code works with the production DB.

* **Output mode** – Original called ``plt.savefig(path)`` to write a PNG
  file to disk.  This version renders server-side into an in-memory buffer
  (``io.BytesIO``) and streams the PNG bytes straight to the browser via
  ``send_file()``, so no temp files are created.

* **Matplotlib backend** – ``matplotlib.use('Agg')`` is set explicitly at
  import time to force the *non-interactive* Agg renderer.  This is required
  because Flask workers have no display (no GUI event loop), and importing
  pyplot before setting the backend would raise a ``cannot connect to X server``
  error on headless servers.
"""
import csv as _csv
import io
import uuid

import matplotlib
matplotlib.use('Agg')  # headless — must be before pyplot import
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from flask import request, jsonify, send_file, session
from sqlalchemy.orm import joinedload as _jl

from database import db
from models.experiment import VariantData
from services.experiment_service import experiment_service
from ._base import experiments_bp, require_auth


@experiments_bp.route('/<experiment_id>/mutations/export', methods=['GET'])
def export_mutations_csv(experiment_id: str):
    """
    Stream a CSV of all mutations for an experiment.

    Columns: variant_index, generation, position, wt_aa, mut_aa,
             wt_codon, mut_codon, mutation_type, aa_change, generation_introduced
    """
    user_id = require_auth()
    if not user_id:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401

    try:
        experiment = experiment_service.get_experiment_by_id(experiment_id, user_id)
        if not experiment:
            return jsonify({'success': False, 'error': 'Experiment not found'}), 404

        exp_uuid = uuid.UUID(experiment_id) if isinstance(experiment_id, str) else experiment_id

        # Single query — avoids N+1
        variants = (
            db.query(VariantData)
            .filter(VariantData.experiment_id == exp_uuid)
            .options(_jl(VariantData.mutations))
            .order_by(
                VariantData.generation.asc(),
                VariantData.plasmid_variant_index.asc(),
            )
            .all()
        )

        if not variants:
            return jsonify({'success': False, 'error': 'No variants found for this experiment'}), 404

        output = io.StringIO()
        fieldnames = [
            'variant_index', 'generation',
            'position', 'wt_aa', 'mut_aa',
            'wt_codon', 'mut_codon',
            'mutation_type', 'aa_change',
            'generation_introduced',
        ]
        writer = _csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for v in variants:
            for m in (v.mutations or []):
                writer.writerow({
                    'variant_index':         v.plasmid_variant_index,
                    'generation':            v.generation,
                    'position':              m.position,
                    'wt_aa':                 m.wild_type,
                    'mut_aa':                m.mutant,
                    'wt_codon':              m.wt_codon or '',
                    'mut_codon':             m.mut_codon or '',
                    'mutation_type':         m.mutation_type,
                    'aa_change':             f"{m.wild_type}{m.position}{m.mutant}",
                    'generation_introduced': m.generation_introduced,
                })

        output.seek(0)
        buf = io.BytesIO(output.getvalue().encode('utf-8'))
        safe_name = (experiment.name or experiment_id).replace(' ', '_')

        return send_file(
            buf,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f"{safe_name}_mutations.csv",
        )

    except Exception:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': 'Server error'}), 500


@experiments_bp.route('/<experiment_id>/plots/activity-distribution', methods=['GET'])
def plot_activity_distribution(experiment_id: str):
    """
    Return a PNG of the activity score distribution violin plot.

    Produces a per-generation violin plot using matplotlib (server-side rendering).
    The PNG is streamed directly from memory — no temp files are created.

    Derived from ``to_integrate/activity_score_distribution_plot.py``.
    See the module docstring for a full list of changes.
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    try:
        experiment = experiment_service.get_experiment_by_id(experiment_id, user_id)
        if not experiment:
            return jsonify({'success': False, 'error': 'Experiment not found'}), 404

        exp_uuid = uuid.UUID(experiment_id) if isinstance(experiment_id, str) else experiment_id

        # Only include QC-passed variants that have a calculated activity score.
        # Controls are excluded because they do not have an activity_score.
        variants = (
            db.query(VariantData)
            .filter(
                VariantData.experiment_id == exp_uuid,
                VariantData.qc_status == 'passed',
                VariantData.activity_score.isnot(None),
            )
            .all()
        )

        if not variants:
            return jsonify({
                'success': False,
                'error': 'No QC-passed variants with activity scores'
            }), 404

        df = pd.DataFrame([
            {
                'Directed_Evolution_Generation': v.generation,
                'activity_score': float(v.activity_score),
            }
            for v in variants
        ]).dropna(subset=['Directed_Evolution_Generation', 'activity_score'])

        gens = sorted(df['Directed_Evolution_Generation'].unique())

        # Filter generations with fewer than 2 data points (violin requires ≥2
        # to draw a shape; a single point would raise a LinAlgError in scipy)
        data = [
            df[df['Directed_Evolution_Generation'] == g]['activity_score'].values.astype(float)
            for g in gens
            if len(df[df['Directed_Evolution_Generation'] == g]) >= 2
        ]
        gens = [
            g for g in gens
            if len(df[df['Directed_Evolution_Generation'] == g]) >= 2
        ]

        if not data:
            return jsonify({
                'success': False,
                'error': 'Not enough data points per generation to draw violin plots (need ≥2 per generation)'
            }), 404

        fig, ax = plt.subplots(figsize=(11, 6))
        fig.patch.set_facecolor('#ffffff')
        ax.set_facecolor('#f8fafc')

        violins = ax.violinplot(data, widths=0.75, points=200)

        # Style each violin body (the KDE-smoothed shape):
        # blue fill + edge, slightly transparent
        for pc in violins['bodies']:
            pc.set_facecolor('#bfdbfe')
            pc.set_edgecolor('#3b82f6')
            pc.set_alpha(0.85)
        # Hide the default whisker/cap lines produced by violinplot —
        # we draw our own manual lines below so we can style them precisely
        for part in ('cbars', 'cmins', 'cmaxes'):
            if part in violins:
                violins[part].set_visible(False)

        # Draw manual whiskers, min/max caps, mean (blue), and median (purple)
        for i, v in enumerate(data, start=1):
            vmin   = np.min(v)
            vmax   = np.max(v)
            mean   = np.mean(v)
            median = np.median(v)

            ax.vlines(i, vmin, vmax, linewidth=1.5, colors='#2563eb')
            ax.hlines(vmin,   i - 0.12, i + 0.12, linewidth=1.5, colors='#2563eb')
            ax.hlines(vmax,   i - 0.12, i + 0.12, linewidth=1.5, colors='#2563eb')
            ax.hlines(mean,   i - 0.18, i + 0.18, linewidth=2.5, colors='#1d4ed8')
            ax.hlines(median, i - 0.18, i + 0.18, linewidth=2.5, colors='#7c3aed')

        ax.set_xticks(range(1, len(gens) + 1))
        ax.set_xticklabels([f'Gen {int(g)}' for g in gens], color='#475569')
        ax.tick_params(colors='#475569')
        ax.set_xlabel('Generation', color='#475569', fontsize=10)
        ax.set_ylabel('Activity Score', color='#475569', fontsize=10)
        ax.set_title(
            'Activity Score Distribution by Generation',
            color='#1e293b', fontsize=12, fontweight='bold', pad=10
        )
        for spine in ax.spines.values():
            spine.set_color('#e2e8f0')
        ax.grid(True, color='#e2e8f0', linewidth=0.6, linestyle='--')
        ax.set_axisbelow(True)

        plt.tight_layout()

        # Render to an in-memory PNG buffer and stream it to the client.
        # plt.close() is critical here — without it, subsequent requests
        # would accumulate open figures and leak memory in the Flask process.
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=140, bbox_inches='tight', facecolor='#ffffff')
        plt.close(fig)
        buf.seek(0)

        return send_file(buf, mimetype='image/png')

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
