# Estrae il copione dalla ROM inglese (con riferimento spagnolo) in un file di testo da tradurre.
# uso: python3 estrai.py rom_inglese.sfc rom_spagnola.sfc copione_it.txt
import sys, json, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gunple as G

HEADER = """\
# ============================================================================
#  GUNPLE: GUNMAN'S PROOF - copione per la traduzione italiana
# ============================================================================
#  Ogni messaggio inizia con una riga  ### Bx-nnn  (non modificarla).
#  Le righe che iniziano con  ;EN  e  ;ES  sono solo riferimento (ignorate).
#  Tutte le altre righe sono il testo che finisce nel gioco: sostituiscile
#  con l'italiano.
#
#  REGOLE
#   - Ogni riga di testo = una riga nella finestra. Massimo 24 caratteri
#     (il nome del giocatore [NAME] conta come 8). Il numero di righe e'
#     libero: quando la finestra e' piena il gioco scorre da solo.
#   - [WAIT] a fine riga = attende il tasto e apre una nuova pagina.
#   - Ogni messaggio deve finire con [END] o [00] (lasciali come sono).
#     Anche [05] e [25] chiudono un pezzo di messaggio (es. prima di un nome
#     di chi parla tipo "Robaton:"): lasciali dove sono.
#   - [20] [21] [22] [24] [25] ecc. = codici del gioco (velocita', pause...):
#     lasciali nella stessa posizione rispetto alla frase.
#   - Scelte Si'/No: la S e la N devono restare alle colonne 7 e 15, es.
#           "      Sì      No[END]"   (6 spazi, Sì, 6 spazi, No)
#   - Lettere accentate disponibili: à è é ì ò ù
#     Maiuscole accentate NON disponibili: scrivi  E'  invece di  È.
#   - Caratteri disponibili: A-Z a-z 0-9 spazio , . - ! ? " ' : ( ) $
#     (& % / * ~ NON esistono piu': i loro posti sono usati dagli accenti)
# ============================================================================

"""

def main(en_path, es_path, out_path):
    en = open(en_path, 'rb').read()
    es = open(es_path, 'rb').read()
    pen, pes = G.dte_pairs(en), G.dte_pairs(es)
    mappa = {'banks': []}
    out = [HEADER]
    for bi, (base, n, end) in enumerate(G.BANKS):
        p = G.ptrs(en, base, n)
        pe = G.ptrs(es, base, n)
        starts = sorted(set(p))
        ids = {}
        for k, s in enumerate(starts):
            ids[s] = 'B%d-%03d' % (bi, k)
        mappa['banks'].append({'pointers': [ids[x] for x in p]})
        for s in starts:
            mid = ids[s]
            idxs = [i for i, x in enumerate(p) if x == s]
            off = base + s - 0x8000
            out.append('### %s   (voci %s)\n' % (mid, ','.join('%03X' % i for i in idxs)))
            if G.is_unused(en, off):
                out.append(';EN (messaggio inutilizzato)\n[00]\n\n')
                continue
            t_en = G.toks_to_text(G.read_message(en, off, pen)[0], G.EN_TABLE)
            try:
                t_es = G.toks_to_text(G.read_message(es, base + pe[idxs[0]] - 0x8000, pes)[0], G.ES_TABLE)
            except Exception:
                t_es = '?'
            for line in t_en.split('\n'):
                out.append(';EN ' + line + '\n')
            for line in t_es.split('\n'):
                out.append(';ES ' + line + '\n')
            out.append(t_en + '\n\n')
    open(out_path, 'w', encoding='utf-8').write(''.join(out))
    json.dump(mappa, open(os.path.splitext(out_path)[0] + '_puntatori.json', 'w'), indent=0)
    print('scritti', sum(len(b['pointers']) for b in mappa['banks']), 'puntatori')

if __name__ == '__main__':
    main(*sys.argv[1:4])
