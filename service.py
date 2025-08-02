"""
Windows Service wrapper for PDF Processing Pipeline
"""

import os
import sys
import time
import logging
import win32serviceutil
import win32service
import win32event
import servicemanager

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from config import Config
from database import setup_logging
from src.pipeline.pipeline_processor import PipelineManager
from src.pipeline.file_monitor import FileMonitor

class PDFProcessingService(win32serviceutil.ServiceFramework):
    """Windows service for PDF processing pipeline"""
    
    _svc_name_ = Config.SERVICE_NAME
    _svc_display_name_ = Config.SERVICE_DISPLAY_NAME
    _svc_description_ = Config.SERVICE_DESCRIPTION
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.is_running = True
        
        # Setup logging
        setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.pipeline_manager = None
        self.file_monitor = None
    
    def SvcStop(self):
        """Stop the service"""
        self.logger.info("PDF Processing Service stopping...")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        
        self.is_running = False
        
        # Stop components
        if self.file_monitor:
            self.file_monitor.stop_monitoring()
        
        if self.pipeline_manager:
            self.pipeline_manager.stop()
        
        win32event.SetEvent(self.hWaitStop)
        self.logger.info("PDF Processing Service stopped")
    
    def SvcDoRun(self):
        """Run the service"""
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        
        self.logger.info("PDF Processing Service starting...")
        
        try:
            # Create directories
            Config.create_directories()
            
            # Initialize pipeline
            self.pipeline_manager = PipelineManager()
            
            if not self.pipeline_manager.start():
                self.logger.error("Failed to start pipeline system")
                return
            
            # Initialize file monitor
            self.file_monitor = FileMonitor(self.pipeline_manager.processor)
            self.file_monitor.start_monitoring()
            
            self.logger.info("PDF Processing Service started successfully")
            self.logger.info(f"Monitoring directory: {Config.WATCH_DIRECTORY}")
            
            # Main service loop
            while self.is_running:
                # Wait for stop event or timeout (30 seconds)
                rc = win32event.WaitForSingleObject(self.hWaitStop, 30000)
                
                if rc == win32event.WAIT_OBJECT_0:
                    # Stop event was triggered
                    break
                elif rc == win32event.WAIT_TIMEOUT:
                    # Timeout - continue monitoring
                    if not self.file_monitor.is_running:
                        self.logger.warning("File monitor stopped unexpectedly, restarting...")
                        try:
                            self.file_monitor.start_monitoring()
                        except Exception as e:
                            self.logger.error(f"Failed to restart file monitor: {str(e)}")
                
        except Exception as e:
            self.logger.error(f"Service error: {str(e)}")
            servicemanager.LogErrorMsg(f"PDF Processing Service error: {str(e)}")

def install_service():
    """Install the Windows service"""
    try:
        win32serviceutil.InstallService(
            PDFProcessingService,
            Config.SERVICE_NAME,
            Config.SERVICE_DISPLAY_NAME,
            description=Config.SERVICE_DESCRIPTION
        )
        print(f"Service '{Config.SERVICE_DISPLAY_NAME}' installed successfully")
    except Exception as e:
        print(f"Failed to install service: {str(e)}")

def remove_service():
    """Remove the Windows service"""
    try:
        win32serviceutil.RemoveService(Config.SERVICE_NAME)
        print(f"Service '{Config.SERVICE_DISPLAY_NAME}' removed successfully")
    except Exception as e:
        print(f"Failed to remove service: {str(e)}")

def start_service():
    """Start the Windows service"""
    try:
        win32serviceutil.StartService(Config.SERVICE_NAME)
        print(f"Service '{Config.SERVICE_DISPLAY_NAME}' started successfully")
    except Exception as e:
        print(f"Failed to start service: {str(e)}")

def stop_service():
    """Stop the Windows service"""
    try:
        win32serviceutil.StopService(Config.SERVICE_NAME)
        print(f"Service '{Config.SERVICE_DISPLAY_NAME}' stopped successfully")
    except Exception as e:
        print(f"Failed to stop service: {str(e)}")

def main():
    """Main entry point for service management"""
    if len(sys.argv) == 1:
        # Called by Windows Service Manager
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(PDFProcessingService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        # Called from command line
        command = sys.argv[1].lower()
        
        if command == 'install':
            install_service()
        elif command == 'remove':
            remove_service()
        elif command == 'start':
            start_service()
        elif command == 'stop':
            stop_service()
        elif command == 'restart':
            stop_service()
            time.sleep(2)
            start_service()
        elif command == 'debug':
            # Run in debug mode (not as service)
            setup_logging()
            service = PDFProcessingService([])
            service.SvcDoRun()
        else:
            print("Usage: service.py [install|remove|start|stop|restart|debug]")
            print("  install  - Install the service")
            print("  remove   - Remove the service")
            print("  start    - Start the service")
            print("  stop     - Stop the service")
            print("  restart  - Restart the service")
            print("  debug    - Run in debug mode (not as service)")

if __name__ == '__main__':
    main()