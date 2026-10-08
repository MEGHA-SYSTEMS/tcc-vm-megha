import os
import time  # NOVO: usado no cache dos produtos
import unicodedata
from functools import wraps

from dotenv import load_dotenv

load_dotenv()  # lê o .env ANTES de importar os serviços (Cloudinary, Firebase)

from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

# Serviços do sistema
from produto import get_todos_produtos, get_produto_por_id
from farmacia_service import (
    cadastrar_farmacia,
    obter_farmacia,
    buscar_farmacias,
    excluir_farmacia,
)
from login_service import entrar
from perfil_service import (
    dados_para_formulario,
    obter_perfil,
    salvar_perfil,
)
from produtos_service import (
    CATEGORIAS,
    adicionar_produto,
    excluir_produto,
    listar_produtos,
)


app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "chave-so-para-testes-locais"
)

app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# Limite de tamanho para uploads (fotos de produtos)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB


# ============================================================
# BUSCA
# ============================================================

def normalizar(texto):
    """Minúsculas e sem acentos, para 'pressao' achar 'Pressão'."""
    texto = unicodedata.normalize("NFD", texto or "")
    texto = "".join(
        c for c in texto
        if unicodedata.category(c) != "Mn"
    )
    return texto.lower()


# ============================================================
# PRODUTOS EM CACHE (NOVO)
# Evita ler o Firebase inteiro a cada visita à landing
# e a cada tecla digitada na busca.
# ============================================================

_CACHE_PRODUTOS = {"quando": 0.0, "dados": []}
_CACHE_SEGUNDOS = 60


def todos_produtos_cache():
    """get_todos_produtos() com cache de 60s.

    Se o Firebase falhar, devolve a última lista boa e tenta de novo
    em 10 segundos, sem derrubar a página.
    """
    agora = time.time()

    if agora - _CACHE_PRODUTOS["quando"] > _CACHE_SEGUNDOS:
        try:
            _CACHE_PRODUTOS["dados"] = get_todos_produtos()
            _CACHE_PRODUTOS["quando"] = agora
        except Exception as erro:
            print(f"[Produtos] Falha ao carregar: {erro}")
            _CACHE_PRODUTOS["quando"] = agora - _CACHE_SEGUNDOS + 10

    return _CACHE_PRODUTOS["dados"]


@app.template_filter("brl")
def formatar_brl(valor):
    """Filtro para os templates: 10.4 -> '10,40' | 1234.5 -> '1.234,50'."""
    try:
        texto = f"{float(valor):,.2f}"
    except (TypeError, ValueError):
        return "—"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


# ============================================================
# PÁGINA INICIAL
# ============================================================

@app.route("/")
def index():
    # Produtos com foto aparecem primeiro; mostra no máximo 10.
    produtos = sorted(
        todos_produtos_cache(),
        key=lambda p: not p.get("imagem"),
    )

    return render_template(
        "index.html",
        site="poupemais.com",
        produtos_home=produtos[:10],
    )


# ============================================================
# LOGIN / PROTEÇÃO DE ROTAS
# ============================================================

def login_obrigatorio(rota):
    """Protege uma página: só deixa entrar quem fez login."""
    @wraps(rota)
    def protegida(*args, **kwargs):
        if "farmacia_id" not in session:
            return redirect(url_for("login"))
        return rota(*args, **kwargs)

    return protegida


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "")
        senha = request.form.get("senha", "")

        ok, mensagem, farmacia = entrar(email, senha)

        if ok:
            session.clear()
            session["farmacia_id"] = farmacia["uid"]
            session["farmacia_nome"] = farmacia["nome"]

            return redirect(url_for("painel"))

        return render_template(
            "login/register.html",
            mensagem=mensagem,
            email=email,
        )

    return render_template("login/register.html")


# ============================================================
# CONTEXTO DO PAINEL
# ============================================================

def _contexto_painel(**extra):
    """Monta os dados necessários para o painel."""
    farmacia_id = session["farmacia_id"]

    contexto = {
        "nome": session["farmacia_nome"],
        "perfil": obter_perfil(farmacia_id),
        "produtos": listar_produtos(farmacia_id),
        "categorias": CATEGORIAS,
        "dados": {},
    }

    contexto.update(extra)

    return contexto


# ============================================================
# PAINEL
# ============================================================

@app.route("/painel")
@login_obrigatorio
def painel():
    return render_template(
        "dashboard/painel.html",
        **_contexto_painel()
    )


# ============================================================
# EDITAR PERFIL DA FARMÁCIA
# ============================================================

@app.route("/painel/perfil", methods=["GET", "POST"])
@login_obrigatorio
def painel_perfil():
    farmacia_id = session["farmacia_id"]

    if request.method == "POST":
        ok, mensagem = salvar_perfil(
            farmacia_id,
            request.form
        )

        if ok:
            session["farmacia_nome"] = request.form.get(
                "nome",
                ""
            ).strip()

            flash(mensagem, "success")

            return redirect(url_for("painel"))

        return render_template(
            "dashboard/perfil_editar.html",
            perfil=obter_perfil(farmacia_id),
            dados=request.form.to_dict(),
            erro=mensagem,
        )

    perfil = obter_perfil(farmacia_id)

    return render_template(
        "dashboard/perfil_editar.html",
        perfil=perfil,
        dados=dados_para_formulario(perfil),
    )


# ============================================================
# CADASTRAR PRODUTO
# ============================================================

@app.route("/painel/produtos", methods=["POST"])
@login_obrigatorio
def painel_adicionar_produto():
    ok, mensagem = adicionar_produto(
        session["farmacia_id"],
        request.form,
        request.files.get("imagem_arquivo"),
    )

    if ok:
        flash(mensagem, "success")
        return redirect(url_for("painel"))

    return render_template(
        "dashboard/painel.html",
        **_contexto_painel(
            dados=request.form.to_dict(),
            erro=mensagem,
        )
    )


