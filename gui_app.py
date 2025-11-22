import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from mic1_hardware import Mic1CPU
from assembler import assemble

class CodeEditor(tk.Frame):
    """
    Editor otimizado com numeração de linhas inteligente.
    """
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.line_numbers = tk.Text(self, width=4, padx=4, takefocus=0, border=0,
                                    background='#f0f0f0', state='disabled', font=("Consolas", 10))
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)
        
        self.text_area = tk.Text(self, font=("Consolas", 10), undo=True)
        self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.sync_scroll)
        self.vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_area['yscrollcommand'] = self.on_text_scroll

        # Tags de Cores
        self.text_area.tag_configure("keyword", foreground="blue", font=("Consolas", 10, "bold"))
        self.text_area.tag_configure("number", foreground="#c00000")
        self.text_area.tag_configure("comment", foreground="#008000") 
        self.text_area.tag_configure("label", foreground="#800080", font=("Consolas", 10, "bold"))

        self.text_area.bind("<<Change>>", self.on_change)
        self.text_area.bind("<KeyRelease>", self.on_change)
        
        self.prev_line_count = -1
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
        current_lines = self.text_area.get('1.0', 'end-1c').count('\n') + 1
        if current_lines != self.prev_line_count:
            line_content = "\n".join(str(i) for i in range(1, current_lines + 1))
            self.line_numbers.config(state='normal')
            self.line_numbers.delete('1.0', tk.END)
            self.line_numbers.insert('1.0', line_content)
            self.line_numbers.config(state='disabled')
            self.prev_line_count = current_lines
        self.line_numbers.yview_moveto(self.text_area.yview()[0])

    def highlight_syntax(self):
        for tag in ["keyword", "number", "comment", "label"]:
            self.text_area.tag_remove(tag, "1.0", tk.END)
        
        keywords = ["LODD", "STOD", "ADDD", "SUBD", "JPOS", "JZER", "JUMP", "LOCO", 
                    "LODL", "STOL", "ADDL", "SUBL", "JNEG", "JNZE", "CALL", "HALT",
                    "PUSH", "POP", "RETN", "SWAP", "PSHI", "POPI", "INSP", "DESP"]
        
        start_idx = "1.0"
        while True:
            pos = self.text_area.search(';', start_idx, stopindex=tk.END)
            if not pos: break
            line_end = self.text_area.index(f"{pos} lineend")
            self.text_area.tag_add("comment", pos, line_end)
            start_idx = line_end

        start_idx = "1.0"
        while True:
            pos = self.text_area.search(r'\w+', start_idx, stopindex=tk.END, regexp=True)
            if not pos: break
            end_pos = f"{pos} wordend"
            word = self.text_area.get(pos, end_pos).upper()
            
            if "comment" not in self.text_area.tag_names(pos):
                if word in keywords:
                    self.text_area.tag_add("keyword", pos, end_pos)
                elif word.isdigit() or (word.startswith('0X') and len(word)>2):
                    self.text_area.tag_add("number", pos, end_pos)
                else:
                    if self.text_area.get(end_pos, f"{end_pos}+1c") == ':':
                        self.text_area.tag_add("label", pos, f"{end_pos}+1c")
            start_idx = end_pos

    def get_code(self): return self.text_area.get("1.0", tk.END)
    def set_code(self, text):
        self.text_area.delete("1.0", tk.END)
        self.text_area.insert("1.0", text)
        self.on_change()


