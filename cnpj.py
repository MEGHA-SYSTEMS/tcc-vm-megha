"""Validação de CNPJ de farmácia.

Camada 1: confere os dígitos verificadores (offline).
Camada 2: consulta a Receita Federal pela BrasilAPI (gratuita) e confere
          se o CNPJ está ATIVO e se a atividade (CNAE) é de farmácia.
"""
import json
import re
import urllib.error
import urllib.request

URL_BRASILAPI = "https://brasilapi.com.br/api/cnpj/v1/{cnpj}"

# CNAE 4771-7: comércio varejista de produtos farmacêuticos
#   4771701 = sem manipulação de fórmulas
#   4771702 = com manipulação de fórmulas
#   4771703 = homeopáticos
# (4771704, medicamentos veterinários, de propósito ficou de fora)
CNAES_FARMACIA = {4771701, 4771702, 4771703}

SITUACAO_ATIVA = 2  # código da Receita para "ATIVA"


class CnpjNaoEncontrado(Exception):
    pass


class ReceitaIndisponivel(Exception):
    pass


def limpar_cnpj(texto):
    """Deixa só os números: '12.345.678/0001-95' -> '12345678000195'."""
    return re.sub(r"\D", "", texto or "")


def cnpj_valido(cnpj):
    """Camada 1: confere tamanho e dígitos verificadores."""
    if len(cnpj) != 14 or not cnpj.isdigit() or cnpj == cnpj[0] * 14:
        return False

    def digito(base, pesos):
        soma = sum(int(n) * p for n, p in zip(base, pesos))
        resto = soma % 11
        return "0" if resto < 2 else str(11 - resto)

    d1 = digito(cnpj[:12], [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    d2 = digito(cnpj[:12] + d1, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    return cnpj[12:] == d1 + d2


def consultar_receita(cnpj):
    """Camada 2: busca o CNPJ na BrasilAPI e devolve um dicionário simples."""
    pedido = urllib.request.Request(
        URL_BRASILAPI.format(cnpj=cnpj),
        headers={"User-Agent": "poupemais-tcc"},
    )
    try:
        with urllib.request.urlopen(pedido, timeout=8) as resposta:
            dados = json.loads(resposta.read().decode("utf-8"))
    except urllib.error.HTTPError as erro:
        if erro.code in (400, 404):
            raise CnpjNaoEncontrado()
        raise ReceitaIndisponivel(f"HTTP {erro.code}")
    except Exception as erro:  # sem internet, timeout, JSON quebrado...
        raise ReceitaIndisponivel(str(erro))

    cnaes = {dados.get("cnae_fiscal")}
    for item in dados.get("cnaes_secundarios") or []:
        cnaes.add(item.get("codigo"))

    return {
        "razao_social": dados.get("razao_social", ""),
        "nome_fantasia": dados.get("nome_fantasia", ""),
        "situacao": dados.get("descricao_situacao_cadastral", ""),
        "ativa": dados.get("situacao_cadastral") == SITUACAO_ATIVA,
        "cnae_farmacia": bool(cnaes & CNAES_FARMACIA),
    }


def verificar_farmacia(cnpj):
    """Roda as duas camadas. Devolve (ok, mensagem_de_erro, dados_da_receita)."""
    if not cnpj_valido(cnpj):
        return False, "CNPJ inválido. Confira os números digitados.", None

    try:
        dados = consultar_receita(cnpj)
    except CnpjNaoEncontrado:
        return False, "CNPJ não encontrado na Receita Federal.", None
    except ReceitaIndisponivel as erro:
        print(f"[CNPJ] Consulta à Receita falhou: {erro}")
        return False, ("Não foi possível consultar a Receita agora. "
                       "Tente novamente em alguns minutos."), None

    if not dados["ativa"]:
        return False, (f"Este CNPJ está com situação "
                       f"'{dados['situacao'].title()}' na Receita."), None

    if not dados["cnae_farmacia"]:
        return False, ("A atividade cadastrada para este CNPJ não é de "
                       "farmácia."), None

    return True, "", dados