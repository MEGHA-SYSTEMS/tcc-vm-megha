from firebase_config import db

def _get_farmacias():
    """Busca as farmácias e retorna um dicionário mapeado por farmacia_id."""
    if db is None:
        return {}
    farmacias = {}
    for doc in db.collection("farmacias").stream():
        dados = doc.to_dict()
        endereco = dados.get("endereco", {})
        
        rua = endereco.get("rua", "")
        numero = endereco.get("numero", "")
        bairro = endereco.get("bairro", "")
        cidade = endereco.get("cidade", "")
        
        partes_end = [p for p in [rua, numero, bairro, cidade] if p]
        end_str = ", ".join(partes_end)
        
        farmacias[doc.id] = {
            "nome": dados.get("nome", "Farmácia Desconhecida"),
            "endereco": end_str
        }
    return farmacias

def _agrupar_produtos():
    """Agrupa os produtos do Firestore pela chave (nome normalizado)."""
    if db is None:
        return []
        
    farmacias = _get_farmacias()
    produtos_agrupados = {}
    
    for doc in db.collection("produtos").stream():
        p = doc.to_dict()
        chave = p.get("chave")
        if not chave:
            continue
            
        farmacia_id = p.get("farmacia_id")
        farmacia_info = farmacias.get(farmacia_id, {"nome": "Farmácia Desconhecida", "endereco": "Endereço não informado"})
        
        preco_info = {
            "farmacia": farmacia_info["nome"],
            "endereco": farmacia_info["endereco"],
            "preco": p.get("preco", 0.0)
        }
        
        if chave not in produtos_agrupados:
            produtos_agrupados[chave] = {
                "id": chave,
                "nome": p.get("nome", "Produto Sem Nome"),
                "categoria": p.get("categoria", "Outros"),
                "imagem": p.get("imagem", "https://via.placeholder.com/300x300.png?text=Sem+Imagem"),
                "descricao": p.get("descricao", "Sem descrição."),
                "principio_ativo": p.get("principio_ativo", "Não informado"),
                "precos": []
            }
            
        produtos_agrupados[chave]["precos"].append(preco_info)
        
    return list(produtos_agrupados.values())

def get_todos_produtos():
    """Retorna a lista completa de produtos agrupados, já com o menor preço calculado."""
    produtos_agrupados = _agrupar_produtos()
    produtos_com_menor_preco = []
    
    for produto in produtos_agrupados:
        if not produto["precos"]:
            continue
        menor = min(produto["precos"], key=lambda p: p["preco"])
        produto_copia = dict(produto)
        produto_copia["menor_preco"] = menor
        produtos_com_menor_preco.append(produto_copia)
        
    return produtos_com_menor_preco

def get_produto_por_id(produto_id):
    """Busca um produto agrupado pelo id (que corresponde à chave). Retorna None se não encontrar."""
    produtos_agrupados = _agrupar_produtos()
    
    for produto in produtos_agrupados:
        if str(produto["id"]) == str(produto_id):
            produto_copia = dict(produto)
            produto_copia["precos_ordenados"] = sorted(
                produto["precos"], key=lambda p: p["preco"]
            )
            return produto_copia
            
    return None