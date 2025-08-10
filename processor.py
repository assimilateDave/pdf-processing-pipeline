import os
import cv2
import numpy as np
import shutil
from pdf2image import convert_from_path
from PIL import Image, ImageFilter, ImageEnhance
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Define your working directories here
WATCH_DIR = os.path.abspath(r"C:\PDF-Processing\PDF_IN")
WORK_DIR = os.path.abspath(r"C:\PDF-Processing\PDF_working")

def move_to_work_folder(file_path):
    """Move file from the watch folder to the work folder."""
    if not os.path.isdir(WORK_DIR):
        os.makedirs(WORK_DIR)
    dest_path = os.path.join(WORK_DIR, os.path.basename(file_path))
    shutil.move(file_path, dest_path)
    return dest_path

def classify_document(file_path, extracted_text):
    """
    Identify and classify the document type based on the file content.
    You can start with some simple keyword matching; later you can replace this with a machine
    learning model or more complex logic.
    """
    if "invoice" in extracted_text.lower():
        return "Invoice"
    elif "receipt" in extracted_text.lower():
        return "Receipt"
    elif "report" in extracted_text.lower():
        return "Report"
    else:
        return "Unknown"

def preprocess_fax_page(pil_img):
    """
    Preprocess a PIL image of a fax PDF page for improved OCR accuracy.
    Steps: grayscale, adaptive threshold, median blur, sharpen, and contrast enhancement.
    """
    # Convert to grayscale
    img = np.array(pil_img.convert('L'))

    # Adaptive thresholding to binarize
    img = cv2.adaptiveThreshold(
        img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 15, 11
    )

    # Median blur to reduce noise
    img = cv2.medianBlur(img, 3)

    # Convert back to PIL for further processing
    pil_img = Image.fromarray(img)

    # Sharpen the image
    pil_img = pil_img.filter(ImageFilter.SHARPEN)

    # Enhance contrast
    enhancer = ImageEnhance.Contrast(pil_img)
    pil_img = enhancer.enhance(2.0)  # Increase contrast; adjust factor as needed

    return pil_img

def extract_text_from_pdf(file_path):
    """
    Extract text from a PDF, using preprocessing optimized for faxed documents.
    Saves debug images with original filename as prefix.
    Skips extraction of the top 60px of each page.
    """
    debug_folder = r"C:\PDF-Processing\debug_imgs"
    os.makedirs(debug_folder, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    try:
        # Use higher DPI for faxes
        pages = convert_from_path(
            file_path, 
            dpi=400, 
            poppler_path=r"C:\PDF-Processing\poppler\Library\bin"
        )
        text = ""
        for i, page in enumerate(pages):
            # Preprocessing step here:
            proc_page = preprocess_fax_page(page)
            debug_path = os.path.join(
                debug_folder, f'{base_name}_debug_page_{i}.png'
            )
            proc_page.save(debug_path)
            # Crop top 60px
            width, height = proc_page.size
            cropped_page = proc_page.crop((0, 60, width, height))
            config = '--oem 1 --psm 3'
            text += pytesseract.image_to_string(cropped_page, config=config, lang='eng')
        return text
    except Exception as e:
        print(f"Error processing PDF: {e}")
        return ""

def extract_text_from_tif(file_path):
    """
    Use OCR to extract text from a TIF, skipping the top 60px.
    """
    try:
        img = Image.open(file_path)
        proc_img = preprocess_fax_page(img)
        # Crop top 60px
        width, height = proc_img.size
        cropped_img = proc_img.crop((0, 60, width, height))
        config = '--oem 1 --psm 6'
        text = pytesseract.image_to_string(cropped_img, config=config, lang='eng')
        return text
    except Exception as e:
        print(f"Error processing TIF: {e}")
        return ""

def process_document(file_path):
    """
    Process the document: move to work folder, extract text, classify the document,
    and return the results.
    """
    print("PROCESS_DOCUMENT CALLED")
    work_file = move_to_work_folder(file_path)
    extracted_text = ""
    if work_file.lower().endswith(".pdf"):
        extracted_text = extract_text_from_pdf(work_file)
    elif work_file.lower().endswith((".tif", ".tiff")):
        extracted_text = extract_text_from_tif(work_file)
    else:
        print("Unsupported file format")
    
    document_type = classify_document(work_file, extracted_text)
    return os.path.basename(work_file), document_type, extracted_text