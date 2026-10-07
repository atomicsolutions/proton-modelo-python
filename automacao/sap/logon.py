from automacao.sap import sessao


class TelaDeLogon:
    """A tela de logon do SAP GUI (SAPMSYST)."""

    def __init__(self):
        self.sessao = sessao.sessao()

    def entrar(self, usuario: str, senha: str, mandante: str = "", idioma: str = "PT") -> None:
        if mandante:
            self.sessao.findById("wnd[0]/usr/txtRSYST-MANDT").Text = mandante

        self.sessao.findById("wnd[0]/usr/txtRSYST-BNAME").Text = usuario
        self.sessao.findById("wnd[0]/usr/pwdRSYST-BCODE").Text = senha
        self.sessao.findById("wnd[0]/usr/txtRSYST-LANGU").Text = idioma
        self.sessao.findById("wnd[0]").sendVKey(0)

        if sessao.existe("wnd[1]/usr/txtMULTI_LOGON_TEXT"):
            raise AssertionError(f"O usuário {usuario} já tem sessão aberta no SAP (logon múltiplo).")

        # Aviso de tentativas de logon sem sucesso desde o último acesso.
        if sessao.existe("wnd[1]/tbar[0]/btn[0]"):
            self.sessao.findById("wnd[1]/tbar[0]/btn[0]").press()

        tipo, texto = sessao.barra_de_status()

        if tipo in ("E", "A"):
            raise AssertionError(f"Logon recusado pelo SAP: {texto}")
