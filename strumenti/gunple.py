# Gunple: Gunman's Proof - libreria comune per traduzione (base: patch inglese Aeon Genesis v1.03)
import struct

# Banchi del copione: (offset file tabella puntatori, numero voci, fine banco)
BANKS = [(0x68000, 0x180, 0x70000), (0x2C0000, 0x100, 0x2C8000)]
DTE_TABLE = 0x3FA00        # $87:FA00, coppie per i byte 0x50..0xFE
DTE_COUNT = 0xFF - 0x50    # 175 coppie
GLYPH_PTRS = 0x3F800       # $87:F800, indirizzo VRAM-sorgente di ogni glifo (0x00..0x7F)
FONT_BASE = 0x60000        # banco $8C

def _base_table():
    t = {0x00: ' '}
    for i in range(10): t[0x01 + i] = str(i)
    for i in range(26):
        t[0x0B + i] = chr(65 + i)
        t[0x25 + i] = chr(97 + i)
    for k, v in zip(range(0x3F, 0x50), [',', '.', '-', '!', '&', '?', '%', '/', '"', "'", ':', '(', ')', '~', '*', '$', '{4F}']):
        t[k] = v
    return t

EN_TABLE = _base_table()
ES_TABLE = dict(EN_TABLE)
ES_TABLE.update({0x15: '¿', 0x21: 'ñ', 0x3B: '¡', 0x43: 'á', 0x46: 'é', 0x48: 'í', 0x4D: 'ó', 0x4F: 'ú'})
# Tabella italiana: slot inutilizzati dal copione inglese (& % / * ~ ろ) -> lettere accentate
IT_TABLE = dict(EN_TABLE)
IT_TABLE.update({0x43: 'à', 0x45: 'è', 0x46: 'é', 0x4D: 'ì', 0x4F: 'ò', 0x4C: 'ù'})

# Codici di controllo (byte FF xx)
CTRL_NAMES = {0x01: None, 0x03: '[WAIT]', 0x04: '[END]', 0x00: '[00]', 0x10: '[NAME]'}

def ptrs(d, base, n):
    return [struct.unpack_from('<H', d, base + 2 * i)[0] for i in range(n)]

def dte_pairs(d):
    return [(d[DTE_TABLE + 2 * i], d[DTE_TABLE + 2 * i + 1]) for i in range(DTE_COUNT)]

def read_message(d, off, pairs):
    """Restituisce lista di token: ('c', codice_carattere) o ('k', codice_controllo) e offset di fine."""
    toks = []
    i = off
    while True:
        b = d[i]
        if b == 0xFF:
            c = d[i + 1]; i += 2
            toks.append(('k', c))
            if c in (0x00, 0x04):
                break
        else:
            i += 1
            if b < 0x50:
                toks.append(('c', b))
            else:
                a, c = pairs[b - 0x50]
                toks.append(('c', a)); toks.append(('c', c))
        if i - off > 4000:
            raise ValueError('messaggio non terminato a %06X' % off)
    return toks, i

def toks_to_text(toks, table):
    out = []
    for kind, v in toks:
        if kind == 'c':
            out.append(table.get(v, '{%02X}' % v))
        elif v == 0x01:
            out.append('\n')
        elif v == 0x03:
            out.append('[WAIT]\n')
        elif v in CTRL_NAMES:
            out.append(CTRL_NAMES[v])
        else:
            out.append('[%02X]' % v)
    return ''.join(out)

def is_unused(d, off):
    return not any(d[off:off + 32])
