from dataclasses import dataclass
from typing import List
from src.common.constants import MASK_16BIT, MASK_12BIT, CACHE_SIZE_L1, MEM_SIZE

@dataclass
class Register:
    """Classe simples pra representar um registrador"""
    name: str
    _value: int = 0

    @property
    def value(self) -> int:
        return self._value & MASK_16BIT

    @value.setter
    def value(self, val: int):
        # Garante que sempre fique em 16 bits ao atribuir
        self._value = val & MASK_16BIT

    def __repr__(self):
        return f"[{self.name}: {self.value:04X}]"

class CacheLine:
    def __init__(self):
        self.valid = False
        self.tag = 0
        self.data = 0

class Cache:
    """Implementacao da Cache L1 (Mapeamento Direto)"""
    def __init__(self, size=CACHE_SIZE_L1, name="L1"):
        self.size = size
        self.name = name
        self.last_status = "COLD"
        self.lines = [CacheLine() for _ in range(size)]

    def read(self, addr: int, ram_ref: List[int]) -> int:
        idx = addr % self.size
        tag = addr // self.size
        line = self.lines[idx]

        # Verifica Hit
        if line.valid and line.tag == tag:
            self.last_status = "HIT"
            return line.data
        
        # Miss: busca na RAM e atualiza a linha
        self.last_status = "MISS"
        val = ram_ref[addr]
        line.valid = True
        line.tag = tag
        line.data = val
        return val

    def write_through(self, addr: int, val: int):
        # Politica Write-Through: atualiza cache se der match
        idx = addr % self.size
        tag = addr // self.size
        line = self.lines[idx]

        if line.valid and line.tag == tag:
            line.data = val & MASK_16BIT
            self.last_status = "WR-HIT"
        else:
            self.last_status = "WR-MISS"

    def flush(self):
        # Limpa tudo (usado quando reseta ou carrega programa novo)
        self.lines = [CacheLine() for _ in range(self.size)]
        self.last_status = "FLUSHED"

class MemorySystem:
    """Gerencia RAM e as duas Caches (Instrucao e Dados)"""
    def __init__(self, size=MEM_SIZE):
        self.size = size
        self.ram = [0] * size
        self.i_cache = Cache(name="I-Cache")
        self.d_cache = Cache(name="D-Cache")
        self.last_addr = -1

    def read_instr(self, addr: int) -> int:
        addr &= MASK_12BIT
        self.last_addr = addr
        return self.i_cache.read(addr, self.ram)

    def read_data(self, addr: int) -> int:
        addr &= MASK_12BIT
        self.last_addr = addr
        return self.d_cache.read(addr, self.ram)

    def write(self, addr: int, val: int):
        addr &= MASK_12BIT
        val &= MASK_16BIT
        self.last_addr = addr
        self.ram[addr] = val
        
        # Atualiza D-Cache e limpa I-Cache (pra evitar codigo velho)
        self.d_cache.write_through(addr, val)
        self.i_cache.flush() 

    def load_bin(self, code_dict):
        # Carrega o codigo de maquina na RAM
        self.ram = [0] * self.size
        if isinstance(code_dict, dict):
            for addr, val in code_dict.items():
                if 0 <= addr < self.size:
                    self.ram[addr] = val & MASK_16BIT
        self.flush_all()

    def flush_all(self):
        self.i_cache.flush()
        self.d_cache.flush()

class ALU:
    """Unidade Logica e Aritmetica"""
    def __init__(self):
        self.n = False # Flag Negative
        self.z = False # Flag Zero
        self.last_res = 0

    def compute(self, a, b, op):
        # Simula complemento de 2 para operacoes com sinal
        sa = a if a < 0x8000 else a - 0x10000
        sb = b if b < 0x8000 else b - 0x10000
        res = 0
        
        if op == 'ADD':   res = sa + sb
        elif op == 'SUB': res = sa - sb
        elif op == 'AND': res = a & b
        elif op == 'OR':  res = a | b
        elif op == 'A':   res = a
        elif op == 'B':   res = b
        elif op == 'INC_A': res = sa + 1
        elif op == 'DEC_A': res = sa - 1
        elif op == 'INV_A': res = ~a
        else: res = a 

        self.last_res = res & MASK_16BIT
        
        # Atualiza as flags pra usar nos Jumps depois
        self.z = (self.last_res == 0)
        self.n = (self.last_res & 0x8000) != 0
        
        return self.last_res

class Shifter:
    @staticmethod
    def compute(val, op):
        val &= MASK_16BIT
        if op == 'LSHIFT': return (val << 1) & MASK_16BIT
        if op == 'RSHIFT': return (val >> 1) & MASK_16BIT
        return val