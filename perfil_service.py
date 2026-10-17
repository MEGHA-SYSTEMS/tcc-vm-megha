"""Perfil da farmácia (dados no documento farmacias/<uid> do Firestore).

A farmácia edita: nome, endereço, telefone, horário, descrição, logo, capa
(com posição ajustável) e galeria de fotos (upload para o Cloudinary).
O CNPJ e o e-mail NÃO são editáveis aqui.
"""
import logging
import re

import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
from firebase_admin import firestore

from firebase_config import db
from geocoding import geocodificar

load_dotenv()
cloudinary.config(secure=True)  # lê a CLOUDINARY_URL do ambiente

logger = logging.getLogger(__name__)

TIPOS_IMAGEM = {"image/jpeg", "image/png", "image/webp"}

MAX_FOTOS = 6
CAMPOS_ENDERECO = ("cep", "rua", "numero", "bairro", "cidade")


def formatar_cnpj(cnpj):
    n = re.sub(r"\D", "", cnpj or "")
    if len(n) != 14:
        return cnpj or ""
    return f"{n[:2]}.{n[2:5]}.{n[5:8]}/{n[8:12]}-{n[12:]}"


def obter_perfil(farmacia_id):
    """Devolve o perfil já com valores padrão para o que ainda não existe."""
    dados = {}
    if db is not None:
        doc = db.collection("farmacias").document(farmacia_id).get()
        if doc.exists:
            dados = doc.to_dict()

    endereco = dados.get("endereco") or {}
    partes = [
        f"{endereco.get('rua', '')}, {endereco.get('numero', '')}".strip(", "),
        endereco.get("bairro", ""),
        endereco.get("cidade", ""),
    ]
    perfil = {
        "nome": dados.get("nome", ""),
        "cnpj": formatar_cnpj(dados.get("cnpj", "")),
        "razao_social": dados.get("razao_social", ""),
        "email": dados.get("email", ""),
        "endereco": endereco,
        "endereco_texto": " - ".join(p for p in partes if p),
        "telefone": dados.get("telefone", ""),
        "horario": dados.get("horario", ""),
        "descricao": dados.get("descricao", ""),
        "logo": dados.get("logo", ""),
        "capa": dados.get("capa", ""),
        "capa_pos": dados.get("capa_pos", 50),
        "capa_pos_x": dados.get("capa_pos_x", 50),
        "fotos": dados.get("fotos") or [],
    }
    perfil["incompleto"] = not (perfil["descricao"] and
                                (perfil["logo"] or perfil["capa"]))
    return perfil


def dados_para_formulario(perfil):
    """Transforma o perfil nos valores iniciais do formulário de edição."""
    dados = {
        "nome": perfil["nome"],
        "telefone": perfil["telefone"],
        "horario": perfil["horario"],
        "descricao": perfil["descricao"],
        "logo": perfil["logo"],
        "capa": perfil["capa"],
        "capa_pos": perfil["capa_pos"],
        "capa_pos_x": perfil["capa_pos_x"],
        "fotos": perfil["fotos"],  # lista de URLs
    }
    for campo in CAMPOS_ENDERECO:
        dados[campo] = perfil["endereco"].get(campo, "")
    return dados


def _enviar_imagem(arquivo, pasta, tamanho_max):
    """Envia a foto ao Cloudinary sem cortar. Devolve (url, erro).

    Sem arquivo, devolve ("", None).
    """
    if not (arquivo and arquivo.filename):
        return "", None
    if arquivo.mimetype not in TIPOS_IMAGEM:
        return None, "Envie uma imagem JPG, PNG ou WEBP."
    try:
        resultado = cloudinary.uploader.upload(
            arquivo,
            folder=pasta,
            resource_type="image",
            transformation=[
                {"width": tamanho_max, "height": tamanho_max, "crop": "limit"},
                {"fetch_format": "auto", "quality": "auto"},
            ],
        )
        return resultado["secure_url"], None
    except Exception:
        logger.exception("Falha no upload para o Cloudinary")
        return None, "Não foi possível enviar a imagem. Tente novamente."


