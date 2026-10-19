import os
import time  # usado no cache dos produtos
import unicodedata
from datetime import datetime, timedelta, timezone
from functools import wraps

from dotenv import load_dotenv
from sintomas import AVISO_SINTOMAS, achar_categorias

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
    listar_farmacias_mapa,  # NOVO
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
    editar_produto,
    excluir_produto,
    gerar_chave,  # NOVO: usado para montar o link do produto na página da farmácia
    listar_produtos,
    obter_produto,
)
from desempenho_service import montar_desempenho, registrar_consultas
from anuncio_service import (
    MAX_ATIVOS as ANUNCIOS_MAX,
    adicionar_anuncio,
    excluir_anuncio,
    excluir_anuncios_da_farmacia,
    listar_anuncios_farmacia,
    listar_anuncios_home,
)

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "chave-so-para-testes-locais"
)

app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# "Lembrar de mim": o login dura 30 dias
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)

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
# PRODUTOS EM CACHE
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

@app.context_processor
def injetar_farmacia_logada():
    """Deixa 'farmacia_logada' disponível em todos os templates."""
    farmacia_id = session.get("farmacia_id")

    if not farmacia_id:
        return {"farmacia_logada": None}

    # a logo fica guardada na sessão para não consultar o Firestore a cada página
    if "farmacia_logo" not in session:
        try:
            session["farmacia_logo"] = obter_perfil(farmacia_id).get("logo", "")
        except Exception:
            session["farmacia_logo"] = ""

    nome = session.get("farmacia_nome", "")

    return {
        "farmacia_logada": {
            "nome": nome,
            "logo": session.get("farmacia_logo", ""),
            "inicial": nome[:1].upper(),
        }
    }

# ============================================================
# PÁGINA INICIAL
# ============================================================


def _promocoes_home(produtos, limite=8):
    """Ofertas com desconto ainda válido, as de maior desconto primeiro.

    De cada produto fica só a melhor oferta em promoção, então o mesmo
    remédio em duas farmácias não aparece repetido.
    """
    agora = datetime.now(timezone.utc)
    lista = []

    for p in produtos:
        melhor = None

        for oferta in p.get("precos", []):
            ate = oferta.get("promocao_ate")
            original = oferta.get("preco_original") or 0

            if not oferta.get("promocao_ativa") or not ate or original <= 0:
                continue
            if ate <= agora:  # o cache pode guardar uma promoção que já acabou
                continue

            desconto = round((1 - oferta["preco"] / original) * 100)
            if desconto < 1:
                continue

            if melhor is None or desconto > melhor["desconto"]:
                melhor = {
                    "id": p["id"],
                    "nome": p["nome"],
                    "imagem": p.get("imagem", ""),
                    "farmacia": oferta["farmacia"],
                    "preco": oferta["preco"],
                    "preco_original": original,
                    "desconto": desconto,
                    "ate": ate,
                }

        if melhor:
            lista.append(melhor)

    lista.sort(key=lambda x: (-x["desconto"], x["ate"]))
    return lista[:limite]


