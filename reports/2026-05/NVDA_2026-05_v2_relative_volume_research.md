# MicroEdge — Ricerca V2 sul volume relativo

**Analisi descrittiva sul research set di maggio 2026; non è una validazione.**

## Metodo

La feature confronta il volume corrente con la mediana delle 30 barre precedenti della stessa sessione. Le fasce sono state definite prima di osservare i risultati. Ogni fascia è simulata separatamente con i parametri baseline e i costi Alpaca.

- Dataset SHA-256: `fb700deb65e3370970455b93147c2714a8e211a2e1fdb529243768f5e7cb0f8a`
- Barre/sessioni: 7720 / 20

## Risultati per fascia

| Fascia | Intervallo | Trade | Win rate | Expectancy | Profit factor | P&L netto |
|---|---:|---:|---:|---:|---:|---:|
| low | < 0.75 | 134 | 32.1% | $-0.5979 | 0.403 | $-80.12 |
| normal | 0.75–<1.25 | 334 | 39.2% | $-0.3166 | 0.615 | $-105.74 |
| high | 1.25–<2.00 | 189 | 36.5% | $-0.4456 | 0.505 | $-84.21 |
| very_high | ≥ 2.00 | 78 | 43.6% | $-0.2267 | 0.706 | $-17.68 |

## Screening

Nessuna fascia supera lo screening minimo predefinito.

Lo screening non dimostra un edge. Un’eventuale regola deve essere congelata prima di accedere al nuovo holdout di aprile.
