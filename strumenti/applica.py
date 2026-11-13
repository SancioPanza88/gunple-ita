# Applica traduzioni al copione.
# uso: python3 applica.py copione_it.txt traduzioni.txt
# traduzioni.txt contiene blocchi "### Bx-nnn" seguiti dal testo italiano.
import sys, re

def blocks(text):
    out = {}; cur = None; buf = []
    for line in text.split('\n'):
        if line.startswith('###'):
            if cur: out[cur] = '\n'.join(buf).rstrip('\n ')
            cur = line.split()[1]; buf = []
        elif cur and not line.startswith(';'):
            buf.append(line)
    if cur: out[cur] = '\n'.join(buf).rstrip('\n ')
    return out

def main(script, trad):
    tr = blocks(open(trad, encoding='utf-8').read())
    lines = open(script, encoding='utf-8').read().split('\n')
    out = []; cur = None; i = 0; done = set()
    while i < len(lines):
        l = lines[i]
        if l.startswith('###'):
            cur = l.split()[1]; out.append(l); i += 1
            while i < len(lines) and lines[i].startswith(';'):
                out.append(lines[i]); i += 1
            body = []
            while i < len(lines) and not lines[i].startswith('###'):
                body.append(lines[i]); i += 1
            if cur in tr:
                out.append(tr[cur]); out.append(''); done.add(cur)
            else:
                out.extend(body)
        else:
            out.append(l); i += 1
    open(script, 'w', encoding='utf-8').write('\n'.join(out))
    missing = set(tr) - done
    print('applicati %d blocchi' % len(done) + ('; ID sconosciuti: %s' % sorted(missing) if missing else ''))

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
