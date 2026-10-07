import re
from decimal import Decimal

from automacao.desktop import sessao


class Calculadora:
    """
    A Calculadora do Windows 10 e 11. Os botões são achados pelo AutomationId, que é o
    mesmo em qualquer idioma do Windows; só o separador decimal do visor muda.
    """

    _BOTOES = {
        **{str(digito): f"num{digito}Button" for digito in range(10)},
        ".": "decimalSeparatorButton",
        "+": "plusButton",
        "-": "minusButton",
        "*": "multiplyButton",
        "/": "divideButton",
    }

    def __init__(self):
        self.janela = sessao.janela("calculadora", "calc.exe", r"Calculadora|Calculator")

    def calcular(self, conta: str) -> Decimal:
        """Faz a conta (ex.: `32.39/3`, com ponto decimal) e devolve o resultado."""
        self._apertar("clearButton")
        separador = self._separador_decimal()
        self._apertar("clearButton")

        for simbolo in conta.replace(" ", ""):
            if simbolo not in self._BOTOES:
                raise ValueError(f'A calculadora não tem o botão "{simbolo}"')
            self._apertar(self._BOTOES[simbolo])

        self._apertar("equalButton")
        return self._numero_do_visor(separador)

    def _apertar(self, automation_id: str) -> None:
        self.janela.child_window(auto_id=automation_id, control_type="Button").invoke()

    def _visor(self) -> str:
        """O texto do visor, como "A exibição é 10,79" ou "Display is 10.79"."""
        return self.janela.child_window(auto_id="CalculatorResults").window_text()

    def _separador_decimal(self) -> str:
        """Digita 1,5 e vê o que o visor põe entre o 1 e o 5: vírgula ou ponto."""
        for simbolo in "1.5":
            self._apertar(self._BOTOES[simbolo])

        return "," if "1,5" in self._visor() else "."

    def _numero_do_visor(self, separador: str) -> Decimal:
        numero = re.findall(r"-?\d[\d.,\s  ]*", self._visor())[-1]
        milhar = "." if separador == "," else ","
        limpo = re.sub(r"[\s  ]", "", numero).replace(milhar, "").replace(separador, ".")
        return Decimal(limpo)
