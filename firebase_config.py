"""Conexão com o Firebase (Firestore).

Como a chave é encontrada, nesta ordem:
1. Variável de ambiente FIREBASE_KEY_JSON (conteúdo do .json) -> usada no Render
2. Arquivo serviceAccountKey.json na mesma pasta deste arquivo -> usado no seu PC

Se nenhuma existir, `db` fica como None e o site continua abrindo
com os dados locais (fallback), avisando no terminal.
"""
import json
import os

db = None

try:
    import firebase_admin
    from firebase_admin import credentials, firestore

    if not firebase_admin._apps:
        pasta = os.path.dirname(os.path.abspath(__file__))
        caminho = os.path.join(pasta, "serviceAccountKey.json")
        chave_env = os.environ.get("FIREBASE_KEY_JSON")

        if chave_env:
            cred = credentials.Certificate(json.loads(chave_env))
        elif os.path.exists(caminho):
            cred = credentials.Certificate(caminho)
        else:
            cred = None
            print("[Firebase] serviceAccountKey.json não encontrado. "
                  "Usando dados locais.")

        if cred is not None:
            firebase_admin.initialize_app(cred)

    if firebase_admin._apps:
        db = firestore.client()
        print("[Firebase] Conectado ao Firestore.")
except Exception as erro:
    db = None
    print(f"[Firebase] Não foi possível conectar: {erro}")