import sys
import tkinter as tk
from src.ui.app import Mic1GUI

# Ponto de entrada do simulador
def main():
    print("Iniciando Simulador MIC-1...")
    
    # Se der erro de display no Linux, verificar se o python3-tk tá instalado
    try:
        root = tk.Tk()
        app = Mic1GUI(root)
        root.mainloop()
    except KeyboardInterrupt:
        # Fecha sem erro feio no terminal se der Ctrl+C
        sys.exit(0)
    except Exception as e:
        print(f"[ERRO FATAL] O programa quebrou: {e}")
        raise

if __name__ == "__main__":
    main()