class Mic1GUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Simulador MIC-1 / MAC-1 v5.1 (Platinum)")
        self.root.geometry("1300x850")
        
        self.cpu = Mic1CPU()
        self.is_running = False
        self.display_hex = True 
        self.run_speed_ms = 500
        self.anim_job = None # Para controlar cancelamento da animação
        
        self.follow_pc = tk.BooleanVar(value=True)
        self.user_interacting = False 
        
        style = ttk.Style()
        style.theme_use('clam')
        
        self.paned_window = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # --- ESQUERDA ---
        left_frame = ttk.Frame(self.paned_window, width=380)
        self.paned_window.add(left_frame, weight=1)
        ttk.Label(left_frame, text="Editor Assembly", font=("Arial", 10, "bold")).pack(pady=5)
        self.editor = CodeEditor(left_frame)
        self.editor.pack(fill=tk.BOTH, expand=True, padx=2)
        
        default_code = """; Teste Platinum v5.1 - Stack & Recursao
LOCO 10     ; Contador = 10
STOD 100    ; Salva na RAM[100]
LOCO 0
STOD 101    ; Soma = 0

Loop:       ; Label
LODD 100
JZER Fim
PUSH        ; Empilha Contador
LODD 101
ADDL 0      ; Soma += Stack[Top]
STOD 101
POP         ; Limpa pilha
LODD 100
LOCO -1
ADDL 0      ; Decrementa
STOD 100
JUMP Loop

Fim:
HALT
"""
        self.editor.set_code(default_code)
        ttk.Button(left_frame, text="Montar (Assemble)", command=self.assemble_code).pack(fill=tk.X, pady=5)

        # --- CENTRO ---
        center_frame = ttk.Frame(self.paned_window, width=600)
        self.paned_window.add(center_frame, weight=3)
        ttk.Label(center_frame, text="Microarquitetura (Datapath)", font=("Arial", 10, "bold")).pack(pady=5)
        self.canvas = tk.Canvas(center_frame, bg="white", bd=2, relief="sunken")
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5)
        self.canvas.bind("<Configure>", self.on_canvas_resize)
        
        # --- DIREITA ---
        right_frame = ttk.Frame(self.paned_window, width=320)
        self.paned_window.add(right_frame, weight=1)
        
        ctrl_frame = ttk.LabelFrame(right_frame, text="Controles")
        ctrl_frame.pack(fill=tk.X, padx=5, pady=5)
        
        btn_f = ttk.Frame(ctrl_frame)
        btn_f.pack(fill=tk.X)
        ttk.Button(btn_f, text="Run", command=self.start_run).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_f, text="Step", command=self.step_cpu).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_f, text="Stop", command=self.stop_run).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_f, text="Reset", command=self.reset_cpu).pack(side=tk.LEFT, padx=2)
        
        self.btn_mode = ttk.Button(ctrl_frame, text="Mode: HEX", command=self.toggle_display_mode)
        self.btn_mode.pack(side=tk.RIGHT, padx=5, pady=2)
        
        spd_frame = ttk.Frame(ctrl_frame)
        spd_frame.pack(fill=tk.X, pady=2)
        ttk.Label(spd_frame, text="Speed:").pack(side=tk.LEFT)
        self.scale_speed = ttk.Scale(spd_frame, from_=50, to=1000, value=500, command=self.update_speed)
        self.scale_speed.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.lbl_cycle = ttk.Label(ctrl_frame, text="Cycles: 0 | Flags: N=0 Z=0")
        self.lbl_cycle.pack(side=tk.LEFT, padx=5)

        # --- Cache (Separada I/D) ---
        cache_main_frame = ttk.LabelFrame(right_frame, text="Caches L1 (Instrução & Dados)")
        cache_main_frame.pack(fill=tk.X, padx=5, pady=5)
        
        split_cache = ttk.Frame(cache_main_frame)
        split_cache.pack(fill=tk.X)

        cols = ("valid", "tag", "data")
        
        # I-Cache
        icache_frame = ttk.Frame(split_cache)
        icache_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2)
        ttk.Label(icache_frame, text="I-Cache", font=("Arial", 8, "bold")).pack()
        
        self.icache_tree = ttk.Treeview(icache_frame, columns=cols, show="headings", height=5)
        for c in cols:
            self.icache_tree.heading(c, text=c[0].upper()) # V, T, D
            self.icache_tree.column(c, width=35, anchor="center")
        self.icache_tree.pack(fill=tk.X)

        # D-Cache
        dcache_frame = ttk.Frame(split_cache)
        dcache_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2)
        ttk.Label(dcache_frame, text="D-Cache", font=("Arial", 8, "bold")).pack()

        self.dcache_tree = ttk.Treeview(dcache_frame, columns=cols, show="headings", height=5)
        for c in cols:
            self.dcache_tree.heading(c, text=c[0].upper())
            self.dcache_tree.column(c, width=35, anchor="center")
        self.dcache_tree.pack(fill=tk.X)
        
        self.lbl_cache_status = ttk.Label(cache_main_frame, text="Status: IDLE", foreground="blue")
        self.lbl_cache_status.pack()

        # Memória
        mem_frame = ttk.LabelFrame(right_frame, text="Memória Principal")
        mem_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        tk.Checkbutton(mem_frame, text="Follow PC (Auto-Scroll)", variable=self.follow_pc).pack(anchor=tk.W)
        
        mem_scroll = ttk.Scrollbar(mem_frame, orient="vertical")
        mem_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.mem_list = tk.Listbox(mem_frame, font=("Consolas", 10), yscrollcommand=mem_scroll.set)
        self.mem_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        mem_scroll.config(command=self.mem_list.yview)
        
        self.mem_list.bind("<Double-Button-1>", self.edit_memory_value)
        # Interação detectada na lista ou no scroll
        self.mem_list.bind("<Enter>", lambda e: self.set_interacting(True))
        self.mem_list.bind("<Leave>", lambda e: self.set_interacting(False))
        mem_scroll.bind("<Button-1>", lambda e: self.set_interacting(True))
        mem_scroll.bind("<ButtonRelease-1>", lambda e: self.set_interacting(False))

        self.reg_rects = {}
        self.reg_texts = {}
        self.control_label_id = None
        
        self.prev_pc = -1
        self.prev_sp = -1
        self.prev_addr = -1
        
        self.root.update_idletasks()
        self.draw_datapath_layout()
        self.init_memory_list()
        self.update_ui(full_refresh=True)

    def set_interacting(self, status):
        self.user_interacting = status

    def on_canvas_resize(self, event):
        if event.width > 100 and event.height > 100:
            self.draw_datapath_layout()

    def update_speed(self, val):
        self.run_speed_ms = int(float(val))

    def fmt_val(self, val):
        if self.display_hex:
            return f"{val & 0xFFFF:04X}"
        else:
            if val >= 0x8000: val -= 0x10000
            return f"{val}"

    def toggle_display_mode(self):
        scroll_pos = self.mem_list.yview()
        self.display_hex = not self.display_hex
        self.btn_mode.config(text="Mode: HEX" if self.display_hex else "Mode: DEC")
        self.update_ui(full_refresh=True)
        self.mem_list.yview_moveto(scroll_pos[0])

    def draw_box(self, x, y, w, h, name, value_hex):
        tag = f"reg_{name}"
        self.canvas.create_rectangle(x, y, x+w, y+h, fill="#e1e1e1", outline="black", tags=tag)
        self.canvas.create_text(x+w/2, y+15, text=name, font=("Arial", 8, "bold"))
        text = self.canvas.create_text(x+w/2, y+h/2+5, text=value_hex, font=("Consolas", 10, "bold"), tags=f"val_{name}")
        self.reg_rects[name] = tag
        self.reg_texts[name] = text

    def draw_bus_line(self, coords, tag):
        # arrow=tk.LAST para indicar direção do fluxo
        self.canvas.create_line(coords, fill="gray", width=4, arrow=tk.LAST, capstyle=tk.ROUND, joinstyle=tk.ROUND, tags=tag)

    def draw_datapath_layout(self):
        self.canvas.delete("all")
        self.reg_rects = {}
        self.reg_texts = {}
        
        cw = self.canvas.winfo_width()
        if cw < 100: cw = 600
        cx = cw // 2
        w, h = 70, 45
        y_start = 50
        gap_y = 60
        gap_x = 180
        
        # Barramento A (Esquerda -> ALU Esq)
        self.draw_bus_line((cx - gap_x + w, 380, cx - 40, 380, cx - 40, 400), "bus_a")
        
        # Barramento B (Direita -> ALU Dir)
        self.draw_bus_line((cx + gap_x, 380, cx + 40, 380, cx + 40, 400), "bus_b")
        
        # Barramento C (ALU/Shifter -> Registradores)
        self.draw_bus_line((cx, 510, cx, 550, cx - gap_x - 40, 550, cx - gap_x - 40, 20, cx + gap_x + 40, 20, cx + gap_x + 40, 50), "bus_c")

        def get_reg(rname):
            if not hasattr(self, 'cpu'): return "0000"
            return self.fmt_val(getattr(self.cpu, rname.lower()).value)

        # Banco de Registradores
        for i, name in enumerate(["MAR", "MDR", "PC", "MBR", "SP"]):
            self.draw_box(cx - gap_x, y_start + i*gap_y, w, h, name, get_reg(name))
        
        for i, name in enumerate(["LV", "CPP", "TOS", "OPC", "H"]):
            self.draw_box(cx + gap_x - w, y_start + i*gap_y, w, h, name, get_reg(name))

        # ALU
        self.canvas.create_polygon(cx-50, 400, cx+50, 400, cx+30, 450, cx-30, 450, fill="#ffcccb", outline="black", width=2)
        self.canvas.create_text(cx, 425, text="ALU", font=("Arial", 11, "bold"))
        
        # Shifter
        self.canvas.create_rectangle(cx-30, 480, cx+30, 510, fill="#add8e6", outline="black")
        self.canvas.create_text(cx, 495, text="Shifter", font=("Arial", 9))
        self.canvas.create_line(cx, 450, cx, 480, width=4, fill="gray") # Link ALU-Shifter

        sig = self.cpu.control_signals if hasattr(self, 'cpu') else "RESET"
        self.control_label_id = self.canvas.create_text(cx, 350, text=sig, fill="red", font=("Consolas", 12, "bold"))
        
        if hasattr(self, 'cpu'): self.update_ui_values_only()

    def animate_buses(self):
        # Cancela animação anterior para evitar conflito de cores
        if self.anim_job:
            self.root.after_cancel(self.anim_job)
            # Garante que volta ao cinza antes de reacender
            for t in ["bus_a", "bus_b", "bus_c"]: self.canvas.itemconfig(t, fill="gray")

        act = self.cpu.bus_activity
        c = "#FF4444"
        if act['bus_a']: self.canvas.itemconfig("bus_a", fill=c)
        if act['bus_b']: self.canvas.itemconfig("bus_b", fill=c)
        if act['bus_c']: self.canvas.itemconfig("bus_c", fill=c)
        
        # Define tempo baseado na velocidade, mas no mínimo 100ms para ser visível
        delay = min(300, max(100, self.run_speed_ms // 2))
        self.anim_job = self.root.after(delay, lambda: [self.canvas.itemconfig(t, fill="gray") for t in ["bus_a", "bus_b", "bus_c"]])

    def init_memory_list(self):
        self.mem_list.delete(0, tk.END)
        for i in range(4096):
            self.mem_list.insert(tk.END, f"[{i:03X}]: {self.fmt_val(0)}")

    def update_memory_row(self, idx, is_pc=False, is_sp=False, is_access=False):
        val = self.cpu.memory.ram[idx]
        markers = []
        if is_pc: markers.append("PC")
        if is_sp: markers.append("SP")
        marker_str = f" [{', '.join(markers)}]" if markers else ""
        
        text = f"[{idx:03X}]: {self.fmt_val(val)}{marker_str}"
        self.mem_list.delete(idx)
        self.mem_list.insert(idx, text)
        
        bg = "white"
        if is_access: bg = "#ffffcc"
        elif is_pc: bg = "#e6f3ff"
        elif is_sp: bg = "#ffe6e6"
        self.mem_list.itemconfig(idx, {'bg': bg})

    def update_ui(self, full_refresh=False):
        self.update_ui_values_only()
        
        curr_pc = self.cpu.pc.value
        curr_sp = self.cpu.sp.value
        curr_addr = self.cpu.memory.last_accessed_addr
        
        idxs = {curr_pc, curr_sp, curr_addr, self.prev_pc, self.prev_sp, self.prev_addr}
        idxs.discard(-1)
        
        if full_refresh:
            self.mem_list.delete(0, tk.END)
            for i in range(4096):
                val = self.cpu.memory.ram[i]
                self.mem_list.insert(tk.END, f"[{i:03X}]: {self.fmt_val(val)}")
            for idx in [curr_pc, curr_sp, curr_addr]:
                 if 0 <= idx < 4096:
                    self.update_memory_row(idx, idx==curr_pc, idx==curr_sp, idx==curr_addr)
        else:
            for idx in idxs:
                if 0 <= idx < 4096:
                    self.update_memory_row(idx, idx==curr_pc, idx==curr_sp, idx==curr_addr)
        
        # Auto-scroll mais robusto
        if self.follow_pc.get() and not self.user_interacting and (self.is_running or not full_refresh):
            self.mem_list.see(curr_pc)
        
        self.prev_pc, self.prev_sp, self.prev_addr = curr_pc, curr_sp, curr_addr

        # --- Atualiza Caches com Formatação HEX ---
        for i in self.icache_tree.get_children(): self.icache_tree.delete(i)
        for i in self.dcache_tree.get_children(): self.dcache_tree.delete(i)

        for line in self.cpu.memory.i_cache.lines:
            tag_str = f"{line['tag']:03X}" if line['valid'] else "000"
            self.icache_tree.insert("", "end", values=("1" if line['valid'] else "0", tag_str, self.fmt_val(line['data'])))
            
        for line in self.cpu.memory.d_cache.lines:
            tag_str = f"{line['tag']:03X}" if line['valid'] else "000"
            self.dcache_tree.insert("", "end", values=("1" if line['valid'] else "0", tag_str, self.fmt_val(line['data'])))

        last_st = f"I: {self.cpu.memory.i_cache.last_status} | D: {self.cpu.memory.d_cache.last_status}"
        self.lbl_cache_status.config(text=last_st)

    def update_ui_values_only(self):
        for name in self.reg_texts:
            reg = getattr(self.cpu, name.lower())
            val_str = self.fmt_val(reg.value)
            self.canvas.itemconfig(self.reg_texts[name], text=val_str)
            color = "#ccffcc" if reg.value != 0 else "#e1e1e1"
            self.canvas.itemconfig(self.reg_rects[name], fill=color)

        self.canvas.itemconfig(self.control_label_id, text=self.cpu.control_signals)
        self.lbl_cycle.config(text=f"Cycles: {self.cpu.cycle_count} | Flags: N={int(self.cpu.alu.n_flag)} Z={int(self.cpu.alu.z_flag)}")
        self.animate_buses()

    def edit_memory_value(self, event):
        sel = self.mem_list.curselection()
        if not sel: return
        addr = sel[0]
        
        prompt = f"Valor para Mem[{addr:03X}]" + (" (HEX):" if self.display_hex else ":")
        self.user_interacting = True 
        res = simpledialog.askstring("Editar", prompt)
        self.user_interacting = False
        
        if res:
            try:
                val = 0
                # Tratamento robusto de input
                clean_res = res.strip().upper()
                if self.display_hex:
                    val = int(clean_res, 16)
                elif clean_res.startswith("0X"):
                    val = int(clean_res, 16)
                else:
                    val = int(clean_res)
                
                self.cpu.memory.write(addr, val)
                self.update_memory_row(addr, addr==self.cpu.pc.value, addr==self.cpu.sp.value, True)
            except ValueError:
                messagebox.showerror("Erro", "Valor inválido! Use formato compatível com o modo (HEX/DEC).")

    def assemble_code(self):
        mc, msg = assemble(self.editor.get_code())
        if not mc and msg != "Sucesso":
            messagebox.showerror("Erro", msg)
            return
        self.reset_cpu()
        self.cpu.memory.load_program(mc)
        self.update_ui(full_refresh=True)
        messagebox.showinfo("Montagem", f"Sucesso! {len(mc)} palavras.")

    def step_cpu(self):
        if self.cpu.halted:
            self.is_running = False
            messagebox.showinfo("Fim", "CPU Halt.")
            return
        try:
            self.cpu.execute_instruction()
            self.update_ui()
        except Exception as e:
            self.is_running = False
            messagebox.showerror("Runtime Error", str(e))

    def start_run(self):
        if not self.is_running:
            self.is_running = True
            self.run_loop()

    def run_loop(self):
        if self.is_running and not self.cpu.halted:
            self.step_cpu()
            self.root.after(self.run_speed_ms, self.run_loop)
        else:
            self.is_running = False

    def stop_run(self): self.is_running = False
    def reset_cpu(self):
        self.stop_run()
        
        # Reset limpa os registradores 'prev' para evitar glitches visuais
        self.prev_pc = -1
        self.prev_sp = -1
        self.prev_addr = -1
        
        self.cpu.reset()
        self.update_ui(full_refresh=True)

if __name__ == "__main__":
    root = tk.Tk()
    app = Mic1GUI(root)
    root.mainloop()