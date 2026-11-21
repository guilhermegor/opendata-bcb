# **Referência da API**

Interface pública desta biblioteca.

> **Veja também:** [Uso](../usage.md)

---

## Módulo: `main`

Módulo de ponto de entrada. Estenda-o com as funções públicas da sua biblioteca.

### `main() -> None`

Executa o ponto de entrada da biblioteca. Troque o corpo pela lógica de nível superior do seu projeto.

```python
from <package_name>.main import main

main()
```

---

## Adicionando novos módulos

Coloque os novos módulos em `src/<package_name>/`. Exporte os símbolos públicos em `src/<package_name>/__init__.py` para que quem usa a biblioteca possa fazer:

```python
from <package_name> import my_function
```

Siga a convenção de uma classe por arquivo: funções utilitárias sem estado compartilhado ficam no nível do módulo, e não dentro de uma classe.

---

## Convenções

| Convenção | Regra |
|-----------|-------|
| Type hints | Obrigatórias em todas as funções públicas, inclusive o retorno `-> None` |
| Docstrings | Estilo NumPy; explique o *porquê*, não o *quê* |
| Nomes de variáveis | Com prefixo de tipo (`str_`, `list_`, `cls_`, `dict_`, …) |
| Testes | `unittest`; uma asserção por teste; nome no formato `test_<unit>_<scenario>_<expected>` |

---

## Módulo: `banks`

Cadastro de bancos do Banco Central: códigos COMPE e ISPB.

### `read_banks(*, dt_reference=None, path_cache_dir=None, bool_use_cache=True, fn_download=...) -> pd.DataFrame`

Lê a lista de participantes do STR, publicada em CSV e atualizada diariamente pelo BCB
(`https://www.bcb.gov.br/content/estabilidadefinanceira/str1/ParticipantesSTR.csv`). A fonte
substitui o PDF legado `CODCOMPE/Tabela.pdf`, congelado em 2009 e sem ISPB; por isso não há
dependência de leitor de PDF.

!!! note "Cobertura"
    O quadro lista apenas os participantes do STR, diretos ou indiretos, e não todos os bancos
    do Brasil. Instituições que participam somente do PIX não aparecem.

!!! warning "Quebra de paridade com o stpstone"
    As colunas diferem das do leitor do stpstone, baseado no PDF `CODCOMPE/Tabela.pdf`: o ISPB
    agora está disponível na fonte e o retrato de 2009 foi descartado.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `ispb` | `string` | ISPB com 8 dígitos (zeros à esquerda preservados) |
| `short_name` | `string` | Nome reduzido |
| `compe_code` | `string` | Código COMPE com 3 dígitos; `NA` quando a fonte informa `n/a` |
| `participates_in_compe` | `bool` | Participa da Compe |
| `main_access` | `string` | Acesso principal (`RSFN` ou `Internet`) |
| `full_name` | `string` | Nome extenso |
| `operation_start` | `date` | Início da operação |

O quadro traz ainda as colunas de proveniência (`url`, `updated_at`, `source_key`,
`package_version`, `ingestion_run_id`, `content_hash`). O arquivo é guardado em cache por dia
de referência: duas leituras no mesmo dia baixam uma vez.

---

## Módulo: `sgs`

Leitura de séries temporais do SGS (Sistema Gerenciador de Séries Temporais) do Banco Central.

### `read_sgs_series(int_code, *, dt_start, dt_end, path_cache_dir, fn_download=..., bool_use_cache=True) -> pd.DataFrame`

Devolve `data` (`date`) e `valor` (`Decimal`), mais as colunas de proveniência. Intervalos
maiores que 10 anos são divididos em janelas e concatenados. O valor é construído a partir do
texto da fonte, nunca de `float`.

### `read_sgs_metadata(int_code, *, dt_reference=None, path_cache_dir=None, bool_use_cache=True, fn_download=...) -> pd.DataFrame`

Devolve uma linha com os metadados da série, lidos do WebService do SGS (`getUltimoValorXML`):
`code` (inteiro), `name`, `periodicity` (letra da fonte, por exemplo `M`) e `unit`, mais as
colunas de proveniência. O serviço não informa a data de início da série, então ela não é devolvida. A `periodicity` é o código de letra da fonte, sem tradução. O resultado é
guardado em cache por dia; `dt_reference` (padrão: hoje) define a chave do cache.

---

## Módulo: `currency_codes`

Tabela de códigos de moeda da PTAX: código, símbolo, nome, país, tipo e data de exclusão.

