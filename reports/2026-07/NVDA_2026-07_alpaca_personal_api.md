# MicroEdge — Baseline report NVDA

## Dataset

- Feed: SIP
- Barre: 8492
- Sessioni: 22
- Inizio: 2026-07-01T09:30:00-04:00
- Fine: 2026-07-31T15:55:00-04:00
- File sorgente: `data/raw/alpaca/sip/NVDA/NVDA_2026-07-01_2026-07-31_1min.parquet`

## Parametri baseline

- Calo a 5 minuti: 0.20%
- Take profit: 0.20%
- Stop loss: 0.15%
- Holding massimo: 5 minuti
- Capitale per trade: $1,000.00
- Spread totale: 2.0 bp
- Slippage per lato: 1.0 bp
- Broker: Alpaca Personal API
- Commissione fissa configurata: $0.00

## Risultato netto

- Trade: 562
- Win rate: 35.8%
- Expectancy: $-0.40
- Profit factor: 0.54
- Max drawdown: $228.32
- P&L totale: $-224.88

## Sensibilità allo slippage

| slippage_bps | trade_count | win_rate | expectancy | profit_factor | total_net_pnl |
|---|---|---|---|---|---|
| 0.00 | 550 | 41.3% | $-0.19 | 0.75 | $-103.33 |
| 1.00 | 562 | 35.8% | $-0.40 | 0.54 | $-224.88 |
| 2.00 | 571 | 30.6% | $-0.60 | 0.39 | $-342.69 |
| 5.00 | 618 | 21.0% | $-1.14 | 0.16 | $-703.37 |

## Risultato per ora di ingresso

| entry_hour | trade_count | win_rate | expectancy | profit_factor | total_net_pnl |
|---|---|---|---|---|---|
| 9 | 89 | 33.7% | $-0.47 | 0.53 | $-41.92 |
| 10 | 161 | 34.8% | $-0.44 | 0.55 | $-70.53 |
| 11 | 79 | 40.5% | $-0.23 | 0.70 | $-18.53 |
| 12 | 67 | 46.3% | $-0.14 | 0.79 | $-9.61 |
| 13 | 51 | 43.1% | $-0.30 | 0.57 | $-15.42 |
| 14 | 51 | 37.3% | $-0.35 | 0.50 | $-17.68 |
| 15 | 64 | 17.2% | $-0.80 | 0.19 | $-51.20 |

## Risultato per motivo di uscita

| exit_reason | trade_count | win_rate | expectancy | profit_factor | total_net_pnl |
|---|---|---|---|---|---|
| take_profit | 149 | 100.0% | $1.58 | ∞ | $235.92 |
| stop_loss | 284 | 0.0% | $-1.56 | 0.00 | $-442.29 |
| max_holding | 129 | 40.3% | $-0.14 | 0.58 | $-18.52 |

## File di dettaglio

I risultati giornalieri e l'elenco completo dei trade sono disponibili nei file CSV adiacenti.

## Interpretazione

Questo report descrive una baseline su un solo mese. Non costituisce validazione dell'edge e non è stato usato per ottimizzare i parametri.
