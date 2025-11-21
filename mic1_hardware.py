import random

class Register:
    """
    Representa um registrador de 16 bits.
    """
    def __init__(self, name, value=0):
        self.name = name
        self._value = value # Armazena internamente

    @property
    def value(self):
        return self._value & 0xFFFF # Garante 16 bits unsigned

    @value.setter
    def value(self, val):
        self._value = val & 0xFFFF

    def __repr__(self):
        return f"[{self.name}: {self.value:04X}]"


class CacheLine:
    """
    Representa uma linha de Cache (Direct Mapped).
    """
    def __init__(self):
        self.valid = False
        self.tag = 0
        self.data = 0 # Armazena uma palavra (simplificação para MIC-1)

class MemorySystem:
    """
    Simula a RAM (4096 palavras) e uma Cache de Dados L1.
    """
    def __init__(self, size=4096, cache_size=16):
        self.ram = [0] * size
        self.cache_lines = [CacheLine() for _ in range(cache_size)]
        self.cache_size = cache_size
        self.last_access_status = "IDLE" # IDLE, HIT, MISS

    def read(self, address):
        """
        Lê da memória verificando a cache primeiro.
        """
        address &= 0xFFF # Limita a 4096 posições
        
        # Lógica de Cache Direct Mapped
        index = address % self.cache_size
        tag = address // self.cache_size
        line = self.cache_lines[index]

        if line.valid and line.tag == tag:
            self.last_access_status = f"CACHE HIT (Idx: {index})"
            return line.data
        else:
            self.last_access_status = f"CACHE MISS (Idx: {index})"
            # Busca na RAM e atualiza Cache
            val = self.ram[address]
            line.valid = True
            line.tag = tag
            line.data = val
            return val

    def write(self, address, value):
        """
        Escreve na memória (Write-Through).
        """
        address &= 0xFFF
        value &= 0xFFFF
        
        # Escreve na RAM
        self.ram[address] = value
        
        # Atualiza Cache se estiver lá (Write Allocate ou apenas update)
        index = address % self.cache_size
        tag = address // self.cache_size
        line = self.cache_lines[index]
        
        # Estratégia simples: Atualiza a cache para manter coerência
        line.valid = True
        line.tag = tag
        line.data = value
        self.last_access_status = "WRITE MEM & CACHE"

    def load_program(self, machine_code):
        """Carrega lista de inteiros na memória a partir do endereço 0."""
        for i, code in enumerate(machine_code):
            if i < len(self.ram):
                self.ram[i] = code


class ALU:
    """
    Unidade Lógica e Aritmética.
    Suporta operações básicas do MIC-1 e gera flags N (Negative) e Z (Zero).
    """
    def __init__(self):
        self.n_flag = False
        self.z_flag = False
        self.last_result = 0

    def compute(self, a, b, op):
        """
        op: Código da operação (string simplificada para simulação)
            'ADD', 'SUB', 'AND', 'A', 'B', 'INC_A', 'DEC_A'
        """
        res = 0
        if op == 'ADD':
            res = a + b
        elif op == 'SUB': # A - B (Simplificado, MIC-1 real usa A + ~B + 1)
            res = a - b
        elif op == 'AND':
            res = a & b
        elif op == 'OR':
            res = a | b
        elif op == 'A':
            res = a
        elif op == 'B':
            res = b
        elif op == 'INC_A':
            res = a + 1
        elif op == 'DEC_A':
            res = a - 1
        elif op == 'INV_A':
            res = ~a
        
        # Ajuste para 16 bits (Simulando overflow circular)
        self.last_result = res & 0xFFFF
        
        # Atualiza Flags baseadas na interpretação de complemento de 2 para N
        self.z_flag = (self.last_result == 0)
        self.n_flag = (self.last_result & 0x8000) != 0 # Bit mais significativo
        
        return self.last_result

    def shifter(self, value, shift_type):
        """
        shift_type: 'None', 'SRA1' (Shift Right Arithmetic), 'SLL8' (Shift Left Logical 8)
        """
        val = value & 0xFFFF
        if shift_type == 'SRA1':
             # Mantém o bit de sinal
            sign = val & 0x8000
            return (val >> 1) | sign
        elif shift_type == 'SLL8':
            return (val << 8) & 0xFFFF
        return val


