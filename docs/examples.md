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

## Receita: listar os códigos de moeda dos boletins de cotação

```python
from opendata_bcb import read_quote_bulletin_codes


df_codes = read_quote_bulletin_codes()
# O código é texto: é o valor que o formulário do BCB espera, sem conversão numérica.
print(df_codes.loc[df_codes["name"].str.contains("ZLOTY"), ["code", "name"]])
```

## Receita: expectativas anuais do Focus

Lê as expectativas de IPCA da pesquisa Focus em uma semana. As estatísticas são `Decimal`, sem
perda de precisão, e `numeroRespondentes` é inteiro.

```python
from datetime import date

from opendata_bcb import read_focus_annual_expectations


df_ipca = read_focus_annual_expectations(
    "IPCA", dt_start=date(2026, 11, 9), dt_end=date(2026, 11, 13)
)
print(df_ipca[["Data", "DataReferencia", "Mediana", "numeroRespondentes"]])
```

## Receita: PTAX dólar/real em um período

As taxas são `Decimal` e `quoted_at` mantém o horário do boletim.

```python
from datetime import date

from opendata_bcb import read_ptax_usd_brl


df_ptax = read_ptax_usd_brl(dt_start=date(2026, 11, 3), dt_end=date(2026, 11, 5))
print(df_ptax[["quoted_at", "buy_rate", "sell_rate"]])
```

## Receita: moedas cotadas pela PTAX

Lista os símbolos, nomes e tipos (`A` ou `B`) das moedas que a PTAX cota.

```python
from opendata_bcb import read_ptax_currencies


df_moedas = read_ptax_currencies()
print(df_moedas[["symbol", "name", "currency_type"]])
```

## Receita: boletins de cotação de uma moeda

Lê os boletins de fechamento do dólar (código `"61"`, veja `read_quote_bulletin_codes`) em um
período. As taxas e paridades são `Decimal`, sem perda de precisão.

```python
from datetime import date

from opendata_bcb import read_quote_bulletins


df_boletins = read_quote_bulletins("61", dt_start=date(2026, 11, 10), dt_end=date(2026, 11, 19))
print(df_boletins[["date", "buy_rate", "sell_rate"]])
```

## Receita: metadados de uma série do SGS

Lê o nome, a periodicidade e a unidade da série 433 (IPCA). A periodicidade vem como a letra
da fonte (`M` para mensal).

```python
from opendata_bcb import read_sgs_metadata


df_meta = read_sgs_metadata(433)
print(df_meta[["code", "name", "periodicity", "unit"]])
```
