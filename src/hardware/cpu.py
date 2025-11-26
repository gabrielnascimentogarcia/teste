from src.common.constants import MASK_12BIT
from src.common.opcodes import Opcode
from src.hardware.components import Register, MemorySystem, ALU, Shifter

class Mic1CPU:
    def __init__(self):
        self.mar = Register("MAR")
        self.mdr = Register("MDR")
        self.pc  = Register("PC")
        self.mbr = Register("MBR")
        self.sp  = Register("SP", 4095)
        self.opc = Register("OPC")
        self.h   = Register("H")
        self.lv  = Register("LV")
        self.cpp = Register("CPP")
        self.tos = Register("TOS")

        self.memory = MemorySystem()
        self.alu = ALU()
        self.shifter = Shifter()
        
        self.halted = False
        self.cycle_count = 0
        self.control_signals = "RESET"
        self.current_opcode = -1
        
        self.bus_activity = {
            'bus_a': False, 'bus_b': False, 'bus_c': False, 
            'mem_read': False, 'mem_write': False
        }

        # Tabela de Despacho (Evita if/else gigante)
        self._ops = {
            Opcode.LODD: self._op_lodd, Opcode.STOD: self._op_stod,
            Opcode.ADDD: self._op_addd, Opcode.SUBD: self._op_subd,
            Opcode.JPOS: self._op_jpos, Opcode.JZER: self._op_jzer,
            Opcode.JUMP: self._op_jump, Opcode.LOCO: self._op_loco,
            Opcode.LODL: self._op_lodl, Opcode.STOL: self._op_stol,
            Opcode.ADDL: self._op_addl, Opcode.SUBL: self._op_subl,
            Opcode.JNEG: self._op_jneg, Opcode.JNZE: self._op_jnze,
            Opcode.CALL: self._op_call, Opcode.EXT:  self._op_ext
        }

    def reset(self):
        for r in [self.mar, self.mdr, self.pc, self.mbr, self.lv, self.cpp, self.tos, self.opc, self.h]:
            r.value = 0
        self.sp.value = 4095
        self.alu.n_flag = False
        self.alu.z_flag = False
        self.memory.flush_caches()
        self.memory.last_accessed_addr = -1
        self.halted = False
        self.cycle_count = 0
        self.control_signals = "RESET"
        self.current_opcode = -1
        self._clear_bus()

    def _clear_bus(self):
        for k in self.bus_activity: self.bus_activity[k] = False

    def _alu_sh(self, a, b, alu_op, sh_op=None):
        res = self.alu.compute(a, b, alu_op)
        return self.shifter.compute(res, sh_op)

    def step_1_fetch_addr(self):
        self.opc.value = self.pc.value
        self.mar.value = self.pc.value
        self._clear_bus()
        self.bus_activity['bus_b'] = True
        self.bus_activity['bus_c'] = True
        self.control_signals = "FETCH: PC -> MAR"

    def step_2_fetch_mem_decode(self):
        val = self.memory.read_instruction(self.mar.value)
        self.pc.value += 1
        self.mdr.value = val
        self.mbr.value = self.mdr.value
        self.current_opcode = self.mbr.value >> 12
        self._clear_bus()
        self.bus_activity['mem_read'] = True
        self.bus_activity['bus_c'] = True
        self.control_signals = "DECODE: Mem -> MDR -> MBR"

    def execute_micro_instruction(self):
        if self.halted: return
        opcode = self.current_opcode
        addr = self.mbr.value & MASK_12BIT
        self.control_signals = f"Op: {opcode:04b}"
        self._clear_bus()
        
        if opcode in self._ops:
            self._ops[opcode](addr)
        else:
            self.control_signals = f"Unknown Op: {opcode}"
        self.cycle_count += 1

    # --- Implementações das Instruções ---
    def _op_lodd(self, addr):
        val = self.memory.read_data(addr)
        self.h.value = self._alu_sh(val, 0, 'A')
        self.control_signals = f"LODD [{addr:03X}]"
        self.bus_activity.update({'mem_read': True, 'bus_c': True})

    def _op_stod(self, addr):
        self.memory.write(addr, self.h.value)
        self.control_signals = f"STOD [{addr:03X}]"
        self.bus_activity.update({'mem_write': True, 'bus_b': True})

    def _op_addd(self, addr):
        val = self.memory.read_data(addr)
        self.h.value = self._alu_sh(self.h.value, val, 'ADD')
        self.control_signals = "ADDD"
        self.bus_activity.update({'bus_a': True, 'bus_b': True, 'bus_c': True})

    def _op_subd(self, addr):
        val = self.memory.read_data(addr)
        self.h.value = self._alu_sh(self.h.value, val, 'SUB')
        self.control_signals = "SUBD"
        self.bus_activity.update({'bus_a': True, 'bus_b': True, 'bus_c': True})

    def _op_jpos(self, addr):
        taken = not self.alu.n_flag and not self.alu.z_flag
        if taken: self.pc.value = addr
        self.control_signals = f"JPOS ({'Taken' if taken else 'Not'})"
        self.bus_activity['bus_c'] = True

    def _op_jzer(self, addr):
        taken = self.alu.z_flag
        if taken: self.pc.value = addr
        self.control_signals = f"JZER ({'Taken' if taken else 'Not'})"
        self.bus_activity['bus_c'] = True

    def _op_jump(self, addr):
        self.pc.value = addr
        self.control_signals = "JUMP"
        self.bus_activity['bus_c'] = True

    def _op_loco(self, addr):
        val = addr if not (addr & 0x800) else addr - 0x1000
        self.h.value = self._alu_sh(val, 0, 'A')
        self.control_signals = f"LOCO {val}"
        self.bus_activity['bus_c'] = True

    def _op_lodl(self, addr):
        eff = (self.sp.value + addr) & MASK_12BIT
        val = self.memory.read_data(eff)
        self.h.value = self._alu_sh(val, 0, 'A')
        self.control_signals = "LODL"
        self.bus_activity.update({'mem_read': True, 'bus_b': True, 'bus_c': True})

    def _op_stol(self, addr):
        eff = (self.sp.value + addr) & MASK_12BIT
        self.memory.write(eff, self.h.value)
        self.control_signals = "STOL"
        self.bus_activity.update({'mem_write': True, 'bus_b': True})

    def _op_addl(self, addr):
        eff = (self.sp.value + addr) & MASK_12BIT
        val = self.memory.read_data(eff)
        self.h.value = self._alu_sh(self.h.value, val, 'ADD')
        self.control_signals = "ADDL"
        self.bus_activity.update({'mem_read': True, 'bus_a': True, 'bus_c': True})

    def _op_subl(self, addr):
        eff = (self.sp.value + addr) & MASK_12BIT
        val = self.memory.read_data(eff)
        self.h.value = self._alu_sh(self.h.value, val, 'SUB')
        self.control_signals = "SUBL"
        self.bus_activity.update({'mem_read': True, 'bus_a': True, 'bus_c': True})

    def _op_jneg(self, addr):
        if self.alu.n_flag: self.pc.value = addr
        self.control_signals = f"JNEG ({'Taken' if self.alu.n_flag else 'Not'})"
        self.bus_activity['bus_c'] = True

    def _op_jnze(self, addr):
        taken = not self.alu.z_flag
        if taken: self.pc.value = addr
        self.control_signals = f"JNZE ({'Taken' if taken else 'Not'})"
        self.bus_activity['bus_c'] = True

    def _op_call(self, addr):
        self.sp.value -= 1
        self.memory.write(self.sp.value, self.pc.value)
        self.pc.value = addr
        self.control_signals = f"CALL {addr:03X}"
        self.bus_activity.update({'mem_write': True, 'bus_c': True})

    def _op_ext(self, func):
        ext_map = {0: self._ex_halt, 1: self._ex_pshi, 2: self._ex_popi, 
                   3: self._ex_push, 4: self._ex_pop, 5: self._ex_retn, 
                   6: self._ex_swap, 7: self._ex_insp, 8: self._ex_desp}
        if func in ext_map: ext_map[func]()
        else: self.control_signals = f"NOP F{func:X}"

    def _ex_halt(self): 
        self.halted = True
        self.control_signals = "HALTED"

    def _ex_pshi(self):
        val = self.memory.read_data(self.h.value)
        self.sp.value -= 1
        self.memory.write(self.sp.value, val)
        self.control_signals = "PSHI"
        self.bus_activity.update({'mem_read': True, 'mem_write': True})

    def _ex_popi(self):
        val = self.memory.read_data(self.sp.value)
        self.sp.value += 1
        self.memory.write(self.h.value, val)
        self.control_signals = "POPI"
        self.bus_activity.update({'mem_read': True, 'mem_write': True})

    def _ex_push(self):
        self.sp.value -= 1
        self.memory.write(self.sp.value, self.h.value)
        self.control_signals = "PUSH"
        self.bus_activity.update({'mem_write': True, 'bus_b': True})

    def _ex_pop(self):
        val = self.memory.read_data(self.sp.value)
        self.sp.value += 1
        self.h.value = self._alu_sh(val, 0, 'A')
        self.control_signals = "POP"
        self.bus_activity.update({'mem_read': True, 'bus_c': True})

    def _ex_retn(self):
        ret = self.memory.read_data(self.sp.value)
        self.sp.value += 1
        self.pc.value = ret
        self.control_signals = "RETN"
        self.bus_activity.update({'mem_read': True, 'bus_c': True})

    def _ex_swap(self):
        self.h.value, self.sp.value = self.sp.value, self.h.value
        self.control_signals = "SWAP"
        self.bus_activity['bus_c'] = True

    def _ex_insp(self): 
        self.sp.value += 1
        self.control_signals = "INSP"

    def _ex_desp(self): 
        self.sp.value -= 1
        self.control_signals = "DESP"

    def execute_full_cycle(self):
        self.step_1_fetch_addr()
        self.step_2_fetch_mem_decode()
        self.execute_micro_instruction()