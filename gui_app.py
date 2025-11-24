import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from mic1_hardware import Mic1CPU, Opcode
from assembler import assemble, OPCODES 

class CodeEditor(tk.Frame):
    """
    Widget de editor de texto com numeração e syntax highlighting.
    """
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.line_numbers = tk.Text(self, width=4, padx=4, takefocus=0, border=0,
                                    background='#f0f0f0', state='disabled', font=("Consolas", 10))
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)
        
        self.text_area = tk.Text(self, font=("Consolas", 10), undo=True, wrap="none")
        self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.sync_scroll)
        self.vsb.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.hsb = ttk.Scrollbar(self, orient="horizontal", command=self.text_area.xview)
        self.hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.text_area['xscrollcommand'] = self.hsb.set
        self.text_area['yscrollcommand'] = self.on_text_scroll

        self.text_area.tag_configure("keyword", foreground="blue", font=("Consolas", 10, "bold"))
        self.text_area.tag_configure("number", foreground="#c00000")
        self.text_area.tag_configure("comment", foreground="#008000") 
        self.text_area.tag_configure("label", foreground="#800080", font=("Consolas", 10, "bold"))
        self.text_area.tag_configure("directive", foreground="#804000", font=("Consolas", 10, "bold"))

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
        for tag in ["keyword", "number", "comment", "label", "directive"]:
            self.text_area.tag_remove(tag, "1.0", tk.END)
        
        keywords = list(OPCODES.keys())
        
        start_idx = "1.0"
        while True:
            pos = self.text_area.search(';', start_idx, stopindex=tk.END)
            if not pos: break
            line_end = self.text_area.index(f"{pos} lineend")
            self.text_area.tag_add("comment", pos, line_end)
            start_idx = line_end

        start_idx = "1.0"
        while True:
            pos = self.text_area.search(r'[\.\w]+', start_idx, stopindex=tk.END, regexp=True)
            if not pos: break
            end_pos = f"{pos} wordend"
            word = self.text_area.get(pos, end_pos).upper()
            
            if "comment" not in self.text_area.tag_names(pos):
                if word in keywords:
                    self.text_area.tag_add("keyword", pos, end_pos)
                elif word.startswith("."):
                     self.text_area.tag_add("directive", pos, end_pos)
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
    """
    Aplicação GUI principal para o Simulador MIC-1.
    """
    def __init__(self, root):
        self.root = root
        self.root.title("Simulador MIC-1 / MAC-1 v6.2 (Polido)")
        self.root.geometry("1400x900")
        
        self.cpu = Mic1CPU()
        self.is_running = False
        self.display_hex = True 
        self.run_speed_ms = 500
        self.anim_job = None
        self.reset_lines_job = None # Controle de concorrência visual
        self.visual_micro_step = 0 
        
        self.follow_pc = tk.BooleanVar(value=True)
        self.user_interacting = False 
        
        self.rev_opcodes = {}
        for k, v in OPCODES.items():
            self.rev_opcodes[v] = k
        
        style = ttk.Style()
        style.theme_use('clam')
        
        self.paned_window = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Painel Esquerdo: Editor
        left_frame = ttk.Frame(self.paned_window, width=380)
        self.paned_window.add(left_frame, weight=1)
        ttk.Label(left_frame, text="Editor Assembly", font=("Arial", 10, "bold")).pack(pady=5)
        self.editor = CodeEditor(left_frame)
        self.editor.pack(fill=tk.BOTH, expand=True, padx=2)
        
        default_code = """; --- ÁREA DE DADOS ---
PRECO:  .DATA 100 20   
FRETE:  .DATA 101 50   
TOTAL:  .DATA 102 0    

; --- INÍCIO DO PROGRAMA ---
Inicio:
    LODD PRECO   ; Busca valor de PRECO (20)
    SUBD FRETE   ; Subtrai FRETE (20 - 50 = -30)
    JPOS Maior   ; Se AC > 0, Pula (Não deve pular pois é negativo)
    
    ; Se chegou aqui, é menor ou igual
    LOCO 1       ; Carrega 1 para indicar "Menor/Igual"
    STOD TOTAL
    JUMP Fim

Maior:
    LOCO 2       ; Carrega 2 para indicar "Maior"
    STOD TOTAL

Fim:
    HALT
"""
        self.editor.set_code(default_code)
        ttk.Button(left_frame, text="Montar (Assemble)", command=self.assemble_code).pack(fill=tk.X, pady=5)

        # Painel Central
        center_frame = ttk.Frame(self.paned_window, width=650)
        self.paned_window.add(center_frame, weight=3)
        ttk.Label(center_frame, text="Microarquitetura (Datapath MIC-1)", font=("Arial", 10, "bold")).pack(pady=5)
        
        canvas_frame = ttk.Frame(center_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(canvas_frame, bg="white", bd=2, relief="sunken")
        vbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        hbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)
        
        vbar.pack(side=tk.RIGHT, fill=tk.Y)
        hbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        self.canvas.bind("<Configure>", self.on_canvas_resize)
        
        # Painel Direito
        right_frame = ttk.Frame(self.paned_window, width=320)
        self.paned_window.add(right_frame, weight=1)
        
        ctrl_frame = ttk.LabelFrame(right_frame, text="Controles")
        ctrl_frame.pack(fill=tk.X, padx=5, pady=5)
        
        btn_f = ttk.Frame(ctrl_frame)
        btn_f.pack(fill=tk.X)
        ttk.Button(btn_f, text="Run", command=self.start_run).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_f, text="Step", command=self.step_button_action).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_f, text="Stop", command=self.stop_run).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_f, text="Reset", command=self.reset_cpu).pack(side=tk.LEFT, padx=2)
        
        # Polimento UX: Texto explícito sobre o estado atual
        self.btn_mode = ttk.Button(ctrl_frame, text="Visualização: HEX", command=self.toggle_display_mode)
        self.btn_mode.pack(side=tk.RIGHT, padx=5, pady=2)
        
        spd_frame = ttk.Frame(ctrl_frame)
        spd_frame.pack(fill=tk.X, pady=2)
        ttk.Label(spd_frame, text="Speed:").pack(side=tk.LEFT)
        self.scale_speed = ttk.Scale(spd_frame, from_=50, to=1000, value=500, command=self.update_speed)
        self.scale_speed.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.lbl_cycle = ttk.Label(ctrl_frame, text="Cycles: 0 | Flags: N=0 Z=0")
        self.lbl_cycle.pack(side=tk.LEFT, padx=5)
        self.lbl_micro = ttk.Label(ctrl_frame, text="Phase: IDLE", foreground="red")
        self.lbl_micro.pack(side=tk.RIGHT, padx=5)

        cache_main_frame = ttk.LabelFrame(right_frame, text="Caches L1 (Split)")
        cache_main_frame.pack(fill=tk.X, padx=5, pady=5)
        split_cache = ttk.Frame(cache_main_frame)
        split_cache.pack(fill=tk.X)
        cols = ("valid", "tag", "data")
        
        # Polimento UX: Colunas mais largas para melhor leitura
        col_width = 45
        
        icache_frame = ttk.Frame(split_cache)
        icache_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2)
        ttk.Label(icache_frame, text="I-Cache", font=("Arial", 8, "bold")).pack()
        self.icache_tree = ttk.Treeview(icache_frame, columns=cols, show="headings", height=5)
        for c in cols: 
            self.icache_tree.heading(c, text=c[0].upper())
            self.icache_tree.column(c, width=col_width, anchor="center")
        self.icache_tree.pack(fill=tk.X)

        dcache_frame = ttk.Frame(split_cache)
        dcache_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2)
        ttk.Label(dcache_frame, text="D-Cache", font=("Arial", 8, "bold")).pack()
        self.dcache_tree = ttk.Treeview(dcache_frame, columns=cols, show="headings", height=5)
        for c in cols: 
            self.dcache_tree.heading(c, text=c[0].upper())
            self.dcache_tree.column(c, width=col_width, anchor="center")
        self.dcache_tree.pack(fill=tk.X)
        
        self.lbl_cache_status = ttk.Label(cache_main_frame, text="Status: IDLE", foreground="blue")
        self.lbl_cache_status.pack()

        mem_frame = ttk.LabelFrame(right_frame, text="Memória Principal")
        mem_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.lbl_curr_instr = tk.Label(mem_frame, text="Inicializado", 
                                       bg="#d9edf7", fg="#31708f", font=("Consolas", 11, "bold"), 
                                       relief="solid", bd=1, padx=5, pady=5)
        self.lbl_curr_instr.pack(fill=tk.X, padx=2, pady=2)

        tk.Checkbutton(mem_frame, text="Follow PC", variable=self.follow_pc).pack(anchor=tk.W)
        
        mem_scroll = ttk.Scrollbar(mem_frame, orient="vertical")
        mem_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.mem_list = tk.Listbox(mem_frame, font=("Consolas", 10), yscrollcommand=mem_scroll.set)
        self.mem_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        mem_scroll.config(command=self.mem_list.yview)
        
        self.mem_list.bind("<Double-Button-1>", self.edit_memory_value)
        self.mem_list.bind("<Enter>", lambda e: self.set_interacting(True))
        self.mem_list.bind("<Leave>", lambda e: self.set_interacting(False))
        mem_scroll.bind("<Button-1>", lambda e: self.set_interacting(True))
        mem_scroll.bind("<ButtonRelease-1>", lambda e: self.set_interacting(False))

        self.reg_rects = {}
        self.reg_texts = {}
        self.bus_ids = {}
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
        # Polimento UX: Texto reflete o estado ATUAL
        mode_text = "HEX" if self.display_hex else "DEC"
        self.btn_mode.config(text=f"Visualização: {mode_text}")
        self.update_ui(full_refresh=True)
        self.mem_list.yview_moveto(scroll_pos[0])

    def draw_box(self, x, y, w, h, name, value_hex):
        tag = f"reg_{name}"
        self.canvas.create_rectangle(x, y, x+w, y+h, fill="#e1e1e1", outline="black", tags=tag)
        self.canvas.create_text(x+w/2, y+15, text=name, font=("Arial", 8, "bold"))
        text = self.canvas.create_text(x+w/2, y+h/2+5, text=value_hex, font=("Consolas", 10, "bold"), tags=f"val_{name}")
        self.reg_rects[name] = tag
        self.reg_texts[name] = text

    def draw_line(self, coords, color="gray", width=2, arrow=None, tags=None):
        return self.canvas.create_line(coords, fill=color, width=width, arrow=arrow, 
                                     capstyle=tk.ROUND, joinstyle=tk.ROUND, tags=tags)

    def draw_datapath_layout(self):
        """
        Desenha o Datapath da MIC-1.
        """
        self.canvas.delete("all")
        self.reg_rects = {}
        self.reg_texts = {}
        self.bus_ids = {}

        cw = self.canvas.winfo_width()
        if cw < 100: cw = 650
        cx = cw // 2
        
        reg_w, reg_h = 70, 40
        y_start = 40 
        gap_y = 50
        
        bus_b_x = cx - 120 
        bus_c_x = cx + 120
        reg_x   = cx - reg_w // 2
        
        reg_order = ["MAR", "MDR", "PC", "MBR", "SP", "LV", "CPP", "TOS", "OPC", "H"]
        total_h = y_start + len(reg_order) * gap_y + 150
        self.canvas.configure(scrollregion=(0, 0, cw, total_h))

        self.canvas.create_text(bus_b_x - 20, y_start - 20, text="Bus B", font=("Arial", 9, "bold"), fill="#555")
        self.canvas.create_text(bus_c_x + 20, y_start - 20, text="Bus C", font=("Arial", 9, "bold"), fill="#555")
        
        bus_bottom_y = y_start + len(reg_order) * gap_y + 20
        
        self.bus_ids['main_bus_b'] = self.draw_line((bus_b_x, y_start, bus_b_x, bus_bottom_y), width=4, tags="main_bus_b")
        self.bus_ids['main_bus_c'] = self.draw_line((bus_c_x, y_start, bus_c_x, bus_bottom_y + 60), width=4, tags="main_bus_c")

        def get_reg(rname):
            if not hasattr(self, 'cpu'): return "0000"
            return self.fmt_val(getattr(self.cpu, rname.lower()).value)

        for i, name in enumerate(reg_order):
            y = y_start + i * gap_y
            self.draw_box(reg_x, y, reg_w, reg_h, name, get_reg(name))
            
            self.bus_ids[f'c_to_{name}'] = self.draw_line(
                (bus_c_x, y + reg_h/2, reg_x + reg_w, y + reg_h/2), 
                arrow=tk.LAST, tags=f"c_to_{name}"
            )
            
            if name not in ["MAR", "H"]:
                self.bus_ids[f'{name}_to_b'] = self.draw_line(
                    (reg_x, y + reg_h/2, bus_b_x, y + reg_h/2), 
                    arrow=tk.LAST, tags=f"{name}_to_b"
                )

        h_y = y_start + (len(reg_order)-1) * gap_y
        alu_in_a_x = cx - 20
        alu_y = bus_bottom_y
        
        self.bus_ids['h_to_alu_a'] = self.draw_line(
            (reg_x, h_y + reg_h, reg_x + 20, h_y + reg_h + 20, alu_in_a_x, alu_y), 
            width=3, arrow=tk.LAST, tags="h_to_alu_a"
        )
        self.canvas.create_text(reg_x - 30, h_y + reg_h + 10, text="Bus A", font=("Arial", 8, "bold"), fill="#555")

        # ALU (Forma Gráfica)
        self.canvas.create_polygon(cx-40, alu_y, cx+40, alu_y, cx+20, alu_y+50, cx-20, alu_y+50, 
                                   fill="#ffcccb", outline="black", width=2)
        self.canvas.create_text(cx, alu_y+25, text="ALU", font=("Arial", 11, "bold"))
        
        self.draw_line((bus_b_x, bus_bottom_y, cx-30, bus_bottom_y), arrow=tk.LAST, tags="bus_b_to_alu")

        shift_y = alu_y + 60
        self.canvas.create_rectangle(cx-30, shift_y, cx+30, shift_y+30, fill="#add8e6", outline="black")
        self.canvas.create_text(cx, shift_y+15, text="Shifter", font=("Arial", 9))
        
        self.canvas.create_line(cx, alu_y+50, cx, shift_y, width=4, fill="gray", tags="alu_to_shifter")
        
        self.draw_line((cx, shift_y+30, cx, shift_y+45, bus_c_x, shift_y+45, bus_c_x, bus_bottom_y + 60), 
                       width=4, arrow=tk.LAST, tags="bus_c")

        ram_x = bus_b_x - 80
        ram_y = y_start
        self.canvas.create_rectangle(ram_x, ram_y, ram_x + 60, ram_y + gap_y + reg_h, fill="#fff0b3", outline="black")
        self.canvas.create_text(ram_x + 30, ram_y + gap_y, text="RAM", font=("Arial", 10, "bold"))
        
        self.draw_line((reg_x, y_start + 10, ram_x + 60, y_start + 10), arrow=tk.LAST, color="black", width=1, tags="ram_addr")
        
        mdr_y = y_start + gap_y
        self.draw_line((ram_x + 60, mdr_y + 20, reg_x, mdr_y + 20), arrow=tk.BOTH, color="black", width=1, tags="ram_data")

        sig = self.cpu.control_signals if hasattr(self, 'cpu') else "RESET"
        self.control_label_id = self.canvas.create_text(cx, 20, text=sig, fill="red", font=("Consolas", 14, "bold"), anchor="center")

        if hasattr(self, 'cpu'): self.update_ui_values_only()

    def animate_buses(self):
        # Cancelar reset anterior se houver (evita race condition visual)
        if self.reset_lines_job:
            self.root.after_cancel(self.reset_lines_job)
            self.reset_lines_job = None
            self.reset_lines()

        if self.anim_job:
            self.root.after_cancel(self.anim_job)

        active_color = "#FF4444"
        tags_to_light = []
        
        opcode = self.cpu.current_opcode
        step = self.visual_micro_step
        
        bus_activity = self.cpu.bus_activity

        # Polimento Acadêmico: Nomes de fases mais precisos
        if step == 1: 
            tags_to_light = ["main_bus_b", "PC_to_b", "main_bus_c", "bus_c", "c_to_MAR"]
            self.lbl_micro.config(text="1. BUSCA (Fetch: PC -> MAR)")

        elif step == 2:
            tags_to_light = []
            if bus_activity['mem_read']: tags_to_light += ["ram_addr", "ram_data"]
            tags_to_light += ["c_to_MDR", "main_bus_c", "bus_c", "c_to_MBR"]
            self.lbl_micro.config(text="2. DECODIFICAÇÃO (Decode)")

        elif step == 3:
            self.lbl_micro.config(text="3. EXECUÇÃO (Execute)")
            
            if bus_activity['bus_b']: tags_to_light.append("main_bus_b")
            if bus_activity['bus_b']: tags_to_light.append("bus_b_to_alu")
            if bus_activity['bus_a']: tags_to_light.append("h_to_alu_a") 

            if opcode in [Opcode.ADDD, Opcode.SUBD, Opcode.LODD, Opcode.ADDL, Opcode.SUBL]:
                 tags_to_light += ["MDR_to_b", "h_to_alu_a"]
                 if bus_activity['mem_read']: tags_to_light.append("ram_data") 
            elif opcode == Opcode.STOD:
                 tags_to_light += ["h_to_alu_a"]
            elif opcode in [Opcode.LOCO, Opcode.JUMP, Opcode.JPOS, Opcode.JZER, Opcode.JNEG, Opcode.JNZE]:
                 tags_to_light += ["MBR_to_b"]
            elif opcode == Opcode.CALL:
                 tags_to_light += ["SP_to_b", "h_to_alu_a"]

        elif step == 4:
            self.lbl_micro.config(text="4. GRAVAÇÃO (Write Back)")
            
            base_tags = ["alu_to_shifter", "main_bus_c", "bus_c"]
            tags_to_light = base_tags[:]
            
            if bus_activity['mem_write']: tags_to_light += ["ram_addr", "ram_data"]
            
            if opcode in [Opcode.LODD, Opcode.ADDD, Opcode.SUBD, Opcode.LOCO, Opcode.LODL, Opcode.ADDL, Opcode.SUBL]:
                 tags_to_light += ["c_to_H"]
            elif opcode == Opcode.STOD:
                 tags_to_light += ["c_to_MDR"]
            elif opcode in [Opcode.JUMP, Opcode.JPOS, Opcode.JZER, Opcode.JNEG, Opcode.JNZE]:
                 if bus_activity['bus_c']: tags_to_light += ["c_to_PC"]
            elif opcode == Opcode.CALL:
                 tags_to_light += ["c_to_SP"]

        for tag in tags_to_light: 
            if "ram" in tag:
                self.canvas.itemconfig(tag, fill=active_color, width=3)
            else:
                self.canvas.itemconfig(tag, fill=active_color)
            
        delay = min(300, max(100, self.run_speed_ms // 2))
        self.anim_job = self.root.after(delay, self.reset_lines_callback)

    def reset_lines_callback(self):
        self.reset_lines()
        self.reset_lines_job = None

    def reset_lines(self):
        for t in ["main_bus_b", "main_bus_c", "bus_c", "bus_a", "h_to_alu_a", "bus_b_to_alu", "alu_to_shifter"]: 
            self.canvas.itemconfig(t, fill="gray")
        for item in self.canvas.find_all():
            tags = self.canvas.gettags(item)
            for t in tags:
                if "_to_" in t or "ram_" in t:
                    if "ram" in t: self.canvas.itemconfig(item, fill="black", width=1)
                    else: self.canvas.itemconfig(item, fill="gray")

    def init_memory_list(self):
        self.mem_list.delete(0, tk.END)
        for i in range(4096): 
            self.mem_list.insert(tk.END, f"[{i:03X} | {i:04d}]: {self.fmt_val(0)}")

    def update_memory_row(self, idx, is_pc=False, is_sp=False, is_access=False):
        if idx < 0 or idx >= 4096: return
        
        val = self.cpu.memory.ram[idx]
        markers = []
        if is_pc: markers.append("PC")
        if is_sp: markers.append("SP")
        marker_str = f" [{', '.join(markers)}]" if markers else ""
        
        text = f"[{idx:03X} | {idx:04d}]: {self.fmt_val(val)}{marker_str}"
        
        try:
            if self.mem_list.get(idx) != text:
                self.mem_list.delete(idx)
                self.mem_list.insert(idx, text)
            
            bg = "white"
            if is_access: bg = "#ffffcc"
            elif is_pc: bg = "#e6f3ff"
            elif is_sp: bg = "#ffe6e6"
            self.mem_list.itemconfig(idx, {'bg': bg})
        except Exception: pass

    def update_ui(self, full_refresh=False):
        self.update_ui_values_only()
        
        curr_pc = self.cpu.pc.value
        curr_sp = self.cpu.sp.value
        curr_addr = self.cpu.memory.last_accessed_addr
        
        target_addr = curr_pc
        if 0 <= target_addr < 4096:
            raw_instr = self.cpu.memory.ram[target_addr]
            opcode_base = raw_instr & 0xF000
            operand = raw_instr & 0xFFF
            
            mnemonic = self.rev_opcodes.get(opcode_base, "UNK")
            if opcode_base == 0xF000: 
                mnemonic = self.rev_opcodes.get(raw_instr, "UNK")
                
            instr_str = f"{mnemonic} {operand:03X}" if self.display_hex else f"{mnemonic} {operand}"
            self.lbl_curr_instr.config(text=f"Next: [{target_addr:03X}] | {instr_str}")

        idxs = {curr_pc, curr_sp, curr_addr, self.prev_pc, self.prev_sp, self.prev_addr}
        idxs.discard(-1)
        
        if full_refresh:
            self.mem_list.delete(0, tk.END)
            for i in range(4096):
                val = self.cpu.memory.ram[i]
                self.mem_list.insert(tk.END, f"[{i:03X} | {i:04d}]: {self.fmt_val(val)}")
            for idx in [curr_pc, curr_sp, curr_addr]:
                 if 0 <= idx < 4096: self.update_memory_row(idx, idx==curr_pc, idx==curr_sp, idx==curr_addr)
        else:
            for idx in idxs:
                if 0 <= idx < 4096: self.update_memory_row(idx, idx==curr_pc, idx==curr_sp, idx==curr_addr)
        
        if self.follow_pc.get() and not self.user_interacting and (self.is_running or not full_refresh):
            self.mem_list.see(curr_pc)
        
        self.prev_pc, self.prev_sp, self.prev_addr = curr_pc, curr_sp, curr_addr

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
            if hasattr(self.cpu, name.lower()):
                reg = getattr(self.cpu, name.lower())
                val_str = self.fmt_val(reg.value)
                self.canvas.itemconfig(self.reg_texts[name], text=val_str)
                color = "#ccffcc" if reg.value != 0 else "#e1e1e1"
                self.canvas.itemconfig(self.reg_rects[name], fill=color)

        self.canvas.itemconfig(self.control_label_id, text=self.cpu.control_signals)
        self.lbl_cycle.config(text=f"Cycles: {self.cpu.cycle_count} | Flags: N={int(self.cpu.alu.n_flag)} Z={int(self.cpu.alu.z_flag)}")
        
        if not self.is_running:
            self.animate_buses()

    def edit_memory_value(self, event):
        sel = self.mem_list.curselection()
        if not sel: return
        addr = sel[0]
        
        prompt = f"Valor para Mem[{addr:03X} | {addr:04d}]" + (" (HEX):" if self.display_hex else ":")
        self.user_interacting = True 
        res = simpledialog.askstring("Editar", prompt)
        self.user_interacting = False
        
        if res:
            try:
                val = 0
                clean_res = res.strip().upper()
                if self.display_hex: val = int(clean_res, 16)
                elif clean_res.startswith("0X"): val = int(clean_res, 16)
                else: val = int(clean_res)
                
                self.cpu.memory.write(addr, val)
                self.update_memory_row(addr, addr==self.cpu.pc.value, addr==self.cpu.sp.value, True)
            except ValueError: messagebox.showerror("Erro", "Valor inválido! Use formato compatível com o modo (HEX/DEC).")

    def assemble_code(self):
        mc, msg = assemble(self.editor.get_code())
        if not mc and msg != "Sucesso":
            messagebox.showerror("Erro", msg)
            return
        
        self.reset_cpu()
        self.cpu.memory.load_program(mc)
        self.update_ui(full_refresh=True)
        
        count = len(mc) if isinstance(mc, dict) else len(mc)
        messagebox.showinfo("Montagem", f"Sucesso! {count} palavras/instruções carregadas.")

    def perform_micro_step(self):
        """
        Executa um micro-passo lógico da CPU e atualiza a UI.
        Retorna True se o ciclo foi concluído (voltou para 0), False caso contrário.
        """
        if self.cpu.halted:
            self.is_running = False
            messagebox.showinfo("Fim", "CPU Halt.")
            return True

        if self.visual_micro_step == 0:
            self.visual_micro_step = 1
            self.cpu.step_1_fetch_addr() 
            self.update_ui()
            return False
            
        elif self.visual_micro_step == 1:
            self.visual_micro_step = 2
            self.cpu.step_2_fetch_mem_decode() 
            self.update_ui()
            return False
            
        elif self.visual_micro_step == 2:
            self.visual_micro_step = 3
            self.update_ui()
            return False
            
        elif self.visual_micro_step == 3:
            self.visual_micro_step = 4
            try:
                self.cpu.execute_micro_instruction() 
                self.update_ui()
            except Exception as e:
                self.is_running = False
                messagebox.showerror("Runtime Error", str(e))
                return True # Erro força fim
            return False
                
        elif self.visual_micro_step == 4:
            self.visual_micro_step = 0
            self.lbl_micro.config(text="Phase: IDLE (Next Instr)")
            self.reset_lines()
            return True # Ciclo completo

    def step_button_action(self):
        if self.is_running: return # Bloqueia se já estiver rodando automaticamente
        self.perform_micro_step()

    def start_run(self):
        if not self.is_running:
            self.is_running = True
            self.run_loop()

    def run_loop(self):
        if not self.is_running or self.cpu.halted:
            self.is_running = False
            return

        # Correção Crítica: Se estivermos no meio de um micro-passo, 
        # terminamos ele antes de iniciar ciclos completos.
        if self.visual_micro_step != 0:
            cycle_completed = self.perform_micro_step()
            # Se ainda não completou o ciclo, agendamos o próximo micro-step mais rápido
            # para dar fluidez até voltar ao estado zero.
            delay = max(50, self.run_speed_ms // 4)
            self.root.after(delay, self.run_loop)
            return

        # Se chegamos aqui, visual_micro_step é 0. Execução normal.
        self.cpu.execute_full_cycle() 
        self.visual_micro_step = 0 
        self.update_ui_values_only() 
        
        self.update_memory_row(self.cpu.pc.value, True, False, False)
        if self.prev_pc != self.cpu.pc.value:
                self.update_memory_row(self.prev_pc, False, False, False)
                self.prev_pc = self.cpu.pc.value
        
        self.root.after(self.run_speed_ms, self.run_loop)

    def stop_run(self): 
        self.is_running = False
        self.visual_micro_step = 0
        self.reset_lines()
        self.lbl_micro.config(text="Phase: IDLE")
        self.update_ui(full_refresh=True)
    
    def reset_cpu(self):
        self.stop_run()
        
        if self.reset_lines_job:
            self.root.after_cancel(self.reset_lines_job)
            self.reset_lines_job = None
            
        if self.anim_job:
            self.root.after_cancel(self.anim_job)
            self.anim_job = None
            
        self.reset_lines()
            
        self.prev_pc = -1
        self.prev_sp = -1
        self.prev_addr = -1
        self.visual_micro_step = 0
        self.lbl_micro.config(text="Phase: IDLE")
        self.cpu.reset()
        self.update_ui(full_refresh=True)