def _ler_posicao(form, campo):
    """Lê uma posição de 0 a 100 do formulário (padrão 50)."""
    try:
        return max(0, min(100, int(form.get(campo, 50))))
    except (TypeError, ValueError):
        return 50


def salvar_perfil(farmacia_id, form, arquivos=None):
    """Valida o formulário e atualiza o perfil. Devolve (ok, mensagem)."""
    if db is None:
        return False, "Sistema indisponível no momento."

    nome = form.get("nome", "").strip()
    telefone = form.get("telefone", "").strip()
    horario = form.get("horario", "").strip()
    descricao = form.get("descricao", "").strip()
    endereco = {c: form.get(c, "").strip() for c in CAMPOS_ENDERECO}
    capa_pos = _ler_posicao(form, "capa_pos")
    capa_pos_x = _ler_posicao(form, "capa_pos_x")

    if not nome or len(nome) > 120:
        return False, "Informe o nome da farmácia (até 120 caracteres)."
    if not all(endereco.values()) or any(len(v) > 120 for v in endereco.values()):
        return False, "Preencha todos os campos de endereço."
    if telefone and not re.fullmatch(r"[\d\s()+-]{8,20}", telefone):
        return False, "Telefone inválido. Use um formato como (16) 99999-0000."
    if len(horario) > 120:
        return False, "O horário de funcionamento está muito longo."
    if len(descricao) > 600:
        return False, "A descrição pode ter no máximo 600 caracteres."

    ref = db.collection("farmacias").document(farmacia_id)
    atual = ref.get().to_dict() or {}

    # Galeria: fotos atuais que continuam marcadas + fotos novas enviadas
    fotos_antigas = atual.get("fotos") or []
    manter = [u for u in form.getlist("fotos_atuais") if u in fotos_antigas]

    arquivos = arquivos or {}
    novas = [a for a in (arquivos.get("galeria") or []) if a and a.filename]
    if len(manter) + len(novas) > MAX_FOTOS:
        return False, f"A galeria pode ter no máximo {MAX_FOTOS} fotos."

    logo, erro = _enviar_imagem(
        arquivos.get("logo"), "poupemais/farmacias/logos", 800)
    if erro:
        return False, erro
    capa, erro = _enviar_imagem(
        arquivos.get("capa"), "poupemais/farmacias/capas", 1800)
    if erro:
        return False, erro

    fotos = list(manter)
    for arquivo in novas:
        url, erro = _enviar_imagem(
            arquivo, "poupemais/farmacias/galeria", 1400)
        if erro:
            return False, erro
        fotos.append(url)

    campos = {
        "nome": nome,
        "endereco": endereco,
        "telefone": telefone,
        "horario": horario,
        "descricao": descricao,
        "logo": logo or atual.get("logo", ""),
        "capa": capa or atual.get("capa", ""),
        "capa_pos": capa_pos,
        "capa_pos_x": capa_pos_x,
        "fotos": fotos,
        "atualizado_em": firestore.SERVER_TIMESTAMP,
    }

    # só geocodifica se o endereço mudou ou se ainda não tem coordenadas
    sem_mapa = False
    if atual.get("endereco") != endereco or atual.get("lat") is None:
        coords = geocodificar(
            endereco["rua"], endereco["numero"],
            endereco["bairro"], endereco["cidade"], endereco["cep"],
        )
        if coords:
            campos["lat"], campos["lng"] = coords
        else:
            # evita deixar a farmácia num ponto antigo/errado do mapa
            campos["lat"] = firestore.DELETE_FIELD
            campos["lng"] = firestore.DELETE_FIELD
            sem_mapa = True

    ref.update(campos)

    if sem_mapa:
        return True, ("Perfil atualizado, mas não conseguimos localizar o endereço "
                      "no mapa. Confira rua, número e bairro.")
    return True, "Perfil atualizado!"