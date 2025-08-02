import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Base paths
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    INPUT_DIR = os.path.join(DATA_DIR, 'input')
    PROCESSED_DIR = os.path.join(DATA_DIR, 'processed')
    MODELS_DIR = os.path.join(DATA_DIR, 'models')
    LOGS_DIR = os.path.join(BASE_DIR, 'logs')
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', f'sqlite:///{os.path.join(BASE_DIR, "pipeline.db")}')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Elasticsearch
    ELASTICSEARCH_URL = os.getenv('ELASTICSEARCH_URL', 'http://localhost:9200')
    ELASTICSEARCH_INDEX = os.getenv('ELASTICSEARCH_INDEX', 'pdf_documents')
    
    # OCR settings
    TESSERACT_CMD = os.getenv('TESSERACT_CMD', 'tesseract')
    OCR_LANGUAGES = os.getenv('OCR_LANGUAGES', 'eng')
    
    # Classification
    CLASSIFICATION_MODEL_PATH = os.path.join(MODELS_DIR, 'document_classifier.pkl')
    VECTORIZER_PATH = os.path.join(MODELS_DIR, 'vectorizer.pkl')
    
    # File monitoring
    WATCH_DIRECTORY = os.getenv('WATCH_DIRECTORY', INPUT_DIR)
    PROCESSED_EXTENSION = '.processed'
    
    # Web interface
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Service settings
    SERVICE_NAME = 'PDFProcessingPipeline'
    SERVICE_DISPLAY_NAME = 'PDF Processing Pipeline Service'
    SERVICE_DESCRIPTION = 'Monitors directory for PDFs and processes them through OCR, classification, and indexing'
    
    @classmethod
    def create_directories(cls):
        """Create all necessary directories"""
        directories = [
            cls.DATA_DIR, cls.INPUT_DIR, cls.PROCESSED_DIR, 
            cls.MODELS_DIR, cls.LOGS_DIR
        ]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)