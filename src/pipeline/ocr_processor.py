import os
import logging
import pytesseract
from PIL import Image
import fitz  # PyMuPDF
import io
from config import Config

logger = logging.getLogger(__name__)

class OCRProcessor:
    """Handles OCR processing for scanned PDFs using Tesseract"""
    
    def __init__(self, tesseract_cmd=None, languages=None):
        """
        Initialize OCR processor
        
        Args:
            tesseract_cmd: Path to tesseract executable
            languages: Languages for OCR (e.g., 'eng', 'eng+fra')
        """
        self.tesseract_cmd = tesseract_cmd or Config.TESSERACT_CMD
        self.languages = languages or Config.OCR_LANGUAGES
        
        # Set tesseract command path
        if self.tesseract_cmd and self.tesseract_cmd != 'tesseract':
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
    
    def extract_text_from_pdf(self, pdf_path, dpi=300):
        """
        Extract text from scanned PDF using OCR
        
        Args:
            pdf_path: Path to PDF file
            dpi: DPI for image conversion (higher = better quality, slower)
            
        Returns:
            dict: {
                'text': str,
                'confidence': float,
                'pages': list of page results,
                'total_pages': int
            }
        """
        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            
            all_text = []
            page_results = []
            total_confidence = 0
            
            logger.info(f"Starting OCR processing for {os.path.basename(pdf_path)} ({total_pages} pages)")
            
            for page_num in range(total_pages):
                page = doc.load_page(page_num)
                
                # Convert page to image
                mat = fitz.Matrix(dpi/72, dpi/72)  # Scaling factor
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                
                # Convert to PIL Image
                image = Image.open(io.BytesIO(img_data))
                
                # Perform OCR
                page_result = self._extract_text_from_image(image, page_num + 1)
                page_results.append(page_result)
                
                all_text.append(page_result['text'])
                total_confidence += page_result['confidence']
                
                logger.debug(f"Page {page_num + 1}: {len(page_result['text'])} characters, confidence: {page_result['confidence']:.2f}")
            
            doc.close()
            
            # Calculate average confidence
            avg_confidence = total_confidence / total_pages if total_pages > 0 else 0
            
            # Combine all text
            combined_text = '\n\n--- Page Break ---\n\n'.join(all_text)
            
            result = {
                'text': combined_text,
                'confidence': avg_confidence,
                'pages': page_results,
                'total_pages': total_pages
            }
            
            logger.info(f"OCR completed for {os.path.basename(pdf_path)}: {len(combined_text)} characters, avg confidence: {avg_confidence:.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error during OCR processing of {pdf_path}: {str(e)}")
            return {
                'text': '',
                'confidence': 0.0,
                'pages': [],
                'total_pages': 0,
                'error': str(e)
            }
    
    def _extract_text_from_image(self, image, page_num):
        """
        Extract text from a single image using OCR
        
        Args:
            image: PIL Image object
            page_num: Page number for logging
            
        Returns:
            dict: {
                'text': str,
                'confidence': float,
                'page_num': int
            }
        """
        try:
            # Configure OCR
            config = f'--oem 3 --psm 6 -l {self.languages}'
            
            # Extract text with confidence data
            data = pytesseract.image_to_data(image, config=config, output_type=pytesseract.Output.DICT)
            
            # Filter out low confidence detections
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            # Extract text
            text = pytesseract.image_to_string(image, config=config)
            
            return {
                'text': text.strip(),
                'confidence': avg_confidence,
                'page_num': page_num
            }
            
        except Exception as e:
            logger.error(f"Error extracting text from page {page_num}: {str(e)}")
            return {
                'text': '',
                'confidence': 0.0,
                'page_num': page_num,
                'error': str(e)
            }
    
    def extract_text_from_image_file(self, image_path):
        """
        Extract text from a single image file
        
        Args:
            image_path: Path to image file
            
        Returns:
            dict: OCR result
        """
        try:
            image = Image.open(image_path)
            return self._extract_text_from_image(image, 1)
        except Exception as e:
            logger.error(f"Error processing image file {image_path}: {str(e)}")
            return {
                'text': '',
                'confidence': 0.0,
                'page_num': 1,
                'error': str(e)
            }
    
    def preprocess_image(self, image):
        """
        Preprocess image to improve OCR accuracy
        
        Args:
            image: PIL Image object
            
        Returns:
            PIL Image: Preprocessed image
        """
        # Convert to grayscale
        if image.mode != 'L':
            image = image.convert('L')
        
        # You can add more preprocessing steps here:
        # - Noise reduction
        # - Contrast enhancement
        # - Deskewing
        # - Thresholding
        
        return image
    
    def test_tesseract_installation(self):
        """
        Test if Tesseract is properly installed and accessible
        
        Returns:
            dict: Test result
        """
        try:
            version = pytesseract.get_tesseract_version()
            logger.info(f"Tesseract version: {version}")
            
            # Test with a simple image
            test_image = Image.new('RGB', (100, 30), color='white')
            test_text = pytesseract.image_to_string(test_image)
            
            return {
                'success': True,
                'version': str(version),
                'test_result': 'OK'
            }
            
        except Exception as e:
            logger.error(f"Tesseract installation test failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'suggestion': 'Please install Tesseract and ensure it is in your PATH or set TESSERACT_CMD in config'
            }