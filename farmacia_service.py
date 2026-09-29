"""Cadastro de farmácia: valida o CNPJ, cria o login e salva os dados."""
from firebase_admin import auth, firestore
from google.api_core.exceptions import AlreadyExists

import cnpj as cnpj_util
from firebase_config import db


def cadastrar_farmacia(form):
    """Recebe request.form e devolve (ok, mensagem)."""
    if db is None:
        return False, "Sistema indisponível no momento (sem conexão com o banco)."

    nome = form.get("nome", "").strip()
    email = form.get("email", "").strip().lower()
    senha = form.get("senha", "")
    confirmar = form.get("confirmar_senha", "")
    cnpj = cnpj_util.limpar_cnpj(form.get("cnpj", ""))
    endereco = {
        campo: form.get(campo, "").strip()
        for campo in ("cep", "rua", "numero", "bairro", "cidade")
    }

    if not nome or not email or not senha or not cnpj:
        return False, "Preencha nome, CNPJ, e-mail e senha."
    if not all(endereco.values()):
        return False, "Preencha todos os campos de endereço."
    if senha != confirmar:
        return False, "As senhas não coincidem."
    if len(senha) < 6:
        return False, "A senha deve ter pelo menos 6 caracteres."
    if not form.get("termos"):
        return False, "É preciso aceitar os termos e condições."

    # Camadas 1 e 2: dígitos do CNPJ + consulta na Receita
    ok, mensagem, receita = cnpj_util.verificar_farmacia(cnpj)
    if not ok:
        return False, mensagem

    # Reserva o CNPJ (o create() falha se já existir, então não duplica)
    reserva = db.collection("cnpjs").document(cnpj)
    try:
        reserva.create({"criado_em": firestore.SERVER_TIMESTAMP})
    except AlreadyExists:
        return False, "Este CNPJ já possui cadastro."

    # Cria o login (o Firebase guarda a senha com segurança)
    try:
        usuario = auth.create_user(email=email, password=senha,
                                   display_name=nome)
    except auth.EmailAlreadyExistsError:
        reserva.delete()
        return False, "Este e-mail já está em uso."
    except ValueError:
        reserva.delete()
        return False, "E-mail ou senha em formato inválido."
    except Exception as erro:
        reserva.delete()
        print(f"[Cadastro] Erro ao criar usuário: {erro}")
        return False, "Não foi possível criar a conta. Tente novamente."

    # Salva os dados da farmácia (mesmo ID do usuário no Authentication)
    try:
        db.collection("farmacias").document(usuario.uid).set({
            "nome": nome,
            "email": email,
            "cnpj": cnpj,
            "razao_social": receita["razao_social"],
            "endereco": endereco,
            # Por enquanto toda farmácia validada já entra aprovada.
            # Quando existir aprovação manual, o valor inicial vira "pendente".
            "status": "aprovada",
            "criado_em": firestore.SERVER_TIMESTAMP,
        })
        reserva.update({"uid": usuario.uid})
    except Exception as erro:
        print(f"[Cadastro] Erro ao salvar farmácia: {erro}")
        auth.delete_user(usuario.uid)
        reserva.delete()
        return False, "Não foi possível salvar o cadastro. Tente novamente."

    return True, "Conta criada com sucesso! Agora é só entrar."