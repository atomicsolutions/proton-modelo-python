# Regras do projeto para agentes de IA

Projeto de automação em Python com várias plataformas no mesmo cenário: web (Playwright),
API (requests), mobile Android (Appium), SAP GUI (SAP GUI Scripting com pywin32) e desktop
Windows (pywinauto). Roda pelo pytest, como robô (`python -m automacao`) ou pelo Proton.
Responda e escreva em português do Brasil.

## Onde fica cada coisa

- `automacao/componentes/`: um arquivo por componente, de qualquer plataforma, com
  `executar(parametros: dict) -> dict | None`.
- `automacao/web/`, `api/`, `mobile/`, `sap/`, `desktop/`: uma pasta por plataforma, com a sessão
  (`sessao.py`) e as páginas, clientes, telas e janelas. Seletores, ids de tela do SAP,
  AutomationId e endereços de API ficam só aqui.
- `automacao/arquivos/`: leitura de arquivos sem sessão (planilha do Excel com a openpyxl,
  `excel.ler_registros`). O arquivo que o passo usa ou gera vai para a pasta de evidências
  (`evidencias.arquivo` e `evidencias.registrar`), para aparecer no passo do Proton.
- `automacao/apoio/`: configuração, sessões, evidências, falhas e execução dos cenários. Mude só se a tarefa pedir.
- `cenarios/`: cenários em JSON, no formato de um dataset do Proton. O que tem
  `falha_esperada` falha de propósito (o `compra-com-falha-proposital`): não o conserte.
- `tests/test_proton_script.py`: ponto de entrada do Proton. Não mude o caminho nem o nome
  do teste (`test_run_proton_execution`): o runner chama exatamente esse.
- `tests/test_sap.py`: as ajudas do SAP com objetos falsos, sem SAP na máquina.

## Contrato do componente

- O nome do componente é o mesmo no Proton e nos cenários, em PascalCase (`FinalizarCompra`).
  O arquivo é o nome em snake_case (`finalizar_compra.py`).
- Parâmetros de entrada com prefixo `in_`, saídas com `out_`, em snake_case e minúsculas.
- Todo valor de parâmetro e de saída é texto (`str`).
- Para falhar, lance uma exceção com uma mensagem que diga o que se esperava e o que veio.
  Nunca só registre o erro no log e siga: o passo precisa falhar.
- O motivo da falha vem da exceção (`automacao/apoio/falhas.py`): `FalhaDeNegocio` quando
  a regra de negócio recusa (a loja recusou os dados, o SAP diz que o material não existe);
  `FalhaDeAmbiente`, com o erro original como causa (`raise ... from erro`), quando o
  ambiente não deixa rodar. A sessão que não abre já vira `FalhaDeAmbiente` sozinha.
  Qualquer outra exceção é falha técnica: não embrulhe erro do robô como negócio.
- Dados passam de um passo para outro só pelas saídas e entradas, nunca por variável global.
- O componente não abre nem fecha sessão: usa as páginas, telas e clientes, que pedem a
  sessão da plataforma deles. As sessões abrem na primeira vez e fecham no fim do cenário
  (no Proton, a SDK as fecha antes de gravar o status).
- Nada em `automacao/` importa o pacote `proton`. A integração com o Proton é só o
  `tests/test_proton_script.py`.
- Log com `logging.getLogger(__name__)`, sem `print`.
- Evidência com `print_da_tela("nome")` da sessão da plataforma (`web`, `mobile`, `sap`, `desktop`)
  ou `api.sessao.evidencia("nome")`. A evidência da falha é automática. Tudo vai para a pasta
  de evidências; no Proton, ela é `evidencias/<id da execução>`, e a SDK sobe o que aparece.

## SAP

O componente SAP usa as ajudas de `automacao/sap/sessao.py`, em vez de repetir o SAP GUI Scripting:

- barra de status: `barra_de_status()` (com o tipo em `TipoDeMensagem`), `confirmar_avisos()`
  e `conferir_sem_erro()`. Depois de gravar ou de avançar, chame `conferir_sem_erro()`: o
  erro na barra (E ou A) vira `FalhaDeNegocio`, com o texto do SAP;
- tabela (GuiTableControl), pelo título da coluna: `ler_celula`, `escrever_celula` e
  `primeira_linha_vazia`;
- elementos: `existe`, `id_pelo_texto`, `id_da_aba` e `subtela` (o número da subtela muda
  conforme a tela);
- tela de relatório (lista): `tabela_da_tela()`;
- evidência: `print_da_tela("nome")`.

Capture o erro do COM (`pywintypes.com_error`), nunca com `except:` nu. Não mate o
`saplogon.exe` (`taskkill`): o runner pode rodar várias execuções ao mesmo tempo na mesma
máquina, e isso derruba o SAP de todas. A sessão fecha só a conexão dela.

## Plataforma nova

Crie `automacao/<plataforma>/sessao.py` com uma classe que tenha `fechar()` e
`evidencia(nome)`, e uma função que peça a sessão com `sessoes.obter("<plataforma>", Classe)`.
Importe bibliotecas que só existem no Windows dentro da classe, não no topo do arquivo. Se
o cenário precisar de algo da máquina, declare em `"requer"`.

## Ao criar ou mudar um componente

1. Escreva as ações na página, tela, cliente ou janela da plataforma, reaproveitando as que existem.
2. Escreva o componente em `automacao/componentes/`.
3. Use-o num cenário de `cenarios/` e rode `uv run pytest -k <cenario>` até passar.
4. Se houver conector MCP do Proton, cadastre ou atualize o componente no sistema da
   plataforma dele (ligado a este repositório), com o mesmo nome e os mesmos parâmetros,
   e documente objetivo e resultado esperado.

## Com o conector MCP do Proton

- `get_project_template`: de onde vem este modelo (repositório, branch, SDK mínima) e as
  regras do contrato. Comece por ele num projeto novo.
- `generate_component_code`: o arquivo de um componente já cadastrado no Proton, no formato
  daqui. Grave no caminho que ele devolve e escreva a lógica no lugar do TODO.
- `check_project`: depois de cada push, confere o repositório contra o cadastro (um arquivo
  por componente, parâmetros `in_` e `out_`, ponto de entrada, SDK). Corrija todo erro.
- `check_automation`: antes da primeira execução, confere os datasets (parâmetros com
  valor, referências, criptografados, runner no ar).

## Segredos

Nunca escreva senha, token ou chave em código, cenário ou commit. Nos cenários, use
`${env:NOME}` e documente a variável no `.env.example`. No Proton, use parâmetro
criptografado.

## Comandos

- `uv sync`: instala as dependências.
- `uv run pytest`: roda todos os cenários (os que a máquina não suporta são pulados).
- `uv run pytest -k <cenario>`: roda um cenário.
- `uv run python -m automacao cenarios/<arquivo>.json`: roda um cenário sem pytest.
