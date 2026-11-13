# Compila la traduzione italiana di Gunple: Gunman's Proof.
# uso: python3 compila.py rom_inglese.sfc copione_it.txt rom_giapponese.sfc cartella_output
#  - parte dalla ROM inglese (Aeon Genesis v1.03), che ha gia' font latino e motore a 8px
#  - disegna le lettere accentate, ricalcola la tabella DTE, reinserisce il copione
#  - scrive la ROM italiana e una patch BPS da applicare alla ROM giapponese originale
import sys, os, re, json, struct, zlib, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gunple as G

MAX_COLS = 24
NAME_LEN = 8

# ---------------------------------------------------------------- glifi
ACCENT_GRAVE = ['.++++...', '.+##++..', '.++##+..']   # righe 5-7
ACCENT_ACUTE = ['...++++.', '..++##+.', '..+##++.']
NEW_GLYPHS = {  # slot: (lettera base nel font inglese, accento)
    0x43: (0x25, ACCENT_GRAVE),  # à
    0x45: (0x29, ACCENT_GRAVE),  # è
    0x46: (0x29, ACCENT_ACUTE),  # é
    0x4D: (0x2D, ACCENT_GRAVE),  # ì
    0x4F: (0x33, ACCENT_GRAVE),  # ò
    0x4C: (0x39, ACCENT_GRAVE),  # ù
}

def glyph_addr(d, c):
    return G.FONT_BASE + struct.unpack_from('<H', d, G.GLYPH_PTRS + 2 * c)[0] - 0x8000

def read_glyph(d, c):
    a = glyph_addr(d, c); rows = []
    for off in (a, a + 0x100):
        for y in range(8):
            p0, p1 = d[off + 2 * y], d[off + 2 * y + 1]
            rows.append([((p0 >> (7 - x)) & 1) | (((p1 >> (7 - x)) & 1) << 1) for x in range(8)])
    return rows

def write_glyph(d, c, rows):
    a = glyph_addr(d, c)
    for half, off in enumerate((a, a + 0x100)):
        for y in range(8):
            r = rows[half * 8 + y]; p0 = p1 = 0
            for x in range(8):
                p0 |= (r[x] & 1) << (7 - x); p1 |= (r[x] >> 1) << (7 - x)
            d[off + 2 * y] = p0; d[off + 2 * y + 1] = p1
        for k in range(16):           # meta' destra del glifo vuota
            d[off + 16 + k] = 0

def make_glyphs(d):
    code = {'.': 0, '#': 1, '+': 2, '@': 3}
    for slot, (base, acc) in NEW_GLYPHS.items():
        rows = read_glyph(d, base)
        if base == 0x2D:  # 'i': togli il puntino
            for y in range(4, 8): rows[y] = [0] * 8
        for k, line in enumerate(acc):
            y = 5 + k
            for x, ch in enumerate(line):
                v = code[ch]
                if v: rows[y][x] = v
        write_glyph(d, slot, rows)

# ---------------------------------------------------------------- menu (tilemap)
# Schede delle mosse: 5 schede, ognuna 4 righe da 16 caselle (word: attributo<<8 | tile)
# {B} {Y} = icone dei tasti, {DPAD} = croce+tasto (3 caselle), = = bordo
SKILL_CARDS = [
    (0x45D84, ['COLPO CARICO', '  TIENI PREMUTO', '  {B} UN ATTIMO', '']),
    (0x45E14, ['COLPO FOLLE', '  PREMI {B} A', '  RIPETIZIONE', '']),
    (0x45EA4, ['PUGNOOOOONE', '  TIENI PREMUTO', '  {Y} UN ATTIMO', '']),
    (0x45F34, ['COMBO DELUXE', '  PREMI {Y} A', '  RIPETIZIONE', '']),
    (0x45FC4, ['SUPER MONTANTE', '  PREMI {DPAD}', '  RAPIDAMENTE', '']),
]
MENU_WORDS = [  # (offset, testo, attributo)  sostituzioni in-place di pari lunghezza
    (0x5930A, 'MOSSE', 0x24),
]
FRAME_TITLES = [  # titoli in cornice: offset prima casella interna, celle interne totali
    (0x5947A, 'STEMMI', 10),
    (0x596BA, 'OGGETTI', 10),
]

def menu_tiles(text, attr=0x24):
    out = []; i = 0
    while i < len(text):
        if text.startswith('{B}', i): out.append(0x38AC); i += 3
        elif text.startswith('{Y}', i): out.append(0x381E); i += 3
        elif text.startswith('{DPAD}', i): out += [0x241C, 0x241D, 0x281F]; i += 6
        else:
            ch = text[i]; i += 1
            if ch == ' ': out.append(0x2440)
            elif ch == '=': out.append(0x24BA)
            elif 'A' <= ch <= 'Z': out.append((attr << 8) | ord(ch))
            else: raise SystemExit('carattere non valido nei menu: %r' % ch)
    return out

