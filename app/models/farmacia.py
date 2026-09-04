from dataclass import dataclass
from datatime import datetime

@dataclass
class user:
    uid:str
    nome:str
    email:str
    created_at: str = datatime = field(default_factory=datatime.utcnow)
    updated_at: str = None
