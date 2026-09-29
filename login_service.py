"""Login da farmácia usando o Firebase Authentication (via API REST).

O Firebase confere e-mail e senha. Depois conferimos se aquele usuário
tem cadastro de farmácia aprovado no Firestore.
"""
import json
import os
import urllib.error
import urllib.request

from firebase_config import db

# A chave de API da Web NÃO é secreta (ela também vai para o navegador em
# qualquer site com Firebase). Pode ficar aqui ou numa variável de ambiente.
API_KEY = os.environ.get(
    "FIREBASE_API_KEY", "AIzaSyCkBfcuxY4TB1bkjvMWiOSQMULwJpPlBWo"
)
URL_LOGIN = ("https://identitytoolkit.googleapis.com/v1/"
             "accounts:signInWithPassword?key=" + API_KEY)

MSG_CREDENCIAIS = "E-mail ou senha incorretos."


def _consultar_firebase(email, senha):
    """Devolve o uid do usuário. Levanta ValueError com a mensagem de erro."""
    corpo = json.dumps({
        "email": email,
        "password": senha,
        "returnSecureToken": True,
    }).encode("utf-8")
    pedido = urllib.request.Request(
        URL_LOGIN, data=corpo, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(pedido, timeout=10) as resposta:
            return json.loads(resposta.read().decode("utf-8"))["localId"]
    except urllib.error.HTTPError as erro:
        try:
            codigo = json.loads(erro.read().decode("utf-8"))["error"]["message"]
        except Exception:
            codigo = ""
        print(f"[Login] Firebase respondeu: HTTP {erro.code} {codigo}")
        if codigo.startswith("TOO_MANY_ATTEMPTS"):
            raise ValueError("Muitas tentativas. Aguarde alguns minutos.")
        if codigo.startswith("USER_DISABLED"):
            raise ValueError("Esta conta foi desativada.")
        if erro.code == 400:
            # senha errada, e-mail não existe, e-mail inválido...
            # (mensagem única, para não revelar se o e-mail existe)
            raise ValueError(MSG_CREDENCIAIS)
        raise ValueError("Não foi possível entrar agora. Tente novamente.")
    except Exception as erro:
        print(f"[Login] Erro de conexão: {erro}")
        raise ValueError("Não foi possível entrar agora. Tente novamente.")


def entrar(email, senha):
    """Devolve (ok, mensagem, farmacia). 'farmacia' = {'uid', 'nome'} se ok."""
    email = (email or "").strip().lower()
    if not email or not senha:
        return False, "Digite o e-mail e a senha.", None
    if db is None:
        return False, "Sistema indisponível no momento.", None

    try:
        uid = _consultar_firebase(email, senha)
    except ValueError as erro:
        return False, str(erro), None

    doc = db.collection("farmacias").document(uid).get()
    if not doc.exists:
        return False, "Esta conta não está cadastrada como farmácia.", None

    dados = doc.to_dict()
    if dados.get("status") != "aprovada":
        return False, "O cadastro desta farmácia ainda não foi aprovado.", None

    return True, "", {"uid": uid, "nome": dados.get("nome", "")}