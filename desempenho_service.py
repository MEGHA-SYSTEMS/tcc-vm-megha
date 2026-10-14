"""Desempenho da farmácia: consultas aos produtos e comparação com o mercado.

Coleção 'consultas' (Firestore): um documento por farmácia + produto + dia.

    id:      <farmacia_id>__<AAAA-MM-DD>__<id-do-produto>
    campos:  farmacia_id, produto_id, dia, count

Assim uma única leitura (todos os documentos da farmácia) alimenta a tabela
de mais consultados e o gráfico de consultas por dia.
"""
from datetime import datetime, timedelta, timezone
from statistics import mean

from firebase_admin import firestore

from firebase_config import db
from produtos_service import FUSO_BR, gerar_chave, listar_produtos

COLECAO_CONSULTAS = "consultas"

MAX_VISTOS_SESSAO = 40     # quantos produtos "já vistos" lembrar na sessão
DIAS_DESATUALIZADO = 60    # preço sem atualização há mais que isso gera alerta
LIMITE_ACIMA_MEDIA = 15    # % acima da média dos concorrentes que gera alerta


# ============================================================
# AUXILIARES
# ============================================================

def _hoje():
    return datetime.now(FUSO_BR).date()


def id_do_produto(produto):
    """Mesmo id usado na URL do catálogo: /produto/<id>."""
    chave = produto.get("chave") or gerar_chave(produto.get("nome", ""))
    return chave.replace(" ", "-")


def _consultas_da_farmacia(farmacia_id):
    try:
        from google.cloud.firestore_v1.base_query import FieldFilter
        return db.collection(COLECAO_CONSULTAS).where(
            filter=FieldFilter("farmacia_id", "==", farmacia_id))
    except ImportError:
        return db.collection(COLECAO_CONSULTAS).where(
            "farmacia_id", "==", farmacia_id)


def _dias_sem_atualizar(produto):
    """Quantos dias desde a última edição (ou cadastro). None se não souber."""
    ref = produto.get("atualizado_em") or produto.get("criado_em")
    if not isinstance(ref, datetime):
        return None
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - ref).days


# ============================================================
# REGISTRO DE CONSULTAS
# ============================================================

def registrar_consultas(produto, sessao):
    """Soma 1 consulta para cada farmácia que vende o produto visualizado.

    'produto' é o dicionário devolvido por get_produto_por_id (com a lista
    'precos', onde cada oferta traz o 'farmacia_id').

    Não conta quando:
      - quem está olhando é uma farmácia logada;
      - a mesma pessoa (sessão) já abriu este produto hoje.

    Nunca derruba a página: se der erro, só avisa no terminal.
    """
    if db is None or "farmacia_id" in sessao:
        return

    dia = _hoje().isoformat()
    produto_id = produto["id"]
    marca = f"{dia}:{produto_id}"

    vistos = list(sessao.get("vistos", []))
    if marca in vistos:
        return

    farmacias = {
        oferta.get("farmacia_id")
        for oferta in produto.get("precos", [])
        if oferta.get("farmacia_id")
    }
    if not farmacias:
        return

    try:
        lote = db.batch()
        for farmacia_id in farmacias:
            ref = db.collection(COLECAO_CONSULTAS).document(
                f"{farmacia_id}__{dia}__{produto_id}"
            )
            lote.set(ref, {
                "farmacia_id": farmacia_id,
                "produto_id": produto_id,
                "dia": dia,
                "count": firestore.Increment(1),
            }, merge=True)
        lote.commit()
    except Exception as erro:
        print(f"[Consultas] Falha ao registrar: {erro}")
        return

    sessao["vistos"] = (vistos + [marca])[-MAX_VISTOS_SESSAO:]


# ============================================================
# LEITURA PARA O PAINEL
# ============================================================

def _ler_consultas(farmacia_id, dias):
    """Devolve ({dia: total}, {produto_id: total}) dentro do período."""
    inicio = (_hoje() - timedelta(days=dias - 1)).isoformat()
    por_dia, por_produto = {}, {}

    if db is None:
        return por_dia, por_produto

    # O filtro de data é feito aqui (e não na consulta) para não exigir
    # a criação de um índice composto no Firestore.
    for doc in _consultas_da_farmacia(farmacia_id).stream():
        d = doc.to_dict()
        dia = d.get("dia", "")
        if dia < inicio:
            continue
        qtd = int(d.get("count") or 0)
        por_dia[dia] = por_dia.get(dia, 0) + qtd
        pid = d.get("produto_id", "")
        por_produto[pid] = por_produto.get(pid, 0) + qtd

    return por_dia, por_produto


