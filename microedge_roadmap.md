# MicroEdge — Roadmap di Progetto

## 1. Obiettivo

Costruire e validare una piattaforma di trading algoritmico intraday capace di individuare piccoli vantaggi statistici ripetibili su strumenti molto liquidi, con particolare attenzione a strategie di **mean reversion / micro-scalping**.

L'obiettivo iniziale non è costruire un "bot che guadagna", ma verificare in modo rigoroso se esiste un **edge statistico reale**, robusto e sfruttabile dopo:

- commissioni;
- spread bid/ask;
- slippage;
- latenza;
- vincoli di esecuzione;
- differenti regimi di mercato.

Il passaggio al trading reale avverrà solo dopo una validazione positiva su dati out-of-sample e paper trading.

---

# 2. Principi del progetto

1. **Research first**  
   Nessun capitale reale finché non esiste evidenza quantitativa di un edge.

2. **Realistic execution**  
   Ogni backtest deve includere costi e condizioni realistiche di esecuzione.

3. **Out-of-sample by design**  
   Training, ottimizzazione e validazione devono essere separati.

4. **No trade è una decisione**  
   Il sistema deve poter decidere di non operare quando il contesto non è favorevole.

5. **Risk management prima del rendimento**  
   Drawdown, perdita massima e rischio per trade vengono prima del profitto assoluto.

6. **Scaling progressivo**  
   Storico → simulazione → paper trading → capitale minimo → scaling.

---

# 3. Universo iniziale

Strumenti candidati:

- NVDA
- AMD
- TSLA
- QQQ

Criteri:

- elevata liquidità;
- spread ridotto;
- volumi intraday elevati;
- volatilità sufficiente;
- disponibilità di dati storici intraday affidabili.

In una fase successiva sarà possibile estendere l'universo a ETF, azioni large-cap, futures o altri strumenti.

---

# 4. Roadmap

## Fase 0 — Definizione del problema

### Obiettivo

Trasformare l'idea iniziale in un'ipotesi quantitativa testabile.

### Ipotesi iniziale

Esempio:

> Dopo una determinata discesa intraday, in specifiche condizioni di volatilità e liquidità, il prezzo ha una probabilità sufficientemente elevata di recuperare X% prima di perdere Y%.

### Attività

- definire timeframe operativo;
- definire holding period atteso;
- definire target iniziale;
- definire stop iniziale;
- scegliere strumenti;
- definire orari di trading;
- definire capitale virtuale;
- definire costi di transazione;
- definire metriche di successo.

### Deliverable

`strategy_hypothesis.md`

### Gate di avanzamento

La strategia deve essere esprimibile come insieme di regole non ambigue e completamente simulabili.

---

## Fase 1 — Data Foundation

### Obiettivo

Costruire il dataset necessario per analisi e backtest.

### Dati minimi

Per ogni strumento:

- timestamp;
- open;
- high;
- low;
- close;
- volume.

Preferibilmente:

- bid;
- ask;
- bid size;
- ask size;
- trades;
- order book / level 2;
- VWAP.

Dati contestuali:

- SPY / QQQ;
- VIX;
- indice Nasdaq;
- settore;
- calendario macro;
- earnings;
- eventi FOMC / CPI / NFP.

### Attività

- selezione provider dati;
- download dati storici;
- normalizzazione timestamp;
- gestione timezone;
- gestione split/dividendi;
- controllo missing data;
- identificazione market halt;
- costruzione data pipeline.

### Deliverable

Dataset storico versionato.

Esempio:

```text
data/
├── raw/
├── normalized/
├── features/
└── metadata/
```

### Gate di avanzamento

Dataset consistente e riproducibile con controlli automatici di qualità.

---

## Fase 2 — Baseline Strategy

### Obiettivo

Implementare volutamente una strategia semplice, vicina all'idea originale.

### Esempio

Condizione di entrata:

```text
prezzo scende dello 0,20%
↓
BUY
```

Condizione di uscita:

```text
take profit: +0,20%
stop loss: -0,15%
max holding: 5 minuti
```

La baseline non deve essere sofisticata.

Serve per costruire il framework sperimentale.

### Componenti

```text
Market Data
    ↓
Signal Engine
    ↓
Position Manager
    ↓
Execution Simulator
    ↓
Performance Engine
```

