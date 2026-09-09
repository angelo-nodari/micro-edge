# MicroEdge — Diagnostica dell'edge NVDA

## Metodo

La strategia e i suoi parametri restano invariati. Il confronto senza costi usa spread, slippage e commissioni pari a zero. La volatilità è calcolata causalmente sui rendimenti a un minuto disponibili fino al segnale.

I regimi sono tercili descrittivi calcolati su questo stesso mese: non sono regole operative e non devono essere applicati out-of-sample senza una validazione separata.

## Confronto complessivo

| Scenario | Trade | Win rate | Expectancy | Profit factor | P&L |
|---|---:|---:|---:|---:|---:|
| Senza costi | 539 | 45.8% | $0.04 | 1.06 | $19.40 |
| Alpaca + esecuzione | 562 | 35.8% | $-0.40 | 0.54 | $-224.88 |

## Scomposizione dei costi sul percorso Alpaca

- P&L lordo: $-4.85
- Spread: $100.70
- Slippage: $100.70
- Commissioni broker: $0.00
- Fee regolamentari: $18.63
- P&L netto: $-224.88

## Soglie descrittive di volatilità

- Bassa: ≤ 8.68 bp
- Normale: ≤ 13.73 bp
- Alta: > 13.73 bp

## Regimi — scenario senza costi

| volatility_regime | trade_count | win_rate | expectancy | profit_factor | total_net_pnl |
|---|---|---|---|---|---|
| high | 180 | 37.8% | $-0.17 | 0.80 | $-30.01 |
| low | 180 | 48.3% | $0.04 | 1.07 | $6.41 |
| normal | 179 | 51.4% | $0.24 | 1.41 | $43.01 |

## Regimi — scenario Alpaca

| volatility_regime | trade_count | win_rate | expectancy | profit_factor | total_net_pnl |
|---|---|---|---|---|---|
| high | 187 | 29.9% | $-0.62 | 0.42 | $-115.56 |
| low | 188 | 35.1% | $-0.36 | 0.49 | $-68.52 |
| normal | 187 | 42.2% | $-0.22 | 0.73 | $-40.81 |

Le combinazioni complete ora × regime sono disponibili nei CSV adiacenti. Nessun segmento è stato selezionato o trasformato in una regola.
