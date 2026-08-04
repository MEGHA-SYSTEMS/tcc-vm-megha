# GitHub Actions

## Objetivo

Este documento descreve a utilização do GitHub Actions para automatização de verificações do projeto PoupeMais.

---

# Finalidade

O GitHub Actions é utilizado para executar processos automáticos sempre que alterações forem enviadas ao repositório.

---

# Fluxo de Execução

1. Um desenvolvedor envia alterações para o GitHub.

2. O GitHub inicia automaticamente o workflow configurado.

3. São executadas verificações da documentação do projeto.

4. Caso todas as verificações sejam aprovadas, o workflow é finalizado com sucesso.

---

# Benefícios

A utilização do GitHub Actions proporciona:

- automação;
- padronização das verificações;
- redução de erros;
- maior organização do projeto;
- integração contínua (CI).

---

# Estrutura

Os workflows ficam armazenados no diretório:

```
.github/workflows/
```

---

# Controle de Qualidade

O workflow verifica a existência dos arquivos de documentação utilizados pelo projeto.

Caso algum arquivo obrigatório esteja ausente, o processo é interrompido até sua correção.

---

# Manutenção

Novos workflows poderão ser adicionados futuramente para testes, deploy e outras validações automáticas.