### Deliverable

Primo backtester funzionante.

### Gate di avanzamento

Il backtest deve produrre risultati completamente riproducibili.

---

## Fase 3 — Execution Simulator

### Obiettivo

Eliminare il profitto "teorico" introducendo condizioni realistiche di mercato.

### Simulare

- spread bid/ask;
- commissioni;
- slippage;
- partial fills;
- ritardo di esecuzione;
- market order;
- limit order;
- mancata esecuzione;
- liquidità insufficiente.

### Scenario analysis

Testare almeno:

- 0 bp slippage;
- 1 bp;
- 2 bp;
- 5 bp;
- scenario stress.

### Deliverable

`execution_engine.py`

### Gate di avanzamento

Una strategia può proseguire solo se rimane profittevole sotto ipotesi realistiche di esecuzione.

---

## Fase 4 — Feature Engineering

### Obiettivo

Descrivere quantitativamente il contesto di mercato.

### Feature candidate

#### Prezzo

- return 1s / 5s / 30s / 1m;
- distanza da VWAP;
- distanza da open;
- accelerazione;
- momentum;
- mean reversion score.

#### Volatilità

- realized volatility;
- ATR intraday;
- rolling standard deviation;
- volatility regime.

#### Volume

- volume relativo;
- volume acceleration;
- volume imbalance.

#### Microstructure

Se disponibili:

- bid/ask spread;
- order book imbalance;
- trade imbalance;
- aggressor side;
- depth.

#### Contesto

- QQQ return;
- SPY return;
- Nasdaq momentum;
- VIX;
- settore;
- ora del giorno;
- giorno della settimana;
- distanza da eventi macro.

### Deliverable

Feature pipeline.

### Gate di avanzamento

Nessun look-ahead bias e nessuna feature costruita usando informazioni future.

---

## Fase 5 — Statistical Edge Discovery

### Obiettivo

Rispondere alla domanda principale:

> In quali condizioni il trade ha aspettativa positiva?

### Analisi

Per ogni setup:

```text
P(+target prima di -stop | condizioni di mercato)
```

Esempio:

```text
P(+0,18% prima di -0,12%
  | distanza VWAP < -0,3%
  | volume elevato
  | QQQ stabile
  | spread < soglia)
```

### Segmentazione

Analizzare per:

- titolo;
- ora del giorno;
- volatilità;
- volume;
- trend di mercato;
- giorno positivo/negativo;
- regime macro.

### Output

Heatmap e ranking dei setup.

### Gate di avanzamento

Identificazione di almeno un setup con expectancy positiva statisticamente significativa dopo costi.

---

## Fase 6 — Strategy Engine V2

### Obiettivo

Passare da una strategia statica a una strategia condizionale.

Da:

```text
se scende → compra
```

A:

```text
se scende
AND volatilità compatibile
AND spread basso
AND volume sufficiente
AND contesto favorevole
→ compra
```

### Target dinamico

Esempio:

| Regime | Target |
|---|---:|
| Bassa volatilità | +0,10% |
| Normale | +0,18% |
| Alta volatilità | +0,30% |
| Trend fortemente negativo | NO TRADE |

### Deliverable

Strategy Engine V2.

---

## Fase 7 — Risk Engine

### Obiettivo

Evitare che piccoli guadagni vengano annullati da pochi eventi estremi.

### Controlli

- max position size;
- max capitale per trade;
- stop per trade;
- max loss giornaliera;
- max drawdown;
- max numero di trade;
- cooldown dopo perdita;
- stop trading durante anomalie;
- stop trading durante news/eventi;
- kill switch.

### Regola fondamentale

```text
Risk Engine > Strategy Engine
```

Il modulo di rischio deve poter bloccare qualsiasi ordine.

### Deliverable

`risk_engine.py`

---

## Fase 8 — Backtest Robusto

### Obiettivo

Verificare che il risultato non sia prodotto da overfitting.

### Suddivisione dati

Esempio:

```text
TRAIN
2022–2024

VALIDATION
2025

TEST / OUT-OF-SAMPLE
2026
```

Alternativa:

Walk-forward validation.

### Metriche

