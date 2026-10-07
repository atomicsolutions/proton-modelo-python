from playwright.sync_api import expect

from automacao.apoio import config, navegador


class PaginaDeLogin:

    def __init__(self):
        self.pagina = navegador.pagina()

    def abrir(self) -> "PaginaDeLogin":
        navegador.ir_para(config.URL_DA_LOJA)
        return self

    def entrar(self, usuario: str, senha: str) -> None:
        self.pagina.locator('[data-test="username"]').fill(usuario)
        self.pagina.locator('[data-test="password"]').fill(senha)
        self.pagina.locator('[data-test="login-button"]').click()

    def mensagem_de_erro(self) -> str:
        erro = self.pagina.locator('[data-test="error"]')
        expect(erro).to_be_visible()
        return erro.inner_text()
