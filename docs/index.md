# **opendata-bcb** <img src="assets/logo.png" align="right" width="200" style="border-radius: 15px;" alt="opendata-bcb">

Uma biblioteca Python mínima, com empacotamento, testes, CI e lint já configurados.

Este pacote não é oficial nem afiliado ao Banco Central do Brasil; ele apenas consome dados que o BCB publica abertamente. Foto do logo: sede do BCB em Brasília, por [Matheus Natan](https://www.pexels.com/@matheusnatan/) no Pexels.

---

## Conteúdo

| Seção | Descrição |
|-------|-----------|
| [Uso](usage.md) | Instalação, importações e exemplos de uso |
| [Referência da API](api/index.md) | Funções dos módulos e interface pública |

---

## Início rápido

```bash
bash bin/venv.sh   # cria o venv (o poe vive dentro dele, então o bootstrap é em shell)
poetry run poe unit_tests    # roda a suíte de testes
poetry run poe docs_serve   # serve esta documentação em http://0.0.0.0:8000
```

---

Gerado a partir do template **lib-minimal** via [BlueprintX](https://github.com/guilhermegor/BlueprintX).
