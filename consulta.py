from playwright.sync_api import sync_playwright
from playwright.sync_api import TimeoutError

URL_LOGIN = "https://cc.netcapital.com.br/WebFIMenuMVC/Login/AC.UI.LOGIN.aspx"

XPATHS = {
    "usuario": 'input[name="EUsuario$CAMPO"]',
    "senha": 'input[name="ESenha$CAMPO"]',
    "login_btn": "#lnkEntrar",
    "menu_negociacao": '//div[@class="divTit" and contains(., "NEGOCIAÇÃO")]',
    "submenu_autorizador": '//div[@class="submenu-item" and contains(., "Autorizador")]',
    "menu_esteira": '(//ul[@class="nav navbar-nav"]/li[contains(., "Esteira")])[1]',
    "campo_pesquisa": '//*[@id="ctl00_Cph_AprCons_txtPesquisa_CAMPO"]',
    "botao_pesquisa": '//*[@id="ctl00_Cph_AprCons_UpdPesquisa"]/table/tbody/tr/td/table/tbody/tr/td[6]',
    "grid": '//*[@id="ctl00_Cph_AprCons_grdConsulta"]/tbody/tr',
    "dropdown_pesquisa": '//*[@id="ctl00_Cph_AprCons_cbxPesquisaPor_CAMPO"]'
}

def pad_contrato(contrato):

    return str(contrato).zfill(9)

def obter_xpath_esteira(esteira):

    return '(//ul[@class="nav navbar-nav"]/li[contains(., "Esteira")]/ul/li[contains(., "Aprovação")])[1]' if esteira == "AND" else '(//ul[@class="nav navbar-nav"]/li[contains(., "Esteira")]/ul/li[contains(., "Aprovação")])[3]'

def login(page, usuario, senha):

    page.goto(URL_LOGIN)
    page.fill(XPATHS["usuario"], usuario)
    page.fill(XPATHS["senha"], senha)
    page.click(XPATHS["login_btn"])
    page.wait_for_load_state("networkidle")

def acessar_consulta(page, esteira):

    esteira_xpath = obter_xpath_esteira(esteira)
    page.click(XPATHS["menu_negociacao"])
    page.wait_for_timeout(800)
    page.click(XPATHS["submenu_autorizador"])
    page.wait_for_load_state("networkidle")
    page.wait_for_selector(XPATHS["menu_esteira"], timeout=20000)
    page.hover(XPATHS["menu_esteira"])
    page.wait_for_timeout(800)
    page.wait_for_selector(esteira_xpath, timeout=15000)
    page.click(esteira_xpath, no_wait_after=True)
    page.wait_for_selector(XPATHS["campo_pesquisa"], timeout=15000)
    print("Tela de consulta carregada")

def selecionar_pesquisa_contrato(page):

    page.select_option(XPATHS["dropdown_pesquisa"], value="Contrato")

def pesquisar_contrato(page, contrato):

    contrato = pad_contrato(contrato)
    page.fill(XPATHS["campo_pesquisa"], "")
    page.fill(XPATHS["campo_pesquisa"], contrato)
    page.click(XPATHS["botao_pesquisa"])
    page.wait_for_timeout(300)

def wait_grid_for_contract(page, contrato, timeout=2000):

    try:

        page.wait_for_function(
            """
            (contrato) => {

                const el = document.evaluate(
                    '//*[@id="ctl00_Cph_AprCons_grdConsulta"]/tbody/tr[2]/td[1]',
                    document,
                    null,
                    XPathResult.FIRST_ORDERED_NODE_TYPE,
                    null
                ).singleNodeValue;

                if (!el) return false;

                return (
                    el.innerText.trim()
                    === contrato
                );
            }
            """,
            arg=contrato,
            timeout=timeout
        )

        return True

    except TimeoutError:

        return False

def consultar_contrato(page, contrato):

    contrato_pesquisa = pad_contrato(contrato)
    pesquisar_contrato(page, contrato)
    localizado = wait_grid_for_contract(page, contrato_pesquisa)

    if not localizado:

        return {
            "CONTRATO": contrato,
            "OBS": "Contrato não Localizado"
        }

    try:

        status = page.inner_text('//*[@id="ctl00_Cph_AprCons_grdConsulta"]/tbody/tr[2]/td[9]').strip()

    except:

        status = "Sem informação"

    return {
        "CONTRATO": contrato,
        "OBS": status
    }