def montar_desempenho(farmacia_id, catalogo, dias=30):
    """Reúne tudo o que a página de desempenho mostra.

    'catalogo' é a lista agrupada de get_todos_produtos() (pode vir do cache).
    A concorrência aparece só de forma agregada (média e menor preço),
    sem nomear as outras farmácias.
    """
    meus = listar_produtos(farmacia_id) if db is not None else []
    mercado = {grupo["id"]: grupo for grupo in catalogo}
    por_dia, por_produto = _ler_consultas(farmacia_id, dias)

    itens = []
    alertas_acima = []
    alertas_antigos = []

    for p in meus:
        pid = id_do_produto(p)
        ofertas = (mercado.get(pid) or {}).get("precos", [])
        meu_preco = p.get("preco_final") or 0

        concorrentes = [
            o["preco"] for o in ofertas
            if o.get("farmacia_id") != farmacia_id
        ]

        posicao = 1 + sum(1 for c in concorrentes if c < meu_preco)
        media = round(mean(concorrentes), 2) if concorrentes else None
        menor_mercado = min(concorrentes + [meu_preco])
        dif_pct = (
            round((meu_preco - media) / media * 100, 1)
            if media else None
        )

        itens.append({
            "id": pid,
            "doc_id": p["id"],
            "nome": p.get("nome", ""),
            "categoria": p.get("categoria", ""),
            "preco": meu_preco,
            "consultas": por_produto.get(pid, 0),
            "posicao": posicao,
            "total": len(concorrentes) + 1,
            "media": media,
            "menor_mercado": menor_mercado,
            "dif_media_pct": dif_pct,
            "promocao_ativa": bool(p.get("promocao_ativa")),
        })

        if dif_pct is not None and dif_pct >= LIMITE_ACIMA_MEDIA:
            alertas_acima.append({
                "tipo": "acima",
                "doc_id": p["id"],
                "nome": p.get("nome", ""),
                "texto": (f"Seu preço está {dif_pct:.0f}% acima da média "
                          f"dos concorrentes."),
                "ordem": dif_pct,
            })

        antigo = _dias_sem_atualizar(p)
        if antigo is not None and antigo >= DIAS_DESATUALIZADO:
            alertas_antigos.append({
                "tipo": "antigo",
                "doc_id": p["id"],
                "nome": p.get("nome", ""),
                "texto": f"Preço sem atualização há {antigo} dias.",
                "ordem": antigo,
            })

    alertas_acima.sort(key=lambda a: a["ordem"], reverse=True)
    alertas_antigos.sort(key=lambda a: a["ordem"], reverse=True)
    alertas = (alertas_acima[:5] + alertas_antigos[:5])

    # ---------- cartões de resumo ----------
    com_concorrencia = [i for i in itens if i["total"] > 1]
    resumo = {
        "total_produtos": len(itens),
        "promocoes_ativas": sum(1 for i in itens if i["promocao_ativa"]),
        "consultas": sum(por_dia.values()),
        "com_concorrencia": len(com_concorrencia),
        "menor_preco": sum(1 for i in com_concorrencia if i["posicao"] == 1),
    }

    # ---------- tabela: mais consultados ----------
    tabela = sorted(
        (i for i in itens if i["consultas"] > 0),
        key=lambda i: i["consultas"],
        reverse=True,
    )[:10]

    # ---------- gráfico: consultas por dia ----------
    inicio = _hoje() - timedelta(days=dias - 1)
    labels, valores = [], []
    for n in range(dias):
        dia = inicio + timedelta(days=n)
        labels.append(dia.strftime("%d/%m"))
        valores.append(por_dia.get(dia.isoformat(), 0))

    # ---------- gráfico: meu preço vs. mercado ----------
    base = sorted(
        com_concorrencia,
        key=lambda i: (-i["consultas"], i["nome"].lower()),
    )[:8]
    mercado_grafico = {
        "labels": [
            (i["nome"][:22] + "…") if len(i["nome"]) > 22 else i["nome"]
            for i in base
        ],
        "meu": [i["preco"] for i in base],
        "media": [i["media"] for i in base],
        "menor": [i["menor_mercado"] for i in base],
    }

    # ---------- gráfico: posição no ranking ----------
    ranking = {
        "1º lugar": 0,
        "2º lugar": 0,
        "3º lugar ou pior": 0,
        "Sem concorrência": 0,
    }
    for i in itens:
        if i["total"] == 1:
            ranking["Sem concorrência"] += 1
        elif i["posicao"] == 1:
            ranking["1º lugar"] += 1
        elif i["posicao"] == 2:
            ranking["2º lugar"] += 1
        else:
            ranking["3º lugar ou pior"] += 1

    return {
        "resumo": resumo,
        "tabela": tabela,
        "alertas": alertas,
        "graficos": {
            "dia": {"labels": labels, "valores": valores},
            "mercado": mercado_grafico,
            "ranking": {
                "labels": list(ranking.keys()),
                "valores": list(ranking.values()),
            },
        },
    }