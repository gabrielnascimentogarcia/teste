"""
Módulo Assembler para a arquitetura MIC-1/MAC-1.
Lida com o processo de montagem em duas passadas: geração da Tabela de Símbolos e Geração de Código.
"""

OPCODES = {
    'LODD': 0x0000, 'STOD': 0x1000, 'ADDD': 0x2000, 'SUBD': 0x3000,
    'JPOS': 0x4000, 'JZER': 0x5000, 'JUMP': 0x6000, 'LOCO': 0x7000,
    'LODL': 0x8000, 'STOL': 0x9000, 'ADDL': 0xA000, 'SUBL': 0xB000,
    'JNEG': 0xC000, 'JNZE': 0xD000, 'CALL': 0xE000,
    'HALT': 0xF000, 'PSHI': 0xF001, 'POPI': 0xF002, 'PUSH': 0xF003,
    'POP':  0xF004, 'RETN': 0xF005, 'SWAP': 0xF006, 'INSP': 0xF007,
    'DESP': 0xF008
}

def assemble(source_code):
    """
    Converte código fonte assembly em código de máquina (dicionário de endereço: valor).
    Realiza duas passadas:
    1. Escaneia rótulos e constrói tabela de símbolos.
    2. Traduz instruções e resolve símbolos.
    """
    lines = source_code.splitlines()
    cleaned_lines = []
    
    # Passada 0: Pré-processamento e tratamento de .DATA
    data_segment = {}
    
    for line in lines:
        line = line.split(';')[0].strip()
        if not line: continue
        
        if line.upper().startswith(".DATA"):
            parts = line.split()
            if len(parts) >= 3:
                try:
                    addr_str = parts[1]
                    val_str = parts[2]
                    
                    if addr_str.upper().startswith("0X"): addr = int(addr_str, 16)
                    else: addr = int(addr_str)
                    
                    if val_str.upper().startswith("0X"): val = int(val_str, 16)
                    else: val = int(val_str)
                    
                    data_segment[addr] = val
                except ValueError:
                    return {}, f"Erro na diretiva .DATA: {line}"
            continue 
            
        cleaned_lines.append(line)

    symbol_table = {}
    temp_program = []
    current_address = 0
    
    # Passada 1: Construção da Tabela de Símbolos
    for line in cleaned_lines:
        parts = line.split()
        if not parts: continue 

        label = None
        instruction = None
        operand = None

        if parts[0].endswith(':'):
            label = parts[0][:-1].upper()
            symbol_table[label] = current_address
            if len(parts) > 1:
                instruction = parts[1].upper()
                if len(parts) > 2:
                    operand = parts[2]
            else:
                continue 
        else:
            instruction = parts[0].upper()
            if len(parts) > 1:
                operand = parts[1]
        
        if instruction:
            temp_program.append({
                'instr': instruction, 
                'op': operand, 
                'addr': current_address,
                'orig': line
            })
            current_address += 1

    machine_code_dict = data_segment.copy()
    error_msg = "Sucesso"

    # Passada 2: Geração de Código
    try:
        for item in temp_program:
            instr = item['instr']
            op = item['op']
            addr = item['addr']

            if instr not in OPCODES:
                raise ValueError(f"Instrução desconhecida '{instr}' na linha {addr} ('{item['orig']}')")

            base_opcode = OPCODES[instr]
            
            if instr in ['HALT', 'RETN', 'SWAP', 'INSP', 'DESP', 'PUSH', 'POP', 'PSHI', 'POPI']:
                machine_code_dict[addr] = base_opcode
                continue

            operand_val = 0
            if op:
                op_upper = op.upper()
                if op_upper in symbol_table:
                    operand_val = symbol_table[op_upper]
                else:
                    try:
                        if op.upper().startswith("0X"):
                            operand_val = int(op, 16)
                        else:
                            operand_val = int(op)
                    except ValueError:
                         raise ValueError(f"Operando inválido '{op}' para instrução {instr}")
            
            # Lida com constantes negativas (complemento de 2 de 12 bits)
            if operand_val < 0:
                operand_val = (operand_val + 4096) & 0xFFF
            
            if operand_val > 4095:
                 raise ValueError(f"Operando {operand_val} excede limite de 12 bits (0-4095)")

            final_instr = base_opcode | (operand_val & 0x0FFF)
            machine_code_dict[addr] = final_instr

    except Exception as e:
        return {}, str(e)

    return machine_code_dict, error_msg