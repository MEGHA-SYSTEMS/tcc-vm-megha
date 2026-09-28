import os

from flask import Flask, render_template
from produto import get_todos_produtos, get_produto_por_id

app = Flask(__name__)


@app.route("/")
def index():
    nome = "poupemais.com"
    return render_template("index.html", site=nome)


# Cadastro da Farmácia
@app.route("/login")
def login():
    return render_template("login/register.html")


# Login do sistema (temporário)
@app.route("/register")
def register():
    return render_template("login/login.html")


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

    # Adicione este bloco no main.py, perto das outras rotas de login/recovery.
# Ajuste o caminho do template ("login/nova_senha.html") se a sua pasta
# de templates de login tiver outro nome.

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

    return render_template("login/nova_senha.html")


@app.route("/produto/<int:produto_id>")
def produto(produto_id):
    nome = "poupemais.com"
    produto = get_produto_por_id(produto_id)
 
    if produto is None:
        from flask import redirect, url_for
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