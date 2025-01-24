# register.py
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

# Define the data model for registration
class RegistrationRequest(BaseModel):
    cin: str
    first_name: str
    last_name: str
    birth_date: str

# Handle the registration POST request
@app.post("/register/")
def register_identity(data: RegistrationRequest):
    # Here you can process the data or save it to a database
    return {
        "message": "Identity registered successfully",
        "data": data
    }
