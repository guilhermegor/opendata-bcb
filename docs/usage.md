# **Uso**

Exemplos de instalação e de uso desta biblioteca.

> **Veja também:** [Referência da API](api/index.md)

---

## Instalação

```bash
pip install opendata-bcb
```

Ou com Poetry:

```bash
poetry add opendata-bcb
```

Toda linha de `pip install` tem um equivalente em Poetry.

---

## Uso básico

Cada leitor devolve um `pandas.DataFrame`; os valores numéricos da fonte são `Decimal`, nunca
`float`. Veja mais receitas em [Exemplos](examples.md).

```python
from opendata_bcb import read_banks


df_banks = read_banks()
print(df_banks[["ispb", "compe_code", "short_name"]].head())
```

---

## Executando os testes

```bash
poe unit_tests         # somente testes unitários
poe integration_tests  # somente testes de integração
poe test_cov           # testes unitários + relatório de cobertura + badge
```

---

## Lint e formatação

```bash
poe lint          # ruff check + ruff format + codespell + pydocstyle
```

---

## Publicação no PyPI

Dois workflows do GitHub Actions cuidam dos lançamentos (presentes quando o repositório tem um remoto no GitHub):

- **`release-test-pypi.yaml`** — publica primeiro no [Test PyPI](https://test.pypi.org).
- **`release-pypi.yaml`** — publica no [PyPI](https://pypi.org) e cria uma release no GitHub.

Dispare qualquer um pela aba **Actions** (`workflow_dispatch`) informando a versão a lançar.
Ambos exigem que a nova versão seja maior que a última já publicada, constroem o pacote com
Poetry e publicam por OIDC (trusted publishing), então nenhum segredo de token é necessário.

Configure uma única vez, em cada índice (pypi.org e test.pypi.org), um pending publisher:

- PyPI: workflow `release-pypi.yaml`, environment `release-pypi`.
- Test PyPI: workflow `release-test-pypi.yaml`, environment `release-test-pypi`.

Depois que a primeira execução de `release-pypi.yaml` criar a branch `gh-pages`, rode
`poe enable_pages` uma vez para publicar a documentação.
