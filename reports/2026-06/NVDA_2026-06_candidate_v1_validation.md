# MicroEdge — Validazione holdout candidata V1

**Decisione: REJECT**

## Integrità

- SHA-256 ipotesi: `9fff8f6936d732a5dead49c761339d2d3bb938a1e51dc4ceb09a037fc80275be`
- SHA-256 dataset: `89c9d23cba623dd55ed91d871f3fe99579f9c8df94ff3516ec0b627442da414f`
- Periodo: 2026-06-01T09:30:00-04:00 — 2026-06-30T15:55:00-04:00
- Barre/sessioni: 8106 / 21

## Regola congelata

- Volatilità normale: > 8.6827624102 bp e ≤ 13.7273479688 bp
- Ora di ingresso: 11 o 12 (New York)
- Calo a 5 minuti: ≤ -0,20%
- TP +0,20%; SL -0,15%; holding massimo 5 barre
- Alpaca Personal API; spread 2 bp; slippage 1 bp per lato

## Risultato primario

- Trade: 60
- Win rate: 40.0%
- Expectancy netta: $-0.3360
- Profit factor: 0.598
- P&L netto: $-20.16
- Max drawdown: $20.40 (0.20%)

## Sensibilità allo slippage

| Slippage/lato (bp) | Trade | Expectancy | Profit factor | P&L netto |
|---:|---:|---:|---:|---:|
| 0 | 60 | $-0.2289 | 0.696 | $-13.74 |
| 1 | 60 | $-0.3360 | 0.598 | $-20.16 |
| 2 | 64 | $-0.4309 | 0.514 | $-27.58 |
| 5 | 68 | $-1.0524 | 0.156 | $-71.57 |

## Nota decisionale

Il risultato usa il holdout una sola volta e senza ricalibrare soglie o parametri. L’intervallo di confidenza per giornata appartiene allo Step 4 e non è stato ancora calcolato.