def patch_menus(d):
    for base, rows in SKILL_CARDS:
        for r, text in enumerate(rows):
            off = base + r * 0x24
            assert d[off - 4:off] == b'\x3f\x2c\x00\x3c', hex(off)
            if r == 0:
                w = menu_tiles(text)
                w = [0x24BA] + w + [0x24BA] * (15 - len(w))
            else:
                w = menu_tiles(text); w = w + [0x2440] * (16 - len(w))
            if len(w) != 16: raise SystemExit('riga di menu troppo lunga: %r' % text)
            for k, v in enumerate(w): struct.pack_into('<H', d, off + 2 * k, v)
    for off, text, attr in MENU_WORDS:
        for k, v in enumerate(menu_tiles(text, attr)): struct.pack_into('<H', d, off + 2 * k, v)
    for off, text, cells in FRAME_TITLES:
        w = [0x2C3D] + menu_tiles(text)
        w += [0x2C3D] * (cells - len(w))
        if len(w) != cells: raise SystemExit('titolo troppo lungo: %r' % text)
        for k, v in enumerate(w): struct.pack_into('<H', d, off + 2 * k, v)

# ---------------------------------------------------------------- grafiche 2bpp
def get_tile(d, o):
    return [[((d[o + 2 * y] >> (7 - x)) & 1) | (((d[o + 2 * y + 1] >> (7 - x)) & 1) << 1) for x in range(8)] for y in range(8)]

def put_tile(d, o, px):
    for y in range(8):
        p0 = p1 = 0
        for x in range(8):
            p0 |= (px[y][x] & 1) << (7 - x); p1 |= (px[y][x] >> 1) << (7 - x)
        d[o + 2 * y] = p0; d[o + 2 * y + 1] = p1

def read_strip(d, tiles):
    rows = [[] for _ in range(8)]
    for o in tiles:
        t = get_tile(d, o)
        for y in range(8): rows[y] += t[y]
    return rows

def write_strip(d, tiles, rows):
    for k, o in enumerate(tiles):
        put_tile(d, o, [r[k * 8:(k + 1) * 8] for r in rows])

# font 6 righe per le etichette dei pulsanti (schermata del nome)
SMALL = {
    'F': ['###', '#..', '###', '#..', '#..', '#..'], 'I': ['#'] * 6,
    'N': ['#..#', '##.#', '#.##', '#..#', '#..#', '#..#'], 'E': ['###', '#..', '###', '#..', '#..', '###'],
    'M': ['#...#', '##.##', '#.#.#', '#...#', '#...#', '#...#'], 'A': ['.#.', '#.#', '#.#', '###', '#.#', '#.#'],
    'U': ['#.#', '#.#', '#.#', '#.#', '#.#', '###'], 'S': ['###', '#..', '###', '..#', '..#', '###'],
    'C': ['###', '#..', '#..', '#..', '#..', '###'],
}
def draw_button(d, tiles, text):
    rows = read_strip(d, tiles); w = len(rows[0])
    for y in range(1, 7):
        for x in range(1, w - 1): rows[y][x] = 1
    glyphs = [SMALL[c] for c in text]
    tw = sum(len(g[0]) for g in glyphs) + len(glyphs) - 1
    x0 = 1 + (w - 2 - tw) // 2
    for g in glyphs:
        for y in range(6):
            for x, ch in enumerate(g[y]):
                if ch == '#': rows[1 + y][x0 + x] = 3
        x0 += len(g[0]) + 1
    write_strip(d, tiles, rows)

NAME_BUTTONS = [  # (tile iniziale nel banco 0x000000 a 2bpp, n. tile, testo)
    (6 * 32 + 2, 2, 'FINE'),
    (6 * 32 + 16, 4, 'MAIUSC'),
    (7 * 32 + 0, 4, 'MINUSC'),
]

