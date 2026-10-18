"""Anúncios do carrossel da página inicial (coleção 'anuncios' no Firestore).

Cada farmácia envia banners pelo painel. Eles nascem como 'pendente' e só
aparecem na página inicial depois de aprovados: no console do Firebase,
mude o campo 'status' do anúncio de "pendente" para "aprovado".
(Para recusar, use "rejeitado" ou apague o documento.)
"""
import logging
import random
import time
from datetime import datetime, timedelta, timezone

import cloudinary
import cloudinary.uploader
from firebase_admin import firestore

from firebase_config import db
from produtos_service import FUSO_BR, TIPOS_IMAGEM, gerar_chave, obter_produto

logger = logging.getLogger(__name__)

COLECAO = "anuncios"
MAX_ATIVOS = 3      # anúncios simultâneos por farmácia (pendentes + no ar)
MAX_DIAS = 90       # validade máxima de um anúncio
LIMITE_HOME = 10    # máximo de banners no carrossel


def _agora():
    return datetime.now(timezone.utc)


def _aware(dt):
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _onde(campo, valor):
    try:
        from google.cloud.firestore_v1.base_query import FieldFilter
        return db.collection(COLECAO).where(
            filter=FieldFilter(campo, "==", valor))
    except ImportError:
        return db.collection(COLECAO).where(campo, "==", valor)


def _apagar_imagem(public_id):
    """Remove a imagem do Cloudinary. Falha em silêncio (só registra)."""
    if not public_id:
        return
    try:
        cloudinary.uploader.destroy(public_id, resource_type="image")
    except Exception:
        logger.exception("Falha ao apagar imagem do Cloudinary")


