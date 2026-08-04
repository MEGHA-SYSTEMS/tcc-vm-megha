# Integração com Firebase

## Objetivo

Este documento descreve a utilização dos serviços do Firebase no projeto PoupeMais.

---

# Serviços Utilizados

O projeto utiliza os seguintes serviços da plataforma Firebase:

- Firebase Firestore
- Firebase Authentication
- Firebase Hosting

---

# Firebase Firestore

O Firestore é utilizado para armazenar informações necessárias ao funcionamento da aplicação.

Sua utilização permite armazenamento em nuvem, sincronização dos dados e escalabilidade.

---

# Firebase Authentication

O Firebase Authentication é responsável pelo controle de autenticação dos usuários autorizados a acessar funcionalidades administrativas da plataforma.

A autenticação poderá ser realizada utilizando os métodos disponibilizados pelo Firebase.

---

# Firebase Hosting

O Firebase Hosting é utilizado como parte da infraestrutura de deploy descrita neste projeto.

Sua configuração é realizada juntamente com os demais serviços da plataforma Firebase.

---

# Segurança

As regras de acesso ao Firestore serão definidas através do arquivo:

```

firestore.rules

```

permitindo controlar quais usuários possuem permissão para leitura e escrita dos dados.

---

# Arquivos de Configuração

Os principais arquivos utilizados pela integração são:

- firebase.json
- .firebaserc
- firestore.rules
- firestore.indexes.json

---

# Benefícios

A utilização do Firebase oferece:

- integração com serviços em nuvem;
- gerenciamento centralizado;
- autenticação segura;
- armazenamento escalável;
- facilidade de manutenção.