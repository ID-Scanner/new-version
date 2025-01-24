from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
import re
import requests
from datetime import datetime

app = FastAPI()

OCR_SERVICE_URL = "http://192.168.11.106:8003/ocr/"
REGISTRATION_SERVICE_URL = "http://192.168.11.106:8004/register/"  # Adjust based on your setup

@app.post("/process/")
async def process_id_card(file: UploadFile = File(...)):
    if file.content_type not in ["image/jpeg", "image/png"]:
        return JSONResponse(content={"error": "Invalid file format. Please upload a JPEG or PNG image."}, status_code=400)
    
    try:
        ocr_response = requests.post(
            OCR_SERVICE_URL,
            files={"file": ("id_card.jpg", file.file, file.content_type)}
        )
        ocr_response.raise_for_status()
    except requests.RequestException as e:
        return JSONResponse(content={"error": f"OCR service failed: {str(e)}"}, status_code=500)

    try:
        ocr_data = ocr_response.json()
        extracted_text = ocr_data.get("text", "")
    except ValueError:
        return JSONResponse(content={"error": "Failed to parse OCR response."}, status_code=500)

    # Extract CIN, name, and first name from the text
    cin = extract_cin(extracted_text)
    name, first_name = extract_name_and_first_name(extracted_text)

    # Extract Birth Date (make sure this part of the code extracts a valid date)
    birth_date = extract_birth_date(extracted_text)

    if not cin:
        return {"valid": False, "message": "CIN not found in the text"}
    if not name or not first_name:
        return {"valid": False, "message": "Name or First Name not found in the text"}
    if not birth_date:
        return {"valid": False, "message": "Birth date not found in the text"}

    # Send the extracted data for registration
    registration_data = {
        "cin": cin,
        "first_name": first_name,
        "last_name": name,
        "birth_date": birth_date
    }

    # Register the identity
    register_identity(registration_data)

    return {
        "valid": True,
        "cin": cin,
        "name": name,
        "first_name": first_name,
        "birth_date": birth_date,
        "message": "Identity processed and registration attempted."
    }

def extract_cin(text: str) -> str:
    pattern = r"[A-Z]{3} \d{6}"  # Format CIN: 3 letters followed by 6 digits
    match = re.search(pattern, text)
    if match:
        return match.group(0)
    return None

def extract_name_and_first_name(text: str) -> tuple:
    name_pattern = r"Nom\s*[:\-]?\s*([A-Za-zÀ-ÿéèôîûç]+)"
    first_name_pattern = r"Prénom\s*[:\-]?\s*([A-Za-zÀ-ÿéèôîûç]+)"
    
    name_match = re.search(name_pattern, text)
    first_name_match = re.search(first_name_pattern, text)
    
    name = name_match.group(1) if name_match else None
    first_name = first_name_match.group(1) if first_name_match else None
    
    return name, first_name

def extract_birth_date(text: str) -> str:
    # Example: Extract birth date in the format 'DD/MM/YYYY'
    birth_date_pattern = r"\b\d{2}/\d{2}/\d{4}\b"
    match = re.search(birth_date_pattern, text)
    if match:
        return match.group(0)
    return None