### `read_currency_codes(*, dt_reference=None, path_cache_dir=None, bool_use_cache=True, fn_download=...) -> pd.DataFrame`

Lê a tabela de códigos de moeda da PTAX, publicada no arquivo diário
`https://www4.bcb.gov.br/Download/fechamento/M<aaaammdd>.csv` (CSV `;`-separado em Latin-1).
Quando a fonte responde 404 para o dia, tenta o dia útil anterior (até 5 vezes); sem nenhum,
levanta `FileNotFoundError`. Qualquer outra falha (5xx, timeout, erro de escrita) levanta
`OSError` em vez de recuar para um arquivo mais antigo.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `currency_code` | `string` | Código da moeda com 3 dígitos (zeros à esquerda preservados) |
| `name` | `string` | Nome da moeda |
| `symbol` | `string` | Símbolo (ISO 4217 quando existe) |
| `country_code` | `string` | Código do país |
| `country` | `string` | País |
| `currency_type` | `string` | Tipo de paridade (`A` ou `B`) |
| `exclusion_date` | `date` | Data de exclusão da PTAX; `NA` enquanto ativa |
| `is_active` | `bool` | `True` quando a data de exclusão está vazia |

Campos em branco na fonte (algumas linhas legadas) viram `NA`. O quadro traz ainda as colunas
de proveniência e o arquivo é guardado em cache por dia de referência.

---

## Módulo: `quote_bulletins`

Códigos de moeda aceitos pelo formulário de boletins de cotação do Banco Central.

### `read_quote_bulletin_codes(*, dt_reference=None, path_cache_dir=None, bool_use_cache=True, fn_download=...) -> pd.DataFrame`

Lê as opções do `<select name="ChkMoeda">` do formulário
`https://ptax.bcb.gov.br/ptax_internet/consultaBoletim.do`. Se o `<select>` sumir ou vier vazio
(mudança de marcação), levanta `ContractError` em vez de devolver um quadro vazio.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `code` | `string` | Valor da opção, o código que a consulta de boletim recebe |
| `name` | `string` | Rótulo da moeda, como a fonte o escreve |

O quadro traz ainda as colunas de proveniência (`url`, `updated_at`, `source_key`,
`package_version`, `ingestion_run_id`, `content_hash`). A página é guardada em cache por dia de
referência.

### `read_quote_bulletins(str_currency_code, *, dt_start, dt_end, dt_reference=None, path_cache_dir=None, bool_use_cache=True, fn_download=...) -> pd.DataFrame`

Lê os boletins de fechamento de uma moeda em um período. O formulário responde ao POST com uma
página cujo link de CSV é um GET que leva só o código da moeda (veja `read_quote_bulletin_codes`;
o dólar é `"61"`) e o período; o CSV é baixado direto por esse link. As taxas, escritas com vírgula
(`5,5834`), viram `Decimal` construído a partir do texto da fonte, nunca de `float`. Levanta
`ValueError` se `dt_start` for posterior a `dt_end` e `ContractError` se o CSV vier sem linhas ou
com uma linha malformada.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `date` | `date` | Dia do boletim |
| `currency_code` | `string` | Código da moeda na tabela de cotações da fonte (não é o código do formulário) |
| `currency_type` | `string` | Tipo da moeda (`A` ou `B`), como em `read_currency_codes` |
| `currency_symbol` | `string` | Símbolo da moeda, por exemplo `USD` |
| `buy_rate` | `Decimal` | Taxa de compra |
| `sell_rate` | `Decimal` | Taxa de venda |
| `buy_parity` | `Decimal` | Paridade de compra |
| `sell_parity` | `Decimal` | Paridade de venda |

O quadro traz ainda as colunas de proveniência. O arquivo é guardado em cache por dia de
referência (`dt_reference`, hoje por padrão), nunca por data dos dados: um período que termina hoje
é baixado de novo amanhã.

---

## Módulo: `focus`

Expectativas anuais de mercado da pesquisa Focus (serviço Olinda `Expectativas`, entidade
`ExpectativasMercadoAnuais`).

### `read_focus_annual_expectations(str_indicator, *, dt_start, dt_end, dt_reference=None, path_cache_dir=None, bool_use_cache=True, fn_download=...) -> pd.DataFrame`

