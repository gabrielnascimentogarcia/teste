from src.common.opcodes import OPCODE_MAP, Opcode

def clean_lines(source_code):
    cleaned = []
    for i, line in enumerate(source_code.splitlines()):
        raw = line.split(';')[0].strip()
        if raw: cleaned.append((i+1, raw))
    return cleaned

def parse_data(cleaned_lines):
    symbol_table = {}
    data_segment = {}
    instructions = []
    
    for lineno, line in cleaned_lines:
        if ".DATA" in line.upper():
            parts = line.split()
            try:
                idx = next(i for i, p in enumerate(parts) if p.upper() == ".DATA")
                if len(parts) < idx + 3: raise ValueError("Argumentos insuficientes")
                
                addr_s, val_s = parts[idx+1], parts[idx+2]
                addr = int(addr_s, 16) if addr_s.upper().startswith("0X") else int(addr_s)
                val = int(val_s, 16) if val_s.upper().startswith("0X") else int(val_s)
                
                if not (0 <= addr < 4096): raise ValueError(f"Endereço {addr} inválido")
                data_segment[addr] = val & 0xFFFF
                
                if idx > 0 and parts[idx-1].endswith(':'):
                    symbol_table[parts[idx-1][:-1].upper()] = addr
            except Exception as e:
                return None, None, None, f"Erro linha {lineno}: {e}"
        else:
            instructions.append((lineno, line))
            
    return symbol_table, data_segment, instructions, "Sucesso"

def assemble(source_code):
    cleaned = clean_lines(source_code)
    symbols, machine_code, lines, msg = parse_data(cleaned)
    if msg != "Sucesso": return {}, msg
    
    # Passada 1: Símbolos
    curr_addr = 0
    temp_prog = []
    for lineno, line in lines:
        parts = line.split()
        label = None
        
        if parts[0].endswith(':'):
            label = parts[0][:-1].upper()
            symbols[label] = curr_addr
            parts = parts[1:]
            
        if not parts: continue
        
        instr = parts[0].upper()
        op = parts[1] if len(parts) > 1 else None
        temp_prog.append({'instr': instr, 'op': op, 'addr': curr_addr, 'line': lineno})
        curr_addr += 1
        
    # Passada 2: Geração
    try:
        for item in temp_prog:
            instr, op, addr, lno = item['instr'], item['op'], item['addr'], item['line']
            if addr in machine_code: raise ValueError(f"Linha {lno}: Colisão de memória em {addr}")
            if instr not in OPCODE_MAP: raise ValueError(f"Linha {lno}: Instrução '{instr}' desconhecida")
            
            opcode = OPCODE_MAP[instr]
            if instr in Opcode.NO_OPERAND_INSTRUCTIONS:
                machine_code[addr] = opcode
                continue
                
            val = 0
            if op:
                if op.upper() in symbols: val = symbols[op.upper()]
                else:
                    try: val = int(op, 16) if op.upper().startswith("0X") else int(op)
                    except: raise ValueError(f"Linha {lno}: Operando '{op}' inválido")
            
            if not (-2048 <= val <= 4095): raise ValueError(f"Linha {lno}: Valor {val} fora dos limites")
            if val < 0: val = (val + 4096) & 0xFFF
            
            machine_code[addr] = opcode | (val & 0xFFF)
            
        return machine_code, "Sucesso"
    except Exception as e:
        return {}, str(e)