# ============================================================
# EXCLUIR PRODUTO
# ============================================================

@app.route(
    "/painel/produtos/<produto_id>/excluir",
    methods=["POST"]
)
@login_obrigatorio
def painel_excluir_produto(produto_id):
    ok, mensagem = excluir_produto(
        session["farmacia_id"],
        produto_id
    )

    flash(
        mensagem,
        "success" if ok else "danger"
    )

    return redirect(url_for("painel"))


# ============================================================
# EXCLUIR CONTA
# ============================================================

@app.route(
    "/painel/excluir-conta",
    methods=["POST"]
)
@login_obrigatorio
def painel_excluir_conta():
    ok, mensagem = excluir_farmacia(
        session["farmacia_id"]
    )

    if ok:
        session.clear()
        flash(mensagem, "success")
        return redirect(url_for("index"))

    flash(mensagem, "danger")
    return redirect(url_for("painel"))


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# ============================================================
# CADASTRO DA FARMÁCIA
# ============================================================

# ATENÇÃO:
# "/register" mostra o cadastro da farmácia.
# "/login" mostra o formulário de entrada.
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        ok, mensagem = cadastrar_farmacia(
            request.form
        )

        return render_template(
            "login/login.html",
            mensagem=mensagem,
            sucesso=ok,
            dados=(
                {}
                if ok
                else request.form.to_dict()
            ),
        )

    return render_template(
        "login/login.html",
        dados={}
    )


# ============================================================
# RECUPERAÇÃO DE SENHA
# ============================================================

@app.route("/recovery")
def recovery():
    return render_template(
        "login/recovery.html"
    )


@app.route(
    "/nova-senha",
    methods=["GET", "POST"]
)
def nova_senha():
    if request.method == "POST":
        nova_senha = request.form.get(
            "novasenha"
        )
        confirmar_senha = request.form.get(
            "confirmar_senha"
        )

        # TODO:
        # Implementar a lógica real de recuperação:
        # 1. validar se o usuário confirmou o código;
        # 2. validar as duas senhas;
        # 3. salvar a nova senha com hash;
        # 4. associar a alteração à conta correta.
        #
        # As variáveis abaixo são mantidas para preservar
        # a estrutura original.
        _ = nova_senha
        _ = confirmar_senha

        return redirect(url_for("login"))

    return render_template(
        "login/novasenha.html"
    )


# ============================================================
# OUTRAS PÁGINAS
# ============================================================

@app.route("/team")
def team():
    nome = "poupemais.com"
    return render_template(
        "pages/team.html",
        site=nome
    )


@app.route("/termos")
def termos():
    return render_template(
        "pages/termos.html"
    )


@app.route("/contato")
def contato():
    return render_template(
        "pages/contato.html"
    )


@app.route("/localizacao")
def localizacao():
    return render_template(
        "pages/localizacao.html"
    )


# ============================================================
# CATÁLOGO
# ============================================================

@app.route("/catalogo")
def catalogo():
    nome = "poupemais.com"
    produtos = get_todos_produtos()

    return render_template(
        "pages/catalogo.html",
        site=nome,
        produtos=produtos,
    )


# ============================================================
# PÁGINA PÚBLICA DA FARMÁCIA
# ============================================================

@app.route("/farmacia/<farmacia_id>")
def perfil_farmacia(farmacia_id):
    farmacia = obter_farmacia(farmacia_id)

    if farmacia is None:
        return redirect(
            url_for("catalogo")
        )

    produtos = listar_produtos(
        farmacia_id
    )

    return render_template(
        "pages/farmacia.html",
        farmacia=farmacia,
        produtos=produtos,
        site="poupemais.com",
    )


# ============================================================
# BUSCA COM SUGESTÕES
# ============================================================

@app.route("/busca")
def busca():
    termo = normalizar(
        request.args.get("q", "").strip()
    )

    if len(termo) < 2:
        return jsonify([])

    resultados = []

    # -----------------------------
    # Produtos (agora com cache)
    # -----------------------------
    for p in todos_produtos_cache():
        campos = [
            p.get("nome", ""),
            p.get("categoria", ""),
            p.get("principio_ativo", ""),
        ]

        if any(
            termo in normalizar(campo)
            for campo in campos
        ):
            resultados.append({
                "tipo": "produto",
                "id": p["id"],
                "nome": p["nome"],
                "categoria": p.get(
                    "categoria",
                    ""
                ),
                "url": url_for(
                    "produto",
                    produto_id=p["id"]
                ),
            })

    # -----------------------------
    # Farmácias
    # -----------------------------
    for farmacia in buscar_farmacias(termo):
        resultados.append({
            "tipo": "farmacia",
            "id": farmacia["uid"],
            "nome": farmacia.get(
                "nome",
                ""
            ),
            "categoria": "Farmácia",
            "url": url_for(
                "perfil_farmacia",
                farmacia_id=farmacia["uid"]
            ),
        })

    return jsonify(
        resultados[:8]
    )


# ============================================================
# PÁGINA DO PRODUTO
# ============================================================

@app.route("/produto/<produto_id>")
def produto(produto_id):
    nome = "poupemais.com"

    produto = get_produto_por_id(
        produto_id
    )

    if produto is None:
        return redirect(
            url_for("catalogo")
        )

    return render_template(
        "pages/produto.html",
        site=nome,
        produto=produto,
    )


# ============================================================
# EXECUTAR SERVIDOR
# ============================================================

def main():
    app.run(
        host="0.0.0.0",
        port=int(
            os.environ.get(
                "PORT",
                10000
            )
        ),
        debug=True,
    )


if __name__ == "__main__":
    main()