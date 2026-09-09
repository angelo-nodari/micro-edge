# MicroEdge — Ipotesi candidata V1

## Stato

**FROZEN — pronta per validazione holdout**

Questa specifica è stata definita usando esclusivamente il dataset di ricerca
NVDA di luglio 2026. Non può essere modificata dopo l'apertura dei risultati del
periodo holdout.

## 1. Domanda di ricerca

> Una strategia long di mean reversion, attiva nelle ore 11–12 di New York e in
> condizioni di volatilità intraday normale, mantiene expectancy positiva dopo
> spread, slippage e costi Alpaca Personal API su dati SIP non usati per
> formulare l'ipotesi?

## 2. Separazione dei dati

### Research set

- Strumento: NVDA.
- Feed: Alpaca SIP storico.
- Periodo: 1–31 luglio 2026.
- Utilizzo: scoperta descrittiva del sottogruppo candidato.

### Holdout set

- Strumento: NVDA.
- Feed: Alpaca SIP storico.
- Periodo: 1–30 giugno 2026.
- Stato al congelamento: non analizzato.
- Utilizzo consentito: una sola valutazione della presente ipotesi V1.

Giugno è precedente a luglio nel calendario, ma resta un holdout valido perché
non è stato consultato durante la formulazione della regola. Una successiva
validazione walk-forward sarà comunque necessaria prima del paper trading.

## 3. Dati e finestra operativa

- Barre OHLCV: 1 minuto.
- Timezone: `America/New_York`.
- Contesto precaricato: 09:30–09:34.
- Prima valutazione possibile del segnale: 09:35.
- Ultima chiusura forzata: 15:55.
- Dati aggiustati: `adjustment=all`.

## 4. Segnale baseline

Alla chiusura della candela `t`:

```text
drop_5m = close[t] / close[t-5] - 1
```

Il segnale long di base è vero quando:

```text
drop_5m <= -0,20%
```

## 5. Feature di volatilità congelata

La volatilità al momento del segnale è calcolata separatamente per ogni
sessione:

```text
return_1m[t] = close[t] / close[t-1] - 1

volatility_bps[t] =
    standard_deviation_sample(
        ultimi 30 return_1m disponibili, incluso t
    ) × 10.000
```

Regole di calcolo:

- finestra rolling: 30 osservazioni;
- minimo iniziale: 5 osservazioni;
- nessun rendimento di una candela futura può essere usato;
- la feature è disponibile alla chiusura della candela del segnale.

Soglie congelate dal research set di luglio:

| Regime | Definizione |
|---|---:|
| Bassa | `volatility_bps <= 8,6827624102` |
| Normale | `8,6827624102 < volatility_bps <= 13,7273479688` |
| Alta | `volatility_bps > 13,7273479688` |

Solo il regime **Normale** è ammesso dalla candidata V1. Le soglie non devono
essere ricalcolate sul dataset di giugno.

## 6. Filtro orario congelato

Il filtro usa l'ora del timestamp di entrata, in ora di New York.

Sono ammesse soltanto entrate con:

```text
entry_hour in {11, 12}
```

Intervallo equivalente:

```text
11:00:00 <= entry_time <= 12:59:59
```

Il segnale viene calcolato alla chiusura di `t` e l'entrata avviene
all'apertura della candela successiva. Un segnale delle 10:59 che entra alle
11:00 è quindi ammesso.

## 7. Regola completa di entrata

```text
IF drop_5m <= -0,20%
AND 8,6827624102 < volatility_bps <= 13,7273479688
AND entry_hour IN {11, 12}
AND nessuna posizione è aperta
THEN entra long all'apertura della candela successiva
```

Nessuna delle condizioni può essere modificata durante la validazione.

## 8. Dimensionamento

- Capitale virtuale iniziale: 10.000 USD.
- Capitale nominale per trade: 1.000 USD.
- Quantità: numero intero di azioni acquistabili con il capitale nominale al
  prezzo eseguito.
- Nessuna leva.
- Nessun reinvestimento dei profitti.
- Massimo una posizione aperta.

## 9. Uscita

Soglie rispetto al prezzo di entrata eseguito:

- take profit: +0,20%;
- stop loss: -0,15%;
- holding massimo: 5 candele, inclusa la candela di entrata;
- chiusura forzata entro le 15:55.

Se target e stop sono toccati nella stessa candela, viene assunto lo stop.

## 10. Esecuzione e broker

Profilo: `alpaca_personal_api`.

- Spread totale: 2 bp, quindi 1 bp sfavorevole per lato.
- Slippage: 1 bp sfavorevole per lato.
- Commissione broker: 0 USD.
- SEC fee sulla vendita: controvalore × 0,00002060, arrotondato per eccesso al
  centesimo.
- FINRA TAF sulla vendita: 0,000195 USD per azione, arrotondato per eccesso al
  centesimo, massimo 9,79 USD per ordine.
- CAT fee azionaria: 0 USD secondo il profilo corrente.

La validazione primaria usa esclusivamente queste condizioni. Gli stress test
con slippage diverso sono riportati separatamente e non sostituiscono il
risultato primario.

## 11. Metriche primarie e secondarie

### Metrica primaria

- expectancy netta per trade.

### Metriche secondarie

- numero di trade;
- win rate netto;
- profit factor;
- P&L netto totale;
- max drawdown;
- distribuzione del P&L per giornata;
- risultati per motivo di uscita;
- sensibilità a slippage 0, 1, 2 e 5 bp.

## 12. Criterio di decisione predefinito

### REJECT

La candidata è respinta se sul holdout:

```text
expectancy netta <= 0
OR profit factor <= 1
```

### INCONCLUSIVE

La candidata è inconclusiva se:

- produce meno di 30 trade; oppure
- expectancy e profit factor sono positivi, ma l'intervallo di confidenza al
  95% ottenuto con bootstrap per giornata include zero.

### PRELIMINARY PASS

La candidata supera preliminarmente il test soltanto se:

```text
trade_count >= 30
AND expectancy netta > 0
AND profit factor > 1
AND limite inferiore CI 95% expectancy > 0
```

Un preliminary pass non autorizza paper o live trading. Richiede altri periodi
out-of-sample e stress test.

## 13. Protocollo anti-overfitting

Dopo aver osservato giugno 2026 è vietato, per la V1:

- modificare le soglie di volatilità;
- aggiungere o rimuovere ore;
- cambiare drop, target, stop o holding;
- cambiare size, spread, slippage o profilo broker;
- escludere giornate o trade dopo averne visto il risultato;
- ricalcolare i tercili sul holdout.

Se la V1 viene respinta o è inconclusiva, ogni modifica genera una nuova ipotesi
versionata e richiede un nuovo dataset holdout.

## 14. Prossima azione autorizzata

Scaricare, validare e versionare NVDA SIP dal 1 al 30 giugno 2026. Prima del
download non devono essere introdotte altre modifiche alla candidata V1.
