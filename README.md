# MicroEdge Simulator

Simulatore locale della strategia baseline descritta in
`strategy_hypothesis.md`. Supporta dati sintetici e dati storici Alpaca SIP.

## Esito del primo MVP

Il primo ciclo di ricerca non ha dimostrato un edge positivo dopo spread,
slippage e costi Alpaca:

- la candidata V1 è stata respinta sul holdout di giugno 2026;
- nessuna fascia di volume relativo ha superato lo screening su maggio 2026;
- nessun regime QQQ ha superato lo screening su maggio 2026.

L'interfaccia mostra questi risultati direttamente dai report versionati. Il
simulatore resta uno strumento di ricerca e non è pronto per paper o live
trading.

## Avvio su Windows

```powershell
.\.venv\Scripts\streamlit.exe run app.py
```

Il browser apre automaticamente l'indirizzo locale del simulatore. Per
interromperlo, premere `Ctrl+C` nel terminale.

## Test

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Credenziali Alpaca

Copia `.streamlit/secrets.toml.example` in `.streamlit/secrets.toml` e sostituisci
i valori di esempio con la tua API Key e Secret Key. Il file reale è escluso da
Git. Non condividere o inserire le chiavi nel codice.

## Dataset locali

I dataset versionati sono salvati in:

```text
data/raw/alpaca/<feed>/<symbol>/
```

Ogni file Parquet ha un file `.metadata.json` adiacente con provenienza,
intervallo richiesto, controlli di qualità e checksum SHA-256. Una versione già
esistente non viene sovrascritta automaticamente.

## Profili broker

Il broker simulato è indipendente dalla sorgente dati. I profili disponibili
sono:

- `alpaca_personal_api`: commissioni retail API e fee regolamentari Alpaca;
- `custom_flat`: commissione fissa configurabile per ordine.

Nuovi broker possono essere aggiunti in `broker_costs.py` implementando lo
stesso calcolo per singolo ordine, senza modificare strategia o dati.
