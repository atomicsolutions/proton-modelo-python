# Regras do projeto para agentes de IA

Projeto de automação em Python com Playwright. Roda pelo pytest, como robô
(`python -m automacao`) ou pelo Proton. Responda e escreva em português do Brasil.

## Onde fica cada coisa

- `automacao/componentes/`: um arquivo por componente, com `executar(parametros: dict) -> dict | None`.
- `automacao/paginas/`: page objects. Seletores e ações de tela ficam só aqui.
- `automacao/apoio/`: configuração, navegador, prints e execução dos cenários. Mude só se a tarefa pedir.
- `cenarios/`: cenários em JSON, no formato de um dataset do Proton.
- `tests/test_proton_script.py`: ponto de entrada do Proton. Não mude o caminho nem o nome do teste (`test_run_proton_execution`): o runner chama exatamente esse.

## Contrato do componente

- O nome do componente é o mesmo no Proton e nos cenários, em PascalCase (`FinalizarCompra`).
  O arquivo é o nome em snake_case (`finalizar_compra.py`).
- Parâmetros de entrada com prefixo `in_`, saídas com `out_`, em snake_case e minúsculas.
- Todo valor de parâmetro e de saída é texto (`str`).
- Para falhar, lance uma exceção com uma mensagem que diga o que se esperava e o que veio.
  Nunca só registre o erro no log e siga: o passo precisa falhar.
- Nada em `automacao/` importa o pacote `proton`. A integração com o Proton é só o
  `tests/test_proton_script.py`.
- Log com `logging.getLogger(__name__)`, sem `print`.
- Prints de tela com `evidencias.print_da_tela("nome")`. O print da falha é automático.

## Ao criar ou mudar um componente

1. Escreva as ações de tela na página (`automacao/paginas/`), reaproveitando as que existem.
2. Escreva o componente em `automacao/componentes/`.
3. Use-o num cenário de `cenarios/` e rode `uv run pytest -k <cenario>` até passar.
4. Se houver conector MCP do Proton, cadastre ou atualize o componente no sistema ligado a
   este repositório, com o mesmo nome e os mesmos parâmetros, e documente objetivo e
   resultado esperado.

## Segredos

Nunca escreva senha, token ou chave em código, cenário ou commit. Nos cenários, use
`${env:NOME}` e documente a variável no `.env.example`. No Proton, use parâmetro
criptografado.

## Comandos

- `uv sync`: instala as dependências.
- `uv run pytest`: roda todos os cenários.
- `uv run pytest -k compra`: roda um cenário.
- `uv run python -m automacao cenarios/<arquivo>.json`: roda um cenário sem pytest.
