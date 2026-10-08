"""
As telas do My Demo App, o app de demonstração da Sauce Labs
(https://github.com/saucelabs/my-demo-app-android), com os mesmos produtos da loja web.
"""

from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

from automacao.apoio import config
from automacao.mobile import sessao

ID = "com.saucelabs.mydemoapp.android:id/"


class TelaDeProdutos:

    def __init__(self):
        self.driver = sessao.driver()
        self.espera = WebDriverWait(self.driver, config.TIMEOUT_MOBILE_S)

    def abrir_produto(self, produto: str) -> "TelaDoProduto":
        self.espera.until(ec.presence_of_element_located((AppiumBy.ID, ID + "productRV")))
        # Rola a lista até o produto e toca na foto dele, que fica no mesmo cartão do nome.
        foto = self.driver.find_element(
            AppiumBy.ANDROID_UIAUTOMATOR,
            f'new UiScrollable(new UiSelector().resourceId("{ID}productRV"))'
            f'.scrollIntoView(new UiSelector().resourceId("{ID}titleTV").text("{produto}")'
            f'.fromParent(new UiSelector().resourceId("{ID}productIV")))',
        )
        foto.click()
        return TelaDoProduto()


class TelaDoProduto:

    def __init__(self):
        self.driver = sessao.driver()
        self.espera = WebDriverWait(self.driver, config.TIMEOUT_MOBILE_S)
        self.espera.until(ec.presence_of_element_located((AppiumBy.ID, ID + "cartBt")))

    def nome(self) -> str:
        return self.driver.find_element(AppiumBy.ID, ID + "productTV").text

    def preco(self) -> str:
        """`$ 29.99` vira `29.99`."""
        return self.driver.find_element(AppiumBy.ID, ID + "priceTV").text.replace("$", "").strip()

    def itens_no_carrinho(self) -> int:
        contador = self.driver.find_elements(AppiumBy.ID, ID + "cartTV")
        return int(contador[0].text) if contador else 0

    def adicionar_ao_carrinho(self) -> None:
        antes = self.itens_no_carrinho()
        self.driver.find_element(AppiumBy.ID, ID + "cartBt").click()
        self.espera.until(
            lambda driver: self.itens_no_carrinho() == antes + 1,
            f"O carrinho não passou de {antes} para {antes + 1} itens",
        )