Filtra por `Indicador` (por exemplo `"IPCA"`) e pelo intervalo de `Data`, paginando pelo cliente
Olinda. Devolve `Indicador`, `IndicadorDetalhe`, `Data` (`date`), `DataReferencia` (texto),
`Media`, `Mediana`, `DesvioPadrao`, `Minimo`, `Maximo` (todos `Decimal`, construídos a partir do
texto da fonte, nunca de `float`), `numeroRespondentes` (`int`) e `baseCalculo`, mais as colunas de
proveniência. Cada linha é uma observação da fonte, sem agregação: o mesmo dia e o mesmo ano de
referência podem aparecer mais de uma vez, distinguidos por `IndicadorDetalhe` e `baseCalculo`
(a janela de respostas usada nas estatísticas). Levanta `ValueError` se `dt_start` for posterior
a `dt_end`. As páginas são guardadas em cache por dia de referência.

---

## Módulo: `ptax`

Cotações PTAX do serviço Olinda `PTAX` do Banco Central.

### `read_ptax_currencies(*, dt_reference=None, path_cache_dir=None, bool_use_cache=True, fn_download=...) -> pd.DataFrame`

Lê a lista de moedas cotadas pela PTAX, via o recurso `Moedas` do serviço Olinda `PTAX`.
Uma lista vazia levanta `ContractError` em vez de devolver um quadro vazio.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `symbol` | `str` | Símbolo da moeda (por exemplo `EUR`) |
| `name` | `str` | Nome da moeda, como a fonte o escreve |
| `currency_type` | `str` | Tipo da moeda na PTAX, `A` ou `B` |

O quadro traz ainda as colunas de proveniência. As páginas são guardadas em cache por dia de
referência (`dt_reference`, hoje por padrão).

### `read_ptax_usd_brl(*, dt_start, dt_end, dt_reference=None, path_cache_dir=None, bool_use_cache=True, fn_download=...) -> pd.DataFrame`

Lê as cotações de compra e venda do dólar (PTAX) em um período, via
`CotacaoDolarPeriodo(dataInicial=, dataFinalCotacao=)` (datas enviadas como `MM-DD-AAAA`).
Se `dt_start` for posterior a `dt_end`, levanta `ValueError`; um período sem cotações levanta
`ContractError` em vez de devolver um quadro vazio.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `buy_rate` | `Decimal` | Cotação de compra, construída a partir do texto da fonte |
| `sell_rate` | `Decimal` | Cotação de venda, construída a partir do texto da fonte |
| `quoted_at` | `datetime64` | Data e hora do boletim, com horário e microssegundos |

Cada data traz uma linha, a cotação de fechamento, sem campo de tipo de boletim. O quadro traz
ainda as colunas de proveniência (`url`, `updated_at`, `source_key`, `package_version`,
`ingestion_run_id`, `content_hash`). As páginas são guardadas em cache por dia de referência
(`dt_reference`, hoje por padrão): duas leituras no mesmo dia baixam uma vez, e um período que
termina hoje é baixado de novo amanhã, já com as cotações publicadas depois.

### `read_ptax_quotes(str_currency, *, dt_start, dt_end, dt_reference=None, path_cache_dir=None, bool_use_cache=True, fn_download=...) -> pd.DataFrame`

Lê as cotações PTAX de uma moeda em um período, incluindo os boletins intradiários, via
`CotacaoMoedaPeriodo(moeda=, dataInicial=, dataFinalCotacao=)`. `str_currency` é o símbolo da
moeda (por exemplo `EUR`, veja `read_ptax_currencies`); as datas vão como `MM-DD-AAAA`. Se
`dt_start` for posterior a `dt_end`, levanta `ValueError`; um período sem cotações levanta
`ContractError` em vez de devolver um quadro vazio.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `buy_parity` | `Decimal` | Paridade de compra, construída a partir do texto da fonte |
| `sell_parity` | `Decimal` | Paridade de venda, construída a partir do texto da fonte |
| `buy_rate` | `Decimal` | Cotação de compra, construída a partir do texto da fonte |
| `sell_rate` | `Decimal` | Cotação de venda, construída a partir do texto da fonte |
| `quoted_at` | `datetime64` | Data e hora do boletim, com horário e microssegundos |
| `bulletin_type` | `str` | Tipo do boletim: `Abertura`, `Intermediário` ou `Fechamento` |

Os boletins não são filtrados: cada data traz várias linhas, e `bulletin_type` serve para
escolher uma delas. O quadro traz ainda as colunas de proveniência. As páginas são guardadas
em cache por dia de referência (`dt_reference`, hoje por padrão), nunca por `dt_end`.
