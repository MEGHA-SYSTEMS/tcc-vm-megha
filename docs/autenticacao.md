# Autenticação

## Objetivo

Este documento descreve a estratégia de autenticação utilizada no projeto PoupeMais.

---

# Tecnologia

O controle de autenticação será realizado utilizando o Firebase Authentication.

---

# Finalidade

A autenticação tem como objetivo restringir o acesso às funcionalidades administrativas da plataforma.

Usuários comuns poderão consultar informações públicas da aplicação sem necessidade de login.

Áreas administrativas exigirão autenticação.

---

# Fluxo de Autenticação

1. O usuário acessa a tela de login.

2. A aplicação envia as credenciais ao Firebase Authentication.

3. O Firebase valida as credenciais.

4. Caso válidas, o usuário recebe autorização para acessar as funcionalidades permitidas.

5. Caso inválidas, o acesso é negado.

---

# Segurança

O gerenciamento das credenciais é realizado pelo Firebase Authentication.

A aplicação não armazena senhas em banco de dados próprio.

---

# Benefícios

A utilização do Firebase Authentication proporciona:

- maior segurança;
- gerenciamento centralizado dos usuários;
- integração com os demais serviços do Firebase;
- facilidade de manutenção.