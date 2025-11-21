import tkinter as tk
from gui_app import Mic1GUI

def main():
    """
    Ponto de entrada para o Simulador MIC-1 v2.0.
    """
    try:
        root = tk.Tk()
        # root.iconbitmap('icon.ico') 
        
        app = Mic1GUI(root)
        
        print("Simulador MIC-1 v2.0 Iniciado...")
        root.mainloop()
        
    except Exception as e:
        print(f"Erro crítico ao iniciar a aplicação: {e}")

if __name__ == "__main__":
    main()