import os

from flask import Flask, render_template

app = Flask(__name__)


@app.route("/")
def index():
    nome = "poupemais.com"
    return render_template("index.html", site=nome)


# Cadastro da Farmácia
@app.route("/login")
def login():
    return render_template("login/login.html")


# Login do sistema (temporário)
@app.route("/register")
def register():
    return render_template("login/register.html")


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
    return render_template("pages/catalogo.html")       


def main():
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        debug=True
    )


if __name__ == "__main__":
    main()
