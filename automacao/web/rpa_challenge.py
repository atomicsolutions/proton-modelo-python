import re
from pathlib import Path

from playwright.sync_api import expect

from automacao.apoio import config
from automacao.web import sessao

# Os campos do formulário, pelo rótulo que aparece na tela (o mesmo título da coluna da planilha).
CAMPOS = ("First Name", "Last Name", "Company Name", "Role in Company", "Address", "Email", "Phone Number")


class PaginaDoDesafio:
    """
    O RPA Challenge: um formulário que muda a posição dos campos a cada envio, e os ids
    mudam a cada carga. Por isso cada campo é achado pelo rótulo, como uma pessoa faria.
    """

    def __init__(self):
        self.pagina = sessao.pagina()

    def abrir(self) -> "PaginaDoDesafio":
        sessao.ir_para(config.URL_DO_DESAFIO_RPA)
        expect(self.pagina.get_by_role("button", name="Start")).to_be_visible()
        return self

    def garantir_aberta(self) -> "PaginaDoDesafio":
        """Abre o desafio se a página do navegador ainda não está nele (o passo rodando sozinho)."""
        if not self.pagina.url.startswith(config.URL_DO_DESAFIO_RPA):
            self.abrir()
        return self

    def baixar_planilha(self, destino: Path) -> Path:
        """Baixa a planilha de cadastros do desafio para o caminho informado."""
        with self.pagina.expect_download() as download:
            self.pagina.get_by_text("Download Excel").click()
        download.value.save_as(destino)
        return destino

    def comecar(self) -> None:
        self.pagina.get_by_role("button", name="Start").click()

    def preencher(self, cadastro: dict[str, str]) -> None:
        for rotulo in CAMPOS:
            campo = self.pagina.locator("label", has_text=re.compile(rf"^\s*{rotulo}\s*$")).locator("xpath=following-sibling::input[1]")
            campo.fill(cadastro[rotulo])

    def enviar(self) -> None:
        self.pagina.locator('input[type="submit"][value="Submit"]').click()

    def resultado(self) -> str:
        """A mensagem do fim do desafio (ex.: "Your success rate is 100% ( 70 out of 70 fields) in 980 milliseconds")."""
        mensagem = self.pagina.locator(".message2")
        expect(mensagem).to_contain_text("success rate")
        return " ".join(mensagem.inner_text().split())
