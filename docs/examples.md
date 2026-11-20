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
