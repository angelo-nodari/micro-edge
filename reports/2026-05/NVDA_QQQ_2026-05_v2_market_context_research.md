# MicroEdge — Ricerca V2 sul contesto QQQ

**Analisi descrittiva sul research set di maggio 2026; non è una validazione.**

## Metodo

Il rendimento QQQ a cinque minuti è misurato allo stesso timestamp del segnale NVDA. I tre regimi sono stati fissati prima dei risultati e sono simulati separatamente con parametri e costi baseline invariati.

- SHA-256 NVDA: `fb700deb65e3370970455b93147c2714a8e211a2e1fdb529243768f5e7cb0f8a`
- SHA-256 QQQ: `15bd449a3be8ff80658c9714f7861171b34cdebdb7cb1f7ef5c4a1b595fd0aae`
- Barre/sessioni allineate: 7720 / 20

## Risultati per regime QQQ

| Regime | Intervallo | Trade | Win rate | Expectancy | Profit factor | P&L netto |
|---|---:|---:|---:|---:|---:|---:|
| falling | ≤ -0.10% | 271 | 35.1% | $-0.4583 | 0.514 | $-124.21 |
| stable | > -0.10% and < +0.10% | 335 | 36.4% | $-0.4276 | 0.511 | $-143.26 |
| rising | ≥ +0.10% | 18 | 33.3% | $-0.5091 | 0.506 | $-9.16 |

## Screening

Nessun regime supera lo screening minimo predefinito.

Lo screening non dimostra un edge. Un’eventuale candidata deve essere congelata prima di accedere al holdout di aprile.
