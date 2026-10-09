from playwright.sync_api import expect

from automacao.web import sessao


class PaginaDeCheckout:

    def __init__(self):
        self.pagina = sessao.pagina()

    def preencher_entrega(self, nome: str, sobrenome: str, cep: str) -> None:
        self.pagina.locator('[data-test="firstName"]').fill(nome)
        self.pagina.locator('[data-test="lastName"]').fill(sobrenome)
        self.pagina.locator('[data-test="postalCode"]').fill(cep)
        self.pagina.locator('[data-test="continue"]').click()
        self._conferir_que_avancou()

    def _conferir_que_avancou(self) -> None:
        """Quando recusa os dados de entrega, a loja mostra o erro na mesma página."""
        resumo = self.pagina.locator('[data-test="subtotal-label"]')
        erro = self.pagina.locator('[data-test="error"]')
        resumo.or_(erro).first.wait_for()

        if erro.is_visible():
            raise AssertionError(f"A loja recusou os dados de entrega: {erro.inner_text()}")

    def total_dos_itens(self) -> str:
        """`Item total: $29.99` vira `29.99`."""
        return self._valor('[data-test="subtotal-label"]')

    def total(self) -> str:
        """`Total: $32.39` vira `32.39`."""
        return self._valor('[data-test="total-label"]')

    def concluir(self) -> None:
        self.pagina.locator('[data-test="finish"]').click()
        expect(self.pagina.locator('[data-test="complete-header"]')).to_have_text("Thank you for your order!")

    def _valor(self, seletor: str) -> str:
        return self.pagina.locator(seletor).inner_text().split("$")[-1].strip()
