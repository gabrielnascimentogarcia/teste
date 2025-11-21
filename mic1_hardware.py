import random

class Register:
    """Representa um registrador de 16 bits."""
    def __init__(self, name, value=0):
        self.name = name
        self._value = value 

    @property
    def value(self):
        return self._value & 0xFFFF 

    @value.setter
    def value(self, val):
        self._value = val & 0xFFFF

    def __repr__(self):
        return f"[{self.name}: {self.value:04X}]"


class CacheLine:
    """Representa uma linha de Cache (Direct Mapped)."""
    def __init__(self):
        self.valid = False
        self.tag = 0
        self.data = 0 

class MemorySystem:
    """Simula a RAM (4096 palavras) e uma Cache de Dados L1."""
    def __init__(self, size=4096, cache_size=16):
        self.ram = [0] * size
        self.cache_lines = [CacheLine() for _ in range(cache_size)]
        self.cache_size = cache_size
        self.last_access_status = "IDLE" # IDLE, HIT, MISS
        self.last_accessed_addr = -1 # Para destaque na GUI

    def read(self, address):
        address &= 0xFFF 
        self.last_accessed_addr = address
        
        index = address % self.cache_size
        tag = address // self.cache_size
        line = self.cache_lines[index]

        if line.valid and line.tag == tag:
            self.last_access_status = f"CACHE HIT (Idx: {index})"
            return line.data
        else:
            self.last_access_status = f"CACHE MISS (Idx: {index})"
            val = self.ram[address]
            line.valid = True
            line.tag = tag
            line.data = val
            return val

    def write(self, address, value):
        address &= 0xFFF
        value &= 0xFFFF
        self.last_accessed_addr = address
        
        self.ram[address] = value
        
        index = address % self.cache_size
        tag = address // self.cache_size
        line = self.cache_lines[index]
        
        line.valid = True
        line.tag = tag
        line.data = value
        self.last_access_status = "WRITE MEM & CACHE"

    def load_program(self, machine_code):
        for i, code in enumerate(machine_code):
            if i < len(self.ram):
                self.ram[i] = code


class ALU:
    """Unidade Lógica e Aritmética."""
    def __init__(self):
        self.n_flag = False
        self.z_flag = False
        self.last_result = 0

    def compute(self, a, b, op):
        res = 0
        if op == 'ADD': res = a + b
        elif op == 'SUB': res = a - b
        elif op == 'AND': res = a & b
        elif op == 'OR':  res = a | b
        elif op == 'A':   res = a
        elif op == 'B':   res = b
        elif op == 'INC_A': res = a + 1
        elif op == 'DEC_A': res = a - 1
        elif op == 'INV_A': res = ~a
        
        self.last_result = res & 0xFFFF
        self.z_flag = (self.last_result == 0)
        self.n_flag = (self.last_result & 0x8000) != 0
        return self.last_result

