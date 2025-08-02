# PDF Processing Pipeline

A comprehensive Python-based PDF processing pipeline that handles both machine-readable and scanned PDFs using Tesseract, PDFMiner, Scikit-learn, and Elasticsearch.

## Features

- **Format Detection**: Automatically identifies machine-readable vs scanned PDFs
- **OCR Processing**: Extracts text from image-based PDFs using Tesseract
- **Text Extraction**: Processes machine-readable PDFs with PDFMiner
- **Document Classification**: Categorizes documents using Scikit-learn
- **Elasticsearch Integration**: Indexes documents for search and analysis
- **File Monitoring**: Watches directories for new files automatically
- **Web Interface**: Flask-based UI for monitoring and management
- **Windows Service**: Runs as a background service on Windows

## Quick Start

### Prerequisites

1. **Python 3.8+**
2. **Tesseract OCR**
   - Windows: Download from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)
   - Linux: `sudo apt-get install tesseract-ocr`
   - macOS: `brew install tesseract`
3. **Elasticsearch** (optional, for indexing)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd pdf-processing-pipeline
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Install additional dependencies:
```bash
# For PyMuPDF (fitz)
pip install PyMuPDF

# For Windows service support (Windows only)
pip install pywin32
```

### Configuration

1. Copy and edit the configuration:
```bash
cp .env.example .env
```

2. Set environment variables in `.env`:
```env
# Elasticsearch settings
ELASTICSEARCH_URL=http://localhost:9200
ELASTICSEARCH_INDEX=pdf_documents

# Tesseract settings
TESSERACT_CMD=tesseract
OCR_LANGUAGES=eng

# Directory settings
WATCH_DIRECTORY=data/input

# Database settings
DATABASE_URL=sqlite:///pipeline.db
```

## Usage

### Web Interface (Recommended)

Start the web interface:
```bash
python main.py --mode web
```

Access the application at `http://localhost:5000`

### Command Line

#### Process a single file:
```bash
python main.py --mode process --file /path/to/document.pdf
```

#### Batch process a directory:
```bash
python main.py --mode batch --directory /path/to/pdfs --recursive
```

#### File monitoring service:
```bash
python main.py --mode monitor
```

### Windows Service Deployment

1. Install the service:
```bash
python service.py install
```

2. Start the service:
```bash
python service.py start
```

3. Check service status in Windows Services console

## Architecture

### Core Components

1. **Format Detector** (`src/pipeline/format_detector.py`)
   - Analyzes PDFs to determine if they're machine-readable or scanned
   - Uses text extraction and image analysis

2. **OCR Processor** (`src/pipeline/ocr_processor.py`)
   - Handles text extraction from scanned PDFs
   - Uses Tesseract OCR engine

3. **Text Extractor** (`src/pipeline/text_extractor.py`)
   - Extracts text from machine-readable PDFs
   - Uses PDFMiner with PyMuPDF fallback

4. **Document Classifier** (`src/pipeline/classifier.py`)
   - Classifies documents into categories (invoice, contract, report, etc.)
   - Uses scikit-learn with TF-IDF vectorization

5. **Elasticsearch Indexer** (`src/pipeline/elasticsearch_indexer.py`)
   - Indexes processed documents for search and analysis
   - Handles document metadata and full-text search

6. **File Monitor** (`src/pipeline/file_monitor.py`)
   - Monitors directories for new PDF files
   - Triggers automatic processing

7. **Pipeline Processor** (`src/pipeline/pipeline_processor.py`)
   - Orchestrates the entire processing workflow
   - Handles error recovery and logging

### Web Interface

- **Dashboard**: Monitor processing status and system health
- **Documents**: Search and browse processed documents
- **Models**: Manage and train classification models
- **Batch Processing**: Process multiple files at once
- **Settings**: Configure system parameters

## API Endpoints

### Status and Monitoring
- `GET /api/status` - Get system status
- `GET /api/logs` - Get processing logs

### Document Management
- `GET /api/search-documents` - Search processed documents
- `GET /api/document/<id>` - Get specific document

### Processing
- `POST /api/process-file` - Process a single file
- `POST /api/batch-process` - Start batch processing
- `POST /api/start-monitoring` - Start file monitoring
- `POST /api/stop-monitoring` - Stop file monitoring

### Model Management
- `POST /api/train-model` - Train classification model
- `POST /api/classify-text` - Classify text sample

## Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ELASTICSEARCH_URL` | Elasticsearch server URL | `http://localhost:9200` |
| `ELASTICSEARCH_INDEX` | Index name for documents | `pdf_documents` |
| `TESSERACT_CMD` | Path to Tesseract executable | `tesseract` |
| `OCR_LANGUAGES` | OCR language codes | `eng` |
| `WATCH_DIRECTORY` | Directory to monitor | `data/input` |
| `DATABASE_URL` | Database connection string | `sqlite:///pipeline.db` |

### Directory Structure

```
pdf-processing-pipeline/
├── main.py                 # Main entry point
├── service.py             # Windows service wrapper
├── config.py              # Configuration management
├── database.py            # Database models and operations
├── requirements.txt       # Python dependencies
├── src/
│   ├── pipeline/          # Core processing modules
│   └── web/              # Flask web application
├── data/
│   ├── input/            # Input directory (monitored)
│   ├── processed/        # Processed files
│   └── models/           # Trained models
├── logs/                 # Application logs
└── docs/                 # Documentation
```

## Database Schema

The application uses SQLite by default with the following main table:

### ProcessingLog
- `id` - Primary key
- `filename` - Original filename
- `file_path` - Full file path
- `status` - Processing status (pending, processing, completed, failed)
- `stage` - Current processing stage
- `document_type` - Detected type (machine_readable, scanned)
- `classification_result` - Document category
- `error_message` - Error details if failed
- `processing_time` - Time taken to process
- `elasticsearch_id` - Document ID in Elasticsearch
- `created_at` / `updated_at` - Timestamps

## Troubleshooting

### Common Issues

1. **Tesseract not found**
   - Ensure Tesseract is installed and in PATH
   - Set `TESSERACT_CMD` environment variable to full path

2. **Elasticsearch connection failed**
   - Verify Elasticsearch is running
   - Check `ELASTICSEARCH_URL` configuration
   - Ensure network connectivity

3. **Permission denied errors**
   - Check file/directory permissions
   - Ensure watch directory is writable

4. **Memory issues with large PDFs**
   - Increase available memory
   - Consider processing files in smaller batches

### Logs

Application logs are stored in:
- `logs/pipeline.log` - Main application log
- Windows Event Log (when running as service)

### Testing Components

Use the web interface Settings page or run:
```bash
# Test all components
curl http://localhost:5000/api/test-components

# Test specific functionality
python -c "
from src.pipeline.pipeline_processor import PipelineManager
pm = PipelineManager()
pm.start()
print(pm.processor.test_components())
"
```

## Performance Considerations

- **OCR Processing**: CPU-intensive, consider parallel processing for large batches
- **Memory Usage**: Large PDFs may require significant memory
- **Elasticsearch**: Index size grows with document count
- **Storage**: Processed files and models require disk space

## Security Notes

- Ensure proper file permissions on watch directories
- Use HTTPS in production deployments
- Implement authentication for web interface in production
- Regularly update dependencies for security patches

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes and add tests
4. Submit a pull request

## License

[Add your license information here]

## Support

For issues and questions:
- Check the troubleshooting section
- Review application logs
- Open an issue on the repository