from typing import List, Optional

from firebase_admin import firestore
from google.api_core.exceptions import NotFound

from app.models.medical import Medicamento


class MedicamentoService:
    COLLECTION = 'medicamentos'

    def __init__(self):
        self.db = firestore.client()
        self.collection = self.db.collection(self.COLLECTION)

    # ---------- Conversões ----------

    @staticmethod
    def _to_dict(medicamento: Medicamento) -> dict:
        return {
            'nome': medicamento.nome,
            'principio_ativo': medicamento.principio_ativo,
            'dosagem': medicamento.dosagem,
            'apresentacao': medicamento.apresentacao,
            'categoria': medicamento.categoria,
            'descricao': medicamento.descricao,
            'imagem': medicamento.imagem,
        }

    @staticmethod
    def _from_doc(doc) -> Medicamento:
        data = doc.to_dict()
        return Medicamento(
            id=doc.id,
            nome=data.get('nome'),
            principio_ativo=data.get('principio_ativo'),
            dosagem=data.get('dosagem'),
            apresentacao=data.get('apresentacao'),
            categoria=data.get('categoria'),
            descricao=data.get('descricao'),
            imagem=data.get('imagem'),
        )

    

    def get_medicamento(self, medicamento_id: str) -> Optional[Medicamento]:
        doc = self.collection.document(medicamento_id).get()
        return self._from_doc(doc) if doc.exists else None

    def list_medicamentos(self, categoria: Optional[str] = None) -> List[Medicamento]:
        query = self.collection
        if categoria:
            query = query.where('categoria', '==', categoria)
        return [self._from_doc(doc) for doc in query.stream()]

    def add_medicamento(self, medicamento: Medicamento) -> str:
        _, doc_ref = self.collection.add(self._to_dict(medicamento))
        return doc_ref.id

    def update_medicamento(self, medicamento_id: str, medicamento: Medicamento) -> bool:
        try:
            self.collection.document(medicamento_id).update(self._to_dict(medicamento))
            return True
        except NotFound:
            return False

    def delete_medicamento(self, medicamento_id: str) -> bool:
        doc_ref = self.collection.document(medicamento_id)
        if not doc_ref.get().exists:
            return False
        doc_ref.delete()
        return True