class Mic1CPU:
    """Controlador principal da microarquitetura."""
    def __init__(self):
        # Datapath Registers
        self.mar = Register("MAR")
        self.mdr = Register("MDR")
        self.pc  = Register("PC")
        self.mbr = Register("MBR")
        self.sp  = Register("SP")
        self.lv  = Register("LV")
        self.cpp = Register("CPP")
        self.tos = Register("TOS")
        self.opc = Register("OPC")
        self.h   = Register("H") 

        self.memory = MemorySystem()
        self.alu = ALU()
        
        self.halted = False
        self.cycle_count = 0
        self.control_signals = ""
        
        # Rastreamento para Animação de Barramento
        # 'active' define se o barramento deve acender na GUI
        self.bus_activity = {
            'bus_a': False, # Registradores -> ALU A
            'bus_b': False, # Registradores/MDR -> ALU B
            'bus_c': False, # ALU/Shifter -> Registradores
            'mem_read': False,
            'mem_write': False
        }

    def reset(self):
        registers = [self.mar, self.mdr, self.pc, self.mbr, self.sp, self.lv, self.cpp, self.tos, self.opc, self.h]
        for r in registers: r.value = 0
        self.memory = MemorySystem()
        self.halted = False
        self.cycle_count = 0
        self.clear_bus_activity()

    def clear_bus_activity(self):
        for k in self.bus_activity:
            self.bus_activity[k] = False

    def fetch_cycle(self):
        """Simula busca e define atividade de barramento visual."""
        self.mar.value = self.pc.value
        self.clear_bus_activity()
        self.bus_activity['bus_b'] = True # PC -> Bus B -> ALU -> MAR (Simplificado visualmente)
        self.bus_activity['mem_read'] = True
        
        val = self.memory.read(self.mar.value)
        self.pc.value += 1
        self.mdr.value = val
        self.mbr.value = self.mdr.value 
        
        return self.mbr.value >> 12 

    def execute_instruction(self):
        if self.halted: return

        opcode = self.fetch_cycle()
        addr_field = self.mbr.value & 0x0FFF
        
        # Reseta atividades para o ciclo de execução
        # (Mantemos mem_read true se o fetch acabou de acontecer para persistência visual breve)
        self.control_signals = f"Op: {opcode:04b}"

        # Lógica das Instruções com Flags de Barramento
        if opcode == 0x0: # LODD
            val = self.memory.read(addr_field)
            self.h.value = val
            self.control_signals = f"LODD: AC <- Mem[{addr_field}]"
            self.bus_activity['mem_read'] = True
            self.bus_activity['bus_c'] = True # Mem -> H

        elif opcode == 0x1: # STOD
            self.memory.write(addr_field, self.h.value)
            self.control_signals = f"STOD: Mem[{addr_field}] <- AC"
            self.bus_activity['mem_write'] = True
            self.bus_activity['bus_b'] = True # AC(H) -> Mem

        elif opcode == 0x2: # ADDD
            mem_val = self.memory.read(addr_field)
            res = self.alu.compute(self.h.value, mem_val, 'ADD')
            self.h.value = res
            self.control_signals = f"ADDD: AC += Mem[{addr_field}]"
            self.bus_activity['bus_a'] = True # H
            self.bus_activity['bus_b'] = True # Mem
            self.bus_activity['bus_c'] = True # Result -> H

        elif opcode == 0x3: # SUBD
            mem_val = self.memory.read(addr_field)
            res = self.alu.compute(self.h.value, mem_val, 'SUB')
            self.h.value = res
            self.control_signals = f"SUBD: AC -= Mem[{addr_field}]"
            self.bus_activity['bus_a'] = True
            self.bus_activity['bus_b'] = True
            self.bus_activity['bus_c'] = True

        elif opcode == 0x4: # JPOS
            if self.h.value < 0x8000:
                self.pc.value = addr_field
                self.bus_activity['bus_c'] = True # Carrega PC
            self.control_signals = "JPOS"

        elif opcode == 0x5: # JZER
            if self.h.value == 0:
                self.pc.value = addr_field
                self.bus_activity['bus_c'] = True
            self.control_signals = "JZER"

        elif opcode == 0x6: # JUMP
            self.pc.value = addr_field
            self.bus_activity['bus_c'] = True
            self.control_signals = "JUMP"

        elif opcode == 0x7: # LOCO
            self.h.value = addr_field
            self.bus_activity['bus_c'] = True # Constante -> H
            self.control_signals = f"LOCO: AC <- {addr_field}"

        elif opcode == 0x8: # LODL
            eff_addr = (self.sp.value + addr_field) & 0xFFF
            self.h.value = self.memory.read(eff_addr)
            self.bus_activity['bus_b'] = True # SP + addr
            self.bus_activity['mem_read'] = True
            self.bus_activity['bus_c'] = True
            self.control_signals = "LODL"

        elif opcode == 0x9: # STOL
            eff_addr = (self.sp.value + addr_field) & 0xFFF
            self.memory.write(eff_addr, self.h.value)
            self.bus_activity['bus_b'] = True
            self.bus_activity['mem_write'] = True
            self.control_signals = "STOL"

        elif opcode == 0xA: # ADDL
            eff_addr = (self.sp.value + addr_field) & 0xFFF
            mem_val = self.memory.read(eff_addr)
            self.h.value = self.alu.compute(self.h.value, mem_val, 'ADD')
            self.bus_activity['bus_a'] = True
            self.bus_activity['mem_read'] = True
            self.bus_activity['bus_c'] = True
            self.control_signals = "ADDL"

        elif opcode == 0xB: # SUBL
            eff_addr = (self.sp.value + addr_field) & 0xFFF
            mem_val = self.memory.read(eff_addr)
            self.h.value = self.alu.compute(self.h.value, mem_val, 'SUB')
            self.bus_activity['bus_a'] = True
            self.bus_activity['mem_read'] = True
            self.bus_activity['bus_c'] = True
            self.control_signals = "SUBL"
            
        elif opcode == 0xC: # JNEG
            if self.h.value >= 0x8000:
                self.pc.value = addr_field
                self.bus_activity['bus_c'] = True
            self.control_signals = "JNEG"

        elif opcode == 0xD: # JNZE
            if self.h.value != 0:
                self.pc.value = addr_field
                self.bus_activity['bus_c'] = True
            self.control_signals = "JNZE"

        elif opcode == 0xE: # CALL
            self.sp.value = (self.sp.value - 1) & 0xFFFF
            self.memory.write(self.sp.value, self.pc.value)
            self.pc.value = addr_field
            self.bus_activity['mem_write'] = True
            self.bus_activity['bus_c'] = True
            self.control_signals = "CALL"

        elif opcode == 0xF: # Special/Halt
            func = addr_field
            if func == 0:
                self.halted = True
                self.control_signals = "HALTED"
            else:
                self.control_signals = f"Special: {func}"

        self.cycle_count += 1