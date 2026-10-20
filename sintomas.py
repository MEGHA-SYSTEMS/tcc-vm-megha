"""Busca por sintomas: liga o que a pessoa digita a produtos relacionados.

Não indica remédio nem dose. Só aponta produtos relacionados (por categoria
e pela descrição do produto), e a busca sempre mostra o aviso abaixo.
Esta lista deve ser revisada por um farmacêutico antes de ir para produção.
"""
import re
import unicodedata

AVISO_SINTOMAS = (
    "Não somos médicos e não podemos indicar medicamentos. Estes produtos "
    "são apenas relacionados ao que você buscou, para ajudar na sua "
    "pesquisa. Procure um médico ou farmacêutico antes de usar qualquer "
    "medicamento."
)

# Nomes dos campos nos seus produtos (ajuste se o seu projeto usar outros).
CAMPO_CATEGORIA = "categoria"
CAMPO_DESCRICAO = "descricao"

# (o que a pessoa pode digitar, sem acento,
#  categorias do sistema,
#  radicais para procurar na DESCRIÇÃO dos produtos, sem acento)
# Os nomes das categorias precisam ser iguais aos de CATEGORIAS.
SINTOMAS = [
    (["dor de cabeca", "cefaleia", "enxaqueca", "febre", "dor no corpo",
      "dor muscular", "dor de dente", "dor de garganta", "mal estar",
      "calafrio"],
     ["Analgésico e Antitérmico"],
     ["dor", "febre", "cefaleia", "enxaqueca", "calafrio", "muscular"]),
    (["dor de barriga", "dor de estomago", "azia", "queimacao", "refluxo",
      "ma digestao", "gastrite", "estomago", "enjoo", "nausea"],
     ["Proteção Gástrica"],
     ["azia", "queimacao", "refluxo", "gastrite", "estomago", "digestao",
      "acidez", "nausea", "enjoo"]),
    (["tosse", "catarro", "falta de ar", "chiado", "nariz entupido",
      "congestao nasal", "coriza", "rinite", "asma", "gripe", "resfriado"],
     ["Saúde Respiratória"],
     ["tosse", "catarro", "expectorante", "congestao", "coriza", "rinite",
      "asma", "gripe", "resfriado", "respiratoria", "respiratorio"]),
    (["insonia", "dificuldade para dormir", "nao consigo dormir",
      "sono ruim"],
     ["Auxílio para o Sono"],
     ["insonia", "dormir", "sono"]),
    (["dor no joelho", "dor nas articulacoes", "dor nas juntas", "artrose",
      "dor nas costas", "rigidez"],
     ["Saúde das Articulações", "Analgésico e Antitérmico"],
     ["articulacao", "articulacoes", "artrose", "rigidez", "dor",
      "muscular"]),
    (["pele seca", "coceira", "alergia de pele", "ressecamento", "assadura"],
     ["Cuidados com a Pele"],
     ["pele", "coceira", "prurido", "alergia", "ressecamento", "assadura",
      "dermatite"]),
    (["vista cansada", "olho seco", "olho vermelho", "ardencia nos olhos"],
     ["Cuidados com a Visão"],
     ["olho", "olhos", "ocular", "visao", "vista", "ardencia"]),
    (["cansaco", "fraqueza", "falta de energia", "indisposicao"],
     ["Vitamina"],
     ["cansaco", "fadiga", "fraqueza", "energia", "disposicao"]),
    (["prisao de ventre", "intestino preso", "inchaco", "retencao de liquido"],
     ["Cuidados Diários", "Diurético"],
     ["constipacao", "intestino", "inchaco", "retencao", "diuretico"]),
]

# Palavras que não ajudam a buscar na descrição.
STOPWORDS = {
    "tenho", "estou", "muito", "muita", "muitos", "muitas", "sinto",
    "sentindo", "para", "com", "sem", "uma", "uns", "umas", "que", "por",
    "nos", "nas", "dos", "das", "meu", "minha", "dor",
}


def _norm(texto):
    """minúsculo, sem acento, espaços simples."""
    t = unicodedata.normalize("NFKD", texto or "")
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", t).strip()


def _tokens(texto):
    """Palavras normalizadas, sem pontuação."""
    return _norm(re.sub(r"[^\w\s]", " ", texto or "")).split()


def _bate(radical, tokens):
    """O radical aparece nas palavras?

    Radicais curtos (ex.: "dor") só batem com a palavra exata ou o plural
    ("dores"), para não pegar "corredor" ou "dorsal". Radicais longos
    batem pelo começo da palavra ("resfriad" acha "resfriado").
    """
    if len(radical) < 5:
        return any(t in (radical, radical + "s", radical + "es")
                   for t in tokens)
    return any(t.startswith(radical) for t in tokens)


def _grupos_do_termo(termo):
    """Grupos de SINTOMAS ligados ao que foi digitado."""
    grupos = []
    for palavras, cats, radicais in SINTOMAS:
        for palavra in palavras:
            # "dor de cab" acha "dor de cabeca"; "tenho muita tosse" acha "tosse"
            if termo in palavra or palavra in termo:
                grupos.append((cats, radicais))
                break
    return grupos


def achar_categorias(termo):
    """Categorias ligadas ao sintoma digitado (lista vazia se não for sintoma)."""
    termo = _norm(termo)
    if len(termo) < 3:
        return []

    categorias = []
    for cats, _ in _grupos_do_termo(termo):
        for c in cats:
            if c not in categorias:
                categorias.append(c)
    return categorias


def buscar_por_sintoma(termo, produtos):
    """Produtos relacionados ao sintoma, do mais ao menos relacionado.

    `produtos` é uma lista de dicts (ou objetos com .get) com os campos
    CAMPO_CATEGORIA e CAMPO_DESCRICAO. Devolve lista vazia se nada bater.
    """
    termo = _norm(termo)
    if len(termo) < 3:
        return []

    grupos = _grupos_do_termo(termo)
    categorias = {c for cats, _ in grupos for c in cats}
    radicais = {r for _, rads in grupos for r in rads}

    # Palavras soltas do que a pessoa digitou (cobre sintomas fora da lista,
    # ex.: "sinusite", desde que apareçam na descrição de algum produto).
    soltas = {p for p in _tokens(termo) if len(p) >= 4 and p not in STOPWORDS}

    resultado = []
    for produto in produtos:
        tokens = _tokens(produto.get(CAMPO_DESCRICAO, ""))
        pontos = 0

        if produto.get(CAMPO_CATEGORIA) in categorias:
            pontos += 2

        achados_desc = sum(1 for r in radicais if _bate(r, tokens))
        pontos += min(achados_desc, 3)

        # Palavra digitada aparece direto na descrição.
        pontos += min(sum(1 for p in soltas if _bate(p, tokens)), 2)

        if pontos > 0:
            resultado.append((pontos, produto))

    resultado.sort(key=lambda par: par[0], reverse=True)
    return [produto for _, produto in resultado]