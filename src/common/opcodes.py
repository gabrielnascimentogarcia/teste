class Opcode:
    # Codigos das operacoes base
    LODD = 0x0
    STOD = 0x1
    ADDD = 0x2
    SUBD = 0x3
    JPOS = 0x4
    JZER = 0x5
    JUMP = 0x6
    LOCO = 0x7
    LODL = 0x8
    STOL = 0x9
    ADDL = 0xA
    SUBL = 0xB
    JNEG = 0xC
    JNZE = 0xD
    CALL = 0xE
    EXT  = 0xF  # Instrucoes estendidas (sem operando explicito)

    # Conjunto de instrucoes que nao recebem parametro de endereco
    NO_OPERAND_SET = {
        'HALT', 'RETN', 'SWAP', 'INSP', 'DESP', 'PUSH', 'POP', 'PSHI', 'POPI'
    }

# Mapeamento Texto -> Hexadecimal para o Assembler usar
# CUIDADO: Nao alterar os valores hexa, senao quebra a compatibilidade
OPCODE_MAP = {
    'LODD': 0x0000, 'STOD': 0x1000, 'ADDD': 0x2000, 'SUBD': 0x3000,
    'JPOS': 0x4000, 'JZER': 0x5000, 'JUMP': 0x6000, 'LOCO': 0x7000,
    'LODL': 0x8000, 'STOL': 0x9000, 'ADDL': 0xA000, 'SUBL': 0xB000,
    'JNEG': 0xC000, 'JNZE': 0xD000, 'CALL': 0xE000,
    
    # Instrucoes estendidas (comecam com F)
    'HALT': 0xF000, 'PSHI': 0xF001, 'POPI': 0xF002, 'PUSH': 0xF003,
    'POP':  0xF004, 'RETN': 0xF005, 'SWAP': 0xF006, 'INSP': 0xF007,
    'DESP': 0xF008
}