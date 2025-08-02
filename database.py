import os
import logging
import sqlite3
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from config import Config

# Initialize SQLAlchemy
db = SQLAlchemy()

class ProcessingLog(db.Model):
    """Model for tracking PDF processing status"""
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)
    status = db.Column(db.String(50), nullable=False)  # pending, processing, completed, failed
    stage = db.Column(db.String(100))  # format_detection, ocr, text_extraction, classification, indexing
    error_message = db.Column(db.Text)
    processing_time = db.Column(db.Float)
    document_type = db.Column(db.String(100))  # machine_readable, scanned
    classification_result = db.Column(db.String(100))
    elasticsearch_id = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'status': self.status,
            'stage': self.stage,
            'error_message': self.error_message,
            'processing_time': self.processing_time,
            'document_type': self.document_type,
            'classification_result': self.classification_result,
            'elasticsearch_id': self.elasticsearch_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class DatabaseManager:
    """Utility class for database operations"""
    
    @staticmethod
    def init_db(app):
        """Initialize database with Flask app"""
        db.init_app(app)
        with app.app_context():
            db.create_all()
    
    @staticmethod
    def create_processing_log(filename, file_path, file_size=None):
        """Create a new processing log entry"""
        log_entry = ProcessingLog(
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            status='pending',
            stage='format_detection'
        )
        db.session.add(log_entry)
        db.session.commit()
        return log_entry
    
    @staticmethod
    def update_processing_log(log_id, **kwargs):
        """Update processing log entry"""
        log_entry = ProcessingLog.query.get(log_id)
        if log_entry:
            for key, value in kwargs.items():
                if hasattr(log_entry, key):
                    setattr(log_entry, key, value)
            log_entry.updated_at = datetime.utcnow()
            db.session.commit()
        return log_entry
    
    @staticmethod
    def get_processing_logs(status=None, limit=100):
        """Get processing logs with optional status filter"""
        query = ProcessingLog.query
        if status:
            query = query.filter_by(status=status)
        return query.order_by(ProcessingLog.created_at.desc()).limit(limit).all()
    
    @staticmethod
    def get_processing_stats():
        """Get processing statistics"""
        total = ProcessingLog.query.count()
        completed = ProcessingLog.query.filter_by(status='completed').count()
        failed = ProcessingLog.query.filter_by(status='failed').count()
        pending = ProcessingLog.query.filter_by(status='pending').count()
        processing = ProcessingLog.query.filter_by(status='processing').count()
        
        return {
            'total': total,
            'completed': completed,
            'failed': failed,
            'pending': pending,
            'processing': processing,
            'success_rate': (completed / total * 100) if total > 0 else 0
        }

def setup_logging():
    """Setup logging configuration"""
    Config.create_directories()
    log_file = os.path.join(Config.LOGS_DIR, 'pipeline.log')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)