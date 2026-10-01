"""Catálogo: junta os produtos cadastrados pelas farmácias (Firestore)
e agrupa o mesmo remédio para comparar preços."""
from firebase_config import db
from produtos_service import COLECAO, gerar_chave

COLECAO_FARMACIAS = "farmacias"  # ajuste se sua coleção tiver outro nome


def _formatar_endereco(end):
    """Transforma o endereço salvo no Firebase em um texto legível."""
    if isinstance(end, str):
        return end
    if not isinstance(end, dict):
        return ""

    rua = ", ".join(x for x in (end.get("rua", ""), end.get("numero", "")) if x)
    local = ", ".join(x for x in (end.get("bairro", ""), end.get("cidade", "")) if x)
    partes = [p for p in (rua, local) if p]
    texto = " - ".join(partes)

    if end.get("cep"):
        texto += f" - CEP {end['cep']}"
    return texto

def _dados_farmacia(farmacia_id, cache):
    """Nome e endereço da farmácia (busca uma vez só por farmácia)."""
    if farmacia_id not in cache:
        nome, endereco = "Farmácia", ""
        try:
            doc = db.collection(COLECAO_FARMACIAS).document(farmacia_id).get()
            if doc.exists:
                dados = doc.to_dict()
                nome = dados.get("nome", nome)
                endereco = _formatar_endereco(dados.get("endereco", ""))
        except Exception:
            pass
        cache[farmacia_id] = (nome, endereco)
    return cache[farmacia_id]


def _agrupar(docs):
    cache = {}
    grupos = {}
    for doc in docs:
        d = doc.to_dict()
        chave = d.get("chave") or gerar_chave(d.get("nome", ""))
        if not chave:
            continue

        nome_farmacia, endereco = _dados_farmacia(d.get("farmacia_id", ""), cache)
        oferta = {
            "farmacia": nome_farmacia,
            "preco": d.get("preco", 0),
            "endereco": endereco,
        }

        grupo = grupos.get(chave)
        if grupo is None:
            grupo = grupos[chave] = {
                "id": chave.replace(" ", "-"),  # vai na URL: /produto/<id>
                "nome": d.get("nome", ""),
                "categoria": d.get("categoria", ""),
                "imagem": d.get("imagem", ""),
                "descricao": d.get("descricao", ""),
                "principio_ativo": d.get("principio_ativo", ""),
                "precos": [],
            }
        grupo["precos"].append(oferta)
        if not grupo["imagem"] and d.get("imagem"):
            grupo["imagem"] = d["imagem"]

    produtos = []
    for grupo in grupos.values():
        grupo["precos"].sort(key=lambda p: p["preco"])
        grupo["precos_ordenados"] = grupo["precos"]
        grupo["menor_preco"] = grupo["precos"][0]
        produtos.append(grupo)
    produtos.sort(key=lambda p: p["nome"].lower())
    return produtos


def get_todos_produtos():
    """Todos os produtos das farmácias, com o menor preço calculado."""
    if db is None:
        return []
    return _agrupar(db.collection(COLECAO).stream())


def get_produto_por_id(produto_id):
    """Um produto (com o preço de cada farmácia). None se não existir."""
    if db is None or not produto_id:
        return None
    chave = produto_id.replace("-", " ")
    produtos = _agrupar(db.collection(COLECAO).where("chave", "==", chave).stream())
    return produtos[0] if produtos else None