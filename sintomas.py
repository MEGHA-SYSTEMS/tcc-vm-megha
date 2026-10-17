"""Busca por sintomas: liga o que a pessoa digita a CATEGORIAS de produtos.

Não indica remédio nem dose. Só aponta categorias relacionadas, e a busca
sempre mostra o aviso abaixo. Esta lista deve ser revisada por um
farmacêutico antes de ir para produção.
"""
import re
import unicodedata

AVISO_SINTOMAS = (
    "Não somos médicos e não podemos indicar medicamentos. Estes produtos "
    "são apenas relacionados ao que você buscou, para ajudar na sua "
    "pesquisa. Procure um médico ou farmacêutico antes de usar qualquer "
    "medicamento."
)

# (palavras que a pessoa pode digitar, sem acento) -> categorias do sistema.
# Os nomes das categorias precisam ser iguais aos de CATEGORIAS.
SINTOMAS = [
    (["dor de cabeca", "cefaleia", "enxaqueca", "febre", "dor no corpo",
      "dor muscular", "dor de dente", "dor de garganta", "mal estar",
      "calafrio"],
     ["Analgésico e Antitérmico"]),
    (["dor de barriga", "dor de estomago", "azia", "queimacao", "refluxo",
      "ma digestao", "gastrite", "estomago", "enjoo", "nausea"],
     ["Proteção Gástrica"]),
    (["tosse", "catarro", "falta de ar", "chiado", "nariz entupido",
      "congestao nasal", "coriza", "rinite", "asma", "gripe", "resfriado"],
     ["Saúde Respiratória"]),
    (["insonia", "dificuldade para dormir", "nao consigo dormir",
      "sono ruim"],
     ["Auxílio para o Sono"]),
    (["dor no joelho", "dor nas articulacoes", "dor nas juntas", "artrose",
      "dor nas costas", "rigidez"],
     ["Saúde das Articulações", "Analgésico e Antitérmico"]),
    (["pele seca", "coceira", "alergia de pele", "ressecamento", "assadura"],
     ["Cuidados com a Pele"]),
    (["vista cansada", "olho seco", "olho vermelho", "ardencia nos olhos"],
     ["Cuidados com a Visão"]),
    (["cansaco", "fraqueza", "falta de energia", "indisposicao"],
     ["Suplemento Vitamínico"]),
    (["prisao de ventre", "intestino preso", "inchaco", "retencao de liquido"],
     ["Cuidados Diários", "Diurético"]),
]


def _norm(texto):
    """minúsculo, sem acento, espaços simples."""
    t = unicodedata.normalize("NFKD", texto or "")
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", t).strip()


def achar_categorias(termo):
    """Categorias ligadas ao sintoma digitado (lista vazia se não for sintoma)."""
    termo = _norm(termo)
    if len(termo) < 3:
        return []

    categorias = []
    for palavras, cats in SINTOMAS:
        for palavra in palavras:
            # "dor de cab" acha "dor de cabeca"; "tenho muita tosse" acha "tosse"
            if termo in palavra or palavra in termo:
                for c in cats:
                    if c not in categorias:
                        categorias.append(c)
                break
    return categorias