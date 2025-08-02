import os
import logging
import fitz  # PyMuPDF
from PIL import Image
import io

logger = logging.getLogger(__name__)

class FormatDetector:
    """Detects if a PDF is machine-readable or scanned (image-based)"""
    
    def __init__(self, text_threshold=100, image_ratio_threshold=0.8):
        """
        Initialize format detector
        
        Args:
            text_threshold: Minimum characters to consider machine-readable
            image_ratio_threshold: Minimum image area ratio to consider scanned
        """
        self.text_threshold = text_threshold
        self.image_ratio_threshold = image_ratio_threshold
    
    def detect_format(self, pdf_path):
        """
        Detect if PDF is machine-readable or scanned
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            dict: {
                'type': 'machine_readable' or 'scanned',
                'confidence': float,
                'details': dict with analysis details
            }
        """
        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            
            if total_pages == 0:
                return {
                    'type': 'unknown',
                    'confidence': 0.0,
                    'details': {'error': 'No pages found'}
                }
            
            # Analyze first few pages (up to 3) for efficiency
            pages_to_analyze = min(3, total_pages)
            
            text_scores = []
            image_scores = []
            
            for page_num in range(pages_to_analyze):
                page = doc.load_page(page_num)
                
                # Extract text
                text = page.get_text()
                text_length = len(text.strip())
                
                # Get page dimensions
                rect = page.rect
                page_area = rect.width * rect.height
                
                # Extract images
                image_list = page.get_images()
                total_image_area = 0
                
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    image_dict = doc.extract_image(xref)
                    image_width = image_dict["width"]
                    image_height = image_dict["height"]
                    total_image_area += image_width * image_height
                
                # Calculate scores
                text_score = min(text_length / self.text_threshold, 1.0)
                image_ratio = total_image_area / page_area if page_area > 0 else 0
                image_score = min(image_ratio / self.image_ratio_threshold, 1.0)
                
                text_scores.append(text_score)
                image_scores.append(image_score)
            
            doc.close()
            
            # Calculate averages
            avg_text_score = sum(text_scores) / len(text_scores)
            avg_image_score = sum(image_scores) / len(image_scores)
            
            # Determine format
            if avg_text_score > 0.5 and avg_image_score < 0.3:
                document_type = 'machine_readable'
                confidence = avg_text_score
            elif avg_image_score > 0.5 and avg_text_score < 0.2:
                document_type = 'scanned'
                confidence = avg_image_score
            elif avg_text_score > avg_image_score:
                document_type = 'machine_readable'
                confidence = avg_text_score * 0.7  # Lower confidence for mixed content
            else:
                document_type = 'scanned'
                confidence = avg_image_score * 0.7
            
            details = {
                'pages_analyzed': pages_to_analyze,
                'total_pages': total_pages,
                'avg_text_score': avg_text_score,
                'avg_image_score': avg_image_score,
                'text_scores': text_scores,
                'image_scores': image_scores
            }
            
            logger.info(f"Format detection for {os.path.basename(pdf_path)}: {document_type} (confidence: {confidence:.2f})")
            
            return {
                'type': document_type,
                'confidence': confidence,
                'details': details
            }
            
        except Exception as e:
            logger.error(f"Error detecting format for {pdf_path}: {str(e)}")
            return {
                'type': 'unknown',
                'confidence': 0.0,
                'details': {'error': str(e)}
            }
    
    def is_machine_readable(self, pdf_path):
        """Simple check if PDF is machine-readable"""
        result = self.detect_format(pdf_path)
        return result['type'] == 'machine_readable'
    
    def is_scanned(self, pdf_path):
        """Simple check if PDF is scanned"""
        result = self.detect_format(pdf_path)
        return result['type'] == 'scanned'