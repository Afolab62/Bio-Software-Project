from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from database import Base
import uuid


class Experiment(Base):
    """Experiment model for storing directed evolution experiments"""
    __tablename__ = 'experiments'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    
    # UniProt data
    protein_accession = Column(String(50), nullable=False)
    wt_protein_sequence = Column(Text, nullable=False)
    protein_features = Column(JSONB, nullable=True)  # Store UniProt features as JSON
    
    # Plasmid data
    plasmid_name = Column(String(255), nullable=True)
    plasmid_sequence = Column(Text, nullable=False)
    
    # Validation results
    validation_status = Column(String(20), nullable=False, default='pending')  # pending, valid, invalid
    validation_message = Column(Text, nullable=True)
    validation_data = Column(JSONB, nullable=True)  # Full validation result from plasmid_validation
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def to_dict(self, include_sequences=False):
        """Convert experiment to dictionary"""
        # Extract protein name from features if available
        protein_name = None
        if self.protein_features and isinstance(self.protein_features, dict):
            protein_name = self.protein_features.get('name')
        
        data = {
            'id': str(self.id),
            'userId': str(self.user_id),
            'name': self.name,
            'proteinAccession': self.protein_accession,
            'proteinName': protein_name,
            'plasmidName': self.plasmid_name,
            'validationStatus': self.validation_status,
            'validationMessage': self.validation_message,
            'createdAt': self.created_at.isoformat(),
            'updatedAt': self.updated_at.isoformat(),
        }
        
        if include_sequences:
            data['wtProteinSequence'] = self.wt_protein_sequence
            data['plasmidSequence'] = self.plasmid_sequence
            data['proteinFeatures'] = self.protein_features
            data['validationData'] = self.validation_data
        
        return data
