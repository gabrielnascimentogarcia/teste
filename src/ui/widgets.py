import tkinter as tk
from tkinter import ttk
from src.common.opcodes import OPCODE_MAP

class CodeEditor(tk.Frame):
    """Editor customizado com numeros de linha e cores"""
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        # Coluna dos numeros das linhas
        self.linenum = tk.Text(self, width=4, padx=4, takefocus=0, border=0,
                               background='#f0f0f0', state='disabled', font=("Consolas", 10))
        self.linenum.pack(side=tk.LEFT, fill=tk.Y)
        
        # Area do texto principal
        self.area = tk.Text(self, font=("Consolas", 10), undo=True, wrap="none")
        self.area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Barras de rolagem
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.sync_scroll)
        self.vsb.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.hsb = ttk.Scrollbar(self, orient="horizontal", command=self.area.xview)
        self.hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.area['xscrollcommand'] = self.hsb.set
        self.area['yscrollcommand'] = self.on_scroll

        # Configuracao das cores (Tags)
        self.area.tag_configure("kw", foreground="blue", font=("Consolas", 10, "bold"))
        self.area.tag_configure("num", foreground="#c00000")
        self.area.tag_configure("com", foreground="#008000") 
        self.area.tag_configure("lbl", foreground="#800080", font=("Consolas", 10, "bold"))
        self.area.tag_configure("dir", foreground="#804000", font=("Consolas", 10, "bold"))

        # Bind pra atualizar cores quando digita
        self.area.bind("<<Change>>", self.on_change)
        self.area.bind("<KeyRelease>", self.on_change)
        
        self.last_lines = -1
        self.update_gutter()

    def sync_scroll(self, *args):
        # Rola texto e numeros juntos
        self.area.yview(*args)
        self.linenum.yview(*args)

    def on_scroll(self, *args):
        self.vsb.set(*args)
        self.linenum.yview_moveto(args[0])

    def on_change(self, event=None):
        self.update_gutter()
        self.highlight()

    def update_gutter(self):
        # Atualiza a numeracao lateral
        lines = self.area.get('1.0', 'end-1c').count('\n') + 1
        if lines != self.last_lines:
            content = "\n".join(str(i) for i in range(1, lines + 1))
            self.linenum.config(state='normal')
            self.linenum.delete('1.0', tk.END)
            self.linenum.insert('1.0', content)
            self.linenum.config(state='disabled')
            self.last_lines = lines
        self.linenum.yview_moveto(self.area.yview()[0])

    def highlight(self):
        # Remove tags antigas
        for tag in ["kw", "num", "com", "lbl", "dir"]:
            self.area.tag_remove(tag, "1.0", tk.END)
        
        kws = list(OPCODE_MAP.keys())
        
        # Pinta comentarios (;)
        start = "1.0"
        while True:
            pos = self.area.search(';', start, stopindex=tk.END)
            if not pos: break
            eol = self.area.index(f"{pos} lineend")
            self.area.tag_add("com", pos, eol)
            start = eol

        # Pinta palavras reservadas e numeros
        start = "1.0"
        while True:
            pos = self.area.search(r'[\.\w]+', start, stopindex=tk.END, regexp=True)
            if not pos: break
            end = f"{pos} wordend"
            word = self.area.get(pos, end).upper()
            
            if "com" not in self.area.tag_names(pos): # Ignora se for comentario
                if word in kws:
                    self.area.tag_add("kw", pos, end)
                elif word.startswith("."):
                     self.area.tag_add("dir", pos, end)
                elif word.isdigit() or (word.startswith('0X') and len(word)>2):
                    self.area.tag_add("num", pos, end)
                else:
                    if self.area.get(end, f"{end}+1c") == ':':
                        self.area.tag_add("lbl", pos, f"{end}+1c")
            start = end

    def get_src(self): return self.area.get("1.0", tk.END)
    def set_src(self, text):
        self.area.delete("1.0", tk.END)
        self.area.insert("1.0", text)
        self.on_change()