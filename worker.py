from consulta import (login, acessar_consulta, selecionar_pesquisa_contrato, consultar_contrato)
from playwright.sync_api import sync_playwright
from logger import logger
from multiprocessing import Queue
import os
import sys

def obter_executable_path():

    if getattr(sys, "frozen", False):

        base = sys._MEIPASS

        return os.path.join(
            base,
            "playwright",
            "chromium-1208",
            "chrome-win",
            "chrome.exe"
        )

    return None

def processar_lote(page, contratos, esteira, cancelar_flag, pasta_saida, worker_id, queue, progress_callback=None, dashboard_callback=None, percentual_inicio=0, percentual_fim=100):

    total_lote = len(contratos)
    resultados = []

    for i, contrato in enumerate(contratos, start=1):

        if cancelar_flag["cancelar"]:
            logger.log("Execução cancelada pelo usuário.")
            return resultados

        try:

            logger.log(f"Pesquisando Contrato: {contrato}")

            resultado = consultar_contrato(page, contrato)

            resultado["ESTEIRA"] = esteira
            queue.put(resultado)

            if dashboard_callback:
                dashboard_callback(resultado)

            resultados.append(resultado)

            if len(resultados) % 100 == 0:
                logger.log(f"Gerando backup temporário ({len(resultados)} registros)")

            logger.log(f"Contrato: {resultado['CONTRATO']} | Status: {resultado['OBS']}")

            percentual = round(percentual_inicio + ((i / total_lote) * (percentual_fim - percentual_inicio)), 2)

            logger.log(f"Atualizando progresso {worker_id} -> {percentual}%")

            if progress_callback:
                progress_callback(worker_id, percentual)

        except Exception as e:

            logger.log(f"Erro no contrato {contrato}: {str(e)}")

            erro = {"CONTRATO": contrato, "OBS": f"ERRO: {str(e)[:100]}", "ESTEIRA": esteira}

            resultados.append(erro)

            queue.put(erro)

    return resultados


def executar_worker(contratos,esteira,usuario,senha,cancelar_flag,worker_id,queue,pasta_saida,progress_callback=None,dashboard_callback=None,headless=False):

    with sync_playwright() as p:

        executable = obter_executable_path()

        if executable and os.path.exists(executable):

            browser = p.chromium.launch(headless=headless,executable_path=executable)

        else:

            browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        page.set_default_timeout(30000)

        try:

            logger.log(f"Iniciando pesquisa na esteira {esteira}")

            login(page, usuario, senha)

            acessar_consulta(page, esteira)

            logger.log(f"Callback recebido? {progress_callback is not None}")

            resultados = processar_lote(page=page, contratos=contratos, esteira=esteira, cancelar_flag=cancelar_flag, pasta_saida=pasta_saida, worker_id=worker_id, queue=queue, progress_callback=progress_callback, dashboard_callback=dashboard_callback, percentual_inicio=0, percentual_fim=100)

        finally:

            browser.close()

    if progress_callback:
        progress_callback(worker_id, 100)

    return resultados