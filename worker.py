from consulta import (login, acessar_consulta, selecionar_pesquisa_contrato, consultar_contrato)
from playwright.sync_api import sync_playwright
from logger import logger
import os

def get_browser_executable_path():
    caminhos = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
    ]
    for path in caminhos:
        if os.path.exists(path):
            return path
    return None

def processar_lote(page, contratos, esteira, cancelar_flag, pasta_saida, worker_id, queue, progress_callback=None, dashboard_callback=None, percentual_inicio=0, percentual_fim=100):
    total_lote = len(contratos)
    resultados = []
    
    contratos_repescagem = []
    contratos_finalizados = 0

    # ==========================================
    # FASE 1: PESQUISA NA ESTEIRA PRINCIPAL
    # ==========================================
    for contrato in contratos:
        if cancelar_flag["cancelar"]:
            logger.log(f"[Worker {worker_id}] Execução cancelada pelo usuário.")
            return resultados

        try:
            logger.log(f"[Worker {worker_id}] Pesquisando Contrato: {contrato} em {esteira}")
            resultado = consultar_contrato(page, contrato)
            resultado["ESTEIRA"] = esteira

            if resultado["OBS"] == "Contrato não Localizado":
                contratos_repescagem.append(contrato)
                logger.log(f"[Worker {worker_id}] Contrato {contrato} não localizado. Separado para Fase 2.")
            else:
                queue.put(resultado)
                if dashboard_callback:
                    dashboard_callback(resultado)
                resultados.append(resultado)
                contratos_finalizados += 1

                if contratos_finalizados % 100 == 0:
                    logger.log(f"[Worker {worker_id}] Processados {contratos_finalizados} registros finais...")

        except Exception as e:
            logger.log(f"[Worker {worker_id}] Erro no contrato {contrato}: {str(e)}")
            erro = {"CONTRATO": contrato, "OBS": f"ERRO: {str(e)[:100]}", "ESTEIRA": esteira}
            resultados.append(erro)
            queue.put(erro) 
            if dashboard_callback:
                dashboard_callback(erro)
            contratos_finalizados += 1

        percentual = round(percentual_inicio + ((contratos_finalizados / total_lote) * (percentual_fim - percentual_inicio)), 2)
        if progress_callback:
            progress_callback(worker_id, percentual)

    # ==========================================
    # FASE 2: REPESCAGEM NA ESTEIRA SECUNDÁRIA
    # ==========================================
    if contratos_repescagem and not cancelar_flag["cancelar"]:
        esteira_secundaria = "INT" if esteira == "AND" else "AND"
        logger.log(f"[Worker {worker_id}] Iniciando FASE 2: Repescagem de {len(contratos_repescagem)} contratos pendentes em {esteira_secundaria}...")
        
        try:
            logger.log(f"[Worker {worker_id}] Clicando no botão Voltar...")
            page.click('//*[@id="btnVoltar_txt"]')
            page.wait_for_timeout(1500) # Pequena pausa para a UI estabilizar
            
            # Chama a consulta com fluxo_completo=False para pular os cliques iniciais
            acessar_consulta(page, esteira_secundaria, fluxo_completo=False)
            
            for contrato in contratos_repescagem:
                if cancelar_flag["cancelar"]:
                    break

                try:
                    logger.log(f"[Worker {worker_id}] Repescagem - Pesquisando Contrato: {contrato} em {esteira_secundaria}")
                    resultado = consultar_contrato(page, contrato)
                    resultado["ESTEIRA"] = esteira_secundaria

                    queue.put(resultado)
                    if dashboard_callback:
                        dashboard_callback(resultado)
                    resultados.append(resultado)
                    
                    if resultado["OBS"] == "Contrato não Localizado":
                        logger.log(f"[Worker {worker_id}] Contrato {contrato} também não localizado na repescagem.")
                    else:
                        logger.log(f"[Worker {worker_id}] Sucesso na repescagem! Status: {resultado['OBS']}")

                except Exception as e:
                    logger.log(f"[Worker {worker_id}] Erro na repescagem do contrato {contrato}: {str(e)}")
                    erro = {"CONTRATO": contrato, "OBS": f"ERRO: {str(e)[:100]}", "ESTEIRA": esteira_secundaria}
                    resultados.append(erro)
                    queue.put(erro) 
                    if dashboard_callback:
                        dashboard_callback(erro)
                
                contratos_finalizados += 1
                percentual = round(percentual_inicio + ((contratos_finalizados / total_lote) * (percentual_fim - percentual_inicio)), 2)
                if progress_callback:
                    progress_callback(worker_id, percentual)

        except Exception as e:
            logger.log(f"[Worker {worker_id}] Erro ao clicar em Voltar ou acessar esteira secundária: {str(e)}")
            for contrato in contratos_repescagem:
                if len(resultados) < total_lote: 
                    erro = {"CONTRATO": contrato, "OBS": "Contrato não Localizado", "ESTEIRA": esteira}
                    resultados.append(erro)
                    queue.put(erro)
                    if dashboard_callback:
                        dashboard_callback(erro)
                    contratos_finalizados += 1

    return resultados

def executar_worker(contratos, esteira, usuario, senha, cancelar_flag, worker_id, queue, pasta_saida, progress_callback=None, dashboard_callback=None, headless=False):
    browser_path = get_browser_executable_path()
    
    with sync_playwright() as p:
        
        # Prepara os argumentos base (comuns para ambos os modos)
        browser_args = [
            "--no-sandbox", 
            "--disable-gpu",
            "--disable-extensions"
        ]
        
        # Adiciona os argumentos ESPECÍFICOS apenas se o modo oculto estiver ativado
        if headless:
            browser_args.append("--headless=new")
            browser_args.append("--window-position=-32000,-32000")

        browser = p.chromium.launch(
            executable_path=browser_path,
            headless=headless,
            args=browser_args
        )
        
        context = browser.new_context()
        page = context.new_page() 
        page.set_default_timeout(30000)

        try:
            logger.log(f"[Worker {worker_id}] Iniciando login e acesso à esteira {esteira}")
            login(page, usuario, senha)
            
            acessar_consulta(page, esteira)
            
            resultados = processar_lote(
                page=page, contratos=contratos, esteira=esteira, 
                cancelar_flag=cancelar_flag, pasta_saida=pasta_saida, 
                worker_id=worker_id, queue=queue, 
                progress_callback=progress_callback, 
                dashboard_callback=dashboard_callback
            )

        finally:
            context.close()
            browser.close() 

    if progress_callback:
        progress_callback(worker_id, 100)
    return resultados