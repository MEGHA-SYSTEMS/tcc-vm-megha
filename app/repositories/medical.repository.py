import firebase_admin
from firebase_admin import firestore
from app.models.medical import medical

class MedicamentoService:  

    def get_medicamento(self, medicamento_id: str):
        db = firestore.client()
        doc = db.collection('medicamentos').document(medicamento_id).get()
        if doc.exists:
            data = doc.to_dict()
            return Medicamento(nome=data.get('nome'),
                               principio_ativo=data.get('principio_ativo'),
                               dosagem=data.get('dosagem'),
                               apresentacao=data.get('apresentacao'),
                               categoria=data.get('categoria'),
                               descricao=data.get('descricao'),
                               imagem=data.get('imagem'))
        return None

    def add_medicamento(self, medicamento: Medicamento) -> str:
        db = firestore.client()
        _, doc = db.collection('medicamentos').add({
            'nome': medicamento.nome,
            'principio_ativo': medicamento.principio_ativo,
            'dosagem': medicamento.dosagem,
            'apresentacao': medicamento.apresentacao,
            'categoria': medicamento.categoria,
            'descricao': medicamento.descricao,
            'imagem': medicamento.imagem
        })
        return doc.id

    def update_medicamento(self, medicamento_id: str, medicamento: Medicamento) -> bool:
        db = firestore.client()
        db.collection('medicamentos').document(medicamento_id).update({
            'nome': medicamento.nome,
            'principio_ativo': medicamento.principio_ativo,
            'dosagem': medicamento.dosagem,
            'apresentacao': medicamento.apresentacao,
            'categoria': medicamento.categoria,
            'descricao': medicamento.descricao,
            'imagem': medicamento.imagem
        })
        return True