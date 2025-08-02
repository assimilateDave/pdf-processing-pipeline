import os
import logging
from pdfminer.high_level import extract_text, extract_pages
from pdfminer.layout import LTTextContainer, LTChar, LTFigure
import fitz  # PyMuPDF as backup

logger = logging.getLogger(__name__)

class TextExtractor:
    """Handles text extraction from machine-readable PDFs using PDFMiner"""
    
    def __init__(self, use_pymupdf_fallback=True):
        """
        Initialize text extractor
        
        Args:
            use_pymupdf_fallback: Use PyMuPDF as fallback if PDFMiner fails
        """
        self.use_pymupdf_fallback = use_pymupdf_fallback
    
    def extract_text_from_pdf(self, pdf_path):
        """
        Extract text from machine-readable PDF
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            dict: {
                'text': str,
                'pages': list of page texts,
                'total_pages': int,
                'metadata': dict,
                'method': str (pdfminer or pymupdf)
            }
        """
        try:
            # First try with PDFMiner
            result = self._extract_with_pdfminer(pdf_path)
            
            if result['success']:
                return result
            elif self.use_pymupdf_fallback:
                logger.warning(f"PDFMiner failed for {pdf_path}, trying PyMuPDF fallback")
                return self._extract_with_pymupdf(pdf_path)
            else:
                return result
                
        except Exception as e:
            logger.error(f"Error extracting text from {pdf_path}: {str(e)}")
            return {
                'text': '',
                'pages': [],
                'total_pages': 0,
                'metadata': {},
                'method': 'none',
                'success': False,
                'error': str(e)
            }
    
    def _extract_with_pdfminer(self, pdf_path):
        """Extract text using PDFMiner"""
        try:
            # Extract all text at once
            text = extract_text(pdf_path)
            
            # Extract page by page for detailed analysis
            pages = []
            page_texts = []
            
            for page_layout in extract_pages(pdf_path):
                page_text = ""
                for element in page_layout:
                    if isinstance(element, LTTextContainer):
                        page_text += element.get_text()
                
                pages.append({
                    'page_num': len(pages) + 1,
                    'text': page_text.strip(),
                    'char_count': len(page_text.strip())
                })
                page_texts.append(page_text.strip())
            
            # Extract metadata
            metadata = self._extract_metadata_pdfminer(pdf_path)
            
            result = {
                'text': text.strip(),
                'pages': pages,
                'page_texts': page_texts,
                'total_pages': len(pages),
                'metadata': metadata,
                'method': 'pdfminer',
                'success': True
            }
            
            logger.info(f"PDFMiner extraction completed for {os.path.basename(pdf_path)}: {len(text)} characters, {len(pages)} pages")
            
            return result
            
        except Exception as e:
            logger.error(f"PDFMiner extraction failed for {pdf_path}: {str(e)}")
            return {
                'text': '',
                'pages': [],
                'total_pages': 0,
                'metadata': {},
                'method': 'pdfminer',
                'success': False,
                'error': str(e)
            }
    
    def _extract_with_pymupdf(self, pdf_path):
        """Extract text using PyMuPDF as fallback"""
        try:
            doc = fitz.open(pdf_path)
            
            all_text = []
            pages = []
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                page_text = page.get_text()
                
                pages.append({
                    'page_num': page_num + 1,
                    'text': page_text.strip(),
                    'char_count': len(page_text.strip())
                })
                
                all_text.append(page_text)
            
            # Extract metadata
            metadata = dict(doc.metadata)
            
            doc.close()
            
            combined_text = '\n\n--- Page Break ---\n\n'.join(all_text)
            
            result = {
                'text': combined_text.strip(),
                'pages': pages,
                'page_texts': [p['text'] for p in pages],
                'total_pages': len(pages),
                'metadata': metadata,
                'method': 'pymupdf',
                'success': True
            }
            
            logger.info(f"PyMuPDF extraction completed for {os.path.basename(pdf_path)}: {len(combined_text)} characters, {len(pages)} pages")
            
            return result
            
        except Exception as e:
            logger.error(f"PyMuPDF extraction failed for {pdf_path}: {str(e)}")
            return {
                'text': '',
                'pages': [],
                'total_pages': 0,
                'metadata': {},
                'method': 'pymupdf',
                'success': False,
                'error': str(e)
            }
    
    def _extract_metadata_pdfminer(self, pdf_path):
        """Extract PDF metadata using PyMuPDF (simpler for metadata)"""
        try:
            doc = fitz.open(pdf_path)
            metadata = dict(doc.metadata)
            doc.close()
            return metadata
        except:
            return {}
    
    def extract_text_with_layout(self, pdf_path):
        """
        Extract text with layout information (advanced)
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            dict: Text with layout information
        """
        try:
            layout_info = []
            
            for page_layout in extract_pages(pdf_path):
                page_info = {
                    'page_num': len(layout_info) + 1,
                    'elements': []
                }
                
                for element in page_layout:
                    if isinstance(element, LTTextContainer):
                        element_info = {
                            'type': 'text',
                            'text': element.get_text().strip(),
                            'bbox': element.bbox,
                            'font_info': self._get_font_info(element)
                        }
                        page_info['elements'].append(element_info)
                    elif isinstance(element, LTFigure):
                        element_info = {
                            'type': 'figure',
                            'bbox': element.bbox
                        }
                        page_info['elements'].append(element_info)
                
                layout_info.append(page_info)
            
            return {
                'layout': layout_info,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error extracting layout from {pdf_path}: {str(e)}")
            return {
                'layout': [],
                'success': False,
                'error': str(e)
            }
    
    def _get_font_info(self, element):
        """Extract font information from text element"""
        font_info = []
        
        for text_line in element:
            if hasattr(text_line, '__iter__'):
                for character in text_line:
                    if isinstance(character, LTChar):
                        font_info.append({
                            'fontname': character.fontname,
                            'fontsize': character.height,
                            'char': character.get_text()
                        })
        
        # Get most common font
        if font_info:
            fonts = [f['fontname'] for f in font_info]
            sizes = [f['fontsize'] for f in font_info]
            
            most_common_font = max(set(fonts), key=fonts.count) if fonts else None
            avg_size = sum(sizes) / len(sizes) if sizes else 0
            
            return {
                'primary_font': most_common_font,
                'average_size': avg_size,
                'character_count': len(font_info)
            }
        
        return {}
    
    def validate_extraction(self, pdf_path, min_chars=50):
        """
        Validate if text extraction was successful
        
        Args:
            pdf_path: Path to PDF file
            min_chars: Minimum characters to consider successful
            
        Returns:
            bool: True if extraction seems valid
        """
        try:
            result = self.extract_text_from_pdf(pdf_path)
            
            if not result['success']:
                return False
            
            text_length = len(result['text'].strip())
            
            if text_length < min_chars:
                logger.warning(f"Extracted text too short ({text_length} chars) for {pdf_path}")
                return False
            
            # Check if text contains meaningful content (not just whitespace/symbols)
            meaningful_chars = sum(1 for c in result['text'] if c.isalnum())
            meaningful_ratio = meaningful_chars / text_length if text_length > 0 else 0
            
            if meaningful_ratio < 0.1:
                logger.warning(f"Extracted text lacks meaningful content for {pdf_path}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating extraction for {pdf_path}: {str(e)}")
            return False