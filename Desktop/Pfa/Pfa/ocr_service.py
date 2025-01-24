import pytesseract
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
import cv2
import numpy as np
from PIL import Image
import re
from langdetect import detect
import logging
from typing import Tuple, Optional
import os

# Configurationer
class Config:
    TESSERACT_CMD = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
    ALLOWED_MIME_TYPES = ["image/png", "image/jpeg"]
    MIN_TEXT_LENGTH = 10
    VALID_YEAR_RANGE = (1900, 2024)
    MOROCCAN_CITIES = [
        "TANGER", "ASSILAH", "CASABLANCA", "RABAT", "FES", "MEKNES", 
        "MARRAKECH", "AGADIR", "TETOUAN", "OUJDA", "KENITRA", "SALE"
    ]

# Initialize FastAPI and logging
app = FastAPI(title="Moroccan ID Card OCR Service")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ocr_service")

# Set Tesseract path
pytesseract.pytesseract.tesseract_cmd = Config.TESSERACT_CMD

class ImageProcessor:
    @staticmethod
    def enhance_image(image_np: np.ndarray) -> np.ndarray:
        """
        Enhanced image preprocessing specifically for Moroccan ID cards.
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)
        
        # Increase contrast using CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        gray = clahe.apply(gray)
        
        # Denoise the image
        denoised = cv2.fastNlMeansDenoising(gray)
        
        # Apply adaptive thresholding
        binary = cv2.adaptiveThreshold(
            denoised, 255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        # Apply morphological operations
        kernel = np.ones((2,2), np.uint8)
        processed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        return processed

class TextProcessor:
    @staticmethod
    def clean_text(text: str) -> str:
        """
        Clean and prepare OCR text while preserving date formats.
        """
        # Split into lines and remove empty lines
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        
        # Remove duplicate lines while preserving order
        seen = set()
        cleaned_lines = []
        for line in lines:
            if line not in seen:
                cleaned_lines.append(line)
                seen.add(line)
        
        return "\n".join(cleaned_lines)

    @staticmethod
    def detect_language_safe(text: str) -> str:
        """
        Safer language detection with error handling.
        """
        if not text or len(text.strip()) < 3:
            return "unknown"
        try:
            return detect(text)
        except:
            return "unknown"

class DataExtractor:
    @staticmethod
    def extract_moroccan_cin(text: str) -> Optional[str]:
        """
        Extract CIN from text with enhanced pattern matching.
        """
        patterns = [
            r'[A-Z]{1,2}\d{5,6}',  # Standard format
            r'CIN\s*[A-Z]{1,2}\d{5,6}',  # With CIN prefix
            r'[A-Z]{1,2}\s*\d{5,6}',  # With space between letters and numbers
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                cin = match.group(0).replace(" ", "").upper()
                if re.match(r'^[A-Z]{1,2}\d{5,6}$', cin):
                    return cin
        
        return None

    @staticmethod
    def extract_name_components(text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract name components with improved handling of Arabic and French text.
        """
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        name = first_name = None

        for line in lines:
            # Skip lines with digits or that are too short
            if re.search(r'\d', line) or len(line) < 2:
                continue

            # Clean the line
            cleaned_line = re.sub(r'[^\w\s\u0600-\u06FF]', '', line)
            words = cleaned_line.split()

            # Check for valid name line
            if len(words) >= 2 and all(word.isalpha() for word in words):
                if not first_name:
                    first_name = words[0]
                    name = " ".join(words[1:])
                    break

        return name, first_name

    @staticmethod
    def extract_birth_date(text: str) -> Optional[str]:
        """
        Extract birth date with comprehensive pattern matching.
        """
        # Process text line by line
        lines = text.split('\n')
        
        date_patterns = [
            r'(?<!\d)(\d{1,2})[.\s-](\d{1,2})[.\s-](\d{4})(?!\d)',
            r'né\s?le\s*:?\s*(\d{1,2})[.\s-](\d{1,2})[.\s-](\d{4})',
            r'nele\s*:?\s*(\d{1,2})[.\s-](\d{1,2})[.\s-](\d{4})',
            r'(?:تاريخ الازدياد|تاريخ الميلاد)\s*:?\s*(\d{1,2})[.\s-](\d{1,2})[.\s-](\d{4})',
            r'(?<!\d)(\d{2})[.\s-](\d{2})[.\s-](\d{4})(?!\d)',
        ]
        
        def is_valid_date(day: str, month: str, year: str) -> bool:
            try:
                day, month, year = map(int, (day, month, year))
                return (Config.VALID_YEAR_RANGE[0] <= year <= Config.VALID_YEAR_RANGE[1] and 
                       1 <= month <= 12 and 
                       1 <= day <= 31)
            except:
                return False
        
        # Check each line for dates
        for line in lines:
            line = ' '.join(line.split()).lower()
            
            for pattern in date_patterns:
                matches = re.finditer(pattern, line)
                for match in matches:
                    if len(match.groups()) == 3:
                        day, month, year = match.groups()
                        day = day.zfill(2)
                        month = month.zfill(2)
                        
                        if is_valid_date(day, month, year):
                            return f"{day}/{month}/{year}"
        
        # Fallback: look for standalone numbers
        for line in lines:
            numbers = re.findall(r'\d+', line)
            if len(numbers) >= 3:
                for i in range(len(numbers)-2):
                    day, month, year = numbers[i:i+3]
                    if len(year) == 4 and is_valid_date(day, month, year):
                        return f"{day.zfill(2)}/{month.zfill(2)}/{year}"
        
        return None

@app.post("/ocr/")
async def extract_text(file: UploadFile = File(...)):
    """
    Process ID card image and extract relevant information.
    """
    try:
        # Validate file type
        if file.content_type not in Config.ALLOWED_MIME_TYPES:
            return JSONResponse(
                content={"error": "Invalid file type. Please upload a PNG or JPEG image."},
                status_code=400
            )

        # Read and process image
        image = Image.open(file.file)
        image_np = np.array(image)
        processed_image = ImageProcessor.enhance_image(image_np)

        # Extract text using Tesseract
        custom_config = r'--oem 3 --psm 3 -l fra+ara+eng --dpi 300'
        raw_text = pytesseract.image_to_string(image_np, config=custom_config)
        processed_text = pytesseract.image_to_string(processed_image, config=custom_config)

        # Clean and combine texts
        combined_text = TextProcessor.clean_text(f"{raw_text}\n{processed_text}")
        logger.info("Combined extracted text: %s", combined_text)

        # Extract information
        cin = DataExtractor.extract_moroccan_cin(combined_text)
        name, first_name = DataExtractor.extract_name_components(combined_text)
        birth_date = DataExtractor.extract_birth_date(combined_text)

        # Validate critical fields
        if not cin:
            logger.warning("CIN not found in text: %s", combined_text)
            raise ValueError("Unable to extract CIN from the image. Please ensure the ID card is clearly visible.")

        if not birth_date:
            logger.warning("Birth date not found in text: %s", combined_text)
            raise ValueError("Unable to extract birth date from the image. Please ensure the ID card is clearly visible.")

        # Log successful extraction
        logger.info(f"Successfully extracted - CIN: {cin}, Birth Date: {birth_date}")

        return {
            "cin": cin,
            "name": name,
            "first_name": first_name,
            "birth_date": birth_date,
            "raw_text": raw_text,
            "processed_text": processed_text
        }

    except Exception as e:
        logger.error("OCR processing error: %s", str(e), exc_info=True)
        return JSONResponse(
            content={
                "error": "Processing error",
                "message": str(e),
                "type": type(e).__name__
            },
            status_code=500
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)