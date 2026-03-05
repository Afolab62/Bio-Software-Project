from typing import Optional, List
from sqlalchemy.exc import IntegrityError
from models.experiment import Experiment
from database import get_db
from services.staging import stage_experiment_validate_plasmid


class ExperimentService:
    """Service for managing experiments with PostgreSQL storage"""
    
    def create_experiment(
        self,
        user_id: str,
        name: str,
        protein_accession: str,
        plasmid_sequence: str,
        plasmid_name: Optional[str] = None,
        fetch_features: bool = True
    ) -> tuple[Optional[Experiment], Optional[str]]:
        """
        Create a new experiment with plasmid validation.
        Returns (experiment, error_message)
        """
        db = get_db()
        try:
            # Validate plasmid against UniProt protein
            validation_result = stage_experiment_validate_plasmid(
                accession=protein_accession,
                plasmid_fasta_text=plasmid_sequence,
                fetch_features=fetch_features
            )
            
            # Check for errors from staging
            if validation_result.get('error'):
                return None, validation_result['error']
            
            # Determine validation status
            validation_data = validation_result.get('validation', {})
            is_valid = validation_data.get('is_valid', False)
            validation_status = 'valid' if is_valid else 'invalid'
            
            # Create validation message
            if is_valid:
                match_type = validation_data.get('match_type', 'unknown')
                identity = validation_data.get('identity', 0)
                validation_message = f"Plasmid validated successfully ({match_type} match, identity: {identity:.2%})"
            else:
                validation_message = validation_data.get('notes', 'Validation failed')
            
            # Create experiment
            experiment = Experiment(
                user_id=user_id,
                name=name,
                protein_accession=protein_accession.strip(),
                wt_protein_sequence=validation_result.get('wt_protein', ''),
                protein_features=validation_result.get('features'),
                plasmid_name=plasmid_name or f"Plasmid-{protein_accession}",
                plasmid_sequence=plasmid_sequence,
                validation_status=validation_status,
                validation_message=validation_message,
                validation_data=validation_data
            )
            
            db.add(experiment)
            db.commit()
            db.refresh(experiment)
            
            return experiment, None
            
        except Exception as e:
            db.rollback()
            return None, f"Failed to create experiment: {str(e)}"
        finally:
            db.close()
    
    def get_experiment_by_id(self, experiment_id: str, user_id: str) -> Optional[Experiment]:
        """Get experiment by ID (ensuring it belongs to user)"""
        db = get_db()
        try:
            experiment = db.query(Experiment).filter(
                Experiment.id == experiment_id,
                Experiment.user_id == user_id
            ).first()
            return experiment
        finally:
            db.close()
    
    def get_experiments_by_user(self, user_id: str, limit: int = 100, offset: int = 0) -> List[Experiment]:
        """Get all experiments for a user"""
        db = get_db()
        try:
            experiments = db.query(Experiment).filter(
                Experiment.user_id == user_id
            ).order_by(Experiment.created_at.desc()).limit(limit).offset(offset).all()
            return experiments
        finally:
            db.close()
    
    def update_experiment(
        self,
        experiment_id: str,
        user_id: str,
        name: Optional[str] = None,
        plasmid_name: Optional[str] = None
    ) -> Optional[Experiment]:
        """Update experiment metadata (not sequences)"""
        db = get_db()
        try:
            experiment = db.query(Experiment).filter(
                Experiment.id == experiment_id,
                Experiment.user_id == user_id
            ).first()
            
            if not experiment:
                return None
            
            if name is not None:
                experiment.name = name
            if plasmid_name is not None:
                experiment.plasmid_name = plasmid_name
            
            db.commit()
            db.refresh(experiment)
            
            return experiment
        except Exception:
            db.rollback()
            return None
        finally:
            db.close()
    
    def delete_experiment(self, experiment_id: str, user_id: str) -> bool:
        """Delete an experiment (ensuring it belongs to user)"""
        db = get_db()
        try:
            experiment = db.query(Experiment).filter(
                Experiment.id == experiment_id,
                Experiment.user_id == user_id
            ).first()
            
            if not experiment:
                return False
            
            db.delete(experiment)
            db.commit()
            return True
        except Exception:
            db.rollback()
            return False
        finally:
            db.close()


# Global instance
experiment_service = ExperimentService()