- total return;
- CAGR;
- expectancy per trade;
- win rate;
- average win;
- average loss;
- profit factor;
- Sharpe ratio;
- Sortino ratio;
- max drawdown;
- recovery time;
- turnover;
- trades/day;
- exposure;
- tail loss;
- P&L distribution.

### Stress test

Testare:

- costi ×2;
- slippage ×2;
- latenza maggiore;
- spread più ampio;
- riduzione fill rate;
- volatilità estrema.

### Gate di avanzamento

Il sistema deve:

1. avere expectancy positiva;
2. essere positivo out-of-sample;
3. mantenere performance accettabile sotto stress;
4. avere drawdown compatibile con il rischio definito.

---

## Fase 9 — Paper Trading

### Obiettivo

Testare il sistema in condizioni di mercato reali senza capitale.

### Broker candidato

Interactive Brokers.

Possibile alternativa:

Alpaca.

### Architettura

```text
Real-Time Market Data
        ↓
Feature Engine
        ↓
Strategy Engine
        ↓
Risk Engine
        ↓
Order Manager
        ↓
Broker API
        ↓
Paper Account
```

### Monitorare

- prezzo teorico vs fill;
- latenza;
- slippage;
- ordini mancati;
- differenza backtest/live;
- stabilità software;
- errori API.

### Durata minima

Non definita a priori.

Il criterio deve essere statistico, non temporale.

### Gate di avanzamento

Performance live-paper coerente con il range previsto dal backtest.

---

## Fase 10 — Shadow Mode

### Obiettivo

Far funzionare il sistema come se operasse con denaro reale senza inviare ordini.

Registrare:

```text
timestamp
signal
expected entry
expected exit
broker quote
simulated fill
expected P&L
realized hypothetical P&L
```

### Vantaggio

Permette di verificare:

- stabilità;
- latenza;
- pricing;
- execution model;
- comportamento in eventi reali.

---

## Fase 11 — Live Trading Minimum Capital

### Obiettivo

Validare il comportamento con denaro reale minimizzando il rischio.

### Capitale iniziale

Capitale volutamente ridotto.

Esempio:

```text
1.000–5.000 USD
```

Il capitale ha funzione sperimentale, non di rendimento.

### Limiti

- size minima;
- perdita giornaliera molto limitata;
- kill switch;
- max trade;
- nessun leverage iniziale.

### Gate di avanzamento

Coerenza tra:

```text
Backtest
    ↓
Paper Trading
    ↓
Live Trading
```

---

## Fase 12 — Scaling

### Obiettivo

Determinare fino a quale capitale l'edge resta sfruttabile.

### Esperimento

Incrementare progressivamente:

```text
1x
2x
5x
10x
```

Analizzando:

- slippage;
- market impact;
- fill rate;
- liquidità;
- performance.

### Domanda chiave

> Qual è la capacity della strategia?

Non assumere che un algoritmo profittevole con 5.000 USD sia profittevole con 500.000 USD.

---

# 5. Possibile evoluzione Machine Learning

Il Machine Learning deve essere introdotto solo dopo aver costruito una baseline quantitativa solida.

## Problema ML

Stimare:

```text
P(target raggiunto prima dello stop | market state)
```

Possibili modelli:

- Logistic Regression;
- Random Forest;
- XGBoost / LightGBM;
- Gradient Boosting;
- reti neurali solo successivamente.

### Output

Non necessariamente:

```text
BUY / SELL
```

Preferibilmente:

```text
probability_of_success = 0.73
expected_return = 0.14%
expected_risk = 0.09%
```

Il Strategy Engine decide poi se operare.

---

# 6. KPI principali

## Trading

| KPI | Descrizione |
|---|---|
| Expectancy | profitto medio atteso per trade |
| Profit Factor | gross profit / gross loss |
| Sharpe | rendimento corretto per volatilità |
| Max Drawdown | perdita massima peak-to-trough |
| Win Rate | percentuale trade positivi |
| Payoff Ratio | average win / average loss |
| Tail Risk | perdita nei casi estremi |
| Trades/day | frequenza operativa |
| Capacity | capitale massimo sostenibile |

## Engineering

- uptime;
- latenza end-to-end;
- error rate API;
- rejected orders;
- fill rate;
- divergence paper/live;
- data integrity.

---

# 7. Stack tecnologico candidato

## Linguaggio

Python.

## Research

