from flask import Flask, render_template, request, jsonify, send_from_directory, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import os
import json
from datetime import datetime
import pandas as pd
from config import Config
from database import DatabaseManager, db, setup_logging
from src.pipeline.pipeline_processor import PipelineManager
from src.pipeline.file_monitor import FileMonitor, BatchProcessor

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize database
DatabaseManager.init_db(app)

# Initialize pipeline
pipeline_manager = PipelineManager()
pipeline_manager.start()

# Global variables for monitoring
file_monitor = None
is_monitoring = False

@app.route('/')
def index():
    """Main dashboard"""
    try:
        # Get processing statistics
        processing_stats = DatabaseManager.get_processing_stats()
        
        # Get system status
        system_status = pipeline_manager.get_system_status()
        
        # Get recent processing logs
        recent_logs = DatabaseManager.get_processing_logs(limit=10)
        
        return render_template('dashboard.html',
                             processing_stats=processing_stats,
                             system_status=system_status,
                             recent_logs=recent_logs,
                             is_monitoring=is_monitoring)
    except Exception as e:
        return render_template('error.html', error=str(e))

@app.route('/api/status')
def api_status():
    """API endpoint for system status"""
    try:
        system_status = pipeline_manager.get_system_status()
        processing_stats = DatabaseManager.get_processing_stats()
        
        return jsonify({
            'success': True,
            'system_status': system_status,
            'processing_stats': processing_stats,
            'monitoring': {
                'is_running': is_monitoring,
                'watch_directory': Config.WATCH_DIRECTORY
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/logs')
def api_logs():
    """API endpoint for processing logs"""
    try:
        status = request.args.get('status')
        limit = int(request.args.get('limit', 50))
        
        logs = DatabaseManager.get_processing_logs(status=status, limit=limit)
        
        return jsonify({
            'success': True,
            'logs': [log.to_dict() for log in logs]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/process-file', methods=['POST'])
def api_process_file():
    """API endpoint to process a single file"""
    try:
        data = request.get_json()
        file_path = data.get('file_path')
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': 'Invalid file path'
            })
        
        # Process the file
        result = pipeline_manager.processor.process_file(file_path)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/start-monitoring', methods=['POST'])
def api_start_monitoring():
    """API endpoint to start file monitoring"""
    global file_monitor, is_monitoring
    
    try:
        if is_monitoring:
            return jsonify({
                'success': False,
                'error': 'Monitoring is already running'
            })
        
        file_monitor = FileMonitor(pipeline_manager.processor)
        file_monitor.start_monitoring()
        is_monitoring = True
        
        return jsonify({
            'success': True,
            'message': 'File monitoring started'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/stop-monitoring', methods=['POST'])
def api_stop_monitoring():
    """API endpoint to stop file monitoring"""
    global file_monitor, is_monitoring
    
    try:
        if not is_monitoring:
            return jsonify({
                'success': False,
                'error': 'Monitoring is not running'
            })
        
        if file_monitor:
            file_monitor.stop_monitoring()
        
        is_monitoring = False
        
        return jsonify({
            'success': True,
            'message': 'File monitoring stopped'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/documents')
def documents():
    """Documents management page"""
    try:
        # Get search parameters
        query = request.args.get('q', '')
        category = request.args.get('category', '')
        document_type = request.args.get('type', '')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        # Build filters
        filters = {}
        if category:
            filters['category'] = category
        if document_type:
            filters['document_type'] = document_type
        
        # Search documents
        search_results = pipeline_manager.processor.es_indexer.search_documents(
            query=query,
            filters=filters,
            size=per_page,
            from_=(page - 1) * per_page
        )
        
        if search_results.get('success', False):
            documents = search_results['documents']
            total = search_results['total']
        else:
            documents = []
            total = 0
        
        # Get available categories for filter
        categories = pipeline_manager.processor.classifier.default_categories
        
        return render_template('documents.html',
                             documents=documents,
                             total=total,
                             page=page,
                             per_page=per_page,
                             query=query,
                             category=category,
                             document_type=document_type,
                             categories=categories)
        
    except Exception as e:
        return render_template('error.html', error=str(e))

@app.route('/api/search-documents')
def api_search_documents():
    """API endpoint for document search"""
    try:
        query = request.args.get('q', '')
        category = request.args.get('category', '')
        document_type = request.args.get('type', '')
        size = int(request.args.get('size', 20))
        from_ = int(request.args.get('from', 0))
        
        filters = {}
        if category:
            filters['category'] = category
        if document_type:
            filters['document_type'] = document_type
        
        result = pipeline_manager.processor.es_indexer.search_documents(
            query=query,
            filters=filters,
            size=size,
            from_=from_
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/document/<doc_id>')
def api_get_document(doc_id):
    """API endpoint to get a specific document"""
    try:
        document = pipeline_manager.processor.es_indexer.get_document_by_id(doc_id)
        
        if document:
            return jsonify({
                'success': True,
                'document': document
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Document not found'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/models')
def models():
    """Model management page"""
    try:
        # Get classifier info
        classifier_info = pipeline_manager.processor.classifier.get_model_info()
        
        # Get sample training data
        sample_data = pipeline_manager.processor.classifier.create_sample_training_data()
        
        return render_template('models.html',
                             classifier_info=classifier_info,
                             sample_data=sample_data.to_dict('records'))
        
    except Exception as e:
        return render_template('error.html', error=str(e))

@app.route('/api/train-model', methods=['POST'])
def api_train_model():
    """API endpoint to train classification model"""
    try:
        data = request.get_json()
        
        # Get training data
        if 'training_data' in data:
            # Use provided training data
            training_texts = data['training_data']['texts']
            training_labels = data['training_data']['labels']
            
            result = pipeline_manager.processor.classifier.train_model(
                training_texts, training_labels
            )
        else:
            # Use sample data
            sample_data = pipeline_manager.processor.classifier.create_sample_training_data()
            result = pipeline_manager.processor.classifier.train_model(sample_data)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/classify-text', methods=['POST'])
def api_classify_text():
    """API endpoint to classify text"""
    try:
        data = request.get_json()
        text = data.get('text', '')
        
        if not text.strip():
            return jsonify({
                'success': False,
                'error': 'No text provided'
            })
        
        result = pipeline_manager.processor.classifier.classify_document(text)
        
        return jsonify({
            'success': True,
            'classification': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/batch')
def batch():
    """Batch processing page"""
    return render_template('batch.html')

@app.route('/api/batch-process', methods=['POST'])
def api_batch_process():
    """API endpoint for batch processing"""
    try:
        data = request.get_json()
        directory_path = data.get('directory_path', '')
        recursive = data.get('recursive', True)
        
        if not directory_path or not os.path.exists(directory_path):
            return jsonify({
                'success': False,
                'error': 'Invalid directory path'
            })
        
        # Process directory
        batch_processor = BatchProcessor(pipeline_manager.processor)
        result = batch_processor.process_directory(directory_path, recursive)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/settings')
def settings():
    """Settings page"""
    try:
        # Get current configuration
        config_info = {
            'watch_directory': Config.WATCH_DIRECTORY,
            'elasticsearch_url': Config.ELASTICSEARCH_URL,
            'elasticsearch_index': Config.ELASTICSEARCH_INDEX,
            'tesseract_cmd': Config.TESSERACT_CMD,
            'ocr_languages': Config.OCR_LANGUAGES,
            'model_path': Config.CLASSIFICATION_MODEL_PATH,
            'vectorizer_path': Config.VECTORIZER_PATH
        }
        
        return render_template('settings.html', config=config_info)
        
    except Exception as e:
        return render_template('error.html', error=str(e))

@app.route('/api/test-components')
def api_test_components():
    """API endpoint to test all components"""
    try:
        test_results = pipeline_manager.processor.test_components()
        return jsonify({
            'success': True,
            'test_results': test_results
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Setup logging
    setup_logging()
    
    # Create directories
    Config.create_directories()
    
    # Run the app
    app.run(debug=True, host='0.0.0.0', port=5000)