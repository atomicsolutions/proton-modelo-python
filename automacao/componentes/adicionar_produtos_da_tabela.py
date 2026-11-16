"""
AdicionarProdutosDaTabela: põe no carrinho cada produto da aba `in_aba` da tabela de dados
(padrão `produtos`) e grava o resultado na mesma linha.

A aba tem a coluna `produto` e as colunas que o passo preenche: `status` (`no carrinho` ou
`erro`), `preco` e `mensagem`. O passo cria a coluna `processado_em` quando ela não existe
e, no fim, inclui uma linha de total. Linha com `status` preenchido fica de fora: é o
resultado de uma execução anterior (levado de volta para o dataset) ou a linha de total.

Um produto que não entra no carrinho marca a linha com erro, e as outras seguem. Só falha o
passo quando nenhum produto entra, ou quando a própria tabela recusa a escrita.

A tabela de dados vem da Proton Cloud SDK (`proton.proton_table`). Numa execução do Proton,
cada execução lê e grava a cópia dela; fora do Proton, a tabela vem do arquivo de
`PROTON_TABLE_FILE` (o `"tabela"` do cenário), e as escritas ficam só na memória.
"""

import logging
from datetime import datetime
from decimal import Decimal

from proton.proton_table import ProtonTableError, get_proton_table

from automacao.apoio import evidencias
from automacao.apoio.falhas import FalhaDeNegocio
from automacao.web import sessao as web
from automacao.web.produtos import PaginaDeProdutos

log = logging.getLogger(__name__)


def executar(parametros: dict) -> dict:
    produtos = get_proton_table(parametros.get("in_aba") or "produtos")

    if "processado_em" not in [coluna.lower() for coluna in produtos.columns]:
        produtos.add_column("processado_em")

    loja = PaginaDeProdutos()
    pendentes = [linha for linha in produtos if linha["produto"].strip() and not linha.get("status", "").strip()]
    no_carrinho, com_erro, total = 0, 0, Decimal("0")

    for linha in pendentes:
        produto = linha["produto"].strip()

        try:
            if not loja.tem_produto(produto):
                raise FalhaDeNegocio(f"O produto {produto} não existe na loja")
            preco = loja.adicionar_ao_carrinho(produto)
        except ProtonTableError:
            raise  # a tabela recusou: coluna errada, execução terminada. Não adianta seguir.
        except Exception as erro:
            com_erro += 1
            log.warning("%s: %s", produto, erro)
            produtos.set(linha, "status", "erro")
            produtos.set(linha, "mensagem", str(erro).splitlines()[0][:500])
        else:
            no_carrinho += 1
            total += Decimal(preco)
            log.info("%s no carrinho, por %s", produto, preco)
            produtos.set(linha, "status", "no carrinho")
            produtos.set(linha, "preco", preco)
            produtos.set(linha, "mensagem", "")

        produtos.set(linha, "processado_em", f"{datetime.now():%Y-%m-%d %H:%M:%S}")

    web.print_da_tela("produtos-da-tabela-no-carrinho")
    produtos.add_row({
        "produto": "Total",
        "status": f"{no_carrinho} de {len(pendentes)} no carrinho",
        "preco": f"{total:.2f}",
        "processado_em": f"{datetime.now():%Y-%m-%d %H:%M:%S}",
    })

    # A aba como ficou, em JSON, também como evidência: fora do Proton, as escritas ficam só
    # na memória, e é por ela que se confere o que o passo gravou.
    resultado = evidencias.arquivo(f"tabela-{produtos.name}", "json")
    resultado.write_text(produtos.to_json(), encoding="utf-8")
    evidencias.registrar(resultado)

    if not no_carrinho:
        raise FalhaDeNegocio(f"Nenhum dos {len(pendentes)} produtos da aba {produtos.name} entrou no carrinho")

    return {
        "out_total_dos_itens": f"{total:.2f}",
        "out_no_carrinho": str(no_carrinho),
        "out_com_erro": str(com_erro),
    }
