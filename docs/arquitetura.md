# Arquitetura do Sistema

## Objetivo

Este documento descreve a arquitetura do projeto PoupeMais, desenvolvido como Trabalho de Conclusão de Curso (TCC), bem como a integração dos serviços utilizados para implantação, autenticação e armazenamento de dados.

---

# Visão Geral

O projeto é uma aplicação web desenvolvida utilizando Python e Flask.

Sua finalidade é permitir que usuários consultem e comparem preços de produtos farmacêuticos entre diferentes redes de farmácias da cidade de Matão-SP.

A plataforma possui apenas finalidade informativa, não realizando vendas ou pagamentos.

---

# Arquitetura da Aplicação

A aplicação está organizada da seguinte forma:

- Backend: Python + Flask
- Frontend: HTML
- Arquivos estáticos: CSS, JavaScript e imagens na pasta `static`
- Templates HTML na pasta `templates`

Estrutura simplificada:

```
main.py
templates/
static/
requirements.txt
```

---

# Serviços Utilizados

O projeto utiliza os seguintes serviços:

| Serviço | Finalidade |
|----------|------------|
| Flask | Backend da aplicação |
| GitHub | Versionamento do código |
| Firebase Firestore | Armazenamento de dados |
| Firebase Authentication | Controle de autenticação |
| GitHub Actions | Automação da documentação e validações |

---

# Fluxo Geral

O usuário acessa a aplicação web.

↓

O Flask processa a requisição.

↓

Quando necessário, a aplicação consulta informações armazenadas no Firestore.

↓

Os dados são retornados para o usuário através da interface web.

---

# Organização do Repositório

O projeto utiliza GitHub como sistema de controle de versão.

As funcionalidades são desenvolvidas em branches específicas antes de serem integradas à branch principal.

---

# Responsabilidade da Arquitetura

A arquitetura deste projeto busca:

- facilitar manutenção;
- organizar os componentes da aplicação;
- permitir integração com serviços em nuvem;
- manter o código documentado;
- possibilitar evolução futura do sistema.