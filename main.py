import os
import unicodedata
from functools import wraps

from flask import (Flask, flash, jsonify, redirect, render_template, request,
                   session, url_for)
from produto import get_todos_produtos, get_produto_por_id
from farmacia_service import cadastrar_farmacia
from login_service import entrar
from produtos_service import (CATEGORIAS, adicionar_produto, excluir_produto,
                               listar_produtos)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "chave-so-para-testes-locais")
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


def normalizar(texto):
    """Minúsculas e sem acentos, para 'pressao' achar 'Pressão'."""
    texto = unicodedata.normalize("NFD", texto or "")
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return texto.lower()


@app.route("/")
def index():
    nome = "poupemais.com"
    return render_template("index.html", site=nome)


def login_obrigatorio(rota):
    """Protege uma página: só deixa entrar quem fez login."""
    @wraps(rota)
    def protegida(*args, **kwargs):
        if "farmacia_id" not in session:
            return redirect(url_for("login"))
        return rota(*args, **kwargs)
    return protegida


# Formulário de ENTRAR (mostra login/register.html, veja o aviso abaixo)
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "")
        ok, mensagem, farmacia = entrar(email, request.form.get("senha", ""))
        if ok:
            session.clear()
            session["farmacia_id"] = farmacia["uid"]
            session["farmacia_nome"] = farmacia["nome"]
            return redirect(url_for("painel"))
        return render_template("login/register.html",
                               mensagem=mensagem, email=email)
    return render_template("login/register.html")


@app.route("/painel")
@login_obrigatorio
def painel():
    return render_template(
        "dashboard/painel.html",
        nome=session["farmacia_nome"],
        produtos=listar_produtos(session["farmacia_id"]),
        categorias=CATEGORIAS,
        dados={},
    )


@app.route("/painel/produtos", methods=["POST"])
@login_obrigatorio
def painel_adicionar_produto():
    ok, mensagem = adicionar_produto(session["farmacia_id"], request.form)
    if ok:
        flash(mensagem, "success")
        return redirect(url_for("painel"))
    # Erro: mostra o painel de novo mantendo o que a farmácia já digitou
    return render_template(
        "dashboard/painel.html",
        nome=session["farmacia_nome"],
        produtos=listar_produtos(session["farmacia_id"]),
        categorias=CATEGORIAS,
        dados=request.form.to_dict(),
        erro=mensagem,
    )


@app.route("/painel/produtos/<produto_id>/excluir", methods=["POST"])
@login_obrigatorio
def painel_excluir_produto(produto_id):
    ok, mensagem = excluir_produto(session["farmacia_id"], produto_id)
    flash(mensagem, "success" if ok else "danger")
    return redirect(url_for("painel"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# ATENÇÃO: os nomes das rotas estão "trocados" de propósito, porque o site
# inteiro já usa assim: "/register" mostra o formulário de CADASTRO da farmácia
# (login.html) e "/login" mostra o formulário de ENTRAR (register.html).
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        ok, mensagem = cadastrar_farmacia(request.form)
        return render_template(
            "login/login.html",
            mensagem=mensagem,
            sucesso=ok,
            dados={} if ok else request.form.to_dict(),
        )
    return render_template("login/login.html", dados={})


# Recuperação de senha
@app.route("/recovery")
def recovery():
    return render_template("login/recovery.html")


@app.route("/team")
def team():
    nome = "poupemais.com"
    return render_template("pages/team.html", site=nome)


@app.route("/termos")
def termos():
    return render_template("pages/termos.html")


@app.route("/contato")
def contato():
    return render_template("pages/contato.html")


@app.route("/localizacao")
def localizacao():
    return render_template("pages/localizacao.html")

@app.route("/catalogo")
def catalogo():
    nome = "poupemais.com"
    produtos = get_todos_produtos()
    return render_template("pages/catalogo.html", site=nome, produtos=produtos)


# Busca com sugestões (devolve JSON para o dropdown da navbar)
@app.route("/busca")
def busca():
    termo = normalizar(request.args.get("q", "").strip())
    if len(termo) < 2:
        return jsonify([])

    resultados = []
    for p in get_todos_produtos():
        campos = [
            p.get("nome", ""),
            p.get("categoria", ""),
            p.get("principio_ativo", ""),
        ]
        if any(termo in normalizar(campo) for campo in campos):
            resultados.append({
                "id": p["id"],
                "nome": p["nome"],
                "categoria": p.get("categoria", ""),
                "url": url_for("produto", produto_id=p["id"]),
            })

    return jsonify(resultados[:8])


# Nova senha (depois da recuperação)
@app.route("/nova-senha", methods=["GET", "POST"])
def nova_senha():
    if request.method == "POST":
        nova_senha = request.form.get("novasenha")
        confirmar_senha = request.form.get("confirmar_senha")

        # TODO: aqui entra a lógica de verdade —
        # validar se o usuário passou pela etapa de confirmação
        # do código, e então salvar a nova senha (com hash!)
        # no seu banco/Firestore, associada ao número confirmado.

        return redirect(url_for("login"))

    return render_template("login/novasenha.html")


@app.route("/produto/<produto_id>")
def produto(produto_id):
    nome = "poupemais.com"
    produto = get_produto_por_id(produto_id)
 
    if produto is None:
        return redirect(url_for("catalogo"))
 
    return render_template("pages/produto.html", site=nome, produto=produto)
 


def main():
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        debug=True
    )


if __name__ == "__main__":
    main()