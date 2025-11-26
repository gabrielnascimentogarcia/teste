import tkinter as tk
from tkinter import ttk
from src.common.opcodes import OPCODE_MAP

class CodeEditor(tk.Frame):
    """
    Widget de editor de texto completo com numeração e syntax highlighting.
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

        # Configuração de Tags (Cores)
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
        
        keywords = list(OPCODE_MAP.keys())
        
        # Highlight Comentários
        start_idx = "1.0"
        while True:
            pos = self.text_area.search(';', start_idx, stopindex=tk.END)
            if not pos: break
            line_end = self.text_area.index(f"{pos} lineend")
            self.text_area.tag_add("comment", pos, line_end)
            start_idx = line_end

        # Highlight Palavras
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