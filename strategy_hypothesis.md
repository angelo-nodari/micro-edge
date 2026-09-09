# MicroEdge — Ipotesi strategica baseline

> La baseline originale resta documentata in questo file. La prima ipotesi
> condizionale congelata per validazione è definita in
> `candidate_hypothesis_v1.md`.

## 1. Scopo dell'esperimento

Verificare il funzionamento di un simulatore intraday riproducibile per una
strategia naïve di mean reversion su NVDA.

In questa prima versione verranno utilizzati dati sintetici. I risultati
serviranno esclusivamente a validare la logica del simulatore e non potranno
essere considerati evidenza di un edge reale.

## 2. Ipotesi testabile

> Quando NVDA perde almeno lo 0,20% nell'arco di cinque minuti, il prezzo può
> mostrare una reversione sufficiente a raggiungere un target dello 0,20% prima
> di uno stop dello 0,15%, entro un massimo di cinque minuti e dopo i costi di
> esecuzione.

L'ipotesi sarà considerata interessante, ma non ancora validata, soltanto se
l'expectancy netta per trade risulterà positiva nel dataset analizzato.

## 3. Universo e dati

- Strumento simulato: NVDA.
- Frequenza: candele OHLCV da 1 minuto.
- Dati iniziali: sintetici e generati con seed fisso.
- Sessione di riferimento: mercato regolare USA.
- Finestra operativa: 09:35–15:55, ora di New York.
- Contesto precaricato: candele dalle 09:30, usate soltanto per calcolare il
  primo segnale delle 09:35.
- Nessuna posizione viene mantenuta oltre la sessione.

## 4. Regola di entrata

Al termine di ogni candela `t` si calcola il rendimento rispetto alla chiusura
di cinque minuti prima:

```text
drop_5m = close[t] / close[t-5] - 1
```

Si genera un segnale long quando:

```text
drop_5m <= -0,20%
```

L'ordine viene eseguito all'apertura della candela successiva, applicando i
costi descritti nella sezione 7.

Vincoli:

- può essere aperta al massimo una posizione alla volta;
- durante una posizione aperta, nuovi segnali vengono ignorati;
- dopo la chiusura di un trade, un nuovo segnale può essere valutato dalla
  candela successiva;
- un segnale privo di una candela successiva eseguibile viene ignorato.

## 5. Dimensionamento

- Capitale virtuale iniziale: 10.000 USD.
- Capitale nominale per trade: 1.000 USD.
- Quantità: numero intero di azioni acquistabili con 1.000 USD al prezzo di
  entrata simulato.
- Nessuna leva.
- Nessun reinvestimento dei profitti nella size iniziale.
- Se non è acquistabile almeno un'azione, il segnale viene ignorato.

## 6. Regole di uscita

Le soglie sono calcolate rispetto al prezzo di entrata eseguito:

- take profit: +0,20%;
- stop loss: -0,15%;
- durata massima: 5 candele da 1 minuto, inclusa la candela di entrata.

A partire dalla candela di entrata, dopo l'esecuzione all'apertura:

1. se viene raggiunto soltanto lo stop, l'uscita avviene allo stop;
2. se viene raggiunto soltanto il target, l'uscita avviene al target;
3. se stop e target risultano entrambi raggiunti nella stessa candela, si assume
   prudentemente che venga eseguito prima lo stop;
4. se nessuna soglia viene raggiunta entro il limite temporale, l'uscita avviene
   alla chiusura della quinta candela;
5. in ogni caso, un'eventuale posizione residua viene chiusa entro le 15:55.

## 7. Modello di esecuzione baseline

Profilo broker baseline: `alpaca_personal_api`.

Costi di esecuzione:

- spread totale: 2 basis point, quindi 1 bp sfavorevole per lato rispetto al
  prezzo centrale simulato;
- slippage: 1 bp sfavorevole per ciascuna esecuzione;
- commissione broker Alpaca Personal API: 0 USD;
- SEC fee sulla vendita: controvalore venduto × 0,00002060, arrotondato per
  eccesso al centesimo;
- FINRA TAF sulla vendita: 0,000195 USD per azione, arrotondato per eccesso al
  centesimo e con massimo di 9,79 USD per ordine;
- CAT fee azionaria corrente: 0 USD.

Per un acquisto, spread e slippage aumentano il prezzo eseguito. Per una
vendita, lo riducono. Tutte le metriche economiche sono calcolate al netto di
questi costi. Il broker è un parametro indipendente dalla sorgente dati; profili
futuri potranno implementare tariffari differenti senza cambiare la strategia.

Questa baseline non simula ancora partial fill, liquidità insufficiente, ordini
limit, latenza variabile o market impact.

## 8. Output minimo richiesto

Il simulatore dovrà produrre:

- numero di trade;
- win rate;
- profitto medio;
- perdita media;
- expectancy netta per trade;
- profit factor;
- max drawdown;
- P&L netto totale;
- elenco riproducibile delle operazioni;
- grafico del prezzo con entrate e uscite;
- equity curve.

## 9. Criteri di correttezza del primo prototipo

Il primo prototipo è accettato se:

1. a parità di seed e parametri produce sempre gli stessi risultati;
2. ogni operazione può essere ricostruita dai dati e dalle regole;
3. spread, slippage e commissioni sono visibili separatamente;
4. non usa informazioni future per generare il segnale;
5. gestisce esplicitamente i casi ambigui descritti nella sezione 6;
6. l'interfaccia permette di modificare i parametri principali e rieseguire la
   simulazione.

## 10. Interpretazione dei risultati

Un risultato positivo sui dati sintetici non costituisce conferma della
strategia. Il passaggio successivo alla validazione tecnica sarà sostituire i
dati sintetici con dati storici intraday reali e ripetere l'esperimento su
periodi separati.

La decisione economica resta quindi sospesa fino alla disponibilità di dati
reali e a una successiva validazione out-of-sample.
