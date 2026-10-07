from automacao.web import sessao


class PaginaDoCarrinho:

    def __init__(self):
        self.pagina = sessao.pagina()

    def ir_para_o_checkout(self) -> None:
        self.pagina.locator('[data-test="checkout"]').click()
