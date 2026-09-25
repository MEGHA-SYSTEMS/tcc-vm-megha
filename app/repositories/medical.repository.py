import firebase_admin
from firebase_admin import firestore
from app.models.medical import medical

class MedicalRepository:
    def get_all_medicals(self) -> list[Medical]:
        db = firestore.client()
        docs = db 