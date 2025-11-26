from dataclasses import dataclass, field
from typing import List
from src.common.constants import MASK_16BIT, MASK_12BIT, CACHE_SIZE_L1, MEM_SIZE

@dataclass
class Register:
    name: str
    _value: int = 0

    @property
    def value(self) -> int:
        return self._value & MASK_16BIT

    @value.setter
    def value(self, val: int):
        self._value = val & MASK_16BIT

    def __repr__(self):
        return f"[{self.name}: {self.value:04X}]"

@dataclass
class CacheLine:
    valid: bool = False
    tag: int = 0
    data: int = 0

class Cache:
    def __init__(self, size=CACHE_SIZE_L1, name="L1"):
        self.size = size
        self.name = name
        self.last_status = "FLUSHED"
        self.lines = [CacheLine() for _ in range(size)]

    def read(self, real_addr: int, ram_memory: List[int]) -> int:
        index = real_addr % self.size
        tag = real_addr // self.size
        line = self.lines[index]

        if line.valid and line.tag == tag:
            self.last_status = "HIT"
            return line.data
        
        self.last_status = "MISS"
        val = ram_memory[real_addr]
        line.valid = True
        line.tag = tag
        line.data = val
        return val

    def write_through(self, real_addr: int, value: int):
        index = real_addr % self.size
        tag = real_addr // self.size
        line = self.lines[index]

        if line.valid and line.tag == tag:
            line.data = value & MASK_16BIT
            self.last_status = "WRITE HIT"
        else:
            self.last_status = "WRITE MISS"

    def flush(self):
        self.lines = [CacheLine() for _ in range(self.size)]
        self.last_status = "FLUSHED"

class MemorySystem:
    def __init__(self, size=MEM_SIZE):
        self.size = size
        self.ram = [0] * size
        self.i_cache = Cache(name="I-Cache")
        self.d_cache = Cache(name="D-Cache")
        self.last_accessed_addr = -1

    def read_instruction(self, address: int) -> int:
        addr = address & MASK_12BIT
        self.last_accessed_addr = addr
        return self.i_cache.read(addr, self.ram)

    def read_data(self, address: int) -> int:
        addr = address & MASK_12BIT
        self.last_accessed_addr = addr
        return self.d_cache.read(addr, self.ram)

    def write(self, address: int, value: int):
        addr = address & MASK_12BIT
        value &= MASK_16BIT
        self.last_accessed_addr = addr
        self.ram[addr] = value
        self.d_cache.write_through(addr, value)
        self.i_cache.flush() # Código automodificável requer flush

    def load_program(self, machine_code):
        self.ram = [0] * self.size
        if isinstance(machine_code, dict):
            for addr, val in machine_code.items():
                if 0 <= addr < self.size:
                    self.ram[addr] = val & MASK_16BIT
        self.flush_caches()

    def flush_caches(self):
        self.i_cache.flush()
        self.d_cache.flush()

class ALU:
    def __init__(self):
        self.n_flag = False
        self.z_flag = False
        self.last_result = 0

    def compute(self, a, b, op, update_flags=True):
        a_signed = a if a < 0x8000 else a - 0x10000
        b_signed = b if b < 0x8000 else b - 0x10000
        res = 0
        
        if op == 'ADD': res = a_signed + b_signed
        elif op == 'SUB': res = a_signed - b_signed
        elif op == 'AND': res = a & b
        elif op == 'OR': res = a | b
        elif op == 'A': res = a
        elif op == 'B': res = b
        elif op == 'INC_A': res = a_signed + 1
        elif op == 'DEC_A': res = a_signed - 1
        elif op == 'INV_A': res = ~a
        else: res = a 

        self.last_result = res & MASK_16BIT
        if update_flags:
            self.z_flag = (self.last_result == 0)
            self.n_flag = (self.last_result & 0x8000) != 0
        return self.last_result

class Shifter:
    @staticmethod
    def compute(val, op):
        val &= MASK_16BIT
        if op == 'LSHIFT': return (val << 1) & MASK_16BIT
        elif op == 'RSHIFT': return (val >> 1) & MASK_16BIT
        return val