"""
Módulo Assembler para a arquitetura MAC-1.
Converte código assembly em inteiros de 16 bits.
"""

OPCODES = {
    'LODD': 0x0000,
    'STOD': 0x1000,
    'ADDD': 0x2000,
    'SUBD': 0x3000,
    'JPOS': 0x4000,
    'JZER': 0x5000,
    'JUMP': 0x6000,
    'LOCO': 0x7000,
    'LODL': 0x8000,
    'STOL': 0x9000,
    'ADDL': 0xA000,
    'SUBL': 0xB000,
    'JNEG': 0xC000,
    'JNZE': 0xD000,
    'CALL': 0xE000,
    # Instruções especiais mapeadas para o prefixo F (1111)
    'PSHI': 0xF000 + 1, # Exemplo
    'POPI': 0xF000 + 2,
    'PUSH': 0xF000 + 3,
    'POP':  0xF000 + 4,
    'RETN': 0xF000 + 5,
    'SWAP': 0xF000 + 6,
    'INSP': 0xF000 + 7,
    'DESP': 0xF000 + 8,
    'HALT': 0xFFFF      # Custom simulation stop
}

def assemble(source_code):
    """
    Recebe uma string contendo o código fonte assembly.
    Retorna uma lista de inteiros (código de máquina).
    """
    lines = source_code.splitlines()
    cleaned_lines = []
    
    # Pré-processamento: remover comentários e espaços extras
    for line in lines:
        line = line.split(';')[0].strip() # Remove comentários
        if line:
            cleaned_lines.append(line)

    symbol_table = {}
    machine_code = []
    current_address = 0

    # --- Passagem 1: Identificar Labels ---
    temp_program = [] # Armazena (label, instruction, operand)
    
    for line in cleaned_lines:
        parts = line.split()
        label = None
        instruction = None
        operand = None

        # Verifica se começa com label (termina com :)
        if parts[0].endswith(':'):
            label = parts[0][:-1]
            symbol_table[label] = current_address
            if len(parts) > 1:
                instruction = parts[1].upper()
                if len(parts) > 2:
                    operand = parts[2]
            else:
                continue # Linha só com label
        else:
            instruction = parts[0].upper()
            if len(parts) > 1:
                operand = parts[1]
        
        if instruction:
            temp_program.append((instruction, operand, current_address))
            current_address += 1

    # --- Passagem 2: Gerar Código de Máquina ---
    try:
        for instr, op, addr in temp_program:
            if instr not in OPCODES:
                raise ValueError(f"Instrução inválida: {instr} na linha {addr}")

            base_opcode = OPCODES[instr]
            
            # Instruções tipo 1111 (Especiais) não usam operando de endereço padrão geralmente,
            # mas aqui simplificamos. Se for HALT ou RETN, não precisa de operando.
            if instr in ['HALT', 'RETN', 'SWAP']:
                machine_code.append(base_opcode)
                continue

            operand_val = 0
            if op:
                if op in symbol_table:
                    operand_val = symbol_table[op]
                else:
                    try:
                        operand_val = int(op)
                    except ValueError:
                         raise ValueError(f"Operando inválido: {op} para instrução {instr}")
            
            # Verifica limites do operando (12 bits = 4095)
            if operand_val > 4095 or operand_val < 0:
                 raise ValueError(f"Operando fora dos limites (0-4095): {operand_val}")

            final_instr = base_opcode | (operand_val & 0x0FFF)
            machine_code.append(final_instr)

    except Exception as e:
        return [], str(e)

    return machine_code, "Sucesso"

# Teste rápido se rodar direto
if __name__ == "__main__":
    code = """
    LOCO 10
    STOD 500
    LOCO 20
    ADDD 500
    STOD 501
    HALT
    """
    bin_code, msg = assemble(code)
    print(f"Montagem: {msg}")
    print([hex(x) for x in bin_code])