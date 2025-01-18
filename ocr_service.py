import pytesseract
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
import cv2
import numpy as np
from PIL import Image
import re

app = FastAPI()

# Configuration de Tesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

@app.post("/ocr/")
async def extract_text(file: UploadFile = File(...)):
    try:
        # Charger et prétraiter l'image
        image = Image.open(file.file)
        image_np = np.array(image)

        # Prétraitement de l'image
        preprocessed = preprocess_image(image_np)

        # Configuration OCR pour le français et l'arabe
        custom_config = r'--oem 3 --psm 3 -l fra+ara'  # Ajouter 'ara' pour l'arabe
        text = pytesseract.image_to_string(preprocessed, config=custom_config)

        # Filtrer uniquement les informations en français
        filtered_text = filter_french_text(text)

        # Extraire les informations
        cin = extract_cin(filtered_text)
        name, first_name = extract_name_and_first_name(filtered_text)
        birth_date = extract_birth_date(filtered_text)

        # Retourner les informations extraites
        return {
            "cin": cin,
            "name": name,
            "first_name": first_name,
            "birth_date": birth_date,
            "raw_text": filtered_text
        }
    except Exception as e:
        # Retourner une erreur détaillée en cas d'échec
        return JSONResponse(
            content={"error": f"Erreur lors du traitement: {str(e)}"},
            status_code=500
        )


def preprocess_image(image):
    """
    Prétraitement amélioré de l'image pour une meilleure reconnaissance
    """
    try:
        # Convertir en niveaux de gris
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Débruitage
        denoised = cv2.fastNlMeansDenoising(gray)

        # Amélioration du contraste avec CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)

        # Binarisation adaptative (seuil variable selon les voisins)
        binary = cv2.adaptiveThreshold(
            enhanced,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,
            2
        )

        # Dilatation pour améliorer la lisibilité (mettre en valeur les contours)
        kernel = np.ones((1, 1), np.uint8)
        dilated = cv2.dilate(binary, kernel, iterations=1)

        return dilated
    except cv2.error as e:
        raise ValueError(f"Erreur OpenCV lors du prétraitement de l'image: {str(e)}")
    except Exception as e:
        raise ValueError(f"Erreur inconnue lors du prétraitement de l'image: {str(e)}")


def filter_french_text(text: str) -> str:
    """
    Filtrer uniquement les lignes en français
    """
    try:
        # Pattern pour identifier les caractères arabes (en excluant les lignes avec des caractères arabes)
        arabic_pattern = r'[\u0600-\u06FF]'

        # Garder uniquement les lignes ne contenant pas de caractères arabes
        filtered_lines = [line for line in text.split('\n') if not re.search(arabic_pattern, line)]

        return '\n'.join(filtered_lines)
    except Exception as e:
        raise ValueError(f"Erreur lors du filtrage du texte français: {str(e)}")


def extract_cin(text: str) -> str:
    """
    Extraction du numéro de CIN avec plusieurs patterns possibles
    """
    try:
        # Patterns possibles pour le CIN marocain
        patterns = [
            r'[A-Z]{1,2}\d{5,6}',  # Format standard
            r'[A-Z]{1,2} \d{5,6}',  # Format avec espace
            r'CIN[:\s]+([A-Z]{1,2}\d{5,6})',  # Format avec préfixe CIN
            r'CARTE NATIONALE[:\s]+([A-Z]{1,2}\d{5,6})'  # Format complet
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1) if len(match.groups()) > 0 else match.group(0)
        return None
    except re.error as e:
        raise ValueError(f"Erreur lors de l'extraction du CIN: {str(e)}")
    except Exception as e:
        raise ValueError(f"Erreur inconnue lors de l'extraction du CIN: {str(e)}")


def extract_name_and_first_name(text: str) -> tuple:
    """
    Extraction du nom et du prénom en français
    """
    try:
        lines = text.split('\n')

        name = None
        first_name = None

        # Patterns pour le nom et le prénom
        name_pattern = r'Nom[:\s]+([A-ZÀ-Ÿ\s]+)'  # Nom
        first_name_pattern = r'Prénom[:\s]+([A-ZÀ-Ÿ\s]+)'  # Prénom

        for line in lines:
            # Recherche du nom
            match_name = re.search(name_pattern, line)
            if match_name and not name:
                name = match_name.group(1).strip()

            # Recherche du prénom
            match_first_name = re.search(first_name_pattern, line)
            if match_first_name and not first_name:
                first_name = match_first_name.group(1).strip()

        return name, first_name
    except re.error as e:
        raise ValueError(f"Erreur lors de l'extraction du nom et du prénom: {str(e)}")
    except Exception as e:
        raise ValueError(f"Erreur inconnue lors de l'extraction du nom et du prénom: {str(e)}")


def extract_birth_date(text: str) -> str:
    """
    Extraction de la date de naissance
    """
    try:
        # Pattern pour la date de naissance
        pattern = r'Néle?[:\s]+(\d{2}.\d{2}.\d{4})|M\w*le[:\s]+(\d{2}.\d{2}.\d{4})'

        match = re.search(pattern, text)
        if match:
            return match.group(1) if match.group(1) else match.group(2)
        return None
    except re.error as e:
        raise ValueError(f"Erreur lors de l'extraction de la date de naissance: {str(e)}")
    except Exception as e:
        raise ValueError(f"Erreur inconnue lors de l'extraction de la date de naissance: {str(e)}")
