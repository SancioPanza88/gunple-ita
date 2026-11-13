# Disegna in PNG come appaiono i messaggi nella ROM compilata (font reale del gioco).
# uso: python3 anteprima.py rom.sfc output.png B0-000 B0-001 ...   (ID del copione)
#      oppure indici di puntatore tipo 0:005 1:01A
import sys, os, json, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw
import gunple as G

PAL = {0: (24, 32, 72), 1: (255, 255, 255), 2: (40, 40, 40), 3: (255, 200, 0)}

def glyph(d, c):
    a = G.FONT_BASE + struct.unpack_from('<H', d, G.GLYPH_PTRS + 2 * c)[0] - 0x8000
    rows = []
    for off in (a, a + 0x100):
        for y in range(8):
            p0, p1 = d[off + 2 * y], d[off + 2 * y + 1]
            rows.append([((p0 >> (7 - x)) & 1) | (((p1 >> (7 - x)) & 1) << 1) for x in range(8)])
    return rows

def render(d, toks, name_codes, S=2, cols=24):
    pages = [[[]]]
    for kind, v in toks:
        if kind == 'c': pages[-1][-1].append(v)
        elif v == 0x10: pages[-1][-1].extend(name_codes)
        elif v == 0x01: pages[-1].append([])
        elif v in (0x03, 0x05, 0x25): pages.append([[]])
    W = (cols * 8 + 16) * S
    blocks = []
    for pg in pages:
        h = (len(pg) * 16 + 16) * S
        im = Image.new('RGB', (W, h), PAL[0]); dr = ImageDraw.Draw(im)
        dr.rectangle([0, 0, W - 1, h - 1], outline=(200, 200, 255), width=S)
        for li, line in enumerate(pg):
            for ci, c in enumerate(line):
                g = glyph(d, c)
                for y in range(16):
                    for x in range(8):
                        v = g[y][x]
                        if v:
                            px = (8 + ci * 8 + x) * S; py = (8 + li * 16 + y) * S
                            dr.rectangle([px, py, px + S - 1, py + S - 1], fill=PAL[v])
            if len(line) > cols:
                dr.rectangle([(8 + cols * 8) * S, (8 + li * 16) * S, W - 1, (8 + li * 16 + 15) * S], outline=(255, 0, 0), width=S)
        blocks.append(im)
    return blocks

def main(rom, out, ids, script=None):
    d = open(rom, 'rb').read(); pairs = G.dte_pairs(d)
    mp = None
    for cand in ([script] if script else []) + [os.path.join(os.path.dirname(rom), '..', 'progetto', 'copione_it_puntatori.json')]:
        if cand and os.path.exists(cand): mp = json.load(open(cand)); break
    name = [G.IT_TABLE and {v: k for k, v in G.IT_TABLE.items()}[ch] for ch in 'Ninnolo']
    ims = []
    for ident in ids:
        if ':' in ident:
            b, i = ident.split(':'); b = int(b); i = int(i, 16)
        else:
            b = int(ident[1]); i = mp['banks'][b]['pointers'].index(ident)
        base = G.BANKS[b][0]
        off = base + G.ptrs(d, base, G.BANKS[b][1])[i] - 0x8000
        toks = G.read_message(d, off, pairs)[0]
        lab = Image.new('RGB', (420, 18), (0, 0, 0)); ImageDraw.Draw(lab).text((4, 3), ident, fill=(255, 255, 0))
        ims.append(lab); ims.extend(render(d, toks, name))
    W = max(i.width for i in ims); H = sum(i.height + 6 for i in ims)
    sheet = Image.new('RGB', (W, H), (0, 0, 0)); y = 0
    for im in ims:
        sheet.paste(im, (0, y)); y += im.height + 6
    sheet.save(out)

if __name__ == '__main__':
    args = sys.argv[1:]
    script = None
    if '--mappa' in args:
        k = args.index('--mappa'); script = args[k + 1]; del args[k:k + 2]
    main(args[0], args[1], args[2:], script)