@app.route("/")
def index():
    todos = todos_produtos_cache()

    # Produtos com foto aparecem primeiro; mostra no máximo 10.
    produtos = sorted(todos, key=lambda p: not p.get("imagem"))

    return render_template(
        "index.html",
        site="poupemais.com",
        produtos_home=produtos[:10],
        promocoes=_promocoes_home(todos),
        anuncios=listar_anuncios_home(),
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
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")
        lembrar = bool(request.form.get("lembrar"))

        ok, mensagem, farmacia = entrar(email, senha)

        if ok:
            session.clear()
            session["farmacia_id"] = farmacia["uid"]
            session["farmacia_nome"] = farmacia["nome"]
            # marcado: fica 30 dias logado; desmarcado: sai ao fechar o navegador
            session.permanent = lembrar

            resposta = redirect(url_for("painel"))

            # guarda só o e-mail (nunca a senha) para preencher da próxima vez
            if lembrar:
                resposta.set_cookie(
                    "email_lembrado",
                    email,
                    max_age=30 * 24 * 60 * 60,
                    httponly=True,
                    samesite="Lax",
                )
            else:
                resposta.delete_cookie("email_lembrado")

            return resposta

        return render_template(
            "login/register.html",
            mensagem=mensagem,
            email=email,
            lembrar=lembrar,
        )

    # quem ainda está logado vai direto para o painel
    if "farmacia_id" in session:
        return redirect(url_for("painel"))

    # e-mail lembrado de uma visita anterior
    email_lembrado = request.cookies.get("email_lembrado", "")

    return render_template(
        "login/register.html",
        email=email_lembrado,
        lembrar=bool(email_lembrado),
    )


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
        "anuncios": listar_anuncios_farmacia(farmacia_id),
        "anuncios_max": ANUNCIOS_MAX,
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


@app.route("/painel/desempenho")
@login_obrigatorio
def painel_desempenho():
    dias = request.args.get("dias", 30, type=int)
    if dias not in (7, 30, 90):
        dias = 30

    dados = montar_desempenho(
        session["farmacia_id"],
        todos_produtos_cache(),
        dias,
    )

    return render_template(
        "dashboard/desempenho.html",
        nome=session["farmacia_nome"],
        dados=dados,
        dias=dias,
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
            request.form,
            {
                "logo": request.files.get("logo"),
                "capa": request.files.get("capa"),
                "galeria": request.files.getlist("galeria"),
            },
        )
        if ok:
            session["farmacia_nome"] = request.form.get("nome", "").strip()
            session.pop("farmacia_logo", None)
            flash(mensagem, "success")
            return redirect(url_for("painel"))

        # Em caso de erro, mostra o formulário de novo. Usamos os dados
        # salvos como base (para manter logo, capa e galeria na tela) e
        # por cima os textos que a pessoa acabou de digitar.
        dados = dados_para_formulario(obter_perfil(farmacia_id))
        dados.update(request.form.to_dict())
        return render_template(
            "dashboard/perfil_editar.html",
            perfil=obter_perfil(farmacia_id),
            dados=dados,
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
# EDITAR PRODUTO
# ============================================================

def _dados_do_produto(produto):
    """Converte o produto salvo nos valores iniciais do formulário."""
    preco = produto.get("preco") or 0
    desconto = produto.get("desconto_percentual")
    fim = produto.get("promocao_ate_local")  # só existe com desconto ativo

    return {
        "nome": produto.get("nome", ""),
        "categoria": produto.get("categoria", ""),
        "principio_ativo": produto.get("principio_ativo", ""),
        "descricao": produto.get("descricao", ""),
        "preco": f"{preco:.2f}".replace(".", ","),
        "desconto_percentual": (
            desconto if produto.get("promocao_ativa") and desconto else ""
        ),
        "promocao_ate": fim.strftime("%Y-%m-%dT%H:%M") if fim else "",
    }


@app.route(
    "/painel/produtos/<produto_id>/editar",
    methods=["GET", "POST"]
)
@login_obrigatorio
def painel_editar_produto(produto_id):
    farmacia_id = session["farmacia_id"]

    # só encontra se o produto for da farmácia logada
    produto = obter_produto(farmacia_id, produto_id)

    if produto is None:
        flash("Produto não encontrado.", "danger")
        return redirect(url_for("painel"))

    if request.method == "POST":
        ok, mensagem = editar_produto(
            farmacia_id,
            produto_id,
            request.form,
            request.files.get("imagem_arquivo"),
        )

        if ok:
            flash(mensagem, "success")
            return redirect(url_for("painel"))

        return render_template(
            "dashboard/produto_editar.html",
            produto=produto,
            categorias=CATEGORIAS,
            dados=request.form.to_dict(),
            erro=mensagem,
        )

    return render_template(
        "dashboard/produto_editar.html",
        produto=produto,
        categorias=CATEGORIAS,
        dados=_dados_do_produto(produto),
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
# ANÚNCIOS DO CARROSSEL
# ============================================================

@app.route("/painel/anuncios", methods=["POST"])
@login_obrigatorio
def painel_adicionar_anuncio():
    ok, mensagem = adicionar_anuncio(
        session["farmacia_id"],
        session["farmacia_nome"],
        request.form,
        request.files.get("imagem_arquivo"),
    )

    flash(mensagem, "success" if ok else "danger")
    return redirect(url_for("painel"))


@app.route("/painel/anuncios/<anuncio_id>/excluir", methods=["POST"])
@login_obrigatorio
def painel_excluir_anuncio(anuncio_id):
    ok, mensagem = excluir_anuncio(
        session["farmacia_id"],
        anuncio_id,
    )

    flash(mensagem, "success" if ok else "danger")
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
    farmacia_id = session["farmacia_id"]

    ok, mensagem = excluir_farmacia(farmacia_id)

    if ok:
        excluir_anuncios_da_farmacia(farmacia_id)
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


# NOVO: farmácias cadastradas (com coordenadas) para o mapa
@app.route("/api/farmacias")
def api_farmacias():
    return jsonify(listar_farmacias_mapa())


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

    # O link do produto usa o mesmo id da página /produto/<id>:
    # a "chave" do medicamento com hífens no lugar dos espaços.
    # (o id do documento da farmácia não serve, a página não o encontraria)
    for p in produtos:
        chave = p.get("chave") or gerar_chave(p.get("nome", ""))
        p["id"] = chave.replace(" ", "-")

    return render_template(
        "pages/farmacia.html",
        farmacia=farmacia,
        farmacia_id=farmacia_id,  # NOVO
        produtos=produtos,
        site="poupemais.com",
    )


# ============================================================
# BUSCA (produtos, farmácias e sintomas)
# Precisa do import:  from sintomas import AVISO_SINTOMAS, achar_categorias
# ============================================================

def _item_produto(p):
    menor = p.get("menor_preco") or {}
    return {
        "tipo": "produto",
        "id": p["id"],
        "nome": p["nome"],
        "categoria": p.get("categoria", ""),
        "imagem": p.get("imagem", ""),
        "preco": menor.get("preco"),
        "exige_receita": bool(p.get("exige_receita")),
        "url": url_for("produto", produto_id=p["id"]),
    }


def _pesquisar(termo_digitado):
    """Procura produtos, farmácias e sintomas.

    Devolve (resultados, e_sintoma). Quando e_sintoma é True, quem
    chamou deve mostrar o aviso "não somos médicos".
    """
    termo = normalizar((termo_digitado or "").strip())

    if len(termo) < 2:
        return [], False

    resultados = []

    # Produtos pelo nome, categoria ou princípio ativo
    for p in todos_produtos_cache():
        campos = [
            p.get("nome", ""),
            p.get("categoria", ""),
            p.get("principio_ativo", ""),
        ]
        if any(termo in normalizar(campo) for campo in campos):
            resultados.append(_item_produto(p))

    # Farmácias
    for farmacia in buscar_farmacias(termo):
        resultados.append({
            "tipo": "farmacia",
            "id": farmacia["uid"],
            "nome": farmacia.get("nome", ""),
            "categoria": "Farmácia",
            "url": url_for("perfil_farmacia", farmacia_id=farmacia["uid"]),
        })

    # Sintomas (dor de cabeça, azia, tosse...)
    categorias_sintoma = achar_categorias(termo)
    if categorias_sintoma:
        ja_listados = {r["id"] for r in resultados if r["tipo"] == "produto"}
        for p in todos_produtos_cache():
            if (
                p.get("categoria") in categorias_sintoma
                and not p.get("exige_receita")  # remédio com receita não é sugerido
                and p["id"] not in ja_listados
            ):
                resultados.append(_item_produto(p))

    return resultados, bool(categorias_sintoma)


@app.route("/busca")
def busca():
    """Lista rápida da barra de pesquisa (JSON)."""
    resultados, e_sintoma = _pesquisar(request.args.get("q", ""))
    resultados = resultados[:8]

    if e_sintoma:
        resultados.insert(0, {
            "tipo": "aviso",
            "id": "",
            "nome": AVISO_SINTOMAS,
            "categoria": "",
            "url": "",
        })

    return jsonify(resultados)


@app.route("/pesquisa")
def pesquisa():
    """Página com todos os resultados (Enter na barra de pesquisa)."""
    q = request.args.get("q", "").strip()
    resultados, e_sintoma = _pesquisar(q)

    return render_template(
        "pages/pesquisa.html",
        q=q,
        produtos=[r for r in resultados if r["tipo"] == "produto"],
        farmacias=[r for r in resultados if r["tipo"] == "farmacia"],
        e_sintoma=e_sintoma,
        aviso=AVISO_SINTOMAS,
        site="poupemais.com",
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
    registrar_consultas(produto, session)
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