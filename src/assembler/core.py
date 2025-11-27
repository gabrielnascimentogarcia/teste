from src.common.opcodes import OPCODE_MAP, Opcode

def clean_lines(src):
    # Remove comentarios e linhas vazias pra facilitar
    cleaned = []
    for i, line in enumerate(src.splitlines()):
        raw = line.split(';')[0].strip()
        if raw: cleaned.append((i+1, raw))
    return cleaned

def parse_data(lines):
    # Separa labels e diretivas .DATA
    sym_table = {}
    data_seg = {}
    instrs = []
    
    for lno, line in lines:
        if ".DATA" in line.upper():
            parts = line.split()
            try:
                # Acha onde ta o .DATA
                idx = next(i for i, p in enumerate(parts) if p.upper() == ".DATA")
                if len(parts) < idx + 3: raise ValueError("Argumentos faltando")
                
                addr_s, val_s = parts[idx+1], parts[idx+2]
                
                # Suporta Hex (0x) ou Decimal
                addr = int(addr_s, 16) if "0X" in addr_s.upper() else int(addr_s)
                val = int(val_s, 16) if "0X" in val_s.upper() else int(val_s)
                
                if not (0 <= addr < 4096): raise ValueError(f"Endereco {addr} fora do limite")
                data_seg[addr] = val & 0xFFFF
                
                # Se tiver label antes do .DATA, guarda na tabela
                if idx > 0 and parts[idx-1].endswith(':'):
                    sym_table[parts[idx-1][:-1].upper()] = addr
            except Exception as e:
                return None, None, None, f"Erro linha {lno}: {e}"
        else:
            instrs.append((lno, line))
            
    return sym_table, data_seg, instrs, "OK"

def assemble(src_code):
    cleaned = clean_lines(src_code)
    symbols, mc, lines, status = parse_data(cleaned)
    if status != "OK": return {}, status
    
    # Passada 1: Resolver Labels (Simbolos)
    curr = 0
    temp = []
    for lno, line in lines:
        parts = line.split()
        
        # Se comeca com Label: (ex: Inicio:)
        if parts[0].endswith(':'):
            label = parts[0][:-1].upper()
            symbols[label] = curr
            parts = parts[1:]
            
        if not parts: continue
        
        instr = parts[0].upper()
        op = parts[1] if len(parts) > 1 else None
        temp.append({'i': instr, 'op': op, 'addr': curr, 'l': lno})
        curr += 1
        
    # Passada 2: Gerar Codigo de Maquina
    try:
        for it in temp:
            instr, op, addr, lno = it['i'], it['op'], it['addr'], it['l']
            
            # Verifica se nao vai sobrescrever dado definido no .DATA
            if addr in mc: raise ValueError(f"Linha {lno}: Colisao de memoria em {addr}")
            if instr not in OPCODE_MAP: raise ValueError(f"Linha {lno}: Instrucao '{instr}' nao existe")
            
            opcode = OPCODE_MAP[instr]
            
            # Instrucoes sem operando (tipo HALT)
            if instr in Opcode.NO_OPERAND_SET:
                mc[addr] = opcode
                continue
                
            val = 0
            if op:
                # Se for label, pega da tabela de simbolos
                if op.upper() in symbols: 
                    val = symbols[op.upper()]
                else:
                    try: 
                        val = int(op, 16) if "0X" in op.upper() else int(op)
                    except: 
                        raise ValueError(f"Linha {lno}: Operando '{op}' invalido")
            
            # Checa limites (-2048 a 4095)
            if not (-2048 <= val <= 4095): 
                raise ValueError(f"Linha {lno}: Valor {val} muito grande")
                
            if val < 0: val = (val + 4096) & 0xFFF
            
            # Monta a instrucao: 4 bits opcode | 12 bits valor
            mc[addr] = opcode | (val & 0xFFF)
            
        return mc, "OK"
    except Exception as e:
        return {}, str(e)