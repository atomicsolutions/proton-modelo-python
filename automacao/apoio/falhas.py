"""
O motivo da falha: de negócio, de ambiente ou técnica.

- `FalhaDeNegocio`: a regra de negócio não deixou seguir, e repetir dá o mesmo resultado
  (a loja recusou os dados de entrega, o material não existe no SAP).
- `FalhaDeAmbiente`: o ambiente não deixou rodar (o navegador, o aparelho, o SAP, o
  aplicativo ou a API que não abrem). Lance com o erro original como causa:
  `raise FalhaDeAmbiente("...") from erro`. A sessão que não abre já vira esta falha
  sozinha (`sessoes.obter`).
- Qualquer outra exceção é falha técnica: o elemento que não apareceu, o valor que não
  bateu, o erro do código.

Numa execução do Proton, a execução termina em Failed nos três casos, e o motivo vai à
parte: o Proton o lê pelo atributo `failure_reason`, na exceção e nas causas dela, sem que
nada aqui importe o Proton. Fora dele, são exceções comuns.
"""


class FalhaDeNegocio(Exception):
    """A regra de negócio não deixou seguir."""

    failure_reason = "business_error"


class FalhaDeAmbiente(Exception):
    """O ambiente não deixou rodar: a sessão da plataforma não abriu."""

    failure_reason = "environment_error"
