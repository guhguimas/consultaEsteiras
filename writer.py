import pandas as pd

def writer(queue, arquivo_temp):

    primeiro_registro = True

    while True:

        item = queue.get()

        if item == "DONE":
            break

        pd.DataFrame([item]).to_csv(arquivo_temp, mode="a", header=primeiro_registro, index=False, sep=";", encoding="utf-8-sig")

        primeiro_registro = False