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
- Commissione per ordine: $1.00

## Risultato netto

- Trade: 562
- Win rate: 0.0%
- Expectancy: $-2.37
- Profit factor: 0.00
- Max drawdown: $1330.25
- P&L totale: $-1330.25

## Sensibilità allo slippage

| slippage_bps | trade_count | win_rate | expectancy | profit_factor | total_net_pnl |
|---|---|---|---|---|---|
| 0.00 | 550 | 0.0% | $-2.15 | 0.00 | $-1185.10 |
| 1.00 | 562 | 0.0% | $-2.37 | 0.00 | $-1330.25 |
| 2.00 | 571 | 0.0% | $-2.57 | 0.00 | $-1465.77 |
| 5.00 | 618 | 0.0% | $-3.11 | 0.00 | $-1918.92 |

## Risultato per ora di ingresso

| entry_hour | trade_count | win_rate | expectancy | profit_factor | total_net_pnl |
|---|---|---|---|---|---|
| 9 | 89 | 0.0% | $-2.44 | 0.00 | $-217.04 |
| 10 | 161 | 0.0% | $-2.40 | 0.00 | $-387.13 |
| 11 | 79 | 0.0% | $-2.20 | 0.00 | $-173.79 |
| 12 | 67 | 0.0% | $-2.11 | 0.00 | $-141.39 |
| 13 | 51 | 0.0% | $-2.27 | 0.00 | $-115.78 |
| 14 | 51 | 0.0% | $-2.31 | 0.00 | $-118.03 |
| 15 | 64 | 0.0% | $-2.77 | 0.00 | $-177.10 |

## Risultato per motivo di uscita

| exit_reason | trade_count | win_rate | expectancy | profit_factor | total_net_pnl |
|---|---|---|---|---|---|
| take_profit | 149 | 0.0% | $-0.38 | 0.00 | $-57.19 |
| stop_loss | 284 | 0.0% | $-3.52 | 0.00 | $-1000.79 |
| max_holding | 129 | 0.0% | $-2.11 | 0.00 | $-272.28 |

## File di dettaglio

I risultati giornalieri e l'elenco completo dei trade sono disponibili nei file CSV adiacenti.

## Interpretazione

Con $1.000 per trade e target dello 0,20%, il guadagno lordo massimo è circa $2. Le commissioni di andata e ritorno sono già $2, prima di spread e slippage: di conseguenza anche le uscite a take profit risultano negative nette.

Questo report descrive una baseline su un solo mese. Non costituisce validazione dell'edge e non è stato usato per ottimizzare i parametri.
