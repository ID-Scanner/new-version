from fastapi import FastAPI
from pydantic import BaseModel
import re

app = FastAPI()

class ValidationRequest(BaseModel):
    cin: str

@app.post("/validate/")
def validate(data: ValidationRequest):
    pattern = r"^[A-Z]{3} \d{6}$"  # Exemple de format CIN
    if re.match(pattern, data.cin):
        return {"valid": True}
    return {"valid": False, "message": "Invalid CIN format"}
