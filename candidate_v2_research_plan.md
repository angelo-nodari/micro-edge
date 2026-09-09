# MicroEdge — Piano di ricerca candidata V2

## Stato

**DRAFT DI RICERCA — non è una strategia congelata**

La candidata V1 è stata respinta sul holdout di giugno 2026. Questo documento
non modifica la V1 e non usa giugno per scegliere nuovi parametri.

## Idea minima

Verificare se un calo intraday seguito da volume anomalo rappresenta una
capitolazione temporanea con maggiore probabilità di rimbalzo.

La V2 introduce una sola feature nuova: il **volume relativo causale**. Target,
stop, holding, size e costi rimangono inizialmente quelli della baseline, così
da misurare separatamente il contributo del volume.

## Feature proposta

Alla chiusura della candela `t`:

```text
relative_volume_30[t] =
    volume[t] / median(volume[t-30 : t-1])
```

Regole:

- la mediana usa soltanto le 30 candele precedenti della stessa sessione;
- la candela corrente non entra nel denominatore;
- minimo 10 osservazioni precedenti;
- nessun dato futuro;
- la feature è disponibile alla chiusura della candela del segnale.

## Separazione dei dati

- **Research set:** NVDA SIP, maggio 2026.
- **Holdout V2:** NVDA SIP, aprile 2026, da non analizzare prima del
  congelamento della candidata.
- **Giugno 2026:** consumato dalla V1; escluso dalla progettazione e dalla
  validazione V2.
- **Luglio 2026:** già usato per la scoperta V1; può essere citato come
  contesto, ma non come nuova validazione.

## Primo esperimento autorizzabile

1. Scaricare e versionare soltanto maggio 2026.
2. Implementare e testare `relative_volume_30` senza cambiare la strategia.
3. Produrre un report descrittivo per fasce di volume relativo.
4. Verificare se esiste un segmento con expectancy positiva dopo costi e un
   numero di trade sufficiente.
5. Solo in caso favorevole, scrivere e congelare `candidate_hypothesis_v2.md`.
6. Scaricare aprile e usarlo una sola volta dopo il congelamento.

## Vincoli anti-overfitting

- una sola nuova feature in questo ciclo;
- nessun Machine Learning;
- nessuna modifica basata sui risultati di giugno;
- nessun accesso ai risultati di aprile prima del congelamento;
- nessun paper trading se il nuovo holdout non supera i criteri predefiniti;
- se maggio non mostra un candidato credibile, la V2 non viene forzata.

## Prossimo passo

Con approvazione esplicita: scaricare NVDA SIP di maggio 2026 e applicare i
controlli di qualità già esistenti. Nessuna analisi di aprile in questa fase.
