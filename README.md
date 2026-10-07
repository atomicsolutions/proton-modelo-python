# Projeto modelo Python

Automação de exemplo na loja de testes [Swag Labs](https://www.saucedemo.com): login,
carrinho e compra, e o login recusado de um usuário bloqueado. Serve de ponto de partida
para projetos novos de QA e de RPA.

O mesmo código roda de três jeitos:

- **pelo pytest**, a partir dos cenários da pasta `cenarios/`;
- **como robô**, sem pytest: `uv run python -m automacao`;
- **pelo [Proton](https://protoncloud.com.br)**, que dispara os mesmos componentes a partir
  de um dataset e guarda log, prints, saídas e resultado de cada execução.

O Proton é opcional. Só um arquivo do projeto conhece o Proton:
`tests/test_proton_script.py`. Apague esse arquivo e a dependência `protoncloud-sdk`, e o
resto continua igual. A automação é sua, com ou sem a ferramenta.

## Rodar localmente

Pré-requisitos: Python 3.10 ou mais novo e o [uv](https://docs.astral.sh/uv/).

```bash
uv sync
cp .env.example .env
uv run pytest
```

Na primeira execução, a automação instala o Chromium da Playwright. Para usar o Chrome ou
o Edge da máquina, sem download, ponha `CANAL_DO_NAVEGADOR=chrome` (ou `msedge`) no
`.env`. Para ver o navegador trabalhando, `HEADLESS=false`.

Outros jeitos de rodar:

```bash
uv run pytest -k compra                                     # um cenário
uv run python -m automacao cenarios/compra-com-sucesso.json # como robô, sem pytest
```

Os prints ficam na pasta `evidencias/`.

## Estrutura

```
automacao/
  componentes/   um arquivo por componente: executar(parametros) -> dict | None
  paginas/       as telas da loja: seletores e ações (page objects)
  apoio/         configuração, navegador, prints e a execução dos cenários
cenarios/        os cenários em JSON, no mesmo formato de um dataset do Proton
tests/
  test_cenarios.py       roda os cenários, sem o Proton
  test_proton_script.py  o ponto de entrada do Proton (o único que importa a SDK)
```

Quem escreve a automação mexe em `componentes/`, `paginas/` e `cenarios/`. A pasta
`apoio/` raramente muda.

## Criar um componente

Um componente é um passo da automação, com o mesmo nome no Proton e nos cenários. O
arquivo tem o nome do componente em minúsculas, com `_` entre as palavras: o componente
`ConsultarPedido` fica em `automacao/componentes/consultar_pedido.py`.

```python
"""ConsultarPedido: abre o pedido e devolve o status."""

from automacao.paginas.pedidos import PaginaDePedidos


def executar(parametros: dict) -> dict:
    status = PaginaDePedidos().abrir(parametros["in_pedido"]).status()

    if status == "Cancelado":
        raise AssertionError(f"O pedido {parametros['in_pedido']} está cancelado")

    return {"out_status": status}
```

As regras:

- os parâmetros chegam num `dict`, com o prefixo `in_`;
- as saídas voltam num `dict`, com o prefixo `out_` (ou `None`, sem saída);
- para falhar, lance uma exceção. O print da tela da falha é automático;
- seletores e ações ficam nas páginas (`automacao/paginas`), não no componente;
- nada em `automacao/` importa o Proton.

## Cenários

Cada arquivo da pasta `cenarios/` é um cenário: os passos em ordem, com o componente e os
parâmetros, como um dataset do Proton.

```json
{
  "descricao": "Compra com sucesso",
  "passos": [
    {"componente": "FazerLogin", "parametros": {"in_usuario": "standard_user", "in_senha": "${env:SENHA_DA_LOJA}"}},
    {"componente": "AdicionarAoCarrinho", "parametros": {"in_produto": "Sauce Labs Backpack"}},
    {"componente": "FinalizarCompra", "parametros": {"in_nome": "Ana", "in_sobrenome": "Souza", "in_cep": "01310-100", "in_preco_esperado": "${out_preco}"}}
  ]
}
```

- `${out_preco}` usa a saída de um passo anterior, como a referência a saída no Proton.
- `${env:SENHA_DA_LOJA}` lê o valor do ambiente ou do `.env`. Senha não vai para o git; no
  Proton, o equivalente é o parâmetro criptografado.

## Rodar pelo Proton

1. **Sistema.** Cadastre um sistema e ligue-o a este repositório. O runner reconhece o
   projeto Python pelo `pytest.ini` na raiz.
2. **Componentes.** Um componente no Proton para cada arquivo de `componentes/`, com o
   mesmo nome (`FazerLogin` para `fazer_login.py`) e os parâmetros `in_` e `out_`.
3. **Automação e dataset.** Os passos do dataset são os componentes, em ordem, com os
   valores dos parâmetros. A saída de um passo vira entrada de outro pela referência a
   saída.
4. **Execução.** O runner roda
   `uv run pytest tests/test_proton_script.py::test_run_proton_execution --id_dataset_run=<id>`
   e entrega no ambiente o endereço do Proton e um token que vale só para aquela
   execução. O projeto não guarda token nem endereço do Proton.

A cada passo, a [Proton Cloud SDK](https://pypi.org/project/protoncloud-sdk/) marca início
e fim, passa ao componente só os parâmetros dele, grava as saídas, sobe os prints que
apareceram na pasta `evidencias/` e manda o log ao vivo. No fim, grava o resultado; quando
um passo falha, grava também o erro com o stack trace.

A máquina do runner precisa de Python e do uv. O Chromium é instalado na primeira execução.

## Com IA

O `AGENTS.md` traz as regras do projeto para agentes de IA (Claude Code, Codex, Cursor e
outros). Com o conector MCP do Proton, o agente cadastra no Proton os componentes que
criar aqui.

## Licença

[MIT](LICENSE).
