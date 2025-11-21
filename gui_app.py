import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import time
import re
from mic1_hardware import Mic1CPU
from assembler import assemble

class CodeEditor(tk.Frame):
    """
    Widget composto com numeração de linhas e syntax highlighting.
    """
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.line_numbers = tk.Text(self, width=4, padx=4, takefocus=0, border=0,
                                    background='#f0f0f0', state='disabled', font=("Consolas", 10))
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)
        
        self.text_area = tk.Text(self, font=("Consolas", 10), undo=True)
        self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbar
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.sync_scroll)
        self.vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_area['yscrollcommand'] = self.on_text_scroll

        # Config Tags de Cores
        self.text_area.tag_configure("keyword", foreground="blue", font=("Consolas", 10, "bold"))
        self.text_area.tag_configure("number", foreground="#c00000")
        self.text_area.tag_configure("comment", foreground="green")

        # Bindings
        self.text_area.bind("<<Change>>", self.on_change)
        self.text_area.bind("<KeyRelease>", self.on_change)
        self.text_area.bind("<MouseWheel>", self.on_change) # Para sync de linhas

        self.update_line_numbers()

    def sync_scroll(self, *args):
        self.text_area.yview(*args)
        self.line_numbers.yview(*args)

    def on_text_scroll(self, *args):
        self.vsb.set(*args)
        self.line_numbers.yview_moveto(args[0])

    def on_change(self, event=None):
        self.update_line_numbers()
        self.highlight_syntax()

    def update_line_numbers(self):
        lines = self.text_area.get('1.0', 'end-1c').count('\n') + 1
        line_content = "\n".join(str(i) for i in range(1, lines + 1))
        
        self.line_numbers.config(state='normal')
        self.line_numbers.delete('1.0', tk.END)
        self.line_numbers.insert('1.0', line_content)
        self.line_numbers.config(state='disabled')

    def highlight_syntax(self):
        # Limpa tags anteriores
        for tag in ["keyword", "number", "comment"]:
            self.text_area.tag_remove(tag, "1.0", tk.END)
        
        content = self.text_area.get("1.0", tk.END)
        
        # Keywords
        keywords = ["LODD", "STOD", "ADDD", "SUBD", "JPOS", "JZER", "JUMP", "LOCO", 
                    "LODL", "STOL", "ADDL", "SUBL", "JNEG", "JNZE", "CALL", "HALT"]
        for kw in keywords:
            start_idx = "1.0"
            while True:
                start_idx = self.text_area.search(kw, start_idx, stopindex=tk.END)
                if not start_idx: break
                end_idx = f"{start_idx}+{len(kw)}c"
                self.text_area.tag_add("keyword", start_idx, end_idx)
                start_idx = end_idx

        # Numbers (simplificado)
        start_idx = "1.0"
        while True:
            # Busca digitos
            start_idx = self.text_area.search(r'\m[0-9]+\M', start_idx, stopindex=tk.END, regexp=True)
            if not start_idx: break
            # Acha o fim do numero
            end_idx = self.text_area.search(r'[^0-9]', start_idx, stopindex=tk.END, regexp=True)
            if not end_idx: end_idx = tk.END 
            self.text_area.tag_add("number", start_idx, end_idx)
            start_idx = end_idx

        # Comentários
        start_idx = "1.0"
        while True:
            start_idx = self.text_area.search(';', start_idx, stopindex=tk.END)
            if not start_idx: break
            # Do ; até o fim da linha
            line_end = self.text_area.index(f"{start_idx} lineend")
            self.text_area.tag_add("comment", start_idx, line_end)
            start_idx = line_end

    def get_code(self):
        return self.text_area.get("1.0", tk.END)
    
    def set_code(self, text):
        self.text_area.delete("1.0", tk.END)
        self.text_area.insert("1.0", text)
        self.on_change()


