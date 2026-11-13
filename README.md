# Gunple: Gunman's Proof - traduzione italiana

Questa è la mia traduzione in italiano di **Ganpuru: Gunman's Proof** (ガンプル), il gioco per Super Famicom del 1997 di ASCII e Lenar. Ci giocavo con la traduzione inglese e mi è sempre dispiaciuto che non ci fosse una versione in italiano, quindi eccola.

Versione attuale: **1.0** (novembre 2026)

![Dialoghi](immagini/anteprima_dialoghi.png)

## Come si applica

Vi serve la ROM giapponese originale, non ancora patchata:

- `Ganpuru - Gunman's Proof (Japan).sfc`
- 3.145.728 byte, senza header
- CRC32: `AF415C24`
- SHA-1: `dad73d2c0b1a3c916d40c4a208566ee4193333b2`

Applicateci sopra `gunple_ita.bps` con [Floating IPS](https://www.romhacking.net/utilities/1040/) oppure online con [Rom Patcher JS](https://www.marcrobledo.com/RomPatcher.js/). Se la ROM ha l'header da 512 byte (file .smc), prima toglietelo, altrimenti la patch non va.

La ROM qui non c'è e non ve la posso dare, quindi non chiedetela.

## Cosa è tradotto

- Tutti i dialoghi (513 messaggi), dall'introduzione al finale
- Le schede delle mosse e i menu MOSSE / STEMMI / OGGETTI
- Le opzioni del game over e i pulsanti della schermata del nome

Rimasti in originale: il logo del titolo, la scritta GAME OVER e un pulsante della schermata del nome ("HELLO!"), che non ho capito bene a cosa serva.

Le lettere accentate ci sono (à è é ì ò ù). Per le maiuscole accentate non c'era spazio nel font, quindi trovate E' al posto di È, come nelle vecchie traduzioni amatoriali.

## L'AI mi ha aiutato

Lo dico chiaramente: in questo progetto **mi sono fatto assistere da un'intelligenza artificiale** (Claude, di Anthropic). Mi ha aiutato con la parte tecnica, cioè capire come il gioco salva il testo, scrivere gli strumenti per estrarlo e reinserirlo e ridisegnare le lettere accentate. Mi ha aiutato anche con la prima stesura della traduzione.

Il testo è stato controllato in automatico: nessuna riga esce dalla finestra e ogni messaggio torna al posto giusto. Però **non è ancora stato rigiocato tutto dall'inizio alla fine**. Quindi ci possono essere:

- frasi che suonano strane o tradotte troppo alla lettera
- errori di battitura
- scritte che si vedono male in qualche punto (soprattutto le grafiche del game over e la riga dei crediti nella schermata del nome)
- scelte Sì/No col cursore un po' disallineato

Insomma, ha bisogno di altri controlli. Se ci giocate e trovate qualcosa che non va, aprite una issue con uno screenshot. Se riuscite, scrivete anche il codice del messaggio (tipo `B0-123`): lo trovate cercando la frase in `copione/copione_it.txt`.

## Ricompilare da soli

Nella cartella `strumenti` ci sono gli script Python che uso io (servono Python 3 e Pillow per le anteprime). La traduzione parte dalla ROM con la patch inglese di Aeon Genesis v1.03 applicata, perché usa il loro font e il loro motore del testo:

```
python3 strumenti/compila.py ROM_INGLESE.sfc copione/copione_it.txt ROM_GIAPPONESE.sfc build
```

Il copione si modifica a mano. Le regole sono scritte in cima al file: massimo 24 caratteri per riga, e i codici tra parentesi quadre non vanno toccati. I menu, le grafiche e la riga dei crediti sono in fondo a `compila.py`.

## Crediti

- Traduzione italiana: **Sanciopanza88**
- Hacking originale e traduzione inglese: **Aeon Genesis** (agtp.romhack.net). Senza il loro lavoro questa traduzione non esisterebbe: font, motore del testo e compressione sono roba loro.
- Traduzione spagnola di **Traducciones Lukas**, che ho usato come riferimento
- Assistenza tecnica e di traduzione: Claude (Anthropic)
- Il gioco è di ASCII, Lenar, Akihito Tomisawa e Isami Nakagawa

Ganpuru: Gunman's Proof © 1997 ASCII / Lenar. Questa è una traduzione amatoriale, fatta senza scopo di lucro e senza nessun legame con i detentori dei diritti.
