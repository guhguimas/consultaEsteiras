import os
import pandas as pd
from logger import logger
import threading


lock_exportacao = threading.Lock()


def salvar_resultados(resultados, pasta_saida, nome_arquivo):

    if not resultados:
        logger.log("Nenhum resultado para exportação.")
        return None

    if not pasta_saida:
        logger.log("Pasta de saída não informada.")
        return None

    nome_arquivo = nome_arquivo.strip()

    if not nome_arquivo:
        nome_arquivo = "Resultado_Consulta"

    os.makedirs(pasta_saida, exist_ok=True)

    arquivo_saida = os.path.join(pasta_saida, f"{nome_arquivo}.xlsx")

    df = pd.DataFrame(resultados)

    df.to_excel(arquivo_saida, index=False)

    logger.log("=" * 60)
    logger.log("Arquivo gerado com sucesso.")
    logger.log(f"Local: {arquivo_saida}")
    logger.log(f"Registros exportados: {len(df):,}")
    logger.log("=" * 60)

    return arquivo_saida