import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from processor import process_document, WATCH_DIR
from database import insert_document

class NewFileHandler(FileSystemEventHandler):
    def on_created(self, event):
        # Only process files (not directories)
        if event.is_directory:
            return
        file_path = event.src_path
        # Only process PDF and TIF files
        if file_path.lower().endswith(('.pdf', '.tif', '.tiff')):
            print(f"New file detected: {file_path}")
            file_name, doc_type, extracted_text = process_document(file_path)
            insert_document(file_name, doc_type, extracted_text)
            print(f"Processed {file_name} as {doc_type}")

if __name__ == "__main__":
    if not os.path.isdir(WATCH_DIR):
        os.makedirs(WATCH_DIR)
    event_handler = NewFileHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCH_DIR, recursive=False)
    observer.start()
    print(f"Watching folder: {WATCH_DIR}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