- pandas;
- NumPy;
- Polars;
- Jupyter.

## Modeling

- scikit-learn;
- XGBoost / LightGBM.

## Storage

Prima fase:

- Parquet;
- DuckDB.

Possibile evoluzione:

- PostgreSQL;
- TimescaleDB.

## Backtest

Possibile implementazione custom per avere pieno controllo sulla microstruttura e sull'execution model.

## Broker

- Interactive Brokers API;
- eventualmente Alpaca.

## Deployment

Prima fase:

```text
Local workstation
```

Successivamente:

```text
Docker
↓
VPS / Cloud
↓
Monitoring
```

---

# 8. Repository suggerito

```text
microedge/
│
├── config/
│
├── data/
│   ├── raw/
│   ├── normalized/
│   └── features/
│
├── notebooks/
│
├── src/
│   ├── data/
│   ├── features/
│   ├── strategies/
│   ├── execution/
│   ├── risk/
│   ├── backtest/
│   ├── broker/
│   └── monitoring/
│
├── tests/
│
├── reports/
│
├── models/
│
└── README.md
```

---

# 9. Milestone

## M0 — Project Definition

Output:

```text
strategia formalizzata
strumenti selezionati
metriche definite
```

## M1 — Data Ready

Output:

```text
dataset storico pulito
```

## M2 — Baseline Backtest

Output:

```text
prima strategia completamente simulabile
```

## M3 — Realistic Simulation

Output:

```text
spread + commissioni + slippage
```

## M4 — Edge Discovery

Output:

```text
identificazione dei contesti profittevoli
```

## M5 — Robust Strategy

Output:

```text
out-of-sample positivo
stress test superati
```

## M6 — Paper Trading

Output:

```text
sistema collegato al mercato reale
```

## M7 — Live Minimal

Output:

```text
prime operazioni con capitale reale minimo
```

## M8 — Scale Decision

Output:

```text
decisione GO / NO-GO sullo scaling
```

---

# 10. Criterio finale GO / NO-GO

Il progetto passa alla fase di scaling solo se tutte queste condizioni sono soddisfatte:

- expectancy positiva dopo tutti i costi;
- risultato positivo out-of-sample;
- drawdown entro i limiti;
- performance non dipendente da pochi trade eccezionali;
- robustezza a spread e slippage superiori al previsto;
- paper trading coerente con il backtest;
- live trading coerente con il paper trading;
- assenza di problemi critici di execution;
- edge stabile su un numero statisticamente significativo di operazioni.

In caso contrario:

```text
NO-GO
↓
analisi
↓
nuova ipotesi
↓
nuovo ciclo di ricerca
```

---

# 11. Primo Sprint

Obiettivo del primo sprint:

> Determinare se una strategia naïve di mean reversion intraday presenta un edge misurabile su un singolo strumento altamente liquido.

## Attività

1. scegliere un titolo, inizialmente NVDA;
2. procurare dati intraday;
3. definire timeframe;
4. implementare entry;
5. implementare take profit;
6. implementare stop loss;
7. implementare max holding time;
8. inserire commissioni;
9. simulare spread;
10. simulare slippage;
11. generare report dei risultati;
12. analizzare risultati per ora e regime di volatilità.

## Output

Un report con:

```text
numero trade
win rate
average win
average loss
expectancy
profit factor
max drawdown
P&L totale
performance per mese
performance per ora
sensibilità allo slippage
```

## Decisione

Se la baseline perde:

> capire in quali condizioni perde e se esistono sottogruppi con edge positivo.

Se la baseline guadagna:

> verificare immediatamente se il risultato sopravvive a costi maggiori e dati out-of-sample.

---

# 12. Visione del progetto

MicroEdge non deve cercare di prevedere il mercato in senso generale.

Deve cercare situazioni specifiche in cui sia possibile affermare:

> Date queste condizioni di mercato, esiste una probabilità sufficientemente elevata che il prezzo raggiunga il target prima dello stop da produrre un'aspettativa positiva dopo tutti i costi.

Se questa condizione non può essere dimostrata quantitativamente, il sistema non deve operare.

Se può essere dimostrata, il progetto passa progressivamente da **ricerca** a **simulazione**, da **simulazione** a **paper trading**, e solo infine a **capitale reale**.
