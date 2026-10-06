"""Produtos cadastrados pelas farmácias (coleção 'produtos' no Firestore).

Cada produto guarda o 'farmacia_id' de quem cadastrou. O campo 'chave' é o
nome normalizado (minúsculo, sem acento), usado depois para juntar o mesmo
remédio de farmácias diferentes no catálogo e comparar preços.
"""
import re
import unicodedata
from datetime import datetime, timedelta, timezone

import cloudinary
import cloudinary.uploader
from firebase_admin import firestore

from firebase_config import db

cloudinary.config(secure=True)  # lê a CLOUDINARY_URL do ambiente

TIPOS_IMAGEM = {"image/jpeg", "image/png", "image/webp"}

COLECAO = "produtos"

# Horário de Brasília (UTC-3). O Brasil não tem horário de verão desde 2019,
# então um deslocamento fixo evita depender do pacote de fusos do servidor.
FUSO_BR = timezone(timedelta(hours=-3))
DESCONTO_MAX = 90  # % máximo permitido

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


def _ler_desconto(form):
    """Lê o desconto do formulário de edição. Devolve (campos, erro).

    - Campo de % vazio  -> remove o desconto.
    - Com %  -> exige a data/hora final (no futuro, horário de Brasília).
    """
    msg_pct = f"Desconto inválido. Use um número entre 1 e {DESCONTO_MAX}."

    texto = (form.get("desconto_percentual") or "").strip().replace(",", ".")
    if not texto:
        return {"desconto_percentual": None, "promocao_ate": None}, None

    try:
        pct = round(float(texto), 2)
    except ValueError:
        return None, msg_pct
    if not 1 <= pct <= DESCONTO_MAX:
        return None, msg_pct
    if pct == int(pct):
        pct = int(pct)

    texto_data = (form.get("promocao_ate") or "").strip()
    if not texto_data:
        return None, "Informe até quando o desconto vale."

    local = None
    for formato in ("%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            local = datetime.strptime(texto_data, formato)
            break
        except ValueError:
            continue
    if local is None:
        return None, "Data final do desconto inválida."

    fim = local.replace(tzinfo=FUSO_BR).astimezone(timezone.utc)
    if fim <= datetime.now(timezone.utc):
        return None, "A data final do desconto precisa ser no futuro."

    return {"desconto_percentual": pct, "promocao_ate": fim}, None


def aplicar_promocao(produto, agora=None):
    """Calcula o preço vigente de um produto (dict do Firestore).

    O preço original ('preco') nunca é alterado. Quando o prazo do desconto
    passa, o produto volta ao preço original sozinho, na hora da leitura,
    sem precisar de nenhuma rotina agendada.

    Acrescenta ao dict:
      preco_original, preco_final, promocao_ativa, promocao_ate_local
    """
    agora = agora or datetime.now(timezone.utc)

    preco = produto.get("preco") or 0
    pct = produto.get("desconto_percentual")
    ate = produto.get("promocao_ate")

    ativa = False
    if pct and ate:
        if ate.tzinfo is None:  # por segurança, assume UTC
            ate = ate.replace(tzinfo=timezone.utc)
        ativa = ate > agora

    produto["preco_original"] = preco
    produto["promocao_ativa"] = ativa
    produto["preco_final"] = (
        round(preco * (1 - pct / 100), 2) if ativa else preco
    )
    produto["promocao_ate_local"] = ate.astimezone(FUSO_BR) if ativa else None
    return produto


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
        aplicar_promocao(produto)
        produtos.append(produto)
    produtos.sort(key=lambda p: str(p.get("criado_em") or ""), reverse=True)
    return produtos


def _validar_dados(form):
    """Valida os campos de texto do formulário (cadastro e edição).

    Devolve (dados, erro). Se 'erro' vier preenchido, 'dados' é None.
    """
    nome = form.get("nome", "").strip()
    categoria = form.get("categoria", "").strip()
    principio = form.get("principio_ativo", "").strip()
    descricao = form.get("descricao", "").strip()

    if not nome or not descricao:
        return None, "Preencha o nome e a descrição do produto."
    if len(nome) > 120 or len(descricao) > 1000 or len(principio) > 120:
        return None, "Texto muito longo. Encurte o nome ou a descrição."
    if categoria not in CATEGORIAS:
        return None, "Escolha uma categoria da lista."
    try:
        preco = converter_preco(form.get("preco", ""))
    except ValueError:
        return None, "Preço inválido. Use um formato como 8,90."

    return {
        "nome": nome,
        "chave": gerar_chave(nome),
        "categoria": categoria,
        "principio_ativo": principio,
        "descricao": descricao,
        "preco": preco,
    }, None


def _enviar_imagem(arquivo):
    """Envia a foto ao Cloudinary. Devolve (url, erro).

    Sem arquivo, devolve ("", None).
    """
    if not (arquivo and arquivo.filename):
        return "", None
    if arquivo.mimetype not in TIPOS_IMAGEM:
        return None, "Envie uma imagem JPG, PNG ou WEBP."
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
        return resultado["secure_url"], None
    except Exception:
        return None, "Não foi possível enviar a imagem. Tente novamente."


def adicionar_produto(farmacia_id, form, arquivo=None):
    """Valida o formulário, envia a foto (se houver) e salva.

    Devolve (ok, mensagem).
    """
    if db is None:
        return False, "Sistema indisponível no momento."

    dados, erro = _validar_dados(form)
    if erro:
        return False, erro

    # Upload só depois das outras validações, para não deixar imagem
    # órfã no Cloudinary quando o cadastro falha.
    imagem, erro = _enviar_imagem(arquivo)
    if erro:
        return False, erro

    db.collection(COLECAO).add({
        "farmacia_id": farmacia_id,
        **dados,
        "imagem": imagem,
        "criado_em": firestore.SERVER_TIMESTAMP,
    })
    return True, "Produto cadastrado!"


def obter_produto(farmacia_id, produto_id):
    """Um produto da farmácia logada (com 'id'). None se não for dela."""
    if db is None or not produto_id:
        return None
    doc = db.collection(COLECAO).document(produto_id).get()
    if not doc.exists:
        return None
    produto = doc.to_dict()
    if produto.get("farmacia_id") != farmacia_id:
        return None
    produto["id"] = doc.id
    return aplicar_promocao(produto)


def editar_produto(farmacia_id, produto_id, form, arquivo=None):
    """Atualiza um produto sem apagá-lo. Devolve (ok, mensagem).

    - Só edita se o produto for da farmácia logada.
    - Sem foto nova, mantém a foto atual.
    - Recalcula a 'chave' quando o nome muda, para o produto continuar
      agrupado corretamente no catálogo.
    - Salva (ou remove) o desconto: percentual + data/hora final.
    """
    if db is None:
        return False, "Sistema indisponível no momento."

    ref = db.collection(COLECAO).document(produto_id)
    doc = ref.get()
    if not doc.exists or doc.to_dict().get("farmacia_id") != farmacia_id:
        return False, "Produto não encontrado."

    dados, erro = _validar_dados(form)
    if erro:
        return False, erro

    desconto, erro = _ler_desconto(form)
    if erro:
        return False, erro

    atualizacao = {
        **dados,
        **desconto,
        "atualizado_em": firestore.SERVER_TIMESTAMP,
    }

    imagem, erro = _enviar_imagem(arquivo)
    if erro:
        return False, erro
    if imagem:  # só troca a foto se enviaram uma nova
        atualizacao["imagem"] = imagem

    ref.update(atualizacao)
    return True, "Produto atualizado!"


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