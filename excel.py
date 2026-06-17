import pandas as pd
from logger import logger


ESTEIRAS_VALIDAS = ["LIBERADO", "EM ANDAMENTO", "REPROVADO", "PENDENTE"]


def ler_csv(arquivo):

    encodings = ["utf-8", "utf-8-sig", "latin1", "cp1252"]

    for encoding in encodings:

        try:

            logger.log(f"Tentando abrir arquivo com encoding: {encoding}")
            return pd.read_csv(arquivo, sep=";", dtype=str, encoding=encoding)

        except UnicodeDecodeError:

            continue

    raise Exception("Não foi possível identificar a codificação do arquivo.")


def carregar_bases(lista_arquivos):

    dfs = []

    for arquivo in lista_arquivos:

        logger.log(f"Lendo arquivo: {arquivo}")

        try:

            df = ler_csv(arquivo)
            df.columns = df.columns.str.strip()

            colunas_necessarias = ["Contrato", "Esteira"]

            for col in colunas_necessarias:

                if col not in df.columns:
                    raise Exception(f"Coluna obrigatória ausente: {col}")

            df = df[colunas_necessarias]
            dfs.append(df)

        except Exception as e:

            logger.log(f"Erro ao ler {arquivo}: {str(e)}")

    if not dfs:
        raise Exception("Nenhum arquivo carregado.")

    df_final = pd.concat(dfs, ignore_index=True)
    logger.log(f"Total de registros carregados: {len(df_final):,}")

    return df_final


def aplicar_filtros(df):

    logger.log("Aplicando filtro de esteira...")

    df["Esteira"] = df["Esteira"].astype(str).str.strip()
    df = df[df["Esteira"].isin(ESTEIRAS_VALIDAS)].copy()

    if df.empty:
        logger.log("⚠ Nenhum registro após filtro de esteira.")

    logger.log(f"Registros após filtro: {len(df):,}")

    return df


def preparar_base_consulta(df):

    logger.log("Preparando base para consulta...")

    df = df[["Contrato"]].copy()
    df["Contrato"] = df["Contrato"].astype(str).str.strip().replace("nan", "")
    df = df[df["Contrato"] != ""]
    df["Contrato"] = df["Contrato"].str.zfill(9)
    df = df.drop_duplicates(subset=["Contrato"])

    return df