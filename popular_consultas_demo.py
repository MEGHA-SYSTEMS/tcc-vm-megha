"""Gera consultas FICTÍCIAS para demonstrar o painel de desempenho.

Use apenas em uma conta de teste: o script sobrescreve os contadores dos
dias gerados. Todos os documentos criados levam "demo": True, e por isso
podem ser apagados depois sem mexer nas consultas reais.

    python popular_consultas_demo.py <farmacia_id>            # gera 30 dias
    python popular_consultas_demo.py <farmacia_id> 60         # gera 60 dias
    python popular_consultas_demo.py <farmacia_id> --apagar   # remove os fictícios

O <farmacia_id> é o uid da farmácia (o mesmo documento em 'farmacias').

IMPORTANTE: se for apresentar esses números, deixe claro no TCC que são
dados de demonstração, gerados para testar a interface.
"""
import random
import sys
from datetime import datetime, timedelta

from desempenho_service import COLECAO_CONSULTAS, id_do_produto
from firebase_config import db
from produtos_service import FUSO_BR, listar_produtos

TAMANHO_LOTE = 400


def gerar(farmacia_id, dias):
    produtos = listar_produtos(farmacia_id)
    if not produtos:
        print("Essa farmácia não tem produtos cadastrados.")
        return

    hoje = datetime.now(FUSO_BR).date()
    lote = db.batch()
    pendentes = 0
    documentos = 0
    consultas = 0

    for produto in produtos:
        pid = id_do_produto(produto)
        popularidade = random.choice([1, 2, 3, 5, 8])  # alguns produtos "bombam"

        for n in range(dias):
            dia = (hoje - timedelta(days=n)).isoformat()
            qtd = random.randint(0, popularidade)
            if qtd == 0:
                continue

            ref = db.collection(COLECAO_CONSULTAS).document(
                f"{farmacia_id}__{dia}__{pid}"
            )
            lote.set(ref, {
                "farmacia_id": farmacia_id,
                "produto_id": pid,
                "dia": dia,
                "count": qtd,
                "demo": True,
            })

            pendentes += 1
            documentos += 1
            consultas += qtd

            if pendentes == TAMANHO_LOTE:
                lote.commit()
                lote = db.batch()
                pendentes = 0

    if pendentes:
        lote.commit()

    print(f"Pronto: {documentos} documentos, {consultas} consultas fictícias.")


def apagar(farmacia_id):
    lote = db.batch()
    pendentes = 0
    total = 0

    docs = db.collection(COLECAO_CONSULTAS).where(
        "farmacia_id", "==", farmacia_id
    ).stream()

    for doc in docs:
        if not doc.to_dict().get("demo"):
            continue

        lote.delete(doc.reference)
        pendentes += 1
        total += 1

        if pendentes == TAMANHO_LOTE:
            lote.commit()
            lote = db.batch()
            pendentes = 0

    if pendentes:
        lote.commit()

    print(f"Removidos {total} documentos fictícios.")


def main():
    if db is None:
        print("Sem conexão com o Firestore.")
        return

    if len(sys.argv) < 2:
        print(__doc__)
        return

    farmacia_id = sys.argv[1]
    extra = sys.argv[2] if len(sys.argv) > 2 else "30"

    if extra == "--apagar":
        apagar(farmacia_id)
    else:
        gerar(farmacia_id, int(extra))


if __name__ == "__main__":
    main()