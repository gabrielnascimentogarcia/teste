import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from src.hardware.cpu import Mic1CPU
from src.common.opcodes import Opcode, OPCODE_MAP
from src.assembler.core import assemble
from src.ui.widgets import CodeEditor

class Mic1GUI:
    """Interface Principal do Simulador"""
    def __init__(self, root):
        self.root = root
        self.root.title("Simulador MIC-1")
        self.root.geometry("1400x900")
        
        self.cpu = Mic1CPU()
        self.running = False
        self.hex_mode = True # Comeca mostrando em Hex
        self.speed = 500
        self.job = None
        self.reset_job = None
        self.u_step = 0 # Contador de micro-passos (0 a 4)
        
        self.follow_pc = tk.BooleanVar(value=True)
        self.interacting = False 
        
        # Tema da interface (clam fica menos feio no Linux/Windows)
        style = ttk.Style()
        style.theme_use('clam')
        
        self._init_layout()
        
        # Referencias pros objetos desenhados no canvas
        self.reg_gfx = {}
        self.reg_txt = {}
        self.bus_gfx = {}
        self.sig_lbl = None
        self.last_pc = -1
        self.last_sp = -1
        self.last_acc = -1
        
        self.root.update_idletasks()
        self.draw_datapath()
        self.init_mem_ui()
        self.update_ui(full=True)

    def _init_layout(self):
        panes = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        panes.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # --- ESQUERDA: EDITOR ---
        lhs = ttk.Frame(panes, width=380)
        panes.add(lhs, weight=1)
        ttk.Label(lhs, text="Codigo Fonte (Assembly)", font=("Arial", 9, "bold")).pack(pady=5)
        self.editor = CodeEditor(lhs)
        self.editor.pack(fill=tk.BOTH, expand=True, padx=2)
        
        # Codigo de exemplo pra nao comecar vazio
        src = """; Setup Inicial
    LOCO 1
    STOD 400    ; Guarda 1 no end 400
    LOCO 5
    STOD 401    ; Contador = 5

; Loop Principal
Main:
    LODD 401    ; Carrega contador
    JZER Fim    ; Se for zero, sai
    PUSH        ; Teste de Pilha
    SUBD 400    ; Decrementa (R = R - 1)
    STOD 401
    JUMP Main   ; Volta pro inicio

; Fim do programa
Fim:
    POP
    HALT
"""
        self.editor.set_src(src)
        ttk.Button(lhs, text="Montar (Assemble)", command=self.do_assemble).pack(fill=tk.X, pady=5)

        # --- CENTRO: DATAPATH (CANVAS) ---
        center = ttk.Frame(panes, width=650)
        panes.add(center, weight=3)
        ttk.Label(center, text="Caminho de Dados (Visual)", font=("Arial", 9, "bold")).pack(pady=5)
        
        cv_frame = ttk.Frame(center)
        cv_frame.pack(fill=tk.BOTH, expand=True)
        
        # Canvas branco com scrollbars
        self.canvas = tk.Canvas(cv_frame, bg="#fafafa", bd=2, relief="sunken")
        vbar = ttk.Scrollbar(cv_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        hbar = ttk.Scrollbar(cv_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)
        
        vbar.pack(side=tk.RIGHT, fill=tk.Y)
        hbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        self.canvas.bind("<Configure>", self.on_resize)
        
        # --- DIREITA: CONTROLES ---
        rhs = ttk.Frame(panes, width=320)
        panes.add(rhs, weight=1)
        
        ctrl = ttk.LabelFrame(rhs, text="Painel de Controle")
        ctrl.pack(fill=tk.X, padx=5, pady=5)
        
        btns = ttk.Frame(ctrl)
        btns.pack(fill=tk.X)
        ttk.Button(btns, text="Run", command=self.toggle_run).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="Step", command=self.do_step).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="Stop", command=self.do_stop).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="Reset", command=self.do_reset).pack(side=tk.LEFT, padx=2)
        
        self.btn_hex = ttk.Button(ctrl, text="Ver: HEX", command=self.toggle_hex)
        self.btn_hex.pack(side=tk.RIGHT, padx=5, pady=2)
        
        s_fr = ttk.Frame(ctrl)
        s_fr.pack(fill=tk.X, pady=2)
        ttk.Label(s_fr, text="Delay (ms):").pack(side=tk.LEFT)
        self.scale = ttk.Scale(s_fr, from_=50, to=1000, value=500, command=self.set_speed)
        self.scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.lbl_stats = ttk.Label(ctrl, text="Ciclos: 0 | N=0 Z=0")
        self.lbl_stats.pack(side=tk.LEFT, padx=5)
        self.lbl_phase = ttk.Label(ctrl, text="PARADO", foreground="red")
        self.lbl_phase.pack(side=tk.RIGHT, padx=5)

        # Caches
        c_fr = ttk.LabelFrame(rhs, text="L1 Cache (Instrucao e Dados)")
        c_fr.pack(fill=tk.X, padx=5, pady=5)
        split = ttk.Frame(c_fr)
        split.pack(fill=tk.X)
        headers = ("V", "Tag", "Dado")
        
        # I-Cache
        i_fr = ttk.Frame(split)
        i_fr.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2)
        ttk.Label(i_fr, text="I-Cache", font=("Arial", 8)).pack()
        self.i_tree = ttk.Treeview(i_fr, columns=headers, show="headings", height=8)
        for h in headers: 
            self.i_tree.heading(h, text=h)
            self.i_tree.column(h, width=35, anchor="center")
        self.i_tree.pack(fill=tk.BOTH, expand=True)

        # D-Cache
        d_fr = ttk.Frame(split)
        d_fr.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2)
        ttk.Label(d_fr, text="D-Cache", font=("Arial", 8)).pack()
        self.d_tree = ttk.Treeview(d_fr, columns=headers, show="headings", height=8)
        for h in headers: 
            self.d_tree.heading(h, text=h)
            self.d_tree.column(h, width=35, anchor="center")
        self.d_tree.pack(fill=tk.BOTH, expand=True)
        
        self.lbl_cache = ttk.Label(c_fr, text="Status: --", foreground="blue")
        self.lbl_cache.pack()

        # RAM
        mem_fr = ttk.LabelFrame(rhs, text="Memoria RAM")
        mem_fr.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.lbl_next = tk.Label(mem_fr, text="PC: 0000", bg="#eee", fg="#333", font=("Consolas", 10))
        self.lbl_next.pack(fill=tk.X, padx=2, pady=2)

        tk.Checkbutton(mem_fr, text="Seguir PC", variable=self.follow_pc).pack(anchor=tk.W)
        
        sb = ttk.Scrollbar(mem_fr, orient="vertical")
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.mem_list = tk.Listbox(mem_fr, font=("Consolas", 10), yscrollcommand=sb.set)
        self.mem_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.config(command=self.mem_list.yview)
        
        self.mem_list.bind("<Double-Button-1>", self.edit_mem)
        self.mem_list.bind("<Enter>", lambda e: self.set_int(True))
        self.mem_list.bind("<Leave>", lambda e: self.set_int(False))

    # --- Logica da GUI ---

    def set_int(self, val): self.interacting = val
    def on_resize(self, e):
        if e.width > 100: self.draw_datapath()

    def set_speed(self, val): self.speed = int(float(val))

    def fval(self, val):
        # Formata o valor pra Hex ou Decimal
        if self.hex_mode: return f"{val & 0xFFFF:04X}"
        val = val & 0xFFFF
        return f"{val if val < 0x8000 else val - 0x10000}"

    def toggle_hex(self):
        pos = self.mem_list.yview()
        self.hex_mode = not self.hex_mode
        self.btn_hex.config(text="Ver: HEX" if self.hex_mode else "Ver: DEC")
        self.update_ui(full=True)
        self.mem_list.yview_moveto(pos[0])

    def draw_box(self, x, y, w, h, name, val, label=None):
        # Desenha caixinha de registrador
        tag = f"reg_{name}"
        lbl = label if label else name
        self.canvas.create_rectangle(x, y, x+w, y+h, fill="#e1e1e1", outline="#333", tags=tag)
        self.canvas.create_text(x+w/2, y+15, text=lbl, font=("Arial", 8, "bold"), fill="#555")
        item = self.canvas.create_text(x+w/2, y+h/2+5, text=val, font=("Consolas", 10, "bold"), tags=f"val_{name}")
        self.reg_gfx[name] = tag
        self.reg_txt[name] = item

    def draw_wire(self, pts, color="#aaa", w=2, arr=None, tags=None):
        return self.canvas.create_line(pts, fill=color, width=w, arrow=arr, capstyle=tk.ROUND, joinstyle=tk.ROUND, tags=tags)

    def draw_datapath(self):
        # Redesenha todo o diagrama (Chamado no resize)
        self.canvas.delete("all")
        self.reg_gfx = {}
        self.reg_txt = {}
        self.bus_gfx = {}

        w = self.canvas.winfo_width()
        w = 650 if w < 100 else w
        cx = w // 2
        
        # Dimensoes e posicoes
        rw, rh = 70, 40
        y0 = 40 
        gy = 50
        
        bx = cx - 120 # Barramento B
        bc = cx + 120 # Barramento C
        rx = cx - rw // 2
        
        order = ["MAR", "MDR", "PC", "MBR", "SP", "LV", "CPP", "TOS", "OPC", "H"]
        
        # Regiao de scroll
        th = y0 + len(order) * gy + 150
        self.canvas.configure(scrollregion=(0, 0, w, th))

        # Textos dos barramentos
        self.canvas.create_text(bx - 20, y0 - 20, text="Bus B", font=("Arial", 8, "bold"), fill="#888")
        self.canvas.create_text(bc + 20, y0 - 20, text="Bus C", font=("Arial", 8, "bold"), fill="#888")
        
        by = y0 + len(order) * gy + 20
        
        self.bus_gfx['main_b'] = self.draw_wire((bx, y0, bx, by), w=4, tags="main_b")
        self.bus_gfx['main_c'] = self.draw_wire((bc, y0, bc, by + 60), w=4, tags="main_c")

        def gv(r): return self.fval(getattr(self.cpu, r.lower()).value) if hasattr(self, 'cpu') else "0000"

        # Desenha registradores em loop
        for i, name in enumerate(order):
            y = y0 + i * gy
            dname = "AC/H" if name == "H" else name
            self.draw_box(rx, y, rw, rh, name, gv(name), label=dname)
            
            # Conexoes
            self.bus_gfx[f'c_{name}'] = self.draw_wire((bc, y + rh/2, rx + rw, y + rh/2), arr=tk.LAST, tags=f"c_{name}")
            if name not in ["MAR", "H"]:
                self.bus_gfx[f'{name}_b'] = self.draw_wire((rx, y + rh/2, bx, y + rh/2), arr=tk.LAST, tags=f"{name}_b")

        # ULA e Shifter
        hy = y0 + (len(order)-1) * gy
        ax = cx - 20
        ay = by
        
        # Conexao H -> ULA
        self.bus_gfx['h_alu'] = self.draw_wire((rx, hy + rh, rx + 20, hy + rh + 20, ax, ay), w=3, arr=tk.LAST, tags="h_alu")
        self.canvas.create_text(rx - 30, hy + rh + 10, text="Bus A", font=("Arial", 8), fill="#888")

        # Desenho da ULA (Trapezio)
        self.canvas.create_polygon(cx-40, ay, cx+40, ay, cx+20, ay+50, cx-20, ay+50, fill="#e8e8e8", outline="#555", width=2, tags="alu")
        self.canvas.create_text(cx, ay+25, text="ALU", font=("Arial", 10, "bold"))
        self.draw_wire((bx, by, cx-30, by), arr=tk.LAST, tags="b_alu")

        # Desenho do Shifter
        sy = ay + 60
        self.canvas.create_rectangle(cx-30, sy, cx+30, sy+30, fill="#e8e8e8", outline="#555", tags="shifter")
        self.canvas.create_text(cx, sy+15, text="Shift", font=("Arial", 9))
        self.canvas.create_line(cx, ay+50, cx, sy, width=4, fill="#aaa", tags="alu_sh")
        self.draw_wire((cx, sy+30, cx, sy+45, bc, sy+45, bc, by + 60), w=4, arr=tk.LAST, tags="sh_c")

        # Memoria RAM (Visual)
        rmx = bx - 80
        rmy = y0
        self.canvas.create_rectangle(rmx, rmy, rmx + 60, rmy + gy + rh, fill="#fff8dc", outline="#555", tags="ram")
        self.canvas.create_text(rmx + 30, rmy + gy, text="RAM", font=("Arial", 10, "bold"))
        self.draw_wire((rx, y0 + 10, rmx + 60, y0 + 10), arr=tk.LAST, color="#333", w=1, tags="ram_addr")
        mdry = y0 + gy
        self.draw_wire((rmx + 60, mdry + 20, rx, mdry + 20), arr=tk.BOTH, color="#333", w=1, tags="ram_data")

        # Sinal de Controle (Texto vermelho no topo)
        sig = self.cpu.ctrl_sig if hasattr(self, 'cpu') else "RESET"
        self.sig_lbl = self.canvas.create_text(cx, 20, text=sig, fill="#d32f2f", font=("Consolas", 12, "bold"))

        if hasattr(self, 'cpu'): self.refresh_vals()

    def hl_wires(self):
        # Logica pra colorir os fios (Animation)
        if self.reset_job:
            self.root.after_cancel(self.reset_job)
            self.reset_job = None
        if self.job: self.root.after_cancel(self.job)
        self.clear_wires()

        if not hasattr(self, 'cpu'): return

        c_act = "#ff5252"  # Cor ativa (Vermelho claro)
        c_comp = "#ffcdd2" # Cor componente ativo

        op = self.cpu.curr_op
        step = self.u_step
        bus = self.cpu.bus
        
        # Verifica se eh instrucao estendida (EXT)
        ext = self.cpu.mbr.value & 0xFFF if op == Opcode.EXT else -1
        
        tags = []
        comps = [] 

        # Mapeamento Visual dos Passos
        if step == 1: # Fetch
            self.lbl_phase.config(text="1. BUSCA")
            tags = ["PC_b", "main_b", "b_alu", "alu_sh", "main_c", "sh_c", "c_MAR"]
            comps = ["alu", "shifter"]
        elif step == 2: # Decode
            self.lbl_phase.config(text="2. DECODE")
            if bus['rd']:
                tags += ["ram_addr", "ram_data"]
                comps += ["ram"]
            tags += ["c_MDR", "MDR_b", "main_b", "b_alu", "alu_sh", "main_c", "sh_c", "c_MBR"] 
            comps += ["alu", "shifter"]
        elif step in [3, 4]: # Exec
            self.lbl_phase.config(text=f"{step}. EXEC/WB")
            if step == 3: comps += ["alu"]
            if step == 4:
                tags += ["alu_sh", "main_c", "sh_c"]
                comps += ["shifter"]

            # Heuristica pra acender os fios certos dependendo da Opcode
            # Nao eh simulacao eletrica real, eh so pra ficar bonito na tela
            if op in [Opcode.ADDD, Opcode.SUBD, Opcode.ADDL, Opcode.SUBL]:
                if step == 3: tags += ["h_alu", "MDR_b", "main_b", "b_alu"]
                if step == 4: 
                    tags += ["c_H"]
                    if bus['rd']: tags += ["ram_data"]; comps += ["ram"]

            elif op in [Opcode.LODD, Opcode.LODL]:
                if step == 3: tags += ["MDR_b", "main_b", "b_alu"]
                if step == 4: tags += ["c_H"]

            elif op == Opcode.LOCO:
                if step == 3: tags += ["MBR_b", "main_b", "b_alu"]
                if step == 4: tags += ["c_H"]

            elif op in [Opcode.STOD, Opcode.STOL]:
                if step == 3: tags += ["h_alu"]
                if step == 4:
                    tags += ["c_MDR"]
                    if bus['wr']: tags += ["ram_addr", "ram_data"]; comps += ["ram"]

            elif op in [Opcode.JUMP, Opcode.JPOS, Opcode.JZER, Opcode.JNEG, Opcode.JNZE]:
                if step == 3: tags += ["MBR_b", "main_b", "b_alu"]
                if step == 4: tags += ["c_PC"]

            elif op == Opcode.CALL:
                if step == 3: tags += ["PC_b", "main_b", "b_alu"]
                if step == 4: tags += ["c_MDR", "c_SP", "c_PC"]

            # Instrucoes Estendidas
            elif op == Opcode.EXT:
                if ext == 3: # PUSH
                    if step == 3: tags += ["h_alu"] 
                    if step == 4:
                        tags += ["c_MDR", "c_SP"]
                        if bus['wr']: tags += ["ram_data"]; comps += ["ram"]
                elif ext == 4: # POP
                    if step == 3: tags += ["MDR_b", "main_b", "b_alu"]
                    if step == 4: tags += ["c_H", "c_SP"]
                elif ext == 5: # RETN
                    if step == 3: tags += ["MDR_b", "main_b", "b_alu"]
                    if step == 4: tags += ["c_PC", "c_SP"]
                elif ext == 6: # SWAP
                    if step == 3: tags += ["h_alu", "SP_b", "main_b", "b_alu"]
                    if step == 4: tags += ["c_H", "c_SP"]
                elif ext in [7, 8]: # INSP/DESP
                    if step == 3: tags += ["SP_b", "main_b", "b_alu"]
                    if step == 4: tags += ["c_SP"]

        # Aplica as cores
        for tag in tags:
            w = 3 if "ram" in tag or "main" in tag else 2
            self.canvas.itemconfig(tag, fill=c_act)
            if "ram" in tag: self.canvas.itemconfig(tag, width=w)
            
            # Acende registradores conectados
            if "_b" in tag or "_alu" in tag:
                r = tag.split("_")[0]
                if r in self.reg_gfx: self.canvas.itemconfig(self.reg_gfx[r], fill=c_comp)
            if "c_" in tag:
                r = tag.split("_")[1]
                if r in self.reg_gfx: self.canvas.itemconfig(self.reg_gfx[r], fill=c_comp)

        for c in comps: self.canvas.itemconfig(c, fill=c_comp)

        if self.running:
            d = min(300, max(100, self.speed // 2))
            self.job = self.root.after(d, self.clear_cb)

    def clear_cb(self):
        self.clear_wires()
        self.reset_job = None

    def clear_wires(self):
        # Reseta cores pro padrao (cinza)
        for t in ["main_b", "main_c", "sh_c", "main_a", "h_alu", "b_alu", "alu_sh"]: 
            self.canvas.itemconfig(t, fill="#aaa")
        for item in self.canvas.find_all():
            tags = self.canvas.gettags(item)
            for t in tags:
                if "_b" in t or "c_" in t or "ram_" in t:
                    c = "#333" if "ram" in t else "#aaa"
                    self.canvas.itemconfig(item, fill=c, width=(1 if "ram" in t else 2))
        
        self.canvas.itemconfig("alu", fill="#e8e8e8")
        self.canvas.itemconfig("shifter", fill="#e8e8e8")
        self.canvas.itemconfig("ram", fill="#fff8dc")
        
        # Reseta registradores (Verde se tiver valor, Cinza se zero)
        for name in self.reg_gfx:
            if hasattr(self.cpu, name.lower()):
                val = getattr(self.cpu, name.lower()).value
                c = "#dcedc8" if val != 0 else "#e1e1e1"
                self.canvas.itemconfig(self.reg_gfx[name], fill=c)

    def init_mem_ui(self):
        self.mem_list.delete(0, tk.END)
        for i in range(4096): 
            self.mem_list.insert(tk.END, f"[{i:03X}]: 0000")

    def update_mem_row(self, idx, pc=False, sp=False, acc=False):
        if not (0 <= idx < 4096): return
        val = self.cpu.mem.ram[idx]
        tags = []
        if pc: tags.append("PC")
        if sp: tags.append("SP")
        ts = f" [{', '.join(tags)}]" if tags else ""
        
        txt = f"[{idx:03X}]: {self.fval(val)}{ts}"
        try:
            if self.mem_list.get(idx) != txt:
                self.mem_list.delete(idx)
                self.mem_list.insert(idx, txt)
            
            # Cores de fundo pra indicar PC, SP e acesso atual
            c = "white"
            if acc: c = "#fff9c4"
            elif pc: c = "#bbdefb"
            elif sp: c = "#ffcdd2"
            self.mem_list.itemconfig(idx, {'bg': c})
        except: pass

    def update_ui(self, full=False):
        self.refresh_vals()
        cpc = self.cpu.pc.value
        csp = self.cpu.sp.value
        caddr = self.cpu.mem.last_addr
        
        # Mostra proxima instrucao no topo da memoria
        if 0 <= cpc < 4096:
            raw = self.cpu.mem.ram[cpc]
            op = raw & 0xF000
            operand = raw & 0xFFF
            rev = {v: k for k, v in OPCODE_MAP.items()}
            mnem = rev.get(op, "UNK")
            if op == 0xF000: mnem = rev.get(raw, "UNK")
            s = f"{mnem} x{operand:03X}"
            self.lbl_next.config(text=f"PC [{cpc:03X}]: {s}")

        # Refresh parcial ou total da lista
        if full:
            self.mem_list.delete(0, tk.END)
            for i in range(4096):
                val = self.cpu.mem.ram[i]
                self.mem_list.insert(tk.END, f"[{i:03X}]: {self.fval(val)}")
            
            if 0 <= cpc < 4096: self.update_mem_row(cpc, pc=True)
            if 0 <= csp < 4096: self.update_mem_row(csp, sp=True)
        else:
            changed = {cpc, csp, caddr, self.last_pc, self.last_sp, self.last_acc}
            for x in changed: self.update_mem_row(x, x==cpc, x==csp, x==caddr)
        
        if self.follow_pc.get() and not self.interacting and (self.running or not full):
            self.mem_list.see(cpc)
        
        self.last_pc, self.last_sp, self.last_acc = cpc, csp, caddr

        # Atualiza arvores da Cache
        for t in [self.i_tree, self.d_tree]:
            for x in t.get_children(): t.delete(x)

        for l in self.cpu.mem.i_cache.lines:
            self.i_tree.insert("", "end", values=("1" if l.valid else "0", f"{l.tag:02X}", self.fval(l.data)))
        for l in self.cpu.mem.d_cache.lines:
            self.d_tree.insert("", "end", values=("1" if l.valid else "0", f"{l.tag:02X}", self.fval(l.data)))

        self.lbl_cache.config(text=f"I: {self.cpu.mem.i_cache.last_status} | D: {self.cpu.mem.d_cache.last_status}")

    def refresh_vals(self):
        # Atualiza os valores dentro dos retangulos
        for name in self.reg_txt:
            if hasattr(self.cpu, name.lower()):
                v = getattr(self.cpu, name.lower()).value
                self.canvas.itemconfig(self.reg_txt[name], text=self.fval(v))
        
        self.canvas.itemconfig(self.sig_lbl, text=self.cpu.ctrl_sig)
        self.lbl_stats.config(text=f"Ciclos: {self.cpu.cycle} | N={int(self.cpu.alu.n)} Z={int(self.cpu.alu.z)}")
        self.hl_wires()

    def edit_mem(self, event):
        # Permite editar memoria clicando duas vezes
        sel = self.mem_list.curselection()
        if not sel: return
        addr = sel[0]
        self.interacting = True 
        res = simpledialog.askstring("Editar RAM", f"End {addr:03X} Valor (Hex ou Dec):")
        self.interacting = False
        if res:
            try:
                val = int(res, 16) if "0X" in res.upper() else int(res)
                self.cpu.mem.write(addr, val)
                self.update_mem_row(addr, addr==self.cpu.pc.value, addr==self.cpu.sp.value, True)
            except: messagebox.showerror("Erro", "Valor invalido")

    def do_assemble(self):
        mc, msg = assemble(self.editor.get_src())
        if msg != "OK":
            messagebox.showerror("Erro no Assembler", msg)
            return
        self.do_reset()
        self.cpu.mem.load_bin(mc)
        self.update_ui(full=True)
        messagebox.showinfo("Assembler", f"Compilado com sucesso: {len(mc)} palavras.")

    def micro_step(self):
        # Maquina de estados dos micro-passos
        if self.cpu.halted:
            self.running = False
            return True

        if self.u_step == 0:
            self.u_step = 1
            self.cpu.fetch() 
            self.update_ui()
            return False
        elif self.u_step == 1:
            self.u_step = 2
            self.cpu.decode() 
            self.update_ui()
            return False
        elif self.u_step == 2:
            self.u_step = 3
            self.update_ui() # Apenas visual, prepara pra executar
            return False
        elif self.u_step == 3:
            self.u_step = 4
            self.cpu.execute() 
            self.update_ui()
            return False
        elif self.u_step == 4:
            self.u_step = 0
            self.lbl_phase.config(text="PARADO")
            self.clear_wires()
            return True 

    def do_step(self):
        if self.running: return 
        self.micro_step()

    def toggle_run(self):
        if not self.running:
            self.running = True
            self.loop()

    def loop(self):
        if not self.running or self.cpu.halted:
            self.running = False
            return
        self.micro_step()
        if self.follow_pc.get() and not self.interacting:
             self.mem_list.see(self.cpu.pc.value)
        self.root.after(self.speed, self.loop)

    def do_stop(self): 
        self.running = False
        self.clear_wires()
        self.lbl_phase.config(text="PAUSA")
        self.update_ui(full=True)
    
    def do_reset(self):
        self.do_stop()
        if self.reset_job: self.root.after_cancel(self.reset_job)
        if self.job: self.root.after_cancel(self.job)
        self.clear_wires()
        self.last_pc = -1
        self.last_sp = -1
        self.last_acc = -1
        self.u_step = 0
        self.lbl_phase.config(text="IDLE")
        self.cpu.reset()
        self.update_ui(full=True)