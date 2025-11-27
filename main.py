import tkinter as tk
import sys
from src.ui.app import Mic1GUI

def main():
    print("Iniciando Simulador MIC-1 (Arquitetura Refatorada)...")
    try:
        root = tk.Tk()
        app = Mic1GUI(root)
        root.mainloop()
    except Exception as e:
        print(f"Erro crítico: {e}")
        input("Pressione Enter para sair...")
        sys.exit(1)

if __name__ == "__main__":
    main()