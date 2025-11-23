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
    Converte código fonte assembly em código de máquina.
    """
    lines = source_code.splitlines()
    cleaned_lines = []
    
    # Pré-passada para capturar labels de .DATA antes de qualquer coisa
    pre_symbol_table = {}
    data_segment = {}
    
    for i, line in enumerate(lines):
        raw_line = line.split(';')[0].strip()
        if not raw_line: continue
        
        # Verifica se existe a diretiva .DATA
        if ".DATA" in raw_line.upper():
            parts = raw_line.split()
            try:
                # Localiza a posição do .DATA na linha
                data_idx = -1
                for idx, p in enumerate(parts):
                    if p.upper() == ".DATA":
                        data_idx = idx
                        break
                
                if data_idx == -1: continue # Estranho, mas segurança
                
                # Verifica argumentos (DATA addr val)
                if len(parts) < data_idx + 3:
                    return {}, f"Erro na linha {i+1}: Diretiva .DATA com argumentos insuficientes."

                addr_str = parts[data_idx+1]
                val_str = parts[data_idx+2]
                
                # Converte endereço e valor
                addr = int(addr_str, 16) if addr_str.upper().startswith("0X") else int(addr_str)
                val = int(val_str, 16) if val_str.upper().startswith("0X") else int(val_str)
                
                data_segment[addr] = val

                # Se houver algo antes do .DATA, deve ser um label (ex: VAR: .DATA ...)
                if data_idx > 0:
                    label_cand = parts[data_idx-1]
                    if label_cand.endswith(':'):
                        label = label_cand[:-1].upper()
                        pre_symbol_table[label] = addr
                
                # Linhas .DATA não vão para cleaned_lines (não são instruções executáveis)
                continue

            except ValueError:
                return {}, f"Erro na linha {i+1}: Valor inválido em .DATA"
            except Exception as e:
                return {}, f"Erro genérico na linha {i+1}: {e}"
                
        cleaned_lines.append((i+1, raw_line)) # Guarda número da linha para erros

    symbol_table = pre_symbol_table.copy()
    temp_program = []
    current_address = 0
    
    # Passada 1: Tabela de Símbolos para Código
    for lineno, line in cleaned_lines:
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
                'line': lineno,
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
            lineno = item['line']

            if instr not in OPCODES:
                raise ValueError(f"Instrução desconhecida '{instr}' na linha {lineno}")

            base_opcode = OPCODES[instr]
            
            # Instruções sem operando
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
                         raise ValueError(f"Operando inválido '{op}' na linha {lineno}")
            
            # Ajuste de sinal (12 bits)
            if operand_val < 0:
                operand_val = (operand_val + 4096) & 0xFFF
            
            if operand_val > 4095:
                 raise ValueError(f"Operando {operand_val} excede 12 bits na linha {lineno}")

            final_instr = base_opcode | (operand_val & 0x0FFF)
            machine_code_dict[addr] = final_instr

    except Exception as e:
        return {}, str(e)

    return machine_code_dict, error_msg