import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from src.hardware.cpu import Mic1CPU
from src.common.opcodes import Opcode, OPCODE_MAP
from src.assembler.core import assemble
from src.ui.widgets import CodeEditor

class Mic1GUI:
    """
    Aplicação GUI principal para o Simulador MIC-1.
    Versão 7.5 - Correção Visual de Caminhos de Dados (PUSH/POP Fix).
    """
    def __init__(self, root):
        self.root = root
        self.root.title("Simulador MIC-1 Profissional v7.5")
        self.root.geometry("1400x900")
        
        self.cpu = Mic1CPU()
        self.is_running = False
        self.display_hex = True 
        self.run_speed_ms = 500
        self.anim_job = None
        self.reset_lines_job = None
        self.visual_micro_step = 0 
        
        self.follow_pc = tk.BooleanVar(value=True)
        self.user_interacting = False 
        
        # Setup Visual
        style = ttk.Style()
        style.theme_use('clam')
        
        self._setup_layout()
        
        # Variáveis de controle visual
        self.reg_rects = {}
        self.reg_texts = {}
        self.bus_ids = {}
        self.control_label_id = None
        self.prev_pc = -1
        self.prev_sp = -1
        self.prev_addr = -1
        
        # Inicialização
        self.root.update_idletasks()
        self.draw_datapath_layout()
        self.init_memory_list()
        self.update_ui(full_refresh=True)

    def _setup_layout(self):
        self.paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # --- PAINEL ESQUERDO: EDITOR ---
        left_frame = ttk.Frame(self.paned_window, width=380)
        self.paned_window.add(left_frame, weight=1)
        ttk.Label(left_frame, text="Editor Assembly", font=("Arial", 10, "bold")).pack(pady=5)
        self.editor = CodeEditor(left_frame)
        self.editor.pack(fill=tk.BOTH, expand=True, padx=2)
        
        default_code = """; --- PREPARAÇÃO (Criação de variáveis manuais) ---
    LOCO 1          ; Carrega a constante 1 no Acumulador (H)
    STOD 400        ; Salva o valor 1 no endereço 400 da RAM 
                    ; (Usaremos este 1 para fazer subtrações)

    LOCO 5          ; Carrega o valor inicial da contagem (5)
    STOD 401        ; Salva o contador no endereço 401 da RAM

; --- LOOP PRINCIPAL ---
Inicio:
    LODD 401        ; Carrega o valor atual do contador (RAM 401 -> MDR -> H)
    JZER Fim        ; Se o valor for ZERO, pula para o label 'Fim'
    
    PUSH            ; Empilha o valor atual (Observe o registrador SP mudando)
                    ; Isso é ótimo para ver a Stack Pointer funcionar
    
    SUBD 400        ; Subtrai o valor do endereço 400 (que é 1) do acumulador
    STOD 401        ; Salva o novo valor decrementado de volta na RAM 401
    
    JUMP Inicio     ; Pula incondicionalmente de volta para o 'Inicio'

; --- FINALIZAÇÃO ---
Fim:
    POP             ; (Opcional) Desempilha o último valor para limpar
    HALT            ; Para a CPU
"""
        self.editor.set_code(default_code)
        ttk.Button(left_frame, text="Montar (Assemble)", command=self.assemble_code).pack(fill=tk.X, pady=5)

        # --- PAINEL CENTRAL: DATAPATH (CANVAS) ---
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
        
        # --- PAINEL DIREITO: CONTROLES E MEMÓRIA ---
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

        # --- Caches L1 ---
        cache_main_frame = ttk.LabelFrame(right_frame, text="Caches L1 (Split)")
        cache_main_frame.pack(fill=tk.X, padx=5, pady=5)
        split_cache = ttk.Frame(cache_main_frame)
        split_cache.pack(fill=tk.X)
        cols = ("valid", "tag", "data")
        col_width = 45
        
        # I-Cache
        icache_frame = ttk.Frame(split_cache)
        icache_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2)
        ttk.Label(icache_frame, text="I-Cache", font=("Arial", 8, "bold")).pack()
        self.icache_tree = ttk.Treeview(icache_frame, columns=cols, show="headings", height=8)
        icache_scroll = ttk.Scrollbar(icache_frame, orient="vertical", command=self.icache_tree.yview)
        self.icache_tree.configure(yscrollcommand=icache_scroll.set)
        icache_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.icache_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        for c in cols: 
            self.icache_tree.heading(c, text=c[0].upper())
            self.icache_tree.column(c, width=col_width, anchor="center")

        # D-Cache
        dcache_frame = ttk.Frame(split_cache)
        dcache_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2)
        ttk.Label(dcache_frame, text="D-Cache", font=("Arial", 8, "bold")).pack()
        self.dcache_tree = ttk.Treeview(dcache_frame, columns=cols, show="headings", height=8)
        dcache_scroll = ttk.Scrollbar(dcache_frame, orient="vertical", command=self.dcache_tree.yview)
        self.dcache_tree.configure(yscrollcommand=dcache_scroll.set)
        dcache_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.dcache_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        for c in cols: 
            self.dcache_tree.heading(c, text=c[0].upper())
            self.dcache_tree.column(c, width=col_width, anchor="center")
        
        self.lbl_cache_status = ttk.Label(cache_main_frame, text="Status: IDLE", foreground="blue")
        self.lbl_cache_status.pack()

        # --- Memória Principal ---
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

    # --- Lógica de Visualização e Controle ---

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
        mode_text = "HEX" if self.display_hex else "DEC"
        self.btn_mode.config(text=f"Visualização: {mode_text}")
        self.update_ui(full_refresh=True)
        self.mem_list.yview_moveto(scroll_pos[0])

    def draw_box(self, x, y, w, h, name, value_hex, display_label=None):
        tag = f"reg_{name}"
        label_text = display_label if display_label else name
        self.canvas.create_rectangle(x, y, x+w, y+h, fill="#e1e1e1", outline="black", tags=tag)
        self.canvas.create_text(x+w/2, y+15, text=label_text, font=("Arial", 8, "bold"))
        text = self.canvas.create_text(x+w/2, y+h/2+5, text=value_hex, font=("Consolas", 10, "bold"), tags=f"val_{name}")
        self.reg_rects[name] = tag
        self.reg_texts[name] = text

    def draw_line(self, coords, color="gray", width=2, arrow=None, tags=None):
        return self.canvas.create_line(coords, fill=color, width=width, arrow=arrow, 
                                     capstyle=tk.ROUND, joinstyle=tk.ROUND, tags=tags)

    def draw_datapath_layout(self):
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
            display_name = "AC / H" if name == "H" else name
            self.draw_box(reg_x, y, reg_w, reg_h, name, get_reg(name), display_label=display_name)
            
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

        # ALU (Polygon) - Added tag 'comp_ALU'
        self.canvas.create_polygon(cx-40, alu_y, cx+40, alu_y, cx+20, alu_y+50, cx-20, alu_y+50, 
                                   fill="#ffcccb", outline="black", width=2, tags="comp_ALU")
        self.canvas.create_text(cx, alu_y+25, text="ALU", font=("Arial", 11, "bold"))
        self.draw_line((bus_b_x, bus_bottom_y, cx-30, bus_bottom_y), arrow=tk.LAST, tags="bus_b_to_alu")

        shift_y = alu_y + 60
        # Shifter (Rect) - Added tag 'comp_Shifter'
        self.canvas.create_rectangle(cx-30, shift_y, cx+30, shift_y+30, fill="#add8e6", outline="black", tags="comp_Shifter")
        self.canvas.create_text(cx, shift_y+15, text="Shifter", font=("Arial", 9))
        self.canvas.create_line(cx, alu_y+50, cx, shift_y, width=4, fill="gray", tags="alu_to_shifter")
        self.draw_line((cx, shift_y+30, cx, shift_y+45, bus_c_x, shift_y+45, bus_c_x, bus_bottom_y + 60), 
                       width=4, arrow=tk.LAST, tags="bus_c")

        ram_x = bus_b_x - 80
        ram_y = y_start
        # RAM (Rect) - Added tag 'comp_RAM'
        self.canvas.create_rectangle(ram_x, ram_y, ram_x + 60, ram_y + gap_y + reg_h, fill="#fff0b3", outline="black", tags="comp_RAM")
        self.canvas.create_text(ram_x + 30, ram_y + gap_y, text="RAM", font=("Arial", 10, "bold"))
        self.draw_line((reg_x, y_start + 10, ram_x + 60, y_start + 10), arrow=tk.LAST, color="black", width=1, tags="ram_addr")
        mdr_y = y_start + gap_y
        self.draw_line((ram_x + 60, mdr_y + 20, reg_x, mdr_y + 20), arrow=tk.BOTH, color="black", width=1, tags="ram_data")

        sig = self.cpu.control_signals if hasattr(self, 'cpu') else "RESET"
        self.control_label_id = self.canvas.create_text(cx, 20, text=sig, fill="red", font=("Consolas", 14, "bold"), anchor="center")

        if hasattr(self, 'cpu'): self.update_ui_values_only()

    def animate_buses(self):
        # 1. Clean up (Logic for Step and Run modes)
        if self.reset_lines_job:
            self.root.after_cancel(self.reset_lines_job)
            self.reset_lines_job = None
        if self.anim_job:
            self.root.after_cancel(self.anim_job)
        self.reset_lines()

        if not hasattr(self, 'cpu'): return

        active_color = "#FF4444"
        component_active_color = "#FF9999" # Cor para componentes ativos (ULA, Shifter, RAM)

        opcode = self.cpu.current_opcode
        step = self.visual_micro_step
        bus_activity = self.cpu.bus_activity
        
        # Determine specific extended function if opcode is EXT (0xF)
        ext_func = self.cpu.mbr.value & 0xFFF if opcode == Opcode.EXT else -1
        
        # Mapeamento local para instruções estendidas (conforme cpu.py)
        IS_PUSH = (opcode == Opcode.EXT and ext_func == 3)
        IS_POP  = (opcode == Opcode.EXT and ext_func == 4)
        IS_RETN = (opcode == Opcode.EXT and ext_func == 5)
        IS_SWAP = (opcode == Opcode.EXT and ext_func == 6)
        IS_INSP = (opcode == Opcode.EXT and ext_func == 7)
        IS_DESP = (opcode == Opcode.EXT and ext_func == 8)
        
        tags = []
        comps = [] # Lista de componentes para acender

        # --- STEP 1: FETCH (PC -> MAR, PC+1 -> PC) ---
        if step == 1:
            self.lbl_micro.config(text="1. BUSCA (Fetch: PC -> MAR)")
            # Path: PC -> Bus B -> ALU -> Shifter -> Bus C -> MAR
            tags = ["PC_to_b", "main_bus_b", "bus_b_to_alu", "alu_to_shifter", "main_bus_c", "bus_c", "c_to_MAR"]
            comps = ["comp_ALU", "comp_Shifter"] # PC passa pela ULA/Shifter

        # --- STEP 2: DECODE (Mem -> MDR -> MBR) ---
        elif step == 2:
            self.lbl_micro.config(text="2. DECODIFICAÇÃO (Decode)")
            # Read from memory
            if bus_activity['mem_read']:
                tags += ["ram_addr", "ram_data"]
                comps += ["comp_RAM"]
            
            # MDR -> Bus B -> ALU -> Bus C -> MBR (Standard MIC-1 decode/transfer path)
            tags += ["c_to_MDR", "MDR_to_b", "main_bus_b", "bus_b_to_alu", "alu_to_shifter", "main_bus_c", "bus_c", "c_to_MBR"] 
            comps += ["comp_ALU", "comp_Shifter"]

        # --- STEP 3 & 4: EXECUTE & WRITEBACK ---
        elif step == 3 or step == 4:
            phase_text = "3. EXECUÇÃO" if step == 3 else "4. GRAVAÇÃO"
            self.lbl_micro.config(text=phase_text)
            
            # Base paths present in Execute/Writeback
            if step == 3: # Inputs to ALU
                # Base para maioria das operações, mas pode ser sobrescrito abaixo (ex: STOD apenas A)
                # Vamos adicionar apenas se não houver conflito específico, mas a lógica abaixo trata melhor.
                comps += ["comp_ALU"] 

            if step == 4: # Outputs from Shifter/Bus C
                tags += ["alu_to_shifter", "main_bus_c", "bus_c"]
                comps += ["comp_Shifter"]

            # -- INSTRUCTION SPECIFIC LOGIC --
            
            # --- ALU OPERATIONS (ADDD, SUBD, ADDL, SUBL) ---
            if opcode in [Opcode.ADDD, Opcode.SUBD, Opcode.ADDL, Opcode.SUBL]:
                if step == 3:
                    tags += ["h_to_alu_a", "MDR_to_b", "main_bus_b", "bus_b_to_alu"]
                if step == 4:
                    tags += ["c_to_H"]
                    if bus_activity['mem_read']: 
                        tags += ["ram_data"]
                        comps += ["comp_RAM"]

            # --- LOAD OPERATIONS (LODD, LODL) ---
            elif opcode in [Opcode.LODD, Opcode.LODL]:
                if step == 3:
                    tags += ["MDR_to_b", "main_bus_b", "bus_b_to_alu"]
                if step == 4:
                    tags += ["c_to_H"]

            # --- LOAD CONSTANT (LOCO) ---
            elif opcode == Opcode.LOCO:
                if step == 3:
                    tags += ["MBR_to_b", "main_bus_b", "bus_b_to_alu"]
                if step == 4:
                    tags += ["c_to_H"]

            # --- STORE OPERATIONS (STOD, STOL) ---
            elif opcode in [Opcode.STOD, Opcode.STOL]:
                if step == 3:
                    tags += ["h_to_alu_a"] # Apenas H vai para a ALU
                if step == 4:
                    tags += ["c_to_MDR"]
                    if bus_activity['mem_write']: 
                        tags += ["ram_addr", "ram_data"]
                        comps += ["comp_RAM"]

            # --- JUMPS (JUMP, JPOS, JZER, JNEG, JNZE) ---
            elif opcode in [Opcode.JUMP, Opcode.JPOS, Opcode.JZER, Opcode.JNEG, Opcode.JNZE]:
                if step == 3:
                    tags += ["MBR_to_b", "main_bus_b", "bus_b_to_alu"]
                if step == 4:
                    tags += ["c_to_PC"]

            # --- CALL ---
            elif opcode == Opcode.CALL:
                if step == 3:
                    tags += ["PC_to_b", "main_bus_b", "bus_b_to_alu"] # Save PC
                if step == 4:
                    tags += ["c_to_MDR", "c_to_SP"] # Write to stack buffer, update SP
                    tags += ["c_to_PC"] # And update PC

            # --- STACK OPS (PUSH) ---
            elif IS_PUSH:
                if step == 3:
                    # CORREÇÃO: H vai para ALU (via Bus A ou direto se possível, aqui simulamos Bus A)
                    # O decremento do SP é interno na simulação hardware. Visualmente, focamos no dado.
                    tags += ["h_to_alu_a"] 
                if step == 4:
                    tags += ["c_to_MDR", "c_to_SP"] # Dado para MDR e SP atualiza visualmente
                    if bus_activity['mem_write']: 
                        tags += ["ram_data"]
                        comps += ["comp_RAM"]

            # --- STACK OPS (POP) ---
            elif IS_POP:
                if step == 3:
                    # CORREÇÃO: MDR (dado lido) vai para Bus B. 
                    # SP incrementa implicitamente/visualmente no passo 4.
                    tags += ["MDR_to_b", "main_bus_b", "bus_b_to_alu"]
                if step == 4:
                    tags += ["c_to_H", "c_to_SP"] # Grava em H e atualiza SP

            # --- RETURN (RETN) ---
            elif IS_RETN:
                if step == 3:
                    tags += ["MDR_to_b", "main_bus_b", "bus_b_to_alu"] # Ret Addr from Mem
                if step == 4:
                    tags += ["c_to_PC", "c_to_SP"] # To PC, update SP

            # --- SWAP ---
            elif IS_SWAP:
                if step == 3:
                    tags += ["h_to_alu_a", "SP_to_b", "main_bus_b", "bus_b_to_alu"]
                if step == 4:
                    tags += ["c_to_H", "c_to_SP"] # Swap complete

            # --- SP ARITHMETIC (INSP, DESP) ---
            elif IS_INSP or IS_DESP:
                if step == 3:
                    tags += ["SP_to_b", "main_bus_b", "bus_b_to_alu"]
                if step == 4:
                    tags += ["c_to_SP"]

        # Apply colors to lines (wires)
        for tag in tags:
            width = 3 if "ram" in tag or "main_bus" in tag else 2
            self.canvas.itemconfig(tag, fill=active_color)
            if "ram" in tag: self.canvas.itemconfig(tag, width=width)
            
            # Auto-highlight Source/Dest registers based on the line tag
            if "_to_b" in tag or "_to_alu" in tag: # Source
                reg = tag.split("_")[0]
                if reg in self.reg_rects: 
                    self.canvas.itemconfig(self.reg_rects[reg], fill=component_active_color)
            if "c_to_" in tag: # Dest
                reg = tag.split("_")[2]
                if reg in self.reg_rects:
                    self.canvas.itemconfig(self.reg_rects[reg], fill=component_active_color)

        # Apply colors to components (ALU, Shifter, RAM)
        for comp in comps:
            self.canvas.itemconfig(comp, fill=component_active_color)

        # Timer logic
        if self.is_running:
            delay = min(300, max(100, self.run_speed_ms // 2))
            self.anim_job = self.root.after(delay, self.reset_lines_callback)

    def reset_lines_callback(self):
        self.reset_lines()
        self.reset_lines_job = None

    def reset_lines(self):
        # Reset Lines
        for t in ["main_bus_b", "main_bus_c", "bus_c", "bus_a", "h_to_alu_a", "bus_b_to_alu", "alu_to_shifter"]: 
            self.canvas.itemconfig(t, fill="gray")
        for item in self.canvas.find_all():
            tags = self.canvas.gettags(item)
            for t in tags:
                if "_to_" in t or "ram_" in t:
                    if "ram" in t: self.canvas.itemconfig(item, fill="black", width=1)
                    else: self.canvas.itemconfig(item, fill="gray")
        
        # Reset Components (Rects/Polygons)
        # Default colors
        self.canvas.itemconfig("comp_ALU", fill="#ffcccb")
        self.canvas.itemconfig("comp_Shifter", fill="#add8e6")
        self.canvas.itemconfig("comp_RAM", fill="#fff0b3")
        
        # Reset Registers
        for name in self.reg_rects:
            # Check value to decide color (Green if non-zero, Gray if zero)
            # We need to access cpu value again or check text
            # Simplification: Reset to Gray/Green logic based on current value
            if hasattr(self.cpu, name.lower()):
                val = getattr(self.cpu, name.lower()).value
                color = "#ccffcc" if val != 0 else "#e1e1e1"
                self.canvas.itemconfig(self.reg_rects[name], fill=color)

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
            # Reverse mapping
            rev_op = {v: k for k, v in OPCODE_MAP.items()}
            mnemonic = rev_op.get(opcode_base, "UNK")
            if opcode_base == 0xF000: 
                mnemonic = rev_op.get(raw_instr, "UNK")
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

        # --- Cache Update ---
        for i in self.icache_tree.get_children(): self.icache_tree.delete(i)
        for i in self.dcache_tree.get_children(): self.dcache_tree.delete(i)

        for line in self.cpu.memory.i_cache.lines:
            valid_str = "1" if line.valid else "0"
            tag_str = f"{line.tag:03X}" if line.valid else "000"
            data_str = self.fmt_val(line.data) if line.valid else "0000"
            self.icache_tree.insert("", "end", values=(valid_str, tag_str, data_str))
            
        for line in self.cpu.memory.d_cache.lines:
            valid_str = "1" if line.valid else "0"
            tag_str = f"{line.tag:03X}" if line.valid else "000"
            data_str = self.fmt_val(line.data) if line.valid else "0000"
            self.dcache_tree.insert("", "end", values=(valid_str, tag_str, data_str))

        last_st = f"I: {self.cpu.memory.i_cache.last_status} | D: {self.cpu.memory.d_cache.last_status}"
        self.lbl_cache_status.config(text=last_st)

    def update_ui_values_only(self):
        for name in self.reg_texts:
            if hasattr(self.cpu, name.lower()):
                reg = getattr(self.cpu, name.lower())
                val_str = self.fmt_val(reg.value)
                self.canvas.itemconfig(self.reg_texts[name], text=val_str)
                # Note: Color logic moved to reset_lines mostly, but here we can force update text
                # We let animate_buses handle active colors.

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
                val = int(res, 16) if self.display_hex or res.upper().startswith("0X") else int(res)
                self.cpu.memory.write(addr, val)
                self.update_memory_row(addr, addr==self.cpu.pc.value, addr==self.cpu.sp.value, True)
            except ValueError: messagebox.showerror("Erro", "Valor inválido!")

    def assemble_code(self):
        mc, msg = assemble(self.editor.get_code())
        if not mc and msg != "Sucesso":
            messagebox.showerror("Erro", msg)
            return
        self.reset_cpu()
        self.cpu.memory.load_program(mc)
        self.update_ui(full_refresh=True)
        messagebox.showinfo("Montagem", f"Sucesso! {len(mc)} palavras carregadas.")

    def perform_micro_step(self):
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
                messagebox.showerror("Erro", str(e))
                return True 
            return False
        elif self.visual_micro_step == 4:
            self.visual_micro_step = 0
            self.lbl_micro.config(text="Phase: IDLE (Next Instr)")
            self.reset_lines()
            return True 

    def step_button_action(self):
        if self.is_running: return 
        self.perform_micro_step()

    def start_run(self):
        if not self.is_running:
            self.is_running = True
            self.run_loop()

    def run_loop(self):
        if not self.is_running or self.cpu.halted:
            self.is_running = False
            return
        self.perform_micro_step()
        if self.follow_pc.get() and not self.user_interacting:
             self.mem_list.see(self.cpu.pc.value)
        self.root.after(self.run_speed_ms, self.run_loop)

    def stop_run(self): 
        self.is_running = False
        self.reset_lines()
        self.lbl_micro.config(text="Phase: PAUSED")
        self.update_ui(full_refresh=True)
    
    def reset_cpu(self):
        self.stop_run()
        if self.reset_lines_job: self.root.after_cancel(self.reset_lines_job)
        if self.anim_job: self.root.after_cancel(self.anim_job)
        self.reset_lines()
        self.prev_pc = -1
        self.prev_sp = -1
        self.prev_addr = -1
        self.visual_micro_step = 0
        self.lbl_micro.config(text="Phase: IDLE")
        self.cpu.reset()
        self.update_ui(full_refresh=True)