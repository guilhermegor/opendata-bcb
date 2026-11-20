# **Exemplos**

Trechos autocontidos e orientados a tarefas para os usos mais comuns desta biblioteca. Cada
receita é independente — copie e ajuste.

> **Veja também:** [Uso](usage.md) para o básico · [Referência da API](api/index.md) para cada
> símbolo público.

---

## Receita: <uma tarefa comum>

Descreva em poucas palavras o problema que esta receita resolve e, em seguida, mostre o menor
trecho que funciona.

```python
from <project_name> import main


# Replace with a real, runnable example of your public API.
main()
```

## Receita: <outra tarefa>

Adicione uma seção `##` por receita. Os comentários no código devem explicar **por quê**, não
apenas o quê.

```python
# Replace with a second illustrative example.
```

## Receita: consultar o código COMPE de um banco

O cadastro traz o ISPB e o código COMPE, ambos como texto, para que os zeros à esquerda
sobrevivam.

```python
from opendata_bcb import read_banks


df_banks = read_banks()
# O código é texto de 3 dígitos; filtrar por número perderia o zero à esquerda.
print(df_banks.loc[df_banks["compe_code"] == "001", ["ispb", "full_name"]])
```

## Receita: série temporal do SGS

Lê a cotação do dólar (série 1) em um intervalo. `valor` é `Decimal`, sem perda de precisão.

```python
from datetime import date
from pathlib import Path

from opendata_bcb import read_sgs_series

df_dolar = read_sgs_series(
    1, dt_start=date(2026, 11, 1), dt_end=date(2026, 11, 10), path_cache_dir=Path(".cache")
)
```

## Receita: listar as moedas ativas na PTAX

A data de exclusão vazia significa que a moeda ainda é cotada; `is_active` já resolve isso.

```python
from opendata_bcb import read_currency_codes


df_codes = read_currency_codes()
# O código é texto de 3 dígitos; comparar com número perderia o zero à esquerda.
print(df_codes.loc[df_codes["is_active"], ["currency_code", "symbol", "name"]])
```