class Mic1GUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Simulador MIC-1 / MAC-1 v2.0 (Tanenbaum)")
        self.root.geometry("1300x850")
        
        self.cpu = Mic1CPU()
        self.is_running = False
        self.display_hex = True # Toggle Hex/Dec
        
        style = ttk.Style()
        style.theme_use('clam')
        
        self.paned_window = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # === ESQUERDA: Editor ===
        left_frame = ttk.Frame(self.paned_window, width=350)
        self.paned_window.add(left_frame, weight=1)
        
        ttk.Label(left_frame, text="Editor Assembly MAC-1", font=("Arial", 10, "bold")).pack(pady=5)
        
        # Usa o novo componente CodeEditor
        self.editor = CodeEditor(left_frame)
        self.editor.pack(fill=tk.BOTH, expand=True, padx=2)
        
        default_code = """; Exemplo MAC-1 v2.0
LOCO 5      ; Carrega 5 no AC
STOD 100    ; Salva 5 na pos 100
LOCO 7      ; Carrega 7 no AC
ADDD 100    ; AC = 7 + 5 = 12
STOD 101    ; Salva 12 na pos 101
HALT        ; Para a execução
"""
        self.editor.set_code(default_code)
        ttk.Button(left_frame, text="Montar (Assemble)", command=self.assemble_code).pack(fill=tk.X, pady=5)

        # === CENTRO: Datapath ===
        center_frame = ttk.Frame(self.paned_window, width=600)
        self.paned_window.add(center_frame, weight=3)
        
        ttk.Label(center_frame, text="Microarquitetura (Datapath)", font=("Arial", 10, "bold")).pack(pady=5)
        self.canvas = tk.Canvas(center_frame, bg="white", bd=2, relief="sunken")
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5)
        
        self.reg_rects = {}
        self.reg_texts = {}
        self.control_label_id = None
        
        self.draw_datapath_layout()

        # === DIREITA: Estado ===
        right_frame = ttk.Frame(self.paned_window, width=350)
        self.paned_window.add(right_frame, weight=1)
        
        # Controles
        control_frame = ttk.LabelFrame(right_frame, text="Controles & Modos")
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        btn_f = ttk.Frame(control_frame)
        btn_f.pack(fill=tk.X)
        ttk.Button(btn_f, text="Run", command=self.start_run).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_f, text="Step", command=self.step_cpu).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_f, text="Stop", command=self.stop_run).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_f, text="Reset", command=self.reset_cpu).pack(side=tk.LEFT, padx=2)
        
        self.btn_mode = ttk.Button(control_frame, text="Mode: HEX", command=self.toggle_display_mode)
        self.btn_mode.pack(side=tk.RIGHT, padx=5, pady=2)
        
        self.lbl_cycle = ttk.Label(control_frame, text="Cycles: 0")
        self.lbl_cycle.pack(side=tk.LEFT, padx=5)

        # Cache
        cache_frame = ttk.LabelFrame(right_frame, text="Cache Dados L1")
        cache_frame.pack(fill=tk.X, padx=5, pady=5)
        
        cols = ("idx", "valid", "tag", "data")
        self.cache_tree = ttk.Treeview(cache_frame, columns=cols, show="headings", height=6)
        for c in cols: self.cache_tree.heading(c, text=c.title())
        self.cache_tree.column("idx", width=30); self.cache_tree.column("valid", width=30)
        self.cache_tree.column("tag", width=40); self.cache_tree.column("data", width=60)
        self.cache_tree.pack(fill=tk.X)
        
        self.lbl_cache_status = ttk.Label(cache_frame, text="Status: IDLE", foreground="blue")
        self.lbl_cache_status.pack()

        # Memória
        mem_frame = ttk.LabelFrame(right_frame, text="Memória Principal (Double-click to Edit)")
        mem_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.mem_list = tk.Listbox(mem_frame, font=("Consolas", 9))
        self.mem_list.pack(fill=tk.BOTH, expand=True)
        self.mem_list.bind("<Double-Button-1>", self.edit_memory_value)

        self.update_ui()

    def fmt_val(self, val):
        """Formata valor baseado no modo Hex/Dec."""
        if self.display_hex:
            return f"{val:04X}"
        else:
            return f"{val}"

    def toggle_display_mode(self):
        self.display_hex = not self.display_hex
        self.btn_mode.config(text="Mode: HEX" if self.display_hex else "Mode: DEC")
        self.update_ui()

    def draw_box(self, x, y, w, h, name, value_hex):
        tag = f"reg_{name}"
        rect = self.canvas.create_rectangle(x, y, x+w, y+h, fill="#e1e1e1", outline="black", tags=tag)
        text = self.canvas.create_text(x+w/2, y+h/2, text=f"{name}\n{value_hex}", font=("Arial", 9, "bold"), tags=f"text_{name}")
        self.reg_rects[name] = rect
        self.reg_texts[name] = text

    def draw_bus_line(self, coords, tag, color="gray"):
        self.canvas.create_line(coords, fill=color, width=4, arrow=tk.LAST if 'c' in tag else tk.NONE, tags=tag)

    def draw_datapath_layout(self):
        self.canvas.delete("all")
        w, h = 80, 40
        cx = 300 # Center X
        
        # Barramentos (Desenhados primeiro para ficarem atrás)
        # Bus A (Esq -> ALU)
        self.draw_bus_line((130, 380, 260, 380, 260, 400), "bus_a") 
        # Bus B (Dir -> ALU)
        self.draw_bus_line((450, 380, 340, 380, 340, 400), "bus_b")
        # Bus C (Shifter -> Registradores/Mem)
        self.draw_bus_line((cx, 510, cx, 560, 10, 560, 10, 20, 490, 20, 490, 50), "bus_c")

        # Registradores Esq
        y = 50
        for name in ["MAR", "MDR", "PC", "MBR", "SP"]:
            self.draw_box(50, y, w, h, name, "0000")
            y += 60
            
        # Registradores Dir
        y = 50
        for name in ["LV", "CPP", "TOS", "OPC", "H"]:
            self.draw_box(450, y, w, h, name, "0000")
            y += 60

        # ALU
        self.canvas.create_polygon(cx, 400, cx-60, 400, cx-40, 460, cx+40, 460, cx+60, 400,
                                   fill="#ffcccb", outline="black", width=2)
        self.canvas.create_text(cx, 430, text="ALU", font=("Arial", 12, "bold"))
        
        # Shifter
        self.canvas.create_rectangle(cx-40, 480, cx+40, 510, fill="#add8e6", outline="black")
        self.canvas.create_text(cx, 495, text="Shifter", font=("Arial", 9))
        
        self.control_label_id = self.canvas.create_text(cx, 350, text="IDLE", fill="red", font=("Consolas", 12, "bold"))

    def animate_buses(self):
        """Ilumina os barramentos ativos brevemente."""
        act = self.cpu.bus_activity
        if act['bus_a']: self.canvas.itemconfig("bus_a", fill="red")
        if act['bus_b']: self.canvas.itemconfig("bus_b", fill="red")
        if act['bus_c']: self.canvas.itemconfig("bus_c", fill="red")
        
        # Desliga após 300ms
        self.root.after(300, self.reset_bus_colors)

    def reset_bus_colors(self):
        self.canvas.itemconfig("bus_a", fill="gray")
        self.canvas.itemconfig("bus_b", fill="gray")
        self.canvas.itemconfig("bus_c", fill="gray")

    def update_ui(self):
        # 1. Registradores
        regs = {
            "MAR": self.cpu.mar, "MDR": self.cpu.mdr, "PC": self.cpu.pc,
            "MBR": self.cpu.mbr, "SP": self.cpu.sp, "LV": self.cpu.lv,
            "CPP": self.cpu.cpp, "TOS": self.cpu.tos, "OPC": self.cpu.opc, "H": self.cpu.h
        }
        
        for name, reg in regs.items():
            val_str = self.fmt_val(reg.value)
            self.canvas.itemconfig(self.reg_texts[name], text=f"{name}\n{val_str}")
            if reg.value != 0:
                self.canvas.itemconfig(self.reg_rects[name], fill="#aaffaa")
            else:
                self.canvas.itemconfig(self.reg_rects[name], fill="#e1e1e1")

        # 2. Controle e Animação
        self.canvas.itemconfig(self.control_label_id, text=self.cpu.control_signals)
        self.animate_buses()
        
        # 3. Memória (Destaque para último acesso)
        self.mem_list.delete(0, tk.END)
        last_addr = self.cpu.memory.last_accessed_addr
        
        # Mostra região próxima ao PC e ao último acesso
        pc_val = self.cpu.pc.value
        start_show = max(0, min(pc_val - 5, last_addr - 5 if last_addr > 0 else 0))
        
        for i in range(start_show, start_show + 30): # Mostra janela de 30 palavras
            val = self.cpu.memory.ram[i]
            marker = " << " if i == last_addr else ""
            marker += " [PC]" if i == pc_val else ""
            
            self.mem_list.insert(tk.END, f"[{self.fmt_val(i)}]: {self.fmt_val(val)} {marker}")
            if i == last_addr:
                self.mem_list.itemconfig(tk.END, {'bg':'yellow'})
        
        # 4. Cache
        for i in self.cache_tree.get_children(): self.cache_tree.delete(i)
        for idx, line in enumerate(self.cpu.memory.cache_lines):
            v = "1" if line.valid else "0"
            t = self.fmt_val(line.tag)
            d = self.fmt_val(line.data)
            self.cache_tree.insert("", "end", values=(idx, v, t, d))
            
        self.lbl_cache_status.config(text=f"Status: {self.cpu.memory.last_access_status}")
        self.lbl_cycle.config(text=f"Cycles: {self.cpu.cycle_count}")

    def edit_memory_value(self, event):
        """Edição manual de memória ao clicar duas vezes."""
        selection = self.mem_list.curselection()
        if not selection: return
        
        item_text = self.mem_list.get(selection[0])
        # Extrai endereço do texto "[XXXX]: YYYY"
        try:
            addr_str = item_text.split(']:')[0].replace('[', '')
            addr = int(addr_str, 16) if self.display_hex else int(addr_str)
            
            new_val = simpledialog.askinteger("Editar Memória", f"Novo valor para endereço {addr}:")
            if new_val is not None:
                self.cpu.memory.write(addr, new_val)
                self.update_ui()
        except:
            pass

    def assemble_code(self):
        code = self.editor.get_code()
        machine_code, msg = assemble(code)
        if not machine_code and msg != "Sucesso":
            messagebox.showerror("Erro", msg)
            return
        self.reset_cpu()
        self.cpu.memory.load_program(machine_code)
        self.update_ui()
        messagebox.showinfo("Montagem", f"Sucesso! {len(machine_code)} palavras.")

    def step_cpu(self):
        if self.cpu.halted:
            messagebox.showinfo("Info", "CPU Halted.")
            self.is_running = False
            return
        self.cpu.execute_instruction()
        self.update_ui()

    def run_loop(self):
        while self.is_running and not self.cpu.halted:
            self.root.after(0, self.step_cpu)
            time.sleep(0.5)
        self.is_running = False

    def start_run(self):
        if not self.is_running:
            self.is_running = True
            threading.Thread(target=self.run_loop, daemon=True).start()

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