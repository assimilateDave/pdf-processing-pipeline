# Data directory for PDF processing pipeline

## Subdirectories

### input/
Directory monitored for new PDF files. Place PDF files here for automatic processing.

### processed/
Stores processed files and metadata.

### models/
Stores trained classification models and vectorizers.

## File Processing Flow

1. PDF files are placed in `input/` directory
2. File monitor detects new files
3. Processing pipeline extracts text, classifies, and indexes
4. Processed files are marked with `.processed` extension
5. Results are stored in database and Elasticsearch