class Mic1CPU:
    """
    Controlador principal da microarquitetura.
    """
    def __init__(self):
        # Datapath Registers
        self.mar = Register("MAR")
        self.mdr = Register("MDR")
        self.pc  = Register("PC")
        self.mbr = Register("MBR") # Usado para conter o opcode as vezes
        self.sp  = Register("SP")
        self.lv  = Register("LV")
        self.cpp = Register("CPP")
        self.tos = Register("TOS")
        self.opc = Register("OPC") # Registrador auxiliar para salvar PC antigo
        self.h   = Register("H")   # Registrador acumulador da ALU (input A)

        # Componentes
        self.memory = MemorySystem()
        self.alu = ALU()
        
        # Estado de Controle
        self.halted = False
        self.cycle_count = 0
        
        # Buffer visual para barramentos (para a GUI ler)
        self.bus_a_val = 0
        self.bus_b_val = 0
        self.bus_c_val = 0
        self.control_signals = "" # Texto descrevendo o que está acontecendo

    def reset(self):
        registers = [self.mar, self.mdr, self.pc, self.mbr, self.sp, self.lv, self.cpp, self.tos, self.opc, self.h]
        for r in registers:
            r.value = 0
        self.memory = MemorySystem()
        self.halted = False
        self.cycle_count = 0
        self.bus_a_val = 0
        self.bus_b_val = 0
        self.bus_c_val = 0

    def step_micro_instruction(self):
        """
        Executa UM ciclo de clock (Microinstrução).
        Nota: Em um emulador completo, leríamos do Control Store.
        Aqui, vamos emular a lógica do interpretador MAC-1 hardcoded
        para facilitar a visualização passo-a-passo das macroinstruções.
        """
        # Esta função deve ser chamada pela GUI repetidamente.
        pass 

    # --- Métodos Auxiliares para Simulação das Macro-Instruções ---
    # Como não estamos implementando um parser de microcódigo binário real (MAL),
    # vamos simular o comportamento dos micro-passos para cada instrução MAC-1.

    def fetch_cycle(self):
        """Simula o ciclo de busca (comum a todas instruções)."""
        # 1. MAR = PC; rd
        self.mar.value = self.pc.value
        self.control_signals = "MAR <- PC; Read Memory"
        val = self.memory.read(self.mar.value)
        
        # 2. PC = PC + 1; rd (wait)
        self.pc.value += 1
        self.mdr.value = val # Dado chega do barramento de dados
        self.control_signals += " -> MDR Loaded"
        
        # 3. IR (MBR) = MDR;
        self.mbr.value = self.mdr.value # No MIC-1 original o byte superior é ignorado ou tratado, aqui usamos word completa
        
        return self.mbr.value >> 12 # Retorna Opcode (4 bits superiores)

    def execute_instruction(self):
        """
        Executa uma instrução MAC-1 completa (Macro-passo).
        Ideal para botão 'Step' na GUI.
        """
        if self.halted: return

        # Fetch
        opcode = self.fetch_cycle()
        addr_field = self.mbr.value & 0x0FFF # 12 bits inferiores

        # Decode & Execute
        self.control_signals = f"Executing Opcode: {opcode:04b}"
        
        # LODD (0000)
        if opcode == 0x0: 
            val = self.memory.read(addr_field)
            self.h.value = val # AC é simulado usando TOS ou lógica específica, no MAC-1 simples AC é o acumulador.
            # Vamos assumir uma arquitetura de acumulador onde AC é um registrador lógico,
            # mas no MIC-1 Tanenbaum, o AC geralmente flui pelo TOS ou um registro dedicado dependendo da versão.
            # Usaremos o registrador 'H' como Acumulador principal para simplificar a visualização Lógica.
            self.control_signals = f"LODD: AC <- Mem[{addr_field}]"

        # STOD (0001)
        elif opcode == 0x1:
            self.memory.write(addr_field, self.h.value)
            self.control_signals = f"STOD: Mem[{addr_field}] <- AC"

        # ADDD (0010)
        elif opcode == 0x2:
            mem_val = self.memory.read(addr_field)
            res = self.alu.compute(self.h.value, mem_val, 'ADD')
            self.h.value = res
            self.control_signals = f"ADDD: AC <- AC + Mem[{addr_field}]"

        # SUBD (0011)
        elif opcode == 0x3:
            mem_val = self.memory.read(addr_field)
            res = self.alu.compute(self.h.value, mem_val, 'SUB')
            self.h.value = res
            self.control_signals = f"SUBD: AC <- AC - Mem[{addr_field}]"

        # JPOS (0100)
        elif opcode == 0x4:
            if self.h.value < 0x8000: # Positivo
                self.pc.value = addr_field
                self.control_signals = f"JPOS: Jumped to {addr_field}"
            else:
                self.control_signals = "JPOS: No Jump"

        # JZER (0101)
        elif opcode == 0x5:
            if self.h.value == 0:
                self.pc.value = addr_field
                self.control_signals = f"JZER: Jumped to {addr_field}"
            else:
                self.control_signals = "JZER: No Jump"

        # JUMP (0110)
        elif opcode == 0x6:
            self.pc.value = addr_field
            self.control_signals = f"JUMP: Jumped to {addr_field}"

        # LOCO (0111)
        elif opcode == 0x7:
            self.h.value = addr_field
            self.control_signals = f"LOCO: AC <- {addr_field}"

        # LODL (1000) - Carrega local (sp + x)
        elif opcode == 0x8:
            eff_addr = (self.sp.value + addr_field) & 0xFFF
            self.h.value = self.memory.read(eff_addr)
            self.control_signals = f"LODL: AC <- Mem[SP + {addr_field}]"

        # STOL (1001)
        elif opcode == 0x9:
            eff_addr = (self.sp.value + addr_field) & 0xFFF
            self.memory.write(eff_addr, self.h.value)
            self.control_signals = f"STOL: Mem[SP + {addr_field}] <- AC"

        # ADDL (1010)
        elif opcode == 0xA:
            eff_addr = (self.sp.value + addr_field) & 0xFFF
            mem_val = self.memory.read(eff_addr)
            self.h.value = self.alu.compute(self.h.value, mem_val, 'ADD')
            self.control_signals = f"ADDL: AC += Mem[SP+{addr_field}]"

        # SUBL (1011)
        elif opcode == 0xB:
            eff_addr = (self.sp.value + addr_field) & 0xFFF
            mem_val = self.memory.read(eff_addr)
            self.h.value = self.alu.compute(self.h.value, mem_val, 'SUB')
            self.control_signals = f"SUBL: AC -= Mem[SP+{addr_field}]"

        # JNEG (1100)
        elif opcode == 0xC:
            if self.h.value >= 0x8000: # Bit de sinal setado
                self.pc.value = addr_field
                self.control_signals = f"JNEG: Jumped to {addr_field}"
            else:
                self.control_signals = "JNEG: No Jump"

        # JNZE (1101)
        elif opcode == 0xD:
            if self.h.value != 0:
                self.pc.value = addr_field
                self.control_signals = f"JNZE: Jumped to {addr_field}"
            else:
                self.control_signals = "JNZE: No Jump"

        # CALL (1110)
        elif opcode == 0xE:
            self.sp.value = (self.sp.value - 1) & 0xFFFF
            self.memory.write(self.sp.value, self.pc.value) # Salva endereço de retorno
            self.pc.value = addr_field
            self.control_signals = f"CALL: Called {addr_field}"

        # Instruções Especiais / Pilha (1111)
        elif opcode == 0xF:
            func = addr_field # 12 bits definem qual operação
            if func == 0: # HALT? Ou POP?
                 # Implementação customizada de HALT para fins educacionais (não padrão MAC-1 mas útil)
                self.halted = True
                self.control_signals = "HALTED"
            elif func == 1: # PSHI (Push Indirect)
                # Simplificado
                pass
            # ... Outras instruções de pilha podem ser adicionadas aqui
            else:
                # Fallback: assumir HALT para código desconhecido neste simulador básico
                self.halted = True
                self.control_signals = f"Unknown/Halt: {func}"

        self.cycle_count += 1