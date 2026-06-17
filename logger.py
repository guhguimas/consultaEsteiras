from datetime import datetime
from queue import Queue


class Logger:

    def __init__(self):
        self.widget_log = None
        self.fila = Queue()

    def configurar_widget(self, widget):
        self.widget_log = widget

    def log(self, mensagem):
        horario = datetime.now().strftime("%H:%M:%S")
        texto = f"[{horario}] {mensagem}\n"
        print(texto)
        self.fila.put(texto)

    def processar_fila(self):

        if not self.widget_log:
            return

        while not self.fila.empty():

            texto = self.fila.get()

            self.widget_log.insert("end", texto)
            self.widget_log.see("end")


logger = Logger()