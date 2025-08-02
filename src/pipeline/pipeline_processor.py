import os
import time
import logging
from datetime import datetime
from config import Config
from database import DatabaseManager, setup_logging
from src.pipeline.format_detector import FormatDetector
from src.pipeline.ocr_processor import OCRProcessor
from src.pipeline.text_extractor import TextExtractor
from src.pipeline.classifier import DocumentClassifier
from src.pipeline.elasticsearch_indexer import ElasticsearchIndexer

logger = logging.getLogger(__name__)

class PipelineProcessor:
    """Main pipeline processor that orchestrates the entire workflow"""
    
    def __init__(self):
        """Initialize the pipeline processor"""
        # Initialize components
        self.format_detector = FormatDetector()
        self.ocr_processor = OCRProcessor()
        self.text_extractor = TextExtractor()
        self.classifier = DocumentClassifier()
        self.es_indexer = ElasticsearchIndexer()
        
        # Processing statistics
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'start_time': datetime.utcnow()
        }
        
        logger.info("Pipeline processor initialized")
    
    def process_file(self, file_path):
        """
        Process a single PDF file through the entire pipeline
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            dict: Processing result
        """
        start_time = time.time()
        
        try:
            # Update statistics
            self.stats['total_processed'] += 1
            
            # Get file information
            filename = os.path.basename(file_path)
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            
            logger.info(f"Starting pipeline processing for: {filename}")
            
            # Create database log entry
            log_entry = DatabaseManager.create_processing_log(filename, file_path, file_size)
            log_id = log_entry.id
            
            # Stage 1: Format Detection
            DatabaseManager.update_processing_log(log_id, stage='format_detection', status='processing')
            
            format_result = self.format_detector.detect_format(file_path)
            document_type = format_result.get('type', 'unknown')
            
            if document_type == 'unknown':
                error_msg = f"Could not determine document format: {format_result.get('details', {}).get('error', 'Unknown error')}"
                DatabaseManager.update_processing_log(log_id, status='failed', error_message=error_msg)
                self.stats['failed'] += 1
                return {
                    'success': False,
                    'error': error_msg,
                    'log_id': log_id
                }
            
            DatabaseManager.update_processing_log(log_id, document_type=document_type)
            
            # Stage 2: Text Extraction
            DatabaseManager.update_processing_log(log_id, stage='text_extraction')
            
            extraction_result = None
            text_content = ""
            extraction_method = ""
            ocr_confidence = None
            
            if document_type == 'scanned':
                # Use OCR for scanned documents
                extraction_result = self.ocr_processor.extract_text_from_pdf(file_path)
                text_content = extraction_result.get('text', '')
                extraction_method = 'ocr'
                ocr_confidence = extraction_result.get('confidence', 0.0)
                
                if not text_content.strip():
                    error_msg = "OCR extraction failed or produced no text"
                    DatabaseManager.update_processing_log(log_id, status='failed', error_message=error_msg)
                    self.stats['failed'] += 1
                    return {
                        'success': False,
                        'error': error_msg,
                        'log_id': log_id
                    }
            
            else:
                # Use PDFMiner for machine-readable documents
                extraction_result = self.text_extractor.extract_text_from_pdf(file_path)
                text_content = extraction_result.get('text', '')
                extraction_method = extraction_result.get('method', 'pdfminer')
                
                if not extraction_result.get('success', False) or not text_content.strip():
                    error_msg = "Text extraction failed or produced no text"
                    DatabaseManager.update_processing_log(log_id, status='failed', error_message=error_msg)
                    self.stats['failed'] += 1
                    return {
                        'success': False,
                        'error': error_msg,
                        'log_id': log_id
                    }
            
            logger.info(f"Text extraction completed for {filename}: {len(text_content)} characters")
            
            # Stage 3: Document Classification
            DatabaseManager.update_processing_log(log_id, stage='classification')
            
            classification_result = self.classifier.classify_document(text_content)
            category = classification_result.get('category', 'other')
            
            DatabaseManager.update_processing_log(log_id, classification_result=category)
            
            # Stage 4: Elasticsearch Indexing
            DatabaseManager.update_processing_log(log_id, stage='indexing')
            
            # Prepare document data for indexing
            document_data = {
                'filename': filename,
                'file_path': file_path,
                'file_size': file_size,
                'text': text_content,
                'document_type': document_type,
                'classification': classification_result,
                'metadata': extraction_result.get('metadata', {}),
                'extraction_method': extraction_method,
                'ocr_confidence': ocr_confidence,
                'processing_time': time.time() - start_time,
                'total_pages': extraction_result.get('total_pages', 0),
                'processed_at': datetime.utcnow().isoformat()
            }
            
            # Index to Elasticsearch
            index_result = self.es_indexer.index_document(document_data)
            
            if not index_result.get('success', False):
                error_msg = f"Elasticsearch indexing failed: {index_result.get('error', 'Unknown error')}"
                DatabaseManager.update_processing_log(log_id, status='failed', error_message=error_msg)
                self.stats['failed'] += 1
                return {
                    'success': False,
                    'error': error_msg,
                    'log_id': log_id
                }
            
            elasticsearch_id = index_result.get('document_id')
            
            # Final update - mark as completed
            processing_time = time.time() - start_time
            DatabaseManager.update_processing_log(
                log_id,
                status='completed',
                processing_time=processing_time,
                elasticsearch_id=elasticsearch_id,
                stage='completed'
            )
            
            # Mark file as processed
            self._mark_file_as_processed(file_path)
            
            # Update statistics
            self.stats['successful'] += 1
            
            logger.info(f"Pipeline processing completed successfully for {filename} in {processing_time:.2f}s")
            
            return {
                'success': True,
                'log_id': log_id,
                'document_type': document_type,
                'classification': category,
                'elasticsearch_id': elasticsearch_id,
                'processing_time': processing_time,
                'text_length': len(text_content),
                'extraction_method': extraction_method
            }
            
        except Exception as e:
            error_msg = f"Pipeline processing failed: {str(e)}"
            logger.error(f"Error processing {file_path}: {error_msg}")
            
            # Update database with error
            if 'log_id' in locals():
                DatabaseManager.update_processing_log(log_id, status='failed', error_message=error_msg)
            
            self.stats['failed'] += 1
            
            return {
                'success': False,
                'error': error_msg,
                'log_id': locals().get('log_id')
            }
    
    def _mark_file_as_processed(self, file_path):
        """Mark file as processed by creating a marker file"""
        try:
            marker_file = file_path + Config.PROCESSED_EXTENSION
            with open(marker_file, 'w') as f:
                f.write(datetime.utcnow().isoformat())
        except Exception as e:
            logger.warning(f"Could not create processed marker for {file_path}: {str(e)}")
    
    def get_processing_stats(self):
        """Get processing statistics"""
        runtime = (datetime.utcnow() - self.stats['start_time']).total_seconds()
        
        return {
            'total_processed': self.stats['total_processed'],
            'successful': self.stats['successful'],
            'failed': self.stats['failed'],
            'success_rate': (self.stats['successful'] / self.stats['total_processed'] * 100) if self.stats['total_processed'] > 0 else 0,
            'runtime_seconds': runtime,
            'avg_processing_time': runtime / self.stats['total_processed'] if self.stats['total_processed'] > 0 else 0,
            'start_time': self.stats['start_time'].isoformat()
        }
    
    def test_components(self):
        """Test all pipeline components"""
        results = {}
        
        # Test format detector
        results['format_detector'] = {
            'available': True,
            'description': 'PDF format detection using PyMuPDF'
        }
        
        # Test OCR processor
        results['ocr_processor'] = self.ocr_processor.test_tesseract_installation()
        
        # Test text extractor
        results['text_extractor'] = {
            'available': True,
            'description': 'Text extraction using PDFMiner and PyMuPDF'
        }
        
        # Test classifier
        classifier_info = self.classifier.get_model_info()
        results['classifier'] = {
            'available': True,
            'trained': classifier_info.get('trained', False),
            'model_info': classifier_info
        }
        
        # Test Elasticsearch
        es_test = self.es_indexer.test_connection()
        results['elasticsearch'] = es_test
        
        return results
    
    def setup_default_classifier(self):
        """Setup classifier with sample data if not already trained"""
        try:
            if not self.classifier.is_trained:
                logger.info("Setting up default classifier with sample data...")
                
                sample_data = self.classifier.create_sample_training_data()
                result = self.classifier.train_model(sample_data)
                
                if result.get('success', False):
                    logger.info(f"Default classifier trained with accuracy: {result.get('accuracy', 0):.3f}")
                    return True
                else:
                    logger.error(f"Failed to train default classifier: {result.get('error', 'Unknown error')}")
                    return False
            else:
                logger.info("Classifier already trained")
                return True
                
        except Exception as e:
            logger.error(f"Error setting up default classifier: {str(e)}")
            return False

