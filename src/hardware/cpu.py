from src.common.constants import MASK_12BIT
from src.common.opcodes import Opcode
from src.hardware.components import Register, MemorySystem, ALU, Shifter

class Mic1CPU:
    def __init__(self):
        # Inicializacao dos registradores
        self.mar = Register("MAR")
        self.mdr = Register("MDR")
        self.pc  = Register("PC")
        self.mbr = Register("MBR")
        self.sp  = Register("SP", 4095) # Pilha comeca no topo
        self.opc = Register("OPC")      # Guarda PC antigo
        self.h   = Register("H")        # Acumulador auxiliar
        self.lv  = Register("LV")
        self.cpp = Register("CPP")
        self.tos = Register("TOS")

        self.mem = MemorySystem()
        self.alu = ALU()
        self.shifter = Shifter()
        
        self.halted = False
        self.cycle = 0
        self.ctrl_sig = "RESET"
        self.curr_op = -1
        
        # Estados do barramento (pra interface grafica saber o que acender)
        self.bus = {
            'a': False, 'b': False, 'c': False, 
            'rd': False, 'wr': False
        }

        # Tabela de despacho (evita aquele monte de if/else)
        self._ops = {
            Opcode.LODD: self._lodd, Opcode.STOD: self._stod,
            Opcode.ADDD: self._addd, Opcode.SUBD: self._subd,
            Opcode.JPOS: self._jpos, Opcode.JZER: self._jzer,
            Opcode.JUMP: self._jump, Opcode.LOCO: self._loco,
            Opcode.LODL: self._lodl, Opcode.STOL: self._stol,
            Opcode.ADDL: self._addl, Opcode.SUBL: self._subl,
            Opcode.JNEG: self._jneg, Opcode.JNZE: self._jnze,
            Opcode.CALL: self._call, Opcode.EXT:  self._ext
        }

    def reset(self):
        # Zera tudo
        for r in [self.mar, self.mdr, self.pc, self.mbr, self.lv, self.cpp, self.tos, self.opc, self.h]:
            r.value = 0
        self.sp.value = 4095
        self.alu.n = False
        self.alu.z = False
        self.mem.flush_all()
        self.mem.last_addr = -1
        self.halted = False
        self.cycle = 0
        self.ctrl_sig = "RESET"
        self.curr_op = -1
        self._reset_bus()

    def _reset_bus(self):
        for k in self.bus: self.bus[k] = False

    def _alu_sh(self, a, b, alu_op, sh_op=None):
        # Helper pra rodar ULA + Shifter juntos
        res = self.alu.compute(a, b, alu_op)
        return self.shifter.compute(res, sh_op)

    # --- Micro-Passos (Ciclo de Instrucao) ---

    def fetch(self):
        # Passo 1: Busca Endereco
        self.opc.value = self.pc.value
        self.mar.value = self.pc.value
        self._reset_bus()
        self.bus['b'] = True # PC -> Barramento B
        self.bus['c'] = True # ... -> Barramento C -> MAR
        self.ctrl_sig = "BUSCA: PC->MAR"

    def decode(self):
        # Passo 2: Le da memoria e Decodifica
        val = self.mem.read_instr(self.mar.value)
        self.pc.value += 1
        self.mdr.value = val
        self.mbr.value = self.mdr.value
        self.curr_op = self.mbr.value >> 12 # Pega os 4 bits mais significativos
        self._reset_bus()
        self.bus['rd'] = True
        self.bus['c'] = True
        self.ctrl_sig = "DECODE"

    def execute(self):
        # Passo 3: Executa a operacao de fato
        if self.halted: return
        op = self.curr_op
        operand = self.mbr.value & MASK_12BIT
        self.ctrl_sig = f"EXEC: {op:X}"
        self._reset_bus()
        
        if op in self._ops:
            self._ops[op](operand)
        else:
            self.ctrl_sig = f"ERRO: Op Desconhecido {op}"
        self.cycle += 1

    # --- Implementacao das Instrucoes ---
    
    def _lodd(self, addr):
        # Carrega Direto: Mem[addr] -> H
        val = self.mem.read_data(addr)
        self.h.value = self._alu_sh(val, 0, 'A')
        self.ctrl_sig = f"LODD x{addr:03X}"
        self.bus.update({'rd': True, 'c': True})

    def _stod(self, addr):
        # Armazena Direto: H -> Mem[addr]
        self.mem.write(addr, self.h.value)
        self.ctrl_sig = f"STOD x{addr:03X}"
        self.bus.update({'wr': True, 'b': True})

    def _addd(self, addr):
        # Soma Direta: H + Mem[addr] -> H
        val = self.mem.read_data(addr)
        self.h.value = self._alu_sh(self.h.value, val, 'ADD')
        self.bus.update({'a': True, 'b': True, 'c': True})

    def _subd(self, addr):
        val = self.mem.read_data(addr)
        self.h.value = self._alu_sh(self.h.value, val, 'SUB')
        self.bus.update({'a': True, 'b': True, 'c': True})

    def _jpos(self, addr):
        # Pula se Positivo (N=0 e Z=0)
        take = not self.alu.n and not self.alu.z
        if take: self.pc.value = addr
        self.ctrl_sig = f"JPOS {'(SIM)' if take else '(NAO)'}"
        self.bus['c'] = True

    def _jzer(self, addr):
        # Pula se Zero (Z=1)
        take = self.alu.z
        if take: self.pc.value = addr
        self.ctrl_sig = f"JZER {'(SIM)' if take else '(NAO)'}"
        self.bus['c'] = True

    def _jump(self, addr):
        # Pulo incondicional
        self.pc.value = addr
        self.bus['c'] = True

    def _loco(self, addr):
        # Carrega constante imediata (0-4095)
        # Verifica sinal (12 bits)
        val = addr if not (addr & 0x800) else addr - 0x1000
        self.h.value = self._alu_sh(val, 0, 'A')
        self.ctrl_sig = f"LOCO {val}"
        self.bus['c'] = True

    def _lodl(self, addr):
        # Load Local: Mem[SP + addr] -> H
        eff = (self.sp.value + addr) & MASK_12BIT
        val = self.mem.read_data(eff)
        self.h.value = self._alu_sh(val, 0, 'A')
        self.bus.update({'rd': True, 'b': True, 'c': True})

    def _stol(self, addr):
        # Store Local: H -> Mem[SP + addr]
        eff = (self.sp.value + addr) & MASK_12BIT
        self.mem.write(eff, self.h.value)
        self.bus.update({'wr': True, 'b': True})

    def _addl(self, addr):
        eff = (self.sp.value + addr) & MASK_12BIT
        val = self.mem.read_data(eff)
        self.h.value = self._alu_sh(self.h.value, val, 'ADD')
        self.bus.update({'rd': True, 'a': True, 'c': True})

    def _subl(self, addr):
        eff = (self.sp.value + addr) & MASK_12BIT
        val = self.mem.read_data(eff)
        self.h.value = self._alu_sh(self.h.value, val, 'SUB')
        self.bus.update({'rd': True, 'a': True, 'c': True})

    def _jneg(self, addr):
        if self.alu.n: self.pc.value = addr
        self.bus['c'] = True

    def _jnze(self, addr):
        if not self.alu.z: self.pc.value = addr
        self.bus['c'] = True

    def _call(self, addr):
        # Chamada de funcao: Salva PC na pilha e pula
        self.sp.value -= 1
        self.mem.write(self.sp.value, self.pc.value)
        self.pc.value = addr
        self.bus.update({'wr': True, 'c': True})

    def _ext(self, func):
        # Instrucoes estendidas (sem operando ou operacoes de pilha)
        fns = {
            0: self._halt, 1: self._pshi, 2: self._popi, 
            3: self._push, 4: self._pop, 5: self._retn, 
            6: self._swap, 7: self._insp, 8: self._desp
        }
        if func in fns: fns[func]()
        else: self.ctrl_sig = f"NOP x{func:X}"

    def _halt(self): 
        self.halted = True
        self.ctrl_sig = "HALTED"

    def _pshi(self):
        # Push Indireto (Mem[H] -> Pilha)
        val = self.mem.read_data(self.h.value)
        self.sp.value -= 1
        self.mem.write(self.sp.value, val)
        self.bus.update({'rd': True, 'wr': True})

    def _popi(self):
        # Pop Indireto (Pilha -> Mem[H])
        val = self.mem.read_data(self.sp.value)
        self.sp.value += 1
        self.mem.write(self.h.value, val)
        self.bus.update({'rd': True, 'wr': True})

    def _push(self):
        # Empilha H
        self.sp.value -= 1
        self.mem.write(self.sp.value, self.h.value)
        self.bus.update({'wr': True, 'b': True})

    def _pop(self):
        # Desempilha para H
        val = self.mem.read_data(self.sp.value)
        self.sp.value += 1
        self.h.value = self._alu_sh(val, 0, 'A')
        self.bus.update({'rd': True, 'c': True})

    def _retn(self):
        # Retorno de funcao (Recupera PC da pilha)
        ret = self.mem.read_data(self.sp.value)
        self.sp.value += 1
        self.pc.value = ret
        self.bus.update({'rd': True, 'c': True})

    def _swap(self):
        # Troca H com SP
        self.h.value, self.sp.value = self.sp.value, self.h.value
        self.bus['c'] = True

    def _insp(self): self.sp.value += 1 # Incrementa SP
    def _desp(self): self.sp.value -= 1 # Decrementa SP

    def cycle_all(self):
        # Roda um ciclo completo (debug)
        self.fetch()
        self.decode()
        self.execute()