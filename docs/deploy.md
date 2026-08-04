# Manual de Deploy

## Objetivo

Este documento descreve o processo de deploy do projeto PoupeMais utilizando GitHub, Firebase e GitHub Actions.

---

# Pré-requisitos

Antes do deploy é necessário possuir:

- Git instalado;
- Node.js instalado;
- Firebase CLI instalada;
- Conta Google;
- Projeto criado no Firebase;
- Permissão de acesso ao repositório GitHub.

---

# Estrutura do Projeto

O código-fonte é mantido em um repositório GitHub.

Todo desenvolvimento deve ocorrer em branches específicas antes da integração com a branch principal.

---

# Fluxo de Deploy

1. Desenvolvedor realiza alterações no projeto.

2. As alterações são enviadas para uma branch no GitHub.

3. O GitHub Actions executa as verificações automáticas.

4. Caso não existam erros, o projeto poderá ser publicado utilizando o Firebase.

---

# Serviços Utilizados

- GitHub
- GitHub Actions
- Firebase Hosting
- Firebase Firestore
- Firebase Authentication

---

# Versionamento

Todo o histórico de alterações permanece registrado no GitHub, permitindo rastreabilidade e controle das versões do projeto.

---

# Observações

O deploy somente deverá ser realizado após validação da documentação e aprovação das alterações realizadas no projeto.