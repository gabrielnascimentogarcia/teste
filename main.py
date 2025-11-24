import tkinter as tk
from gui_app import Mic1GUI
import sys

def main():
    """
    Ponto de entrada para o Simulador MIC-1.
    Inicializa a raiz do Tkinter e a aplicação GUI principal.
    """
    print("Iniciando Simulador MIC-1 v6.1 (Patched)...")
    try:
        root = tk.Tk()
        app = Mic1GUI(root)
        root.mainloop()
        
    except Exception as e:
        print(f"Erro crítico ao iniciar a aplicação: {e}")
        input("Pressione Enter para sair...")
        sys.exit(1)

if __name__ == "__main__":
    main()