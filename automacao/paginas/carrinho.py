from automacao.apoio import navegador


class PaginaDoCarrinho:

    def __init__(self):
        self.pagina = navegador.pagina()

    def ir_para_o_checkout(self) -> None:
        self.pagina.locator('[data-test="checkout"]').click()
