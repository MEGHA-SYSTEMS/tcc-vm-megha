from dataclasses import dataclass

@dataclass
class medical:
   id: str
    nome: str
    principio_ativo: str
    laboratorio: str
    categoria: str
    dosagem: str
    apresentacao: str
    farmacia_id: str
    preco: float
    desconto: float
    exige_receita: bool
    estoque: int
    descricao: str
    imagem: str