class PipelineManager:
    """High-level manager for the entire pipeline system"""
    
    def __init__(self):
        """Initialize pipeline manager"""
        # Setup logging
        setup_logging()
        
        # Create directories
        Config.create_directories()
        
        # Initialize processor
        self.processor = PipelineProcessor()
        
        logger.info("Pipeline manager initialized")
    
    def start(self):
        """Start the pipeline system"""
        try:
            logger.info("Starting PDF processing pipeline...")
            
            # Test components
            component_status = self.processor.test_components()
            
            # Log component status
            for component, status in component_status.items():
                if status.get('available', False) or status.get('connected', False):
                    logger.info(f"✓ {component}: OK")
                else:
                    logger.warning(f"✗ {component}: {status.get('error', 'Not available')}")
            
            # Setup default classifier if needed
            self.processor.setup_default_classifier()
            
            logger.info("Pipeline system started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start pipeline system: {str(e)}")
            return False
    
    def stop(self):
        """Stop the pipeline system"""
        logger.info("Pipeline system stopped")
    
    def get_system_status(self):
        """Get overall system status"""
        component_status = self.processor.test_components()
        processing_stats = self.processor.get_processing_stats()
        
        return {
            'components': component_status,
            'processing_stats': processing_stats,
            'system_ready': all(
                status.get('available', False) or status.get('connected', False)
                for status in component_status.values()
            )
        }