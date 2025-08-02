import os
import time
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from config import Config

logger = logging.getLogger(__name__)

class PDFFileHandler(FileSystemEventHandler):
    """File system event handler for PDF files"""
    
    def __init__(self, pipeline_processor):
        """
        Initialize file handler
        
        Args:
            pipeline_processor: Instance of PipelineProcessor to handle files
        """
        self.pipeline_processor = pipeline_processor
        self.supported_extensions = ['.pdf', '.PDF']
    
    def on_created(self, event):
        """Handle file creation events"""
        if not event.is_directory:
            self._process_file_event(event.src_path, 'created')
    
    def on_moved(self, event):
        """Handle file move events"""
        if not event.is_directory:
            self._process_file_event(event.dest_path, 'moved')
    
    def on_modified(self, event):
        """Handle file modification events"""
        if not event.is_directory:
            # Only process if file size is stable (file write completed)
            if self._is_file_stable(event.src_path):
                self._process_file_event(event.src_path, 'modified')
    
    def _process_file_event(self, file_path, event_type):
        """Process file events for PDF files"""
        try:
            # Check if it's a PDF file
            if not any(file_path.endswith(ext) for ext in self.supported_extensions):
                return
            
            # Check if file already processed
            if self._is_already_processed(file_path):
                logger.debug(f"File {file_path} already processed, skipping")
                return
            
            # Check if file exists and is readable
            if not os.path.exists(file_path) or not os.access(file_path, os.R_OK):
                logger.warning(f"File {file_path} not accessible, skipping")
                return
            
            logger.info(f"New PDF file detected ({event_type}): {file_path}")
            
            # Process the file
            self.pipeline_processor.process_file(file_path)
            
        except Exception as e:
            logger.error(f"Error processing file event for {file_path}: {str(e)}")
    
    def _is_file_stable(self, file_path, wait_time=2):
        """Check if file size is stable (write operation completed)"""
        try:
            if not os.path.exists(file_path):
                return False
            
            size1 = os.path.getsize(file_path)
            time.sleep(wait_time)
            
            if not os.path.exists(file_path):
                return False
            
            size2 = os.path.getsize(file_path)
            return size1 == size2
            
        except Exception:
            return False
    
    def _is_already_processed(self, file_path):
        """Check if file has already been processed"""
        try:
            processed_marker = file_path + Config.PROCESSED_EXTENSION
            return os.path.exists(processed_marker)
        except Exception:
            return False

