"""Produtos cadastrados pelas farmácias (coleção 'produtos' no Firestore).

Cada produto guarda o 'farmacia_id' de quem cadastrou. O campo 'chave' é o
nome normalizado (minúsculo, sem acento), usado depois para juntar o mesmo
remédio de farmácias diferentes no catálogo e comparar preços.
"""
import re
import unicodedata

import cloudinary
import cloudinary.uploader
from firebase_admin import firestore

from firebase_config import db

cloudinary.config(secure=True)  # lê a CLOUDINARY_URL do ambiente

TIPOS_IMAGEM = {"image/jpeg", "image/png", "image/webp"}

COLECAO = "produtos"

CATEGORIAS = [
    "Analgésico e Antitérmico", "Anticoagulante", "Auxílio para o Sono",
    "Controle da Diabetes", "Controle da Pressão Arterial",
    "Controle da Tireoide", "Controle do Colesterol", "Cuidados Diários",
    "Cuidados com a Pele", "Cuidados com a Visão", "Diurético",
    "Prevenção Cardiovascular", "Proteção Gástrica", "Saúde Respiratória",
    "Saúde das Articulações", "Saúde dos Ossos", "Suplemento Vitamínico",
    "Outros",
]


def gerar_chave(nome):
    """'Dipirona Monoidratada 500 mg' -> 'dipirona monoidratada 500mg'."""
    texto = unicodedata.normalize("NFKD", nome)
    texto = "".join(c for c in texto if not unicodedata.combining(c)).lower()
    texto = re.sub(r"[^a-z0-9]+", " ", texto).strip()
    return re.sub(r"(\d)\s+(mg|mcg|g|ml|ui)\b", r"\1\2", texto)


def converter_preco(texto):
    """'8,90' / '8.90' / 'R$ 1.234,56' -> float. Levanta ValueError se ruim."""
    limpo = (texto or "").replace("R$", "").replace(" ", "")
    if "," in limpo:
        limpo = limpo.replace(".", "").replace(",", ".")
    preco = round(float(limpo), 2)
    if preco <= 0 or preco > 100000:
        raise ValueError("preço fora do intervalo")
    return preco


def _query_da_farmacia(farmacia_id):
    try:
        from google.cloud.firestore_v1.base_query import FieldFilter
        return db.collection(COLECAO).where(
            filter=FieldFilter("farmacia_id", "==", farmacia_id))
    except ImportError:
        return db.collection(COLECAO).where("farmacia_id", "==", farmacia_id)


def listar_produtos(farmacia_id):
    """Produtos de uma farmácia, os mais novos primeiro."""
    if db is None:
        return []
    produtos = []
    for doc in _query_da_farmacia(farmacia_id).stream():
        produto = doc.to_dict()
        produto["id"] = doc.id
        produtos.append(produto)
    produtos.sort(key=lambda p: str(p.get("criado_em") or ""), reverse=True)
    return produtos


def adicionar_produto(farmacia_id, form, arquivo=None):
    """Valida o formulário, envia a foto (se houver) e salva.

    Devolve (ok, mensagem).
    """
    if db is None:
        return False, "Sistema indisponível no momento."

    nome = form.get("nome", "").strip()
    categoria = form.get("categoria", "").strip()
    principio = form.get("principio_ativo", "").strip()
    descricao = form.get("descricao", "").strip()

    if not nome or not descricao:
        return False, "Preencha o nome e a descrição do produto."
    if len(nome) > 120 or len(descricao) > 1000 or len(principio) > 120:
        return False, "Texto muito longo. Encurte o nome ou a descrição."
    if categoria not in CATEGORIAS:
        return False, "Escolha uma categoria da lista."
    try:
        preco = converter_preco(form.get("preco", ""))
    except ValueError:
        return False, "Preço inválido. Use um formato como 8,90."

    # Upload só depois das outras validações, para não deixar imagem
    # órfã no Cloudinary quando o cadastro falha.
    imagem = ""
    if arquivo and arquivo.filename:
        if arquivo.mimetype not in TIPOS_IMAGEM:
            return False, "Envie uma imagem JPG, PNG ou WEBP."
        try:
            resultado = cloudinary.uploader.upload(
                arquivo,
                folder="poupemais/produtos",
                resource_type="image",
                transformation=[
                    {"width": 800, "height": 800, "crop": "fill", "gravity": "auto"},
                    {"fetch_format": "auto", "quality": "auto"},
                ],
            )
            imagem = resultado["secure_url"]
        except Exception:
            return False, "Não foi possível enviar a imagem. Tente novamente."

    db.collection(COLECAO).add({
        "farmacia_id": farmacia_id,
        "nome": nome,
        "chave": gerar_chave(nome),
        "categoria": categoria,
        "principio_ativo": principio,
        "descricao": descricao,
        "preco": preco,
        "imagem": imagem,
        "criado_em": firestore.SERVER_TIMESTAMP,
    })
    return True, "Produto cadastrado!"


def excluir_produto(farmacia_id, produto_id):
    """Só exclui se o produto for da farmácia logada. Devolve (ok, mensagem)."""
    if db is None:
        return False, "Sistema indisponível no momento."
    ref = db.collection(COLECAO).document(produto_id)
    doc = ref.get()
    if not doc.exists or doc.to_dict().get("farmacia_id") != farmacia_id:
        return False, "Produto não encontrado."
    ref.delete()
    return True, "Produto excluído."