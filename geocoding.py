"""Converte o endereço de uma farmácia em latitude/longitude (Nominatim/OSM)."""
import time

import requests

NOMINATIM = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "PoupeMais/1.0 (contato@poupemais.com)"}


def _buscar(params):
    params = {**params, "format": "json", "limit": 1, "countrycodes": "br"}
    try:
        r = requests.get(NOMINATIM, params=params, headers=HEADERS, timeout=10)
        r.raise_for_status()
        dados = r.json()
    except (requests.RequestException, ValueError):
        return None

    if not dados:
        return None
    return float(dados[0]["lat"]), float(dados[0]["lon"])


def geocodificar(rua, numero, bairro, cidade, cep=""):
    """Devolve (lat, lng) ou None. Tenta do mais preciso ao menos preciso."""
    tentativas = [
        {"q": f"{rua} {numero}, {bairro}, {cidade}, Brasil"},
        {"q": f"{rua}, {bairro}, {cidade}, Brasil"},
        {"q": f"{rua}, {cidade}, Brasil"},
    ]
    if cep:
        tentativas.append({"postalcode": cep, "country": "Brasil"})

    for i, params in enumerate(tentativas):
        if i > 0:
            time.sleep(1.1)  # respeita o limite do Nominatim (1 req/s)
        resultado = _buscar(params)
        if resultado:
            return resultado
    return None