class FileMonitor:
    """Monitors directory for new PDF files and triggers processing"""
    
    def __init__(self, pipeline_processor, watch_directory=None):
        """
        Initialize file monitor
        
        Args:
            pipeline_processor: Instance of PipelineProcessor
            watch_directory: Directory to monitor
        """
        self.pipeline_processor = pipeline_processor
        self.watch_directory = watch_directory or Config.WATCH_DIRECTORY
        self.observer = None
        self.is_running = False
        
        # Ensure watch directory exists
        os.makedirs(self.watch_directory, exist_ok=True)
        
        # Create event handler
        self.event_handler = PDFFileHandler(pipeline_processor)
    
    def start_monitoring(self):
        """Start monitoring the directory"""
        try:
            if self.is_running:
                logger.warning("File monitor is already running")
                return
            
            self.observer = Observer()
            self.observer.schedule(
                self.event_handler, 
                self.watch_directory, 
                recursive=True
            )
            
            self.observer.start()
            self.is_running = True
            
            logger.info(f"Started monitoring directory: {self.watch_directory}")
            
            # Process existing files in directory
            self._process_existing_files()
            
        except Exception as e:
            logger.error(f"Error starting file monitor: {str(e)}")
            raise
    
    def stop_monitoring(self):
        """Stop monitoring the directory"""
        try:
            if self.observer and self.is_running:
                self.observer.stop()
                self.observer.join()
                self.is_running = False
                logger.info("File monitor stopped")
            
        except Exception as e:
            logger.error(f"Error stopping file monitor: {str(e)}")
    
    def _process_existing_files(self):
        """Process existing PDF files in the watch directory"""
        try:
            logger.info("Scanning for existing PDF files to process...")
            
            processed_count = 0
            for root, dirs, files in os.walk(self.watch_directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    
                    # Check if it's a PDF file
                    if any(file.endswith(ext) for ext in ['.pdf', '.PDF']):
                        # Check if already processed
                        if not self.event_handler._is_already_processed(file_path):
                            try:
                                logger.info(f"Processing existing file: {file_path}")
                                self.pipeline_processor.process_file(file_path)
                                processed_count += 1
                            except Exception as e:
                                logger.error(f"Error processing existing file {file_path}: {str(e)}")
            
            logger.info(f"Processed {processed_count} existing PDF files")
            
        except Exception as e:
            logger.error(f"Error processing existing files: {str(e)}")
    
    def run_forever(self):
        """Run the monitor indefinitely"""
        try:
            self.start_monitoring()
            
            logger.info("File monitor is running. Press Ctrl+C to stop.")
            
            while self.is_running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, stopping monitor...")
            self.stop_monitoring()
        except Exception as e:
            logger.error(f"Error in monitor main loop: {str(e)}")
            self.stop_monitoring()
            raise
    
    def get_status(self):
        """Get monitor status"""
        return {
            'is_running': self.is_running,
            'watch_directory': self.watch_directory,
            'directory_exists': os.path.exists(self.watch_directory),
            'directory_accessible': os.access(self.watch_directory, os.R_OK) if os.path.exists(self.watch_directory) else False
        }

class BatchProcessor:
    """Process multiple files in batch mode"""
    
    def __init__(self, pipeline_processor):
        """
        Initialize batch processor
        
        Args:
            pipeline_processor: Instance of PipelineProcessor
        """
        self.pipeline_processor = pipeline_processor
    
    def process_directory(self, directory_path, recursive=True):
        """
        Process all PDF files in a directory
        
        Args:
            directory_path: Path to directory containing PDFs
            recursive: Whether to search subdirectories
            
        Returns:
            dict: Processing results
        """
        try:
            if not os.path.exists(directory_path):
                return {
                    'success': False,
                    'error': f'Directory does not exist: {directory_path}'
                }
            
            pdf_files = []
            
            if recursive:
                for root, dirs, files in os.walk(directory_path):
                    for file in files:
                        if file.lower().endswith('.pdf'):
                            pdf_files.append(os.path.join(root, file))
            else:
                for file in os.listdir(directory_path):
                    file_path = os.path.join(directory_path, file)
                    if os.path.isfile(file_path) and file.lower().endswith('.pdf'):
                        pdf_files.append(file_path)
            
            logger.info(f"Found {len(pdf_files)} PDF files to process in {directory_path}")
            
            results = {
                'total_files': len(pdf_files),
                'successful': 0,
                'failed': 0,
                'errors': []
            }
            
            for pdf_file in pdf_files:
                try:
                    logger.info(f"Processing: {pdf_file}")
                    result = self.pipeline_processor.process_file(pdf_file)
                    
                    if result.get('success', False):
                        results['successful'] += 1
                    else:
                        results['failed'] += 1
                        results['errors'].append({
                            'file': pdf_file,
                            'error': result.get('error', 'Unknown error')
                        })
                        
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append({
                        'file': pdf_file,
                        'error': str(e)
                    })
                    logger.error(f"Error processing {pdf_file}: {str(e)}")
            
            logger.info(f"Batch processing completed: {results['successful']} successful, {results['failed']} failed")
            
            return {
                'success': True,
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Error in batch processing: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def process_file_list(self, file_list):
        """
        Process a specific list of files
        
        Args:
            file_list: List of file paths
            
        Returns:
            dict: Processing results
        """
        try:
            results = {
                'total_files': len(file_list),
                'successful': 0,
                'failed': 0,
                'errors': []
            }
            
            for file_path in file_list:
                if not os.path.exists(file_path):
                    results['failed'] += 1
                    results['errors'].append({
                        'file': file_path,
                        'error': 'File does not exist'
                    })
                    continue
                
                try:
                    result = self.pipeline_processor.process_file(file_path)
                    
                    if result.get('success', False):
                        results['successful'] += 1
                    else:
                        results['failed'] += 1
                        results['errors'].append({
                            'file': file_path,
                            'error': result.get('error', 'Unknown error')
                        })
                        
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append({
                        'file': file_path,
                        'error': str(e)
                    })
            
            return {
                'success': True,
                'results': results
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }