from playwright.sync_api import expect

from automacao.apoio import navegador


class PaginaDeProdutos:

    def __init__(self):
        self.pagina = navegador.pagina()

    def conferir_que_abriu(self) -> None:
        expect(self.pagina.locator('[data-test="title"]')).to_have_text("Products")

    def adicionar_ao_carrinho(self, produto: str) -> str:
        """Adiciona o produto e devolve o preço dele, sem o símbolo da moeda."""
        item = self.pagina.locator('[data-test="inventory-item"]').filter(has_text=produto)
        expect(item, f'Produto "{produto}" não encontrado na loja').to_have_count(1)

        preco = item.locator('[data-test="inventory-item-price"]').inner_text()
        antes = self.itens_no_carrinho()
        item.get_by_role("button", name="Add to cart").click()
        expect(self.pagina.locator('[data-test="shopping-cart-badge"]')).to_have_text(str(antes + 1))

        return preco.replace("$", "").strip()

    def itens_no_carrinho(self) -> int:
        contador = self.pagina.locator('[data-test="shopping-cart-badge"]')
        return int(contador.inner_text()) if contador.count() else 0

    def abrir_carrinho(self) -> None:
        self.pagina.locator('[data-test="shopping-cart-link"]').click()
