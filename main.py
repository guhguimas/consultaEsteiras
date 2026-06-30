import multiprocessing
from tela import TelaPrincipal # Ajuste para a sua importação correta

if __name__ == '__main__':
    # ESSA É A MÁGICA QUE RESOLVE O PROBLEMA DAS JANELAS DUPLICADAS
    multiprocessing.freeze_support() 
    
    # O resto do seu código de inicialização da tela continua igual
    app = TelaPrincipal()
    app.executar()