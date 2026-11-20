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

## Módulo: `ingestion.banks`

Cadastro de bancos do Banco Central: códigos COMPE e ISPB.

### `read_banks(*, dt_reference=None, path_cache_dir=None, bool_use_cache=True, fn_download=...) -> pd.DataFrame`

Lê a lista de participantes do STR, publicada em CSV e atualizada diariamente pelo BCB
(`https://www.bcb.gov.br/content/estabilidadefinanceira/str1/ParticipantesSTR.csv`). A fonte
substitui o PDF legado `CODCOMPE/Tabela.pdf`, congelado em 2009 e sem ISPB; por isso não há
dependência de leitor de PDF.

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

## Módulo: `ingestion.sgs`

Leitura de séries temporais do SGS (Sistema Gerenciador de Séries Temporais) do Banco Central.

### `read_sgs_series(int_code, *, dt_start, dt_end, path_cache_dir, fn_download=..., bool_use_cache=True) -> pd.DataFrame`

Devolve `data` (`date`) e `valor` (`Decimal`), mais as colunas de proveniência. Intervalos
maiores que 10 anos são divididos em janelas e concatenados. O valor é construído a partir do
texto da fonte, nunca de `float`.
