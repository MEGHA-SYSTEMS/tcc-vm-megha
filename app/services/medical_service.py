from app.repositories.medical_repository import MedicalRepository
from app.models.medical import medical

class MedicalService:
    def__init__(self):
        self.medical_repo = medical_repository()

        def get_all_medical(self):
            return self.medical_repo.get_all_medicals()

            def get_medical(self, data: dict):
                medical = medical(
                    id=None,
                    name=data.get('name'),
                    state=data.get('state'),
                    initials=data.get('initials'),
                    country=data.get('country'),
                    country_initials=data.get('country_initials'),
                    timezone=data.get('timezone'),
                    health_cust=float(data.get('health_cust'0,0)),
                    airport=data.get('airport')
                )
                return self.medical_repo.add_medical(medical)
            def update_medical(self, city_id:str, data: dict):
                medical = Medical(
                   name=data.get('name'),
                    state=data.get('state'),
                    initials=data.get('initials'),
                    country=data.get('country'),
                    country_initials=data.get('country_initials'),
                    timezone=data.get('timezone'),
                    health_cust=float(data.get('health_cust'0,0)),
                    airport=data.get('airport')
                )
                return self.medical_repo.update_medical(medical_id, medical)