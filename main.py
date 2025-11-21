import tkinter as tk
from gui_app import Mic1GUI
import sys

def main():
    """
    Ponto de entrada para o Simulador MIC-1 Final (v4.0).
    """
    print("Iniciando Simulador MIC-1 v4.0...")
    try:
        root = tk.Tk()
        # Se tiver um ícone .ico, descomente a linha abaixo
        # root.iconbitmap('icon.ico') 
        
        app = Mic1GUI(root)
        root.mainloop()
        
    except Exception as e:
        print(f"Erro crítico ao iniciar a aplicação: {e}")
        # Mantém console aberto em caso de erro se rodado via bat/sh
        input("Pressione Enter para sair...")
        sys.exit(1)

if __name__ == "__main__":
    main()