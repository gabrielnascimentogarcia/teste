import random

class Register:
    """Representa um registrador de 16 bits com comportamento cíclico (wrap-around)."""
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


class Cache:
    """Classe genérica para Cache (I-Cache ou D-Cache)."""
    def __init__(self, size=16, name="L1"):
        self.lines = [{'valid': False, 'tag': 0, 'data': 0} for _ in range(size)]
        self.size = size
        self.name = name
        self.last_status = "IDLE"
        self.hit_count = 0
        self.miss_count = 0

    def read(self, real_addr, ram_memory):
        index = real_addr % self.size
        tag = real_addr // self.size
        line = self.lines[index]

        if line['valid'] and line['tag'] == tag:
            self.last_status = "HIT"
            self.hit_count += 1
            return line['data']
        else:
            self.last_status = "MISS"
            self.miss_count += 1
            val = ram_memory[real_addr]
            line['valid'] = True
            line['tag'] = tag
            line['data'] = val
            return val

    def write_through(self, real_addr, value):
        index = real_addr % self.size
        tag = real_addr // self.size
        line = self.lines[index]

        # Só atualiza se já estiver na cache (Write No-Allocate)
        if line['valid'] and line['tag'] == tag:
            line['data'] = value
            self.last_status = "WRITE HIT"
        else:
            self.last_status = "WRITE MISS"
    
    def flush(self):
        for line in self.lines:
            line['valid'] = False
        self.last_status = "FLUSHED"


class MemorySystem:
    """Simula RAM (4096 palavras) e Caches separadas."""
    def __init__(self, size=4096, cache_size=8):
        self.size = size
        self.ram = [0] * size
        self.i_cache = Cache(cache_size, "I-Cache")
        self.d_cache = Cache(cache_size, "D-Cache")
        self.last_accessed_addr = -1 

    def _mask_addr(self, address):
        return address & 0xFFF

    def read_instruction(self, address):
        real_addr = self._mask_addr(address)
        self.last_accessed_addr = real_addr
        return self.i_cache.read(real_addr, self.ram)

    def read_data(self, address):
        real_addr = self._mask_addr(address)
        self.last_accessed_addr = real_addr
        return self.d_cache.read(real_addr, self.ram)

    def write(self, address, value):
        real_addr = self._mask_addr(address)
        value &= 0xFFFF
        self.last_accessed_addr = real_addr
        
        self.ram[real_addr] = value
        self.d_cache.write_through(real_addr, value)

    def load_program(self, machine_code):
        self.ram = [0] * self.size
        for i, code in enumerate(machine_code):
            if i < len(self.ram):
                self.ram[i] = code
        self.flush_caches()

    def flush_caches(self):
        self.i_cache.flush()
        self.d_cache.flush()


class ALU:
    def __init__(self):
        self.n_flag = False 
        self.z_flag = False
        self.last_result = 0

    def compute(self, a, b, op):
        res = 0
        a_signed = a if a < 0x8000 else a - 0x10000
        b_signed = b if b < 0x8000 else b - 0x10000
        
        if op == 'ADD': res = a_signed + b_signed
        elif op == 'SUB': res = a_signed - b_signed
        elif op == 'AND': res = a & b
        elif op == 'OR': res = a | b
        elif op == 'A': res = a
        elif op == 'B': res = b
        elif op == 'INC_A': res = a_signed + 1
        elif op == 'DEC_A': res = a_signed - 1
        elif op == 'INV_A': res = ~a
        
        self.last_result = res & 0xFFFF
        self.z_flag = (self.last_result == 0)
        self.n_flag = (self.last_result & 0x8000) != 0
        return self.last_result

