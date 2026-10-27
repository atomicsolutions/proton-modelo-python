# Projeto modelo Python

Automação de exemplo com várias plataformas no mesmo cenário: consulta um CEP numa API
pública ([ViaCEP](https://viacep.com.br)), faz uma compra na loja de testes
[Swag Labs](https://www.saucedemo.com), põe o mesmo produto no carrinho de um app Android e
calcula a parcela na Calculadora do Windows. Traz
também o logon no SAP GUI, como ponto de partida para quem automatiza SAP. Serve de base
para projetos novos de QA e de RPA.

Duas demonstrações de RPA completam o modelo: o **cadastro em lote pela planilha** (baixa
o Excel do [RPA Challenge](https://rpachallenge.com) e preenche cada linha num formulário
que muda os campos de lugar a cada envio) e o **contrato em dólar** (converte o valor
pela cotação oficial no [Conversor de Moedas do Banco Central](https://www.bcb.gov.br/conversao)).
As duas são só web: rodam em qualquer runner, em paralelo.

| Plataforma | Biblioteca | Pasta |
|---|---|---|
| Web | [Playwright](https://playwright.dev/python/) | `automacao/web` |
| API | [requests](https://requests.readthedocs.io) | `automacao/api` |
| Mobile (Android) | [Appium](https://appium.io) (Appium-Python-Client) | `automacao/mobile` |
| SAP GUI | SAP GUI Scripting com [pywin32](https://github.com/mhammond/pywin32) | `automacao/sap` |
| Desktop (Windows) | [pywinauto](https://pywinauto.readthedocs.io) | `automacao/desktop` |
| Excel (.xlsx) | [openpyxl](https://openpyxl.readthedocs.io), sem o Excel instalado | `automacao/arquivos` |

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
o `compra-parcelada` abre a Calculadora e só roda no Windows (com execuções em paralelo, cada
uma espera a vez dela na Calculadora, que tem uma janela só por máquina); o `login-sap` precisa do SAP
GUI e de `SAP_CONEXAO`, `SAP_USUARIO` e `SAP_SENHA` no `.env`.

As evidências (prints e respostas de API) ficam na pasta `evidencias/`. Numa execução do
Proton, cada execução grava em `evidencias/<id da execução>`.

## Estrutura

```
automacao/
  componentes/   um arquivo por componente, de qualquer plataforma
  web/           sessão do navegador e páginas (page objects) da loja, do RPA Challenge e do Banco Central
  api/           sessão HTTP e clientes das APIs
  mobile/        sessão do aparelho (Appium) e telas do app
  sap/           sessão do SAP GUI e telas das transações
  desktop/       sessão dos aplicativos do Windows e janelas de cada um
  arquivos/      leitura de planilhas do Excel, sem sessão
  apoio/         configuração, sessões, evidências, falhas e a execução dos cenários
cenarios/        os cenários em JSON, no mesmo formato de um dataset do Proton
tests/
  test_cenarios.py       roda os cenários, sem o Proton
  test_sap.py            as ajudas do SAP, com objetos falsos (roda sem SAP)
  test_proton_script.py  o ponto de entrada do Proton (o único que importa a SDK)
```

Quem escreve a automação mexe em `componentes/`, nas pastas das plataformas e em
`cenarios/`. A pasta `apoio/` raramente muda. Use só as plataformas de que precisar e
apague as outras pastas.

## Sessões

Cada plataforma tem uma sessão: o navegador, o cliente HTTP, o aparelho, a conexão SAP, os
aplicativos abertos. A sessão abre na primeira vez que um passo pede e serve aos passos seguintes do
mesmo cenário, mesmo quando eles são de outra plataforma. No fim do cenário, todas fecham,
na ordem inversa, mesmo com erro. Um cenário só de API nem abre navegador. No Proton, quem
fecha é a SDK, antes de gravar o resultado: o que sai do fechamento (um vídeo, o último
print) ainda sobe para a execução.

A sessão que não abre (o navegador, o aparelho, o SAP, o aplicativo) e a API que não
responde depois das novas tentativas são falha de ambiente: veja [Motivo da
falha](#motivo-da-falha).

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
- para falhar, lance uma exceção. A evidência da falha é automática. Quando a regra de
  negócio recusa, lance `FalhaDeNegocio` (veja [Motivo da falha](#motivo-da-falha));
- seletores, ids de tela e chamadas ficam nas páginas, telas e clientes, não no componente;
- nada em `automacao/` importa o Proton.

## Motivo da falha

O Proton separa três motivos de falha. A execução termina em **Failed** nos três, e o motivo
aparece à parte, para separar o que é do robô do que não é:

| Motivo | Quando | No código |
|---|---|---|
| Negócio | A regra não deixou seguir, e repetir dá o mesmo resultado: a loja recusou os dados, o material não existe no SAP. | `FalhaDeNegocio` |
| Ambiente | O ambiente não deixou rodar: a sessão que não abre, a API fora do ar. | `FalhaDeAmbiente`, com o erro original como causa |
| Técnica | Qualquer outro erro: o elemento que não apareceu, o valor que não bateu, o erro do código. | qualquer outra exceção |

```python
from automacao.apoio.falhas import FalhaDeNegocio

if saldo < valor:
    raise FalhaDeNegocio(f"Saldo {saldo} menor que o valor {valor}")
```

As duas classes ficam em `automacao/apoio/falhas.py` e não importam o Proton: a SDK lê o
motivo pelo atributo `failure_reason`, na exceção e nas causas dela (`raise ... from erro`).
A sessão que não abre já vira `FalhaDeAmbiente` sozinha. Fora do Proton, são exceções
comuns.

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
- `falha_esperada` marca o cenário que falha de propósito, com um trecho da mensagem do erro.

O `compra-com-falha-proposital` falha de propósito: o usuário `problem_user` da loja tem um
defeito conhecido no checkout (o sobrenome vai para o campo do nome) e a compra para em
"Error: Last Name is required". Fora do Proton ele conta como falha esperada (`xfail` no
pytest), e a suíte segue verde. No Proton, o mesmo dataset termina em **Failed**, com o
log, o print da tela, o erro do passo e o motivo **negócio** (a recusa da loja é
`FalhaDeNegocio`): serve para conhecer uma execução que falhou e o diagnóstico da falha.

As duas demonstrações de RPA:

- `cadastro-em-lote-pela-planilha`: `LerPlanilhaDeCadastros` baixa a planilha (que vira
  evidência do passo) e devolve o caminho dela em `out_planilha` (a saída de um passo é um
  texto curto, e a planilha pode ter milhares de linhas); `PreencherCadastros` lê a planilha e
  preenche cada linha no formulário, achando os campos pelo rótulo, e confere os 100% de acerto.
  `in_pausa_ms` espera entre um cadastro e outro, para uma apresentação.
- `contrato-em-dolar`: `ConverterMoeda` converte `in_valor` em `in_moeda` para reais pela
  cotação do dia útil e confere a conta (valor vezes cotação) antes de devolver o valor em
  reais, a cotação e a data dela.

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

1. Cadastre o app como um sistema de plataforma **Mobile** e o APK em **Aplicativos Mobile**,
   ligado a esse sistema. A automação não tem mais a marcação mobile: o que ela pede no
   disparo sai dos sistemas dos componentes.
2. Ao disparar, escolha o aparelho (os que o runner encontra) e o app de cada sistema mobile,
   ou deixe o aparelho padrão do sistema.
3. Antes de cada passo, o ponto de entrada do Proton pede à SDK o aparelho e o app do sistema
   do passo (`get_current_component_device()`), baixa o app e os entrega à sessão mobile. O código do componente não
   muda.

Uma execução pode ter mais de um sistema mobile (o app do cliente e o app do entregador, por
exemplo), cada um com o seu aparelho. A sessão mobile é uma por sistema (`mobile:<id do
sistema>`): o passo de um app usa o aparelho dele, e o passo seguinte do outro app abre o
outro aparelho. Cada aparelho local tem o seu `systemPort` no UiAutomator2, para os dois não
disputarem a mesma porta. Com um sistema mobile só, nada muda.

## SAP

O componente SAP usa as ajudas de `automacao/sap/sessao.py`, em vez de repetir o SAP GUI
Scripting em cada tela:

| Ajuda | O que faz |
|---|---|
| `barra_de_status()` | O tipo (`TipoDeMensagem`: sucesso, aviso, erro, aborto, informação) e o texto da barra de status. |
| `confirmar_avisos()` | Aperta Enter enquanto a barra mostra aviso, até um número máximo de vezes. |
| `conferir_sem_erro()` | Lança `FalhaDeNegocio` com o texto da barra quando ela mostra erro (E ou A). |
| `ler_celula`, `escrever_celula` | A célula de uma tabela (GuiTableControl), pelo título da coluna. |
| `primeira_linha_vazia` | A primeira linha visível com a coluna vazia, onde entra o próximo item. |
| `existe`, `id_pelo_texto`, `id_da_aba` | Se o elemento está na tela; o id pelo texto visível; o id da aba pelo nome. |
| `subtela` | O nome da subtela que começa com um prefixo, porque o número do fim muda conforme a tela. |
| `tabela_da_tela()` | Os textos de uma tela de relatório (lista), linha a linha. |
| `print_da_tela(nome)` | O print da janela ativa, na pasta de evidências. |

```python
from automacao.sap import sessao as sap

sap.sessao().findById("wnd[0]/tbar[0]/btn[11]").press()  # Gravar
sap.confirmar_avisos()
sap.conferir_sem_erro()  # "Material não existe" vira falha de negócio
```

O modelo não mata o `saplogon.exe`: o runner pode rodar várias execuções ao mesmo tempo na
mesma máquina, e isso derrubaria o SAP de todas. A sessão fecha só a conexão dela.

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
5. **Navegador na tela.** O runner não tem o `.env`, então o navegador abre oculto. Para
   ver a automação trabalhando (numa apresentação, por exemplo), cadastre no Proton um
   ambiente com a variável `HEADLESS` igual a `false` e use-o no dataset ou no disparo.
   `CANAL_DO_NAVEGADOR` (`chrome` ou `msedge`) também vale pelo ambiente.

A [Proton Cloud SDK](https://pypi.org/project/protoncloud-sdk/) roda os passos em ordem,
no mesmo processo, enquanto este projeto tiver o componente: as sessões abertas valem para
a execução inteira, de uma plataforma para a outra. A cada passo, marca início e fim,
passa ao componente só os parâmetros dele, grava as saídas, sobe as evidências e manda o
log ao vivo. Cada execução grava as evidências em `evidencias/<id da execução>`, e a SDK
sobe só as dela, mesmo com outras rodando ao mesmo tempo na mesma pasta. No fim, a SDK
fecha as sessões, sobe o que saiu do fechamento e grava o resultado; quando um passo falha,
grava também o erro com o stack trace e o motivo da falha. Um passo cujo componente fica em
outro repositório volta para o runner, que chama o projeto daquele sistema.

A máquina do runner precisa de Python e do uv. Para mobile, do adb e do Appium. Para
desktop e SAP, precisa ser Windows,
com a sessão do usuário aberta, e, para SAP, com o SAP GUI e o scripting habilitado.

## Com IA

O `AGENTS.md` traz as regras do projeto para agentes de IA (Claude Code, Codex, Cursor e
outros). Com o conector MCP do Proton, o agente cadastra no Proton os componentes que
criar aqui, e o caminho é este:

1. `get_project_template`: de onde vem este modelo e as regras do contrato.
2. `generate_component_code`: o arquivo de um componente já cadastrado, no formato daqui.
3. `check_project`, depois de cada push: confere o repositório contra o cadastro.
4. `check_automation`, antes da primeira execução: confere os datasets.

## Licença

[MIT](LICENSE).
