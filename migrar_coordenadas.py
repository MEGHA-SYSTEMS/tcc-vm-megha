"""Rode UMA vez: python migrar_coordenadas.py
Salva lat/lng nas farmácias que ainda não têm coordenadas."""
import time

from firebase_config import db
from geocoding import geocodificar

for doc in db.collection("farmacias").stream():
    d = doc.to_dict()

    if d.get("lat") is not None:
        print(f"[pula]   {d.get('nome')} já tem coordenadas")
        continue

    e = d.get("endereco") or {}
    coords = geocodificar(
        e.get("rua", ""), e.get("numero", ""), e.get("bairro", ""),
        e.get("cidade", ""), e.get("cep", ""),
    )

    if coords:
        doc.reference.update({"lat": coords[0], "lng": coords[1]})
        print(f"[ok]     {d.get('nome')} -> {coords}")
    else:
        print(f"[FALHOU] {d.get('nome')}: confira o endereço")

    time.sleep(1.1)