# font 5x7 per le opzioni del game over (corpo colore 1, ombra colore 3)
BIG = {
    'A': ['.###.', '#...#', '#...#', '#####', '#...#', '#...#', '#...#'],
    'B': ['####.', '#...#', '#...#', '####.', '#...#', '#...#', '####.'],
    'E': ['#####', '#....', '#....', '####.', '#....', '#....', '#####'],
    'G': ['.###.', '#...#', '#....', '#.###', '#...#', '#...#', '.###.'],
    'I': ['###', '.#.', '.#.', '.#.', '.#.', '.#.', '###'],
    'L': ['#....', '#....', '#....', '#....', '#....', '#....', '#####'],
    'N': ['#...#', '##..#', '#.#.#', '#..##', '#...#', '#...#', '#...#'],
    'O': ['.###.', '#...#', '#...#', '#...#', '#...#', '#...#', '.###.'],
    'P': ['####.', '#...#', '#...#', '####.', '#....', '#....', '#....'],
    'R': ['####.', '#...#', '#...#', '####.', '#.#..', '#..#.', '#...#'],
    'S': ['.####', '#....', '#....', '.###.', '....#', '....#', '####.'],
    'T': ['#####', '..#..', '..#..', '..#..', '..#..', '..#..', '..#..'],
    'V': ['#...#', '#...#', '#...#', '#...#', '#...#', '.#.#.', '..#..'],
    ' ': ['...'] * 7,
}
def draw_big_line(text, width):
    rows = [[0] * width for _ in range(8)]
    glyphs = [BIG[c] for c in text]
    tw = sum(len(g[0]) for g in glyphs) + len(glyphs) - 1
    x0 = max(0, (width - tw) // 2)
    for g in glyphs:
        for y in range(7):
            for x, ch in enumerate(g[y]):
                if ch == '#':
                    if x0 + x + 1 < width and rows[y + 1][x0 + x + 1] == 0: rows[y + 1][x0 + x + 1] = 3
                    rows[y][x0 + x] = 1
        x0 += len(g[0]) + 1
    return rows

GAMEOVER_BASE = 0x2E1000   # righe di tile 2 e 3: due opzioni da 16x2 tile
GAMEOVER_OPTIONS = [(0, 'TORNA AL', 'VILLAGGIO'), (16, 'BASTA', 'PER OGGI')]

# Crediti nella schermata del nome (tilemap, 2 copie), sopra a quelli di Aeon Genesis
NAME_CREDIT_ROWS = [0x14C0, 0x1CC0]     # riga 19 della tilemap
NAME_CREDIT_TEXT = '@Trad. ITA by Sanciopanza88'   # @ = bandiera italiana
FLAG_TILE = 0x7E                        # tile vuoto (ex kana) nel font della schermata
FLAG_PAL_ATTR = 0x30                    # palette 4: 0=trasp. 1=rosso 2=verde 3=bianco
PALETTE_BASE = 0x51146                  # CGRAM della schermata (verificata: cornice = pal. 2)
FLAG_RED = 0x18B9                       # rosso bandiera (BGR555), al posto del nero in pal. 4
FLAG_PIXELS = [
    '........',
    '.223311.',
    '.223311.',
    '.223311.',
    '.223311.',
    '.223311.',
    '.223311.',
    '........',
]

def name_tile(c):
    if c == '@': return (FLAG_PAL_ATTR << 8) | FLAG_TILE
    if 'a' <= c <= 'z': return 0x2400 | (ord(c) - 97)
    if 'A' <= c <= 'Z': return 0x2400 | (0x80 + ord(c) - 65)
    if '0' <= c <= '9': return 0x2400 | (0xA0 + ord(c) - 48)
    if c == ' ': return 0x3C9A
    return 0x2400 | {'.': 0xAA, '-': 0xAB, '/': 0xAC}[c]

def patch_name_credit(d):
    # tile bandiera + rosso nella palette 4 (inutilizzata in questa schermata)
    assert not any(d[FLAG_TILE * 16:FLAG_TILE * 16 + 16]), 'tile bandiera non vuoto'
    put_tile(d, FLAG_TILE * 16, [[int(c) if c != '.' else 0 for c in r] for r in FLAG_PIXELS])
    assert struct.unpack_from('<4H', d, PALETTE_BASE + 16 * 2) == (0x2542, 0x0000, 0x02C0, 0x7FFF), 'palette inattesa'
    struct.pack_into('<H', d, PALETTE_BASE + 17 * 2, FLAG_RED)
    t = NAME_CREDIT_TEXT
    if len(t) > 28: raise SystemExit('credito troppo lungo')
    col = 2 + (28 - len(t)) // 2
    for row in NAME_CREDIT_ROWS:
        assert all(struct.unpack_from('<H', d, row + 2 * k)[0] == 0x3C9A for k in range(2, 30)), 'riga non vuota'
        for k, c in enumerate(t):
            struct.pack_into('<H', d, row + 2 * (col + k), name_tile(c))

def patch_graphics(d):
    patch_name_credit(d)
    for t0, n, text in NAME_BUTTONS:
        draw_button(d, [(t0 + k) * 16 for k in range(n)], text)
    for col, l1, l2 in GAMEOVER_OPTIONS:
        for trow, txt in ((2, l1), (3, l2)):
            tiles = [GAMEOVER_BASE + (trow * 32 + col + k) * 16 for k in range(16)]
            write_strip(d, tiles, draw_big_line(txt, 128))

# ---------------------------------------------------------------- copione
REV = {v: k for k, v in G.IT_TABLE.items() if len(v) == 1}
TOKEN_RE = re.compile(r'\[WAIT\]\n?|\[END\]|\[NAME\]|\[[0-9A-Fa-f]{2}\]|\{[0-9A-Fa-f]{2}\}|\n|.', re.S)
SUBST = {'È': "E'", 'À': "A'", 'Ì': "I'", 'Ò': "O'", 'Ù': "U'", '’': "'", '‘': "'", '“': '"', '”': '"', '…': '...', '¿': '', '¡': ''}

def parse_script(path):
    msgs = collections.OrderedDict(); cur = None; buf = []
    for raw in open(path, encoding='utf-8').read().split('\n'):
        if raw.startswith('###'):
            if cur: msgs[cur] = buf
            cur = raw.split()[1]; buf = []
        elif raw.startswith(';') or raw.startswith('#') or cur is None:
            continue
        else:
            buf.append(raw.rstrip('\r'))
    if cur: msgs[cur] = buf
    return {k: '\n'.join(v).rstrip('\n ') for k, v in msgs.items()}

def tokenize(mid, text, warnings):
    for a, b in SUBST.items(): text = text.replace(a, b)
    toks = []
    for m in TOKEN_RE.finditer(text):
        t = m.group()
        if t.startswith('[WAIT]'): toks.append(('k', 0x03))
        elif t == '[END]': toks.append(('k', 0x04))
        elif t == '[NAME]': toks.append(('k', 0x10))
        elif t == '\n': toks.append(('k', 0x01))
        elif t.startswith('['): toks.append(('k', int(t[1:3], 16)))
        elif t.startswith('{'): toks.append(('c', int(t[1:3], 16)))
        elif t in REV: toks.append(('c', REV[t]))
        else:
            warnings.append('%s: carattere non disponibile %r (sostituito con spazio)' % (mid, t))
            toks.append(('c', 0x00))
    if not toks or toks[-1] not in (('k', 0x00), ('k', 0x04)):
        warnings.append('%s: manca [END] o [00] alla fine (aggiunto [00])' % mid)
        toks.append(('k', 0x00))
    # controllo larghezza righe / righe per pagina
    col = 0; lines = 1
    for kind, v in toks:
        if kind == 'c': col += 1
        elif v == 0x10: col += NAME_LEN
        elif v == 0x01:
            col = 0; lines += 1
        elif v in (0x03, 0x05, 0x25, 0x00, 0x04):
            col = 0; lines = 1
        if col > MAX_COLS:
            warnings.append('%s: riga oltre %d caratteri' % (mid, MAX_COLS)); col = -999
    return toks

# ---------------------------------------------------------------- DTE
def segments(all_toks):
    segs = []
    for toks in all_toks:
        cur = []
        for kind, v in toks:
            if kind == 'c': cur.append(v)
            else:
                if cur: segs.append(cur)
                cur = []
        if cur: segs.append(cur)
    return segs

def choose_pairs(segs, n=G.DTE_COUNT):
    work = [list(s) for s in segs]   # token: int (singolo) o tuple (coppia)
    chosen = []
    for _ in range(n):
        cnt = collections.Counter()
        for s in work:
            i = 0
            while i < len(s) - 1:
                if isinstance(s[i], int) and isinstance(s[i + 1], int):
                    cnt[(s[i], s[i + 1])] += 1
                i += 1
        if not cnt: break
        best, c = cnt.most_common(1)[0]
        if c < 2: break
        chosen.append(best)
        for k, s in enumerate(work):
            out = []; i = 0
            while i < len(s):
                if i < len(s) - 1 and s[i] == best[0] and s[i + 1] == best[1] and isinstance(s[i], int) and isinstance(s[i + 1], int):
                    out.append(best); i += 2
                else:
                    out.append(s[i]); i += 1
            work[k] = out
    while len(chosen) < n: chosen.append((0x00, 0x00))
    return chosen

def encode(toks, pair_index):
    out = bytearray(); seg = []
    def flush():
        n = len(seg)
        best = [0] * (n + 1); how = [None] * (n + 1)
        for i in range(n - 1, -1, -1):
            best[i] = 1 + best[i + 1]; how[i] = 1
            if i + 1 < n and (seg[i], seg[i + 1]) in pair_index and 1 + best[i + 2] < best[i]:
                best[i] = 1 + best[i + 2]; how[i] = 2
        i = 0
        while i < n:
            if how[i] == 2:
                out.append(0x50 + pair_index[(seg[i], seg[i + 1])]); i += 2
            else:
                out.append(seg[i]); i += 1
        seg.clear()
    for kind, v in toks:
        if kind == 'c': seg.append(v)
        else:
            flush(); out += bytes([0xFF, v])
    flush()
    return bytes(out)

# ---------------------------------------------------------------- checksum / patch
def fix_checksum(d):
    d[0x7FDC:0x7FE0] = b'\xff\xff\x00\x00'
    s = (sum(d[:0x200000]) + 2 * sum(d[0x200000:])) & 0xFFFF
    struct.pack_into('<HH', d, 0x7FDC, s ^ 0xFFFF, s)

def _vlq(n):
    out = bytearray()
    while True:
        x = n & 0x7F; n >>= 7
        if n == 0:
            out.append(0x80 | x); return bytes(out)
        out.append(x); n -= 1

def make_bps(src, dst, meta=b''):
    out = bytearray(b'BPS1') + _vlq(len(src)) + _vlq(len(dst)) + _vlq(len(meta)) + meta
    i = 0; n = len(dst)
    while i < n:
        same = i < len(src) and src[i] == dst[i]
        j = i
        while j < n and (j < len(src) and src[j] == dst[j]) == same: j += 1
        length = j - i
        if same:
            out += _vlq(((length - 1) << 2) | 0)          # SourceRead
        else:
            out += _vlq(((length - 1) << 2) | 1) + dst[i:j]  # TargetRead
        i = j
    out += struct.pack('<III', zlib.crc32(src) & 0xFFFFFFFF, zlib.crc32(dst) & 0xFFFFFFFF, 0)
    struct.pack_into('<I', out, len(out) - 4, zlib.crc32(out[:-4]) & 0xFFFFFFFF)
    return bytes(out)

# ---------------------------------------------------------------- main
def main(en_path, script_path, jp_path, outdir):
    d = bytearray(open(en_path, 'rb').read())
    jp = open(jp_path, 'rb').read()
    mappa = json.load(open(os.path.splitext(script_path)[0] + '_puntatori.json'))
    msgs = parse_script(script_path)
    warnings = []
    toks = {mid: tokenize(mid, t, warnings) for mid, t in msgs.items()}
    pairs = choose_pairs(segments(toks.values()))
    pair_index = {}
    for i, p in enumerate(pairs):
        pair_index.setdefault(p, i)
    for i, (a, b) in enumerate(pairs):
        d[G.DTE_TABLE + 2 * i] = a; d[G.DTE_TABLE + 2 * i + 1] = b
    make_glyphs(d)
    patch_menus(d)
    patch_graphics(d)
    report = []
    for bi, (base, n, end) in enumerate(G.BANKS):
        ptr_ids = mappa['banks'][bi]['pointers']
        ids = [k for k in msgs if k.startswith('B%d-' % bi)]
        pos = base + 2 * n
        start = pos
        addr = {}
        for mid in ids:
            blob = encode(toks[mid], pair_index)
            if pos + len(blob) > end:
                raise SystemExit('ERRORE: il banco %d e\' pieno (messaggio %s). Accorcia il testo.' % (bi, mid))
            d[pos:pos + len(blob)] = blob
            addr[mid] = pos - base + 0x8000
            pos += len(blob)
        d[pos:end] = bytes(end - pos)
        for i, mid in enumerate(ptr_ids):
            struct.pack_into('<H', d, base + 2 * i, addr[mid])
        report.append('banco %d: %d byte usati, %d liberi' % (bi, pos - start, end - pos))
    fix_checksum(d)
    os.makedirs(outdir, exist_ok=True)
    rom_out = os.path.join(outdir, "Gunple - Gunman's Proof (ITA).sfc")
    open(rom_out, 'wb').write(d)
    bps = make_bps(jp, bytes(d))
    open(os.path.join(outdir, 'gunple_ita.bps'), 'wb').write(bps)
    for line in report: print(line)
    print('CRC32 ROM italiana: %08X' % (zlib.crc32(d) & 0xFFFFFFFF))
    if warnings:
        print('\n%d avvisi:' % len(warnings))
        for w in warnings[:200]: print('  ' + w)
    return d

if __name__ == '__main__':
    main(*sys.argv[1:5])
