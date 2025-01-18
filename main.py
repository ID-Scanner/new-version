import requests
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
import re 

app = FastAPI()

# Adresse du service OCR
OCR_SERVICE_URL = "http://192.168.11.106:8003/ocr/"
VALIDATION_SERVICE_URL = "http://192.168.11.106:8002/validate/"  # Adresse du service de validation

@app.post("/process/")
async def process_id_card(file: UploadFile = File(...)):
    # Vérification du type de fichier (JPEG ou PNG)
    if file.content_type not in ["image/jpeg", "image/png"]:
        return JSONResponse(content={"error": "Invalid file format. Please upload a JPEG or PNG image."}, status_code=400)
    
    # Étape 1: Envoyer l'image au service OCR
    try:
        ocr_response = requests.post(
            OCR_SERVICE_URL,
            files={"file": ("id_card.jpg", file.file, file.content_type)}
        )
        ocr_response.raise_for_status()  # Lève une exception si le code HTTP est >= 400
    except requests.RequestException as e:
        return JSONResponse(content={"error": f"OCR service failed: {str(e)}"}, status_code=500)

    try:
        ocr_data = ocr_response.json()
        extracted_text = ocr_data.get("text", "")
    except ValueError:
        return JSONResponse(content={"error": "Failed to parse OCR response."}, status_code=500)

    # Étape 2: Extraire le CIN, le nom et le prénom
    cin = extract_cin(extracted_text)
    name, first_name = extract_name_and_first_name(extracted_text)

    if not cin:
        return {"valid": False, "message": "CIN not found in the text"}
    if not name or not first_name:
        return {"valid": False, "message": "Name or First Name not found in the text"}

    # Étape 3: Valider le CIN
    try:
        validation_response = requests.post(
            VALIDATION_SERVICE_URL,
            json={"cin": cin}
        )
        validation_response.raise_for_status()
        validation_data = validation_response.json()
    except requests.RequestException as e:
        return JSONResponse(content={"error": f"Validation service failed: {str(e)}"}, status_code=500)

    # Étape 4: Retourner les résultats
    return {
        "valid": True,
        "cin": cin,
        "name": name,
        "first_name": first_name,
        "validation": validation_data
    }

def extract_cin(text: str) -> str:
    """Extraire le CIN depuis le texte brut."""
    pattern = r"[A-Z]{3} \d{6}"  # Exemple de format CIN: 3 lettres majuscules suivies de 6 chiffres
    match = re.search(pattern, text)
    if match:
        return match.group(0)
    return None

def extract_name_and_first_name(text: str) -> tuple:
    """Extraire le nom et le prénom depuis le texte brut."""
    # Expressions régulières pour extraire le nom et le prénom
    name_pattern = r"Nom\s*[:\-]?\s*([A-Za-zÀ-ÿéèôîûç]+)"  # Cherche le nom
    first_name_pattern = r"Prénom\s*[:\-]?\s*([A-Za-zÀ-ÿéèôîûç]+)"  # Cherche le prénom
    
    name_match = re.search(name_pattern, text)
    first_name_match = re.search(first_name_pattern, text)
    
    name = name_match.group(1) if name_match else None
    first_name = first_name_match.group(1) if first_name_match else None
    
    return name, first_name
