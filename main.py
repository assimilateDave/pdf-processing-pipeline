#!/usr/bin/env python3
"""
PDF Processing Pipeline
Main entry point for the application
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config import Config
from database import setup_logging
from src.pipeline.pipeline_processor import PipelineManager
from src.pipeline.file_monitor import FileMonitor, BatchProcessor

def main():
    parser = argparse.ArgumentParser(description='PDF Processing Pipeline')
    parser.add_argument('--mode', choices=['web', 'monitor', 'batch', 'process'], 
                       default='web', help='Operation mode')
    parser.add_argument('--file', help='Single file to process (process mode)')
    parser.add_argument('--directory', help='Directory to process (batch mode)')
    parser.add_argument('--recursive', action='store_true', 
                       help='Process subdirectories recursively (batch mode)')
    parser.add_argument('--host', default='0.0.0.0', help='Web server host (web mode)')
    parser.add_argument('--port', type=int, default=5000, help='Web server port (web mode)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Create directories
    Config.create_directories()
    
    # Initialize pipeline
    pipeline_manager = PipelineManager()
    
    if not pipeline_manager.start():
        logger.error("Failed to start pipeline system")
        sys.exit(1)
    
    try:
        if args.mode == 'web':
            run_web_server(args.host, args.port, args.debug)
        elif args.mode == 'monitor':
            run_file_monitor(pipeline_manager)
        elif args.mode == 'batch':
            run_batch_processing(pipeline_manager, args.directory, args.recursive)
        elif args.mode == 'process':
            run_single_file_processing(pipeline_manager, args.file)
        else:
            parser.print_help()
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)
    finally:
        pipeline_manager.stop()

def run_web_server(host, port, debug):
    """Run the Flask web server"""
    from src.web.app import app
    
    print(f"Starting PDF Processing Pipeline Web Server")
    print(f"Access the application at: http://{host}:{port}")
    print(f"Press Ctrl+C to stop")
    
    app.run(host=host, port=port, debug=debug)

def run_file_monitor(pipeline_manager):
    """Run the file monitoring service"""
    logger = logging.getLogger(__name__)
    
    file_monitor = FileMonitor(pipeline_manager.processor)
    
    logger.info("Starting file monitoring service...")
    logger.info(f"Monitoring directory: {Config.WATCH_DIRECTORY}")
    logger.info("Press Ctrl+C to stop")
    
    file_monitor.run_forever()

def run_batch_processing(pipeline_manager, directory, recursive):
    """Run batch processing on a directory"""
    logger = logging.getLogger(__name__)
    
    if not directory:
        directory = Config.INPUT_DIR
    
    if not os.path.exists(directory):
        logger.error(f"Directory does not exist: {directory}")
        sys.exit(1)
    
    logger.info(f"Starting batch processing on directory: {directory}")
    logger.info(f"Recursive: {recursive}")
    
    batch_processor = BatchProcessor(pipeline_manager.processor)
    result = batch_processor.process_directory(directory, recursive)
    
    if result['success']:
        results = result['results']
        logger.info(f"Batch processing completed:")
        logger.info(f"  Total files: {results['total_files']}")
        logger.info(f"  Successful: {results['successful']}")
        logger.info(f"  Failed: {results['failed']}")
        
        if results['errors']:
            logger.warning("Failed files:")
            for error in results['errors']:
                logger.warning(f"  {error['file']}: {error['error']}")
    else:
        logger.error(f"Batch processing failed: {result['error']}")
        sys.exit(1)

def run_single_file_processing(pipeline_manager, file_path):
    """Process a single file"""
    logger = logging.getLogger(__name__)
    
    if not file_path:
        logger.error("No file specified for processing")
        sys.exit(1)
    
    if not os.path.exists(file_path):
        logger.error(f"File does not exist: {file_path}")
        sys.exit(1)
    
    logger.info(f"Processing file: {file_path}")
    
    result = pipeline_manager.processor.process_file(file_path)
    
    if result['success']:
        logger.info("File processed successfully:")
        logger.info(f"  Document type: {result['document_type']}")
        logger.info(f"  Classification: {result['classification']}")
        logger.info(f"  Processing time: {result['processing_time']:.2f}s")
        logger.info(f"  Text length: {result['text_length']} characters")
        logger.info(f"  Elasticsearch ID: {result['elasticsearch_id']}")
    else:
        logger.error(f"File processing failed: {result['error']}")
        sys.exit(1)

if __name__ == '__main__':
    main()