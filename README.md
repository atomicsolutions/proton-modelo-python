# Projeto modelo Python

Automação de exemplo com várias plataformas no mesmo cenário: consulta um CEP numa API
pública ([ViaCEP](https://viacep.com.br)), faz uma compra na loja de testes
[Swag Labs](https://www.saucedemo.com), põe o mesmo produto no carrinho de um app Android e
calcula a parcela na Calculadora do Windows. Traz
também o logon no SAP GUI, como ponto de partida para quem automatiza SAP. Serve de base
para projetos novos de QA e de RPA.

| Plataforma | Biblioteca | Pasta |
|---|---|---|
| Web | [Playwright](https://playwright.dev/python/) | `automacao/web` |
| API | [requests](https://requests.readthedocs.io) | `automacao/api` |
| Mobile (Android) | [Appium](https://appium.io) (Appium-Python-Client) | `automacao/mobile` |
| SAP GUI | SAP GUI Scripting com [pywin32](https://github.com/mhammond/pywin32) | `automacao/sap` |
| Desktop (Windows) | [pywinauto](https://pywinauto.readthedocs.io) | `automacao/desktop` |

O mesmo código roda de três jeitos:

- **pelo pytest**, a partir dos cenários da pasta `cenarios/`;
- **como robô**, sem pytest: `uv run python -m automacao`;
- **pelo [Proton](https://protoncloud.com.br)**, que dispara os mesmos componentes a partir
  de um dataset e guarda log, evidências, saídas e resultado de cada execução.

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

Um cenário só, pelo nome do arquivo, ou como robô:

```bash
uv run pytest -k compra-parcelada
uv run python -m automacao cenarios/compra-parcelada.json
```

Os cenários dizem o que precisam da máquina (`"requer"`) e são pulados quando ela não tem:
o `compra-parcelada` abre a Calculadora e só roda no Windows; o `login-sap` precisa do SAP
GUI e de `SAP_CONEXAO`, `SAP_USUARIO` e `SAP_SENHA` no `.env`.

As evidências (prints e respostas de API) ficam na pasta `evidencias/`.

## Estrutura

```
automacao/
  componentes/   um arquivo por componente, de qualquer plataforma
  web/           sessão do navegador e páginas da loja (page objects)
  api/           sessão HTTP e clientes das APIs
  mobile/        sessão do aparelho (Appium) e telas do app
  sap/           sessão do SAP GUI e telas das transações
  desktop/       sessão dos aplicativos do Windows e janelas de cada um
  apoio/         configuração, sessões, evidências e a execução dos cenários
cenarios/        os cenários em JSON, no mesmo formato de um dataset do Proton
tests/
  test_cenarios.py       roda os cenários, sem o Proton
  test_proton_script.py  o ponto de entrada do Proton (o único que importa a SDK)
```

Quem escreve a automação mexe em `componentes/`, nas pastas das plataformas e em
`cenarios/`. A pasta `apoio/` raramente muda. Use só as plataformas de que precisar e
apague as outras pastas.

## Sessões

Cada plataforma tem uma sessão: o navegador, o cliente HTTP, o aparelho, a conexão SAP, os
aplicativos abertos. A sessão abre na primeira vez que um passo pede e serve aos passos seguintes do
mesmo cenário, mesmo quando eles são de outra plataforma. No fim do cenário, todas fecham,
na ordem inversa, mesmo com erro. Um cenário só de API nem abre navegador.

Os componentes não lidam com sessão: usam as páginas e telas, que pedem a sessão da
plataforma delas (`web.sessao.pagina()`, `api.sessao.cliente()`, `mobile.sessao.driver()`,
`sap.sessao.sessao()`, `desktop.sessao.janela(...)`).

Quando um passo falha, cada sessão aberta grava a evidência dela: o print da página, da
janela do SAP ou do aplicativo, e a última resposta da API.

Para uma plataforma nova, crie a pasta dela com um `sessao.py` cuja classe tenha
`fechar()` e `evidencia(nome)`, e peça a sessão com `sessoes.obter("nome", Classe)`. Use as
pastas que existem como exemplo.

## Criar um componente

Um componente é um passo da automação, com o mesmo nome no Proton e nos cenários. O
arquivo tem o nome do componente em minúsculas, com `_` entre as palavras: o componente
`ConsultarPedido` fica em `automacao/componentes/consultar_pedido.py`.

```python
"""ConsultarPedido: abre o pedido no SAP e confere o status no portal."""

from automacao.sap.va03 import TelaDoPedido
from automacao.web.pedidos import PaginaDePedidos


def executar(parametros: dict) -> dict:
    status = TelaDoPedido().abrir(parametros["in_pedido"]).status()
    PaginaDePedidos().conferir_status(parametros["in_pedido"], status)
    return {"out_status": status}
```

As regras:

- os parâmetros chegam num `dict`, com o prefixo `in_`;
- as saídas voltam num `dict`, com o prefixo `out_` (ou `None`, sem saída);
- para falhar, lance uma exceção. A evidência da falha é automática;
- seletores, ids de tela e chamadas ficam nas páginas, telas e clientes, não no componente;
- nada em `automacao/` importa o Proton.

## Cenários

Cada arquivo da pasta `cenarios/` é um cenário: os passos em ordem, com o componente e os
parâmetros, como um dataset do Proton.

```json
{
  "descricao": "Compra parcelada",
  "requer": ["windows"],
  "passos": [
    {"componente": "ConsultarCep", "parametros": {"in_cep": "01310-100"}},
    {"componente": "FazerLogin", "parametros": {"in_usuario": "standard_user", "in_senha": "${env:SENHA_DA_LOJA}"}},
    {"componente": "AdicionarAoCarrinho", "parametros": {"in_produto": "Sauce Labs Backpack"}},
    {"componente": "FinalizarCompra", "parametros": {"in_nome": "Ana", "in_sobrenome": "Souza", "in_cep": "${out_cep}", "in_preco_esperado": "${out_preco}"}},
    {"componente": "CalcularParcela", "parametros": {"in_total": "${out_total}", "in_parcelas": "3"}}
  ]
}
```

- `${out_cep}` usa a saída de um passo anterior, como a referência a saída no Proton.
- `${env:SENHA_DA_LOJA}` lê o valor do ambiente ou do `.env`. Senha não vai para o git; no
  Proton, o equivalente é o parâmetro criptografado.
- `requer` lista o que o cenário precisa da máquina: `windows`, `sap` ou `android`.

## Mobile

O exemplo mobile usa o [My Demo App](https://github.com/saucelabs/my-demo-app-android), o app de
demonstração da Sauce Labs, com os mesmos produtos da loja web. Os cenários mobile pedem
`"requer": ["android"]` e são pulados quando não há aparelho conectado.

Pré-requisitos na máquina:

- Android SDK, com o `adb` no `PATH`;
- [Appium](https://appium.io) com o driver UiAutomator2: `npm install -g appium` e
  `appium driver install uiautomator2`;
- um aparelho Android com a depuração USB ligada (ou um emulador), visível no `adb devices`.

Para rodar o exemplo, baixe o APK da [página de releases do My Demo
App](https://github.com/saucelabs/my-demo-app-android/releases) e instale no aparelho
(`adb install mda-*.apk`), ou aponte `MOBILE_APP` para o arquivo no `.env`. Depois:

```bash
uv run pytest -k app
```

Se o Appium não estiver no ar no endereço de `APPIUM_URL`, a automação o inicia e o encerra
no fim do cenário. `MOBILE_DISPOSITIVO` escolhe o aparelho quando há mais de um conectado.

No Proton:

1. Marque a automação como mobile e cadastre o APK em **Aplicativos Mobile**.
2. Ao disparar, escolha o aparelho (os que o runner encontra) e o app.
3. O ponto de entrada do Proton lê da execução o aparelho e o app, baixa o app e o entrega à
   sessão mobile. O código do componente não muda.

## Rodar pelo Proton

1. **Sistemas.** Cadastre um sistema para cada plataforma (por exemplo, o portal, a API e
   o SAP) e ligue todos a este repositório. O runner reconhece o projeto Python pelo
   `pytest.ini` na raiz.
2. **Componentes.** Um componente no Proton para cada arquivo de `componentes/`, no sistema
   da plataforma dele, com o mesmo nome (`FazerLogin` para `fazer_login.py`) e os
   parâmetros `in_` e `out_`.
3. **Automação e dataset.** Os passos do dataset são os componentes, em ordem, com os
   valores dos parâmetros. A saída de um passo vira entrada de outro pela referência a
   saída.
4. **Execução.** O runner roda
   `uv run pytest tests/test_proton_script.py::test_run_proton_execution --id_dataset_run=<id>`
   e entrega no ambiente o endereço do Proton e um token que vale só para aquela
   execução. O projeto não guarda token nem endereço do Proton.

A [Proton Cloud SDK](https://pypi.org/project/protoncloud-sdk/) roda os passos em ordem,
no mesmo processo, enquanto este projeto tiver o componente: as sessões abertas valem para
a execução inteira, de uma plataforma para a outra. A cada passo, marca início e fim,
passa ao componente só os parâmetros dele, grava as saídas, sobe as evidências e manda o
log ao vivo. No fim, grava o resultado; quando um passo falha, grava também o erro com o
stack trace. Um passo cujo componente fica em outro repositório volta para o runner, que
chama o projeto daquele sistema.

A máquina do runner precisa de Python e do uv. Para mobile, do adb e do Appium. Para
desktop e SAP, precisa ser Windows,
com a sessão do usuário aberta, e, para SAP, com o SAP GUI e o scripting habilitado.

## Com IA

O `AGENTS.md` traz as regras do projeto para agentes de IA (Claude Code, Codex, Cursor e
outros). Com o conector MCP do Proton, o agente cadastra no Proton os componentes que
criar aqui.

## Licença

[MIT](LICENSE).