class Mic1CPU:
    def __init__(self):
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
        self.control_signals = "RESET"
        
        self.bus_activity = {
            'bus_a': False, 'bus_b': False, 'bus_c': False, 
            'mem_read': False, 'mem_write': False
        }
        self.sp.value = 4095

    def reset(self):
        registers = [self.mar, self.mdr, self.pc, self.mbr, self.lv, self.cpp, self.tos, self.opc, self.h]
        for r in registers: r.value = 0
        self.sp.value = 4095
        self.alu.n_flag = False
        self.alu.z_flag = False
        self.memory.flush_caches()
        self.memory.last_accessed_addr = -1
        self.halted = False
        self.cycle_count = 0
        self.control_signals = "RESET"
        self.clear_bus_activity()

    def clear_bus_activity(self):
        for k in self.bus_activity: self.bus_activity[k] = False

    def fetch_cycle(self):
        # CORREÇÃO: Atualizar OPC (Old PC) com o PC atual antes de incrementar
        self.opc.value = self.pc.value
        
        self.mar.value = self.pc.value
        self.clear_bus_activity()
        self.bus_activity['bus_b'] = True 
        self.bus_activity['mem_read'] = True
        
        val = self.memory.read_instruction(self.mar.value)
        self.pc.value += 1
        self.mdr.value = val
        self.mbr.value = self.mdr.value 
        return self.mbr.value >> 12 

    def execute_instruction(self):
        if self.halted: return
        opcode = self.fetch_cycle()
        addr_field = self.mbr.value & 0x0FFF
        op_bin = f"{opcode:04b}"
        self.control_signals = f"Op: {op_bin}"

        if opcode == 0x0: # LODD
            val = self.memory.read_data(addr_field)
            self.h.value = self.alu.compute(val, 0, 'A') 
            self.control_signals = f"LODD: AC <- Mem[{addr_field:03X}]"
            self.bus_activity['mem_read'] = True; self.bus_activity['bus_c'] = True

        elif opcode == 0x1: # STOD
            self.memory.write(addr_field, self.h.value)
            self.control_signals = f"STOD: Mem[{addr_field:03X}] <- AC"
            self.bus_activity['mem_write'] = True; self.bus_activity['bus_b'] = True

        elif opcode == 0x2: # ADDD
            mem_val = self.memory.read_data(addr_field)
            res = self.alu.compute(self.h.value, mem_val, 'ADD')
            self.h.value = res
            self.control_signals = f"ADDD"
            self.bus_activity['bus_a'] = True; self.bus_activity['bus_b'] = True; self.bus_activity['bus_c'] = True

        elif opcode == 0x3: # SUBD
            mem_val = self.memory.read_data(addr_field)
            res = self.alu.compute(self.h.value, mem_val, 'SUB')
            self.h.value = res
            self.control_signals = f"SUBD"
            self.bus_activity['bus_a'] = True; self.bus_activity['bus_b'] = True; self.bus_activity['bus_c'] = True

        elif opcode == 0x4: # JPOS
            if not self.alu.n_flag and not self.alu.z_flag:
                self.pc.value = addr_field
                self.control_signals = "JPOS (Taken)"
            else: self.control_signals = "JPOS (Not Taken)"
            self.bus_activity['bus_c'] = True

        elif opcode == 0x5: # JZER
            if self.alu.z_flag:
                self.pc.value = addr_field
                self.control_signals = "JZER (Taken)"
            else: self.control_signals = "JZER (Not Taken)"
            self.bus_activity['bus_c'] = True

        elif opcode == 0x6: # JUMP
            self.pc.value = addr_field
            self.control_signals = "JUMP"
            self.bus_activity['bus_c'] = True

        elif opcode == 0x7: # LOCO
            const_val = addr_field
            if const_val & 0x800: const_val -= 0x1000 
            self.h.value = self.alu.compute(const_val, 0, 'A') 
            self.control_signals = f"LOCO: AC <- {const_val}"
            self.bus_activity['bus_c'] = True

        elif opcode == 0x8: # LODL
            eff_addr = (self.sp.value + addr_field) & 0xFFF 
            val = self.memory.read_data(eff_addr)
            self.h.value = self.alu.compute(val, 0, 'A')
            self.control_signals = f"LODL"
            self.bus_activity['mem_read'] = True; self.bus_activity['bus_b'] = True; self.bus_activity['bus_c'] = True

        elif opcode == 0x9: # STOL
            eff_addr = (self.sp.value + addr_field) & 0xFFF
            self.memory.write(eff_addr, self.h.value)
            self.control_signals = f"STOL"
            self.bus_activity['mem_write'] = True; self.bus_activity['bus_b'] = True

        elif opcode == 0xA: # ADDL
            eff_addr = (self.sp.value + addr_field) & 0xFFF
            mem_val = self.memory.read_data(eff_addr)
            self.h.value = self.alu.compute(self.h.value, mem_val, 'ADD')
            self.control_signals = "ADDL"
            self.bus_activity['mem_read'] = True; self.bus_activity['bus_a'] = True; self.bus_activity['bus_c'] = True

        elif opcode == 0xB: # SUBL
            eff_addr = (self.sp.value + addr_field) & 0xFFF
            mem_val = self.memory.read_data(eff_addr)
            self.h.value = self.alu.compute(self.h.value, mem_val, 'SUB')
            self.control_signals = "SUBL"
            self.bus_activity['mem_read'] = True; self.bus_activity['bus_a'] = True; self.bus_activity['bus_c'] = True
            
        elif opcode == 0xC: # JNEG
            if self.alu.n_flag:
                self.pc.value = addr_field
                self.control_signals = "JNEG (Taken)"
            else: self.control_signals = "JNEG (Not Taken)"
            self.bus_activity['bus_c'] = True

        elif opcode == 0xD: # JNZE
            if not self.alu.z_flag:
                self.pc.value = addr_field
                self.control_signals = "JNZE (Taken)"
            else: self.control_signals = "JNZE (Not Taken)"
            self.bus_activity['bus_c'] = True

        elif opcode == 0xE: # CALL
            self.sp.value -= 1
            self.memory.write(self.sp.value, self.pc.value)
            self.pc.value = addr_field
            self.control_signals = f"CALL {addr_field:03X}"
            self.bus_activity['mem_write'] = True; self.bus_activity['bus_c'] = True

        elif opcode == 0xF:
            func = addr_field
            if func == 0: # HALT
                self.halted = True
                self.control_signals = "HALTED"
            elif func == 1: # PSHI
                addr_ptr = self.h.value
                val = self.memory.read_data(addr_ptr)
                self.sp.value -= 1
                self.memory.write(self.sp.value, val)
                self.control_signals = "PSHI"
                self.bus_activity['mem_read'] = True; self.bus_activity['mem_write'] = True
            elif func == 2: # POPI
                val = self.memory.read_data(self.sp.value)
                self.sp.value += 1
                addr_ptr = self.h.value
                self.memory.write(addr_ptr, val)
                self.control_signals = "POPI"
                self.bus_activity['mem_read'] = True; self.bus_activity['mem_write'] = True
            elif func == 3: # PUSH
                self.sp.value -= 1
                self.memory.write(self.sp.value, self.h.value)
                self.control_signals = "PUSH"
                self.bus_activity['mem_write'] = True; self.bus_activity['bus_b'] = True
            elif func == 4: # POP
                val = self.memory.read_data(self.sp.value)
                self.sp.value += 1
                self.h.value = self.alu.compute(val, 0, 'A') 
                self.control_signals = "POP"
                self.bus_activity['mem_read'] = True; self.bus_activity['bus_c'] = True
            elif func == 5: # RETN
                ret_addr = self.memory.read_data(self.sp.value)
                self.sp.value += 1
                self.pc.value = ret_addr
                self.control_signals = "RETN"
                self.bus_activity['mem_read'] = True; self.bus_activity['bus_c'] = True
            elif func == 6: # SWAP
                tmp = self.h.value
                self.h.value = self.sp.value
                self.sp.value = tmp
                self.control_signals = "SWAP"
                self.bus_activity['bus_c'] = True
            elif func == 7: # INSP
                self.sp.value += 1
                self.control_signals = "INSP"
            elif func == 8: # DESP
                self.sp.value -= 1
                self.control_signals = "DESP"
            else:
                self.control_signals = f"NOP / Unknown F{func:03X}"
        self.cycle_count += 1