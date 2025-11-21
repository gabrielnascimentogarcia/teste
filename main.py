import tkinter as tk
from gui_app import Mic1GUI

def main():
    """
    Ponto de entrada para o Simulador MIC-1.
    """
    try:
        root = tk.Tk()
        # Configura ícone se existir, senão ignora
        # root.iconbitmap('icon.ico') 
        
        app = Mic1GUI(root)
        
        print("Simulador MIC-1 Iniciado...")
        print("Feche a janela da GUI para encerrar o processo.")
        
        root.mainloop()
        
    except Exception as e:
        print(f"Erro crítico ao iniciar a aplicação: {e}")

if __name__ == "__main__":
    main()