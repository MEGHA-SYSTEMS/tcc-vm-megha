from dataclass import dataclass

@dataclass
class user:
    uid:str
    nome:str
    email:str
    created_at: str = None
    updated_at: str = None