def _ler_validade(form):
    """Lê a data final do formulário. Devolve (datetime UTC, erro)."""
    texto = (form.get("valido_ate") or "").strip()
    if not texto:
        return None, "Informe até quando o anúncio vale."

    local = None
    for formato in ("%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            local = datetime.strptime(texto, formato)
            break
        except ValueError:
            continue
    if local is None:
        return None, "Data final do anúncio inválida."

    fim = local.replace(tzinfo=FUSO_BR).astimezone(timezone.utc)
    agora = _agora()
    if fim <= agora:
        return None, "A data final do anúncio precisa ser no futuro."
    if fim > agora + timedelta(days=MAX_DIAS):
        return None, f"O anúncio pode durar no máximo {MAX_DIAS} dias."
    return fim, None


def _enviar_banner(arquivo):
    """Envia o banner (cortado em 16:9). Devolve (url, public_id, erro)."""
    if not (arquivo and arquivo.filename):
        return None, None, "Envie a imagem do anúncio."
    if arquivo.mimetype not in TIPOS_IMAGEM:
        return None, None, "Envie uma imagem JPG, PNG ou WEBP."
    try:
        resultado = cloudinary.uploader.upload(
            arquivo,
            folder="poupemais/anuncios",
            resource_type="image",
            transformation=[
                {"width": 1600, "height": 900, "crop": "fill", "gravity": "auto"},
                {"fetch_format": "auto", "quality": "auto"},
            ],
        )
        return resultado["secure_url"], resultado["public_id"], None
    except Exception:
        logger.exception("Falha no upload do banner para o Cloudinary")
        return None, None, "Não foi possível enviar a imagem. Tente novamente."


# ------------------------------------------------------------------
# Painel da farmácia
# ------------------------------------------------------------------

def listar_anuncios_farmacia(farmacia_id):
    """Anúncios de uma farmácia, com a situação de cada um."""
    if db is None:
        return []

    agora = _agora()
    lista = []

    for doc in _onde("farmacia_id", farmacia_id).stream():
        d = doc.to_dict()
        ate = _aware(d.get("valido_ate"))
        if ate is None:
            continue

        if ate <= agora:
            situacao = "expirado"
        elif d.get("status") == "aprovado":
            situacao = "no_ar"
        elif d.get("status") == "rejeitado":
            situacao = "recusado"
        else:
            situacao = "pendente"

        lista.append({
            "id": doc.id,
            "imagem": d.get("imagem", ""),
            "destino": d.get("destino", "farmacia"),
            "situacao": situacao,
            "valido_ate_local": ate.astimezone(FUSO_BR),
        })

    lista.sort(key=lambda a: a["valido_ate_local"], reverse=True)
    return lista


def adicionar_anuncio(farmacia_id, farmacia_nome, form, arquivo=None):
    """Valida e salva um anúncio como 'pendente'. Devolve (ok, mensagem)."""
    if db is None:
        return False, "Sistema indisponível no momento."

    ativos = sum(
        1 for a in listar_anuncios_farmacia(farmacia_id)
        if a["situacao"] in ("pendente", "no_ar")
    )
    if ativos >= MAX_ATIVOS:
        return False, (f"Você já tem {MAX_ATIVOS} anúncios ativos. "
                       "Exclua um ou espere um expirar.")

    validade, erro = _ler_validade(form)
    if erro:
        return False, erro

    # para onde o clique leva: a página da farmácia ou um produto dela
    destino = (form.get("destino") or "farmacia").strip()
    produto_slug = ""
    if destino != "farmacia":
        produto = obter_produto(farmacia_id, destino)  # só se for dela
        if produto is None:
            return False, "Produto não encontrado."
        chave = produto.get("chave") or gerar_chave(produto.get("nome", ""))
        produto_slug = chave.replace(" ", "-")
        destino = "produto"

    # upload só depois das outras validações, para não deixar imagem órfã
    imagem, public_id, erro = _enviar_banner(arquivo)
    if erro:
        return False, erro

    db.collection(COLECAO).add({
        "farmacia_id": farmacia_id,
        "farmacia_nome": farmacia_nome,
        "imagem": imagem,
        "imagem_public_id": public_id,
        "destino": destino,
        "produto_slug": produto_slug,
        "valido_ate": validade,
        "status": "pendente",
        "criado_em": firestore.SERVER_TIMESTAMP,
    })
    return True, ("Anúncio enviado! Ele aparece no carrossel "
                  "assim que for aprovado.")


def excluir_anuncio(farmacia_id, anuncio_id):
    """Só exclui se o anúncio for da farmácia logada. Devolve (ok, mensagem)."""
    if db is None:
        return False, "Sistema indisponível no momento."

    ref = db.collection(COLECAO).document(anuncio_id)
    doc = ref.get()
    if not doc.exists or doc.to_dict().get("farmacia_id") != farmacia_id:
        return False, "Anúncio não encontrado."

    _apagar_imagem(doc.to_dict().get("imagem_public_id"))
    ref.delete()
    _CACHE["quando"] = 0.0  # a home atualiza na próxima visita
    return True, "Anúncio excluído."


def excluir_anuncios_da_farmacia(farmacia_id):
    """Usado ao excluir a conta: apaga todos os anúncios da farmácia."""
    if db is None:
        return
    for doc in _onde("farmacia_id", farmacia_id).stream():
        _apagar_imagem(doc.to_dict().get("imagem_public_id"))
        doc.reference.delete()
    _CACHE["quando"] = 0.0


# ------------------------------------------------------------------
# Página inicial
# ------------------------------------------------------------------

_CACHE = {"quando": 0.0, "dados": []}
_CACHE_SEGUNDOS = 60


def _carregar_aprovados():
    lista = []
    for doc in _onde("status", "aprovado").stream():
        d = doc.to_dict()
        ate = _aware(d.get("valido_ate"))
        if not d.get("imagem") or ate is None:
            continue
        lista.append({
            "id": doc.id,
            "farmacia_id": d.get("farmacia_id", ""),
            "farmacia_nome": d.get("farmacia_nome", ""),
            "imagem": d["imagem"],
            "destino": d.get("destino", "farmacia"),
            "produto_slug": d.get("produto_slug", ""),
            "valido_ate": ate,
        })
    return lista


def listar_anuncios_home():
    """Anúncios aprovados e dentro do prazo, em ordem aleatória.

    A ordem muda a cada visita, para nenhuma farmácia ficar sempre na frente.
    """
    if db is None:
        return []

    agora = time.time()
    if agora - _CACHE["quando"] > _CACHE_SEGUNDOS:
        try:
            _CACHE["dados"] = _carregar_aprovados()
            _CACHE["quando"] = agora
        except Exception as erro:
            print(f"[Anúncios] Falha ao carregar: {erro}")
            _CACHE["quando"] = agora - _CACHE_SEGUNDOS + 10

    agora_dt = _agora()
    # o cache pode guardar um anúncio que acabou de vencer
    ativos = [a for a in _CACHE["dados"] if a["valido_ate"] > agora_dt]
    random.shuffle(ativos)
    return ativos[:LIMITE_HOME]