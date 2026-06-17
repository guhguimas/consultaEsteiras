import os
import tkinter as tk
import threading
from tkinter import ttk, filedialog
from concurrent.futures import ThreadPoolExecutor

from worker import executar_worker
from excel import (carregar_bases, aplicar_filtros, preparar_base_consulta)
from exportador import salvar_resultados
from logger import logger
import math
from multiprocessing import Queue
from multiprocessing import Process
from writer import writer
import pandas as pd


class TelaPrincipal:

    def __init__(self):

        self.arquivos = []
        self.cancelar_flag = {"cancelar": False}
        self.em_execucao = False

        self.progresso_workers = {}

        self.total_encontrados = 0
        self.total_pendentes = 0
        self.total_erros = 0

        self.pasta_saida = ""

        self.root = tk.Tk()
        self.root.title("Consulta de Esteiras - Contratos Função")
        self.root.geometry("900x700")

        self.criar_componentes()

    def atualizar_dashboard(self, resultado):

        status = str(resultado.get("OBS", "")).upper()

        if "REP" in status:
            self.total_encontrados += 1

        elif "PEN" in status:
            self.total_pendentes += 1

        elif "ERRO" in status:
            self.total_erros += 1

        self.root.after(
            0,
            lambda: self.lbl_encontrados.config(
                text=f"Encontrados\n{self.total_encontrados:,}"
            )
        )

        self.root.after(
            0,
            lambda: self.lbl_pendentes.config(
                text=f"Pendentes\n{self.total_pendentes:,}"
            )
        )

        self.root.after(
            0,
            lambda: self.lbl_erros.config(
                text=f"Erros\n{self.total_erros:,}"
            )
        )

    def criar_componentes(self):

        frame_login = ttk.LabelFrame(self.root, text="Credenciais")
        frame_login.pack(fill="x", padx=10, pady=5)

        ttk.Label(frame_login, text="Usuário:").grid(row=0, column=0, padx=5, pady=5)
        self.entry_usuario = ttk.Entry(frame_login, width=30)
        self.entry_usuario.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(frame_login, text="Senha:").grid(row=1, column=0, padx=5, pady=5)
        self.entry_senha = ttk.Entry(frame_login, show="*", width=30)
        self.entry_senha.grid(row=1, column=1, padx=5, pady=5)

        frame_opcoes = ttk.Frame(self.root)
        frame_opcoes.pack(fill="x", padx=10, pady=5)

        frame_esteira = ttk.LabelFrame(frame_opcoes, text="Esteira")
        frame_esteira.pack(side="left", fill="both", expand=True, padx=5)

        self.var_esteira = tk.StringVar(value="AND")

        ttk.Radiobutton(frame_esteira, text="AND", variable=self.var_esteira, value="AND").pack(side="left", padx=10)
        ttk.Radiobutton(frame_esteira, text="INT", variable=self.var_esteira, value="INT").pack(side="left", padx=10)

        frame_workers = ttk.LabelFrame(frame_opcoes, text="Workers")
        frame_workers.pack(side="left", fill="both", expand=True, padx=5)

        self.var_workers = tk.IntVar(value=2)

        ttk.Radiobutton(frame_workers,text="1 Worker",variable=self.var_workers,value=1).pack(side="left", padx=10)
        ttk.Radiobutton(frame_workers,text="2 Workers",variable=self.var_workers,value=2).pack(side="left", padx=10)

        frame_browser = ttk.LabelFrame(frame_opcoes, text="Navegador")
        frame_browser.pack(side="left", fill="both", expand=True, padx=5)

        self.var_headless = tk.BooleanVar(value=False)

        ttk.Radiobutton(frame_browser,text="Visível",variable=self.var_headless,value=False).pack(side="left", padx=10)

        ttk.Radiobutton(frame_browser,text="Oculto",variable=self.var_headless,value=True).pack(side="left", padx=10)

        frame_arquivos = ttk.LabelFrame(self.root, text="Arquivos CSV")
        frame_arquivos.pack(fill="both", expand=False, padx=10, pady=5)

        self.listbox = tk.Listbox(frame_arquivos, height=3)
        self.listbox.pack(fill="x", padx=5, pady=5)

        ttk.Button(frame_arquivos, text="Adicionar Arquivo", command=self.adicionar_arquivo).pack(side="left", padx=5, pady=5)
        ttk.Button(frame_arquivos, text="Remover Selecionado", command=self.remover_arquivo).pack(side="left", padx=5, pady=5)

        frame_saida = ttk.LabelFrame(self.root, text="Saída")
        frame_saida.pack(fill="x", padx=10, pady=5)

        ttk.Label(frame_saida, text="Nome Arquivo:").grid(row=0, column=0, padx=5, pady=5)

        self.entry_nome_arquivo = ttk.Entry(frame_saida, width=40)
        self.entry_nome_arquivo.grid(row=0, column=1, padx=5, pady=5)
        self.entry_nome_arquivo.insert(0, "Resultado_Consulta")

        ttk.Label(frame_saida, text="Pasta Destino:").grid(row=1, column=0, padx=5, pady=5)

        self.label_pasta = ttk.Label(frame_saida, text="Nenhuma pasta selecionada")
        self.label_pasta.grid(row=1, column=1, sticky="w", padx=5, pady=5)

        ttk.Button(frame_saida, text="Selecionar Pasta", command=self.selecionar_pasta).grid(row=1, column=2, padx=5, pady=5)

        frame_botoes = ttk.Frame(self.root)
        frame_botoes.pack(fill="x", padx=10, pady=10)

        ttk.Button(frame_botoes, text="Iniciar Robô", command=self.iniciar_robo).pack(side="left", padx=5)
        ttk.Button(frame_botoes, text="Cancelar Operação", command=self.cancelar_operacao).pack(side="left", padx=5)
        ttk.Button(frame_botoes, text="Limpar Logs", command=self.limpar_logs).pack(side="left", padx=5)
        ttk.Button(frame_botoes, text="Abrir Pasta Resultado", command=self.abrir_pasta_resultado).pack(side="left", padx=5)

        self.progress = ttk.Progressbar(self.root, mode="indeterminate")
        self.progress.pack(fill="x", padx=10, pady=5)

        self.label_progresso = ttk.Label(self.root, text="Status: 0%")
        self.label_progresso.pack(anchor="e", padx=10)

        frame_dashboard = ttk.LabelFrame(self.root, text="Dashboard")
        frame_dashboard.pack(fill="x", padx=10, pady=5)

        self.lbl_total = ttk.Label(frame_dashboard, text="Contratos\n0", width=20)
        self.lbl_total.pack(side="left", padx=5, pady=5)

        self.lbl_encontrados = ttk.Label(frame_dashboard, text=f"Encontrados\n{self.total_encontrados:,}", width=20)
        self.lbl_encontrados.pack(side="left", padx=5, pady=5)

        self.lbl_pendentes = ttk.Label(frame_dashboard, text="Pendentes\n0", width=20)
        self.lbl_pendentes.pack(side="left", padx=5, pady=5)

        self.lbl_erros = ttk.Label(frame_dashboard, text="Erros\n0", width=20)
        self.lbl_erros.pack(side="left", padx=5, pady=5)

        frame_logs = ttk.LabelFrame(self.root, text="Logs")
        frame_logs.pack(fill="both", expand=True, padx=10, pady=5)

        scrollbar = ttk.Scrollbar(frame_logs)
        scrollbar.pack(side="right", fill="y")

        self.text_logs = tk.Text(frame_logs, yscrollcommand=scrollbar.set)
        self.text_logs.pack(side="left", fill="both", expand=True)

        scrollbar.config(command=self.text_logs.yview)

        logger.configurar_widget(self.text_logs)

        self.processar_logs()

        logger.log("Tela iniciada.")

    def processar_logs(self):

        logger.processar_fila()

        self.root.after(100, self.processar_logs)

    def adicionar_arquivo(self):

        arquivos = filedialog.askopenfilenames(filetypes=[("CSV", "*.csv")])

        for arquivo in arquivos:

            if arquivo not in self.arquivos:

                self.arquivos.append(arquivo)

                self.listbox.insert(tk.END, arquivo)

                logger.log(f"Arquivo adicionado: {arquivo}")
                logger.log(f"Total de arquivos: {len(self.arquivos)}")

    def remover_arquivo(self):

        selecionado = self.listbox.curselection()

        if not selecionado:
            return

        indice = selecionado[0]

        arquivo = self.arquivos.pop(indice)

        self.listbox.delete(indice)

        logger.log(f"Arquivo removido: {arquivo}")

    def selecionar_pasta(self):

        pasta = filedialog.askdirectory()

        if pasta:

            self.pasta_saida = pasta

            self.label_pasta.config(text=pasta)

            logger.log(f"Pasta selecionada: {pasta}")

    def iniciar_robo(self):

        if self.em_execucao:

            logger.log("Robô já está em execução.")
            return

        self.em_execucao = True
        self.cancelar_flag["cancelar"] = False

        self.total_encontrados = 0
        self.total_pendentes = 0
        self.total_erros = 0

        self.lbl_encontrados.config(text="Encontrados\n0")
        self.lbl_pendentes.config(text="Pendentes\n0")
        self.lbl_erros.config(text="Erros\n0")

        self.progress.start(10)

        def rodar():

            queue = None
            writer_process = None

            try:

                if not self.arquivos:
                    logger.log("Nenhum arquivo selecionado.")
                    return

                if not self.entry_usuario.get().strip():
                    logger.log("Usuário não informado.")
                    return

                if not self.entry_senha.get().strip():
                    logger.log("Senha não informada.")
                    return

                if not self.pasta_saida:
                    logger.log("Selecione uma pasta de saída.")
                    return

                nome_arquivo = self.entry_nome_arquivo.get().strip()

                if not nome_arquivo:
                    logger.log("Informe o nome do arquivo.")
                    return

                logger.log("Iniciando processamento...")

                df = carregar_bases(self.arquivos)

                if self.cancelar_flag["cancelar"]:
                    logger.log("Processamento cancelado durante leitura dos arquivos.")
                    return

                df = aplicar_filtros(df)

                if self.cancelar_flag["cancelar"]:
                    logger.log("Processamento cancelado durante aplicação dos filtros.")
                    return

                df = preparar_base_consulta(df)

                if self.cancelar_flag["cancelar"]:
                    logger.log("Processamento cancelado durante preparação da base.")
                    return

                contratos = df["Contrato"].tolist()

                self.total_contratos = len(contratos)
                self.processados = 0

                self.root.after(0, lambda: self.lbl_total.config(text=f"Contratos\n{self.total_contratos:,}"))

                self.progresso_workers = {
                    i: 0
                    for i in range(1,self.var_workers.get() + 1)
                }

                lotes = self.dividir_lotes(contratos,quantidade_workers=self.var_workers.get())

                if self.cancelar_flag["cancelar"]:
                    logger.log("Processamento cancelado durante agrupamento.")
                    return

                logger.log(f"Contratos para processamento: {len(contratos):,}")

                arquivo_temp = os.path.join(self.pasta_saida, f"{nome_arquivo}_temp.csv")

                if os.path.exists(arquivo_temp):
                    os.remove(arquivo_temp)

                queue = Queue()

                writer_process = Process(target=writer, args=(queue, arquivo_temp))
                writer_process.start()

                with ThreadPoolExecutor(max_workers=self.var_workers.get()) as executor:

                    futuros = []

                    for indice, lote in enumerate(lotes, start=1):

                        futuro = executor.submit(executar_worker,lote,self.var_esteira.get(),self.entry_usuario.get(),self.entry_senha.get(),self.cancelar_flag,indice,queue,self.pasta_saida,self.atualizar_progresso,self.atualizar_dashboard,self.var_headless.get())

                        futuros.append(futuro)
                    
                    resultados = []

                    for futuro in futuros:
                        resultados.extend(futuro.result())

                    queue.put("DONE")

                    writer_process.join()

                if os.path.exists(arquivo_temp):

                    df_final = pd.read_csv(arquivo_temp, sep=";")

                    arquivo_gerado = os.path.join(self.pasta_saida, f"{nome_arquivo}.xlsx")

                    df_final.to_excel(arquivo_gerado, index=False)

                    logger.log(f"Arquivo gerado: {arquivo_gerado}")

                else:

                    logger.log("Nenhum resultado para exportação.")

                logger.log("=" * 60)
                logger.log("Processamento concluído.")
                logger.log(f"Registros retornados: {len(resultados):,}")
                logger.log("=" * 60)

            except Exception as e:

                logger.log(f"Erro geral: {str(e)}")

            finally:

                if queue:
                    try:
                        queue.put("DONE")
                    except:
                        pass

                if writer_process:
                    writer_process.join(timeout=5)

                self.em_execucao = False

                self.root.after(0, self.progress.stop)

                self.root.after(0, lambda: self.label_progresso.config(text="Status: 0%"))

        threading.Thread(target=rodar, daemon=True).start()

    def cancelar_operacao(self):

        if not self.em_execucao:

            logger.log("Nenhuma execução em andamento.")
            return

        self.cancelar_flag["cancelar"] = True

        logger.log("Solicitação de cancelamento enviada. Aguarde finalização da etapa atual.")

    def limpar_logs(self):

        self.text_logs.delete("1.0", "end")

        logger.log("Logs limpos.")

    def abrir_pasta_resultado(self):

        if not self.pasta_saida:

            logger.log("Nenhuma pasta de saída selecionada.")
            return

        if os.path.exists(self.pasta_saida):

            os.startfile(self.pasta_saida)

            logger.log("Pasta de resultados aberta.")

        else:

            logger.log("Pasta não encontrada.")

    def atualizar_progresso(self, worker_id, valor):

        logger.log(f"Worker {worker_id} -> {valor}%")

        self.progresso_workers[worker_id] = valor

        percentual_total = (sum(self.progresso_workers.values()) / len(self.progresso_workers))

        self.root.after(0, lambda: self.label_progresso.config(text=f"Status: {percentual_total:.2f}%"))

    def dividir_lotes(self, contratos, quantidade_workers=2):

        tamanho = math.ceil(len(contratos) / quantidade_workers)

        lotes = []

        inicio = 0

        for i in range(quantidade_workers):

            if i == quantidade_workers - 1:

                lote = contratos[inicio:]

            else:

                lote = contratos[inicio:inicio+tamanho]

            lotes.append(lote)

            inicio += tamanho

        return lotes

    def executar(self):

        self.root.mainloop()