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


    # Reserva o CNPJ.
    # O create() falha se já existir, evitando cadastro duplicado.
    reserva = db.collection("cnpjs").document(cnpj)


    try:
        reserva.create({
            "criado_em": firestore.SERVER_TIMESTAMP
        })
    except AlreadyExists:
        return False, "Este CNPJ já possui cadastro."


    # Cria o login.
    # O Firebase Authentication guarda a senha com segurança.
    try:
        usuario = auth.create_user(
            email=email,
            password=senha,
            display_name=nome
        )


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


    # Salva os dados da farmácia.
    # O documento usa o mesmo ID do usuário no Firebase Authentication.
    try:
        db.collection("farmacias").document(usuario.uid).set({
            "nome": nome,
            "email": email,
            "cnpj": cnpj,
            "razao_social": receita["razao_social"],
            "endereco": endereco,
            "status": "aprovada",
            "criado_em": firestore.SERVER_TIMESTAMP,
        })


        reserva.update({
            "uid": usuario.uid
        })


    except Exception as erro:
        print(f"[Cadastro] Erro ao salvar farmácia: {erro}")


        auth.delete_user(usuario.uid)
        reserva.delete()


        return False, "Não foi possível salvar o cadastro. Tente novamente."


    return True, "Conta criada com sucesso! Agora é só entrar."




def obter_farmacia(farmacia_id):
    """Busca os dados públicos de uma farmácia pelo ID."""


    if db is None:
        return None


    doc = db.collection("farmacias").document(farmacia_id).get()


    if not doc.exists:
        return None


    farmacia = doc.to_dict()
    farmacia["uid"] = doc.id


    return farmacia


def buscar_farmacias(termo):
    """Busca farmácias pelo nome."""


    if db is None:
        return []


    termo = (termo or "").strip().lower()


    if len(termo) < 2:
        return []


    resultados = []


    docs = db.collection("farmacias").stream()


    for doc in docs:
        farmacia = doc.to_dict()


        nome = farmacia.get("nome", "")


        if termo in nome.lower():
            farmacia["uid"] = doc.id
            resultados.append(farmacia)


    return resultados[:8]


def excluir_farmacia(farmacia_id):
    """Exclui a conta da farmácia e todos os seus dados."""


    if db is None:
        return False, "Sistema indisponível no momento."


    try:
        # Excluir produtos da farmácia
        produtos = (
            db.collection("produtos")
            .where("farmacia_id", "==", farmacia_id)
            .stream()
        )


        batch = db.batch()
        quantidade = 0


        for produto in produtos:
            batch.delete(produto.reference)
            quantidade += 1


            if quantidade == 500:
                batch.commit()
                batch = db.batch()
                quantidade = 0


        if quantidade > 0:
            batch.commit()


        # Excluir documento da farmácia
        db.collection("farmacias").document(farmacia_id).delete()


        # Excluir usuário do Firebase Authentication
        auth.delete_user(farmacia_id)


        return True, "Conta excluída com sucesso."


    except Exception as erro:
        print(f"[Exclusão] Erro ao excluir farmácia: {erro}")
        return False, "Não foi possível excluir a conta. Tente novamente."


