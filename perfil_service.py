"""Perfil da farmácia (dados no documento farmacias/<uid> do Firestore).




A farmácia edita: nome, endereço, telefone, horário, descrição, logo, capa
e galeria de fotos (por link). O CNPJ e o e-mail NÃO são editáveis aqui.
"""
import re




from firebase_admin import firestore




from firebase_config import db




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
        "fotos": "\n".join(perfil["fotos"]),
    }
    for campo in CAMPOS_ENDERECO:
        dados[campo] = perfil["endereco"].get(campo, "")
    return dados








def _link_valido(url):
    return url.lower().startswith(("http://", "https://")) and len(url) <= 500








def salvar_perfil(farmacia_id, form):
    """Valida o formulário e atualiza o perfil. Devolve (ok, mensagem)."""
    if db is None:
        return False, "Sistema indisponível no momento."




    nome = form.get("nome", "").strip()
    telefone = form.get("telefone", "").strip()
    horario = form.get("horario", "").strip()
    descricao = form.get("descricao", "").strip()
    logo = form.get("logo", "").strip()
    capa = form.get("capa", "").strip()
    fotos = [l.strip() for l in form.get("fotos", "").splitlines() if l.strip()]
    endereco = {c: form.get(c, "").strip() for c in CAMPOS_ENDERECO}




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
    if len(fotos) > MAX_FOTOS:
        return False, f"Você pode adicionar no máximo {MAX_FOTOS} fotos na galeria."
    for link in [logo, capa] + fotos:
        if link and not _link_valido(link):
            return False, ("Os links de imagem devem começar com http:// ou "
                           "https://")




    db.collection("farmacias").document(farmacia_id).update({
        "nome": nome,
        "endereco": endereco,
        "telefone": telefone,
        "horario": horario,
        "descricao": descricao,
        "logo": logo,
        "capa": capa,
        "fotos": fotos,
        "atualizado_em": firestore.SERVER_TIMESTAMP,
    })
    return True, "Perfil atualizado!"


