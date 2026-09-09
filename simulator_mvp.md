# MicroEdge — Struttura minima del simulatore

## Obiettivo

Costruire una piccola applicazione web locale per eseguire e ispezionare la
strategia definita in `strategy_hypothesis.md` su dati sintetici riproducibili.

Questa versione serve a validare il flusso completo:

```text
dati sintetici → segnale → esecuzione → trade → metriche → grafici
```

Non serve ancora a valutare se la strategia possiede un edge reale.

## Tecnologia proposta

- Python
- Streamlit per l'interfaccia web locale
- pandas e NumPy per dati e calcoli
- Plotly per i due grafici interattivi
- unittest della libreria standard per i test essenziali

Streamlit permette di ottenere un'interfaccia locale modificabile senza creare
un frontend e un backend separati.

## Struttura iniziale

```text
MicroEdge/
├── app.py
├── simulator.py
├── requirements.txt
├── strategy_hypothesis.md
├── microedge_roadmap.md
└── tests/
    └── test_simulator.py
```

Responsabilità:

- `app.py`: controlli, visualizzazione dei risultati e messaggi all'utente;
- `simulator.py`: generazione dati, regole strategiche, esecuzione e metriche;
- `test_simulator.py`: verifica delle regole più importanti;
- `requirements.txt`: sole dipendenze necessarie all'MVP.

Per ora non verranno create ulteriori cartelle o livelli architetturali.

## Schermata unica

La pagina conterrà quattro aree, nello stesso ordine.

### 1. Parametri

Controlli modificabili:

- seed casuale;
- numero di giornate simulate;
- soglia del calo a 5 minuti;
- take profit;
- stop loss;
- durata massima;
- capitale per trade;
- spread;
- slippage;
- commissione per ordine.
- broker simulato e relativo modello commissionale.

Un solo pulsante avvia nuovamente la simulazione.

### 2. Metriche

Saranno mostrate soltanto:

- numero di trade;
- win rate;
- expectancy netta;
- profit factor;
- max drawdown;
- P&L netto.

### 3. Grafici

- prezzo di una giornata selezionata, con entrate e uscite;
- equity curve dell'intera simulazione.

### 4. Operazioni

Tabella con:

- entrata e uscita;
- prezzi teorici ed eseguiti;
- quantità;
- motivo dell'uscita;
- P&L lordo;
- spread, slippage e commissioni;
- P&L netto.

## Generatore sintetico iniziale

Il generatore creerà candele OHLCV da un minuto per giornate indipendenti,
usando un seed fisso. La prima versione simulerà soltanto:

- prezzo iniziale configurato internamente;
- rendimenti casuali con volatilità intraday;
- volatilità maggiore all'apertura e alla chiusura;
- volume coerente, ma non ancora usato dalla strategia.

Non verrà inserita artificialmente una mean reversion favorevole: lo scopo è
testare il motore senza costruire intenzionalmente un risultato positivo.

## Regole di separazione

`simulator.py` non dipenderà da Streamlit. Riceverà parametri e restituirà:

```text
candele, operazioni, equity curve, metriche
```

Questo consentirà in seguito di sostituire i dati sintetici con dati reali
senza riscrivere le regole della strategia o l'interfaccia.

## Test minimi

Prima di considerare completo l'MVP verranno verificati questi casi:

1. stesso seed e stessi parametri producono gli stessi risultati;
2. nessun segnale usa dati successivi alla candela corrente;
3. stop e target nella stessa candela producono uno stop;
4. la posizione viene chiusa al termine del holding period;
5. non esistono due posizioni contemporanee;
6. costi nulli producono P&L netto uguale al P&L lordo;
7. i costi riducono correttamente il P&L;
8. una giornata senza segnali non causa errori.

## Esclusioni deliberate

Non fanno parte del primo MVP:

- dati di mercato reali;
- broker e paper trading;
- account utente;
- database;
- API web separata;
- Docker e deployment cloud;
- ordini limit e partial fill;
- machine learning;
- ottimizzazione automatica dei parametri;
- analisi per regime di mercato;
- responsive design avanzato.

## Criterio di completamento

L'MVP sarà completo quando potrà essere avviato localmente, modificare i
parametri, ripetere una simulazione deterministica e ricostruire ogni trade dai
dati mostrati.
