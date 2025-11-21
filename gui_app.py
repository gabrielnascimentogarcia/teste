import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import time
from mic1_hardware import Mic1CPU
from assembler import assemble

class Mic1GUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Simulador MIC-1 / MAC-1 (Tanenbaum Architecture)")
        self.root.geometry("1200x800")
        
        # Instância da CPU
        self.cpu = Mic1CPU()
        self.is_running = False
        
        # Estilos
        style = ttk.Style()
        style.theme_use('clam')
        
        # Layout Principal (3 Colunas)
        # Esquerda: Editor Assembly
        # Centro: Datapath Visual (Canvas)
        # Direita: Memória, Cache e Controles
        
        self.paned_window = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # --- PAINEL ESQUERDO (EDITOR) ---
        left_frame = ttk.Frame(self.paned_window, width=300)
        self.paned_window.add(left_frame, weight=1)
        
        ttk.Label(left_frame, text="Editor Assembly MAC-1", font=("Arial", 10, "bold")).pack(pady=5)
        self.code_editor = tk.Text(left_frame, font=("Consolas", 10), height=30)
        self.code_editor.pack(fill=tk.BOTH, expand=True, padx=5)
        
        # Exemplo de código inicial
        default_code = """; Exemplo MAC-1
LOCO 5      ; Carrega 5 no AC
STOD 100    ; Salva 5 na pos 100
LOCO 7      ; Carrega 7 no AC
ADDD 100    ; AC = 7 + 5 = 12
STOD 101    ; Salva 12 na pos 101
HALT        ; Para a execução
"""
        self.code_editor.insert(tk.END, default_code)
        
        ttk.Button(left_frame, text="Montar (Assemble)", command=self.assemble_code).pack(fill=tk.X, pady=5, padx=5)

        # --- PAINEL CENTRAL (VISUALIZAÇÃO) ---
        center_frame = ttk.Frame(self.paned_window, width=600)
        self.paned_window.add(center_frame, weight=3)
        
        ttk.Label(center_frame, text="Microarquitetura (Datapath)", font=("Arial", 10, "bold")).pack(pady=5)
        self.canvas = tk.Canvas(center_frame, bg="white", bd=2, relief="sunken")
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5)
        
        # Elementos gráficos (Referências para atualização)
        self.reg_rects = {}
        self.reg_texts = {}
        self.bus_lines = {}
        self.control_label_id = None
        
        # Desenha o hardware estático inicial
        self.draw_datapath_layout()

        # --- PAINEL DIREITO (ESTADOS E CONTROLES) ---
        right_frame = ttk.Frame(self.paned_window, width=300)
        self.paned_window.add(right_frame, weight=1)
        
        # Controles
        control_frame = ttk.LabelFrame(right_frame, text="Controles")
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(control_frame, text="Run", command=self.start_run).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Button(control_frame, text="Step", command=self.step_cpu).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Button(control_frame, text="Stop", command=self.stop_run).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Button(control_frame, text="Reset", command=self.reset_cpu).pack(side=tk.LEFT, padx=2, pady=2)
        
        # Status
        self.lbl_cycle = ttk.Label(control_frame, text="Cycles: 0")
        self.lbl_cycle.pack(side=tk.RIGHT, padx=5)

        # Visualização de Cache
        cache_frame = ttk.LabelFrame(right_frame, text="Cache de Dados L1 (Direct Mapped)")
        cache_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Tabela de Cache
        columns = ("idx", "valid", "tag", "data")
        self.cache_tree = ttk.Treeview(cache_frame, columns=columns, show="headings", height=8)
        self.cache_tree.heading("idx", text="Idx")
        self.cache_tree.heading("valid", text="V")
        self.cache_tree.heading("tag", text="Tag")
        self.cache_tree.heading("data", text="Data (Hex)")
        
        self.cache_tree.column("idx", width=30)
        self.cache_tree.column("valid", width=30)
        self.cache_tree.column("tag", width=40)
        self.cache_tree.column("data", width=60)
        self.cache_tree.pack(fill=tk.X)
        
        self.lbl_cache_status = ttk.Label(cache_frame, text="Status: IDLE", foreground="blue")
        self.lbl_cache_status.pack()

        # Visualização de Memória
        mem_frame = ttk.LabelFrame(right_frame, text="Memória Principal (RAM)")
        mem_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.mem_list = tk.Listbox(mem_frame, font=("Consolas", 9))
        self.mem_list.pack(fill=tk.BOTH, expand=True)

        # Inicializa UI
        self.update_ui()

    def draw_box(self, x, y, w, h, name, value_hex):
        """Desenha um registrador no canvas."""
        tag = f"reg_{name}"
        rect = self.canvas.create_rectangle(x, y, x+w, y+h, fill="#e1e1e1", outline="black", tags=tag)
        text = self.canvas.create_text(x+w/2, y+h/2, text=f"{name}\n{value_hex}", font=("Arial", 9, "bold"), tags=f"text_{name}")
        self.reg_rects[name] = rect
        self.reg_texts[name] = text

    def draw_datapath_layout(self):
        """Desenha a estrutura estática do MIC-1."""
        self.canvas.delete("all")
        
        w = 80
        h = 40
        center_x = 300
        
        # Stack Registers (Left Side)
        self.draw_box(50, 50, w, h, "MAR", "0000")
        self.draw_box(50, 110, w, h, "MDR", "0000")
        self.draw_box(50, 170, w, h, "PC", "0000")
        self.draw_box(50, 230, w, h, "MBR", "0000")
        self.draw_box(50, 290, w, h, "SP", "0000")
        
        # ALU / Accumulator Side (Right Side)
        self.draw_box(450, 50, w, h, "LV", "0000")
        self.draw_box(450, 110, w, h, "CPP", "0000")
        self.draw_box(450, 170, w, h, "TOS", "0000")
        self.draw_box(450, 230, w, h, "OPC", "0000")
        self.draw_box(450, 290, w, h, "H", "0000") # Holding Register (Input A ALU)

        # ALU (Center)
        self.canvas.create_polygon(
            center_x, 400, center_x-60, 400, center_x-40, 460, center_x+40, 460, center_x+60, 400,
            fill="#ffcccb", outline="black", width=2
        )
        self.canvas.create_text(center_x, 430, text="ALU", font=("Arial", 12, "bold"))
        
        # Shifter (Below ALU)
        self.canvas.create_rectangle(center_x-40, 480, center_x+40, 510, fill="#add8e6", outline="black")
        self.canvas.create_text(center_x, 495, text="Shifter", font=("Arial", 9))
        
        # Control Signals Label
        self.control_label_id = self.canvas.create_text(center_x, 20, text="Control: IDLE", fill="red", font=("Consolas", 12, "bold"))

        # Barramentos (Simplificado visualmente)
        # Linha vertical central representando o Barramento C (Write back)
        self.canvas.create_line(center_x, 510, center_x, 550, arrow=tk.LAST, width=3, fill="gray") # Saída Shifter
        self.canvas.create_text(center_x + 20, 530, text="Bus C")

    def update_ui(self):
        """Atualiza todos os elementos visuais com o estado atual da CPU."""
        # 1. Atualiza Registradores no Canvas
        registers = {
            "MAR": self.cpu.mar, "MDR": self.cpu.mdr, "PC": self.cpu.pc,
            "MBR": self.cpu.mbr, "SP": self.cpu.sp, "LV": self.cpu.lv,
            "CPP": self.cpu.cpp, "TOS": self.cpu.tos, "OPC": self.cpu.opc, "H": self.cpu.h
        }
        
        for name, reg in registers.items():
            val_hex = f"{reg.value:04X}"
            # Atualiza texto
            self.canvas.itemconfig(self.reg_texts[name], text=f"{name}\n{val_hex}")
            
            # Highlight se mudou (lógica simplificada: se não é zero, destaca levemente)
            if reg.value != 0:
                self.canvas.itemconfig(self.reg_rects[name], fill="#aaffaa") # Verde claro
            else:
                self.canvas.itemconfig(self.reg_rects[name], fill="#e1e1e1") # Cinza

        # 2. Atualiza Sinais de Controle
        self.canvas.itemconfig(self.control_label_id, text=f"Last Op: {self.cpu.control_signals}")
        
        # 3. Atualiza Memória (Mostra apenas endereços não zero ou próximos)
        self.mem_list.delete(0, tk.END)
        # Mostra os primeiros 20 endereços e depois apenas os usados
        for i in range(20):
            val = self.cpu.memory.ram[i]
            self.mem_list.insert(tk.END, f"[{i:04X}]: {val:04X}  ({val})")
        
        # 4. Atualiza Cache Treeview
        for i in self.cache_tree.get_children():
            self.cache_tree.delete(i)
            
        for idx, line in enumerate(self.cpu.memory.cache_lines):
            valid_str = "1" if line.valid else "0"
            tag_hex = f"{line.tag:03X}"
            data_hex = f"{line.data:04X}"
            self.cache_tree.insert("", "end", values=(idx, valid_str, tag_hex, data_hex))
            
        # 5. Label Cache Status e Ciclos
        self.lbl_cache_status.config(text=f"Access: {self.cpu.memory.last_access_status}")
        self.lbl_cycle.config(text=f"Cycles: {self.cpu.cycle_count}")

    def assemble_code(self):
        code = self.code_editor.get("1.0", tk.END)
        machine_code, msg = assemble(code)
        
        if not machine_code and msg != "Sucesso":
            messagebox.showerror("Erro de Montagem", msg)
            return
            
        # Carrega na memória
        self.reset_cpu() # Limpa antes de carregar
        self.cpu.memory.load_program(machine_code)
        self.update_ui()
        messagebox.showinfo("Montagem", f"Sucesso! {len(machine_code)} palavras carregadas na memória.")

    def step_cpu(self):
        if self.cpu.halted:
            messagebox.showinfo("Info", "CPU Halted.")
            self.is_running = False
            return
            
        self.cpu.execute_instruction()
        self.update_ui()

    def run_loop(self):
        while self.is_running and not self.cpu.halted:
            # Usa after para thread safety com GUI
            self.root.after(0, self.step_cpu)
            time.sleep(0.5) # Velocidade da simulação (500ms)
            
        self.is_running = False

    def start_run(self):
        if not self.is_running:
            self.is_running = True
            t = threading.Thread(target=self.run_loop)
            t.daemon = True # Fecha thread se app fechar
            t.start()

    def stop_run(self):
        self.is_running = False

    def reset_cpu(self):
        self.stop_run()
        self.cpu.reset()
        self.update_ui()

if __name__ == "__main__":
    root = tk.Tk()
    app = Mic1GUI(root)
    root.mainloop()