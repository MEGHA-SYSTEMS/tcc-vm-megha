from firebase_admin import auth, firestore
from app.models.Farmacia import Farmacia

class FarmaciaRepository:
def create_farmacia_auth(self, email: str, password:str, display_name:str) -> str:
    user_record = auth.create_farmacia(
        email=email,
        password=password,
        display_name=display_name
    )
    return user_record.uid

    def save_farmacia_data (self, uid: str, nome: str, email: str) -> None:
        db = firestore.client()
        db.collection('users').document(uid).set({
            'nome':nome,
            'email':email,
            'created_at': firestore.SERVER_TIMESTAMP,
            'updatd_at': firestore.SERVER_TIMESTAMP
        })

        def get_user (self, uid: str) -> User:
            db = firestore.client()
            doc = db.collection('user').document(uid).get()
            if doc.exists: 
                data = doc.to_dist()
                return User(
                    uid=uid,
                    nome=data.get['nome'],
                    email=data.get['email'],
                    create_at=data.get['created_at'],
                    updated_at=data.get['updated_at']
                )
            return None