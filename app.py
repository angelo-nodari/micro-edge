"""Local Streamlit interface for the MicroEdge baseline simulator."""

from __future__ import annotations

import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from alpaca_data import AlpacaDataError, fetch_historical_bars
from broker_costs import BROKER_LABELS
from research_status import load_research_status
from simulator import calculate_performance, generate_synthetic_data, simulate_strategy


st.set_page_config(page_title="MicroEdge Simulator", layout="wide")


def money(value: float) -> str:
    return f"${value:,.2f}"


def ratio(value: float) -> str:
    return "∞" if math.isinf(value) else f"{value:.2f}"


def run_simulation(parameters: dict[str, object]):
    if parameters["data_source"] == "Alpaca":
        api_key = str(st.secrets.get("ALPACA_API_KEY", ""))
        secret_key = str(st.secrets.get("ALPACA_SECRET_KEY", ""))
        if not api_key or not secret_key:
            raise ValueError(
                "Inserisci le credenziali Alpaca in .streamlit/secrets.toml."
            )
        data = fetch_historical_bars(
            api_key=api_key,
            secret_key=secret_key,
            symbol=str(parameters["symbol"]),
            start=parameters["start_date"],
            end=parameters["end_date"],
            feed="sip",
        )
        if data.empty:
            raise ValueError("Alpaca non ha restituito barre nell'intervallo selezionato.")
    else:
        data = generate_synthetic_data(
            seed=int(parameters["seed"]),
            days=int(parameters["days"]),
        )
    trades = simulate_strategy(
        data,
        drop_threshold=float(parameters["drop_threshold_pct"]) / 100,
        take_profit=float(parameters["take_profit_pct"]) / 100,
        stop_loss=float(parameters["stop_loss_pct"]) / 100,
        max_holding_bars=int(parameters["max_holding_bars"]),
        capital_per_trade=float(parameters["capital_per_trade"]),
        spread_bps=float(parameters["spread_bps"]),
        slippage_bps=float(parameters["slippage_bps"]),
        broker_profile=str(parameters["broker_profile"]),
        commission_per_order=float(parameters["commission_per_order"]),
    )
    metrics, equity = calculate_performance(trades)
    return data, trades, metrics, equity


st.title("MicroEdge Simulator")
st.caption("Baseline mean reversion intraday")

research_status = load_research_status()
st.subheader("Stato della ricerca")
if research_status["verdict"] == "NO_EDGE_DEMONSTRATED":
    st.error(
        "MVP concluso: nessun edge statistico è stato dimostrato dopo costi. "
        "La strategia non è pronta per paper trading o capitale reale."
    )
elif research_status["verdict"] == "RESEARCH_INCOMPLETE":
    st.warning("La ricerca MVP non è ancora completa.")
else:
    st.warning("Esiste un candidato da riesaminare prima di qualsiasi avanzamento.")

if research_status["experiments"]:
    research_table = pd.DataFrame(research_status["experiments"]).rename(
        columns={
            "esperimento": "Esperimento",
            "periodo": "Periodo",
            "segmento": "Configurazione migliore",
            "trade": "Trade",
            "expectancy": "Expectancy netta",
            "profit_factor": "Profit factor",
            "esito": "Esito",
        }
    )
    with st.expander("Vedi i risultati degli esperimenti", expanded=True):
        st.dataframe(
            research_table,
            width="stretch",
            hide_index=True,
            column_config={
                "Expectancy netta": st.column_config.NumberColumn(format="$%.3f"),
                "Profit factor": st.column_config.NumberColumn(format="%.3f"),
            },
        )
        st.caption(
            "I valori mostrati provengono dai report versionati. Il simulatore "
            "sottostante resta disponibile per esperimenti, non per decisioni operative."
        )

st.divider()
st.subheader("Simulatore esplorativo")

data_source = st.radio(
    "Sorgente dati",
    options=["Sintetici", "Alpaca"],
    horizontal=True,
)
broker_label = st.selectbox(
    "Broker simulato",
    options=list(BROKER_LABELS.values()),
    index=0,
)
broker_profile = next(
    profile for profile, label in BROKER_LABELS.items() if label == broker_label
)

if data_source == "Alpaca":
    st.info(
        "Uso il feed SIP consolidato per dati storici conclusi. Il piano Basic "
        "può rifiutare intervalli che includono gli ultimi 15 minuti."
    )
else:
    st.warning(
        "I dati sono sintetici e servono solo a verificare il simulatore. "
        "I risultati non dimostrano l'esistenza di un edge finanziario."
    )

with st.form("simulation_parameters"):
    st.subheader("Parametri")
    source_row = st.columns(4)
    if data_source == "Alpaca":
        symbol = source_row[0].text_input("Simbolo", value="NVDA", max_chars=12)
        start_date = source_row[1].date_input(
            "Data iniziale", value=pd.Timestamp("2026-08-20").date()
        )
        end_date = source_row[2].date_input(
            "Data finale", value=pd.Timestamp("2026-08-20").date()
        )
        source_row[3].text_input("Feed", value="SIP storico", disabled=True)
        seed = 42
        days = 20
    else:
        seed = source_row[0].number_input("Seed", min_value=0, value=42, step=1)
        days = source_row[1].number_input(
            "Giornate", min_value=1, max_value=250, value=20
        )
        symbol = "NVDA"
        start_date = pd.Timestamp("2026-08-20").date()
        end_date = pd.Timestamp("2026-08-20").date()

    strategy_row = st.columns(4)
    drop_threshold_pct = strategy_row[0].number_input(
        "Calo in 5 min (%)", min_value=0.01, value=0.20, step=0.01, format="%.2f"
    )
    take_profit_pct = strategy_row[1].number_input(
        "Take profit (%)", min_value=0.01, value=0.20, step=0.01, format="%.2f"
    )
    stop_loss_pct = strategy_row[2].number_input(
        "Stop loss (%)", min_value=0.01, value=0.15, step=0.01, format="%.2f"
    )
    max_holding_bars = strategy_row[3].number_input(
        "Durata max (min)", min_value=1, max_value=60, value=5
    )

    cost_row = st.columns(4)
    capital_per_trade = cost_row[0].number_input(
        "Capitale per trade ($)", min_value=1.0, value=1_000.0, step=100.0
    )
    spread_bps = cost_row[1].number_input(
        "Spread totale (bp)", min_value=0.0, value=2.0, step=0.5
    )
    slippage_bps = cost_row[2].number_input(
        "Slippage per lato (bp)", min_value=0.0, value=1.0, step=0.5
    )
    if broker_profile == "custom_flat":
        commission_per_order = cost_row[3].number_input(
            "Commissione per ordine ($)", min_value=0.0, value=1.0, step=0.25
        )
    else:
        commission_per_order = cost_row[3].number_input(
            "Commissione broker ($)", min_value=0.0, value=0.0, disabled=True
        )

    submitted = st.form_submit_button("Esegui simulazione", type="primary")

parameters = {
    "data_source": data_source,
    "symbol": symbol,
    "start_date": start_date,
    "end_date": end_date,
    "seed": seed,
    "days": days,
    "drop_threshold_pct": drop_threshold_pct,
    "take_profit_pct": take_profit_pct,
    "stop_loss_pct": stop_loss_pct,
    "max_holding_bars": max_holding_bars,
    "capital_per_trade": capital_per_trade,
    "spread_bps": spread_bps,
    "slippage_bps": slippage_bps,
    "broker_profile": broker_profile,
    "commission_per_order": commission_per_order,
}

if "simulation_result" not in st.session_state:
    st.session_state.simulation_result = run_simulation(parameters)
    st.session_state.simulation_source = data_source
    st.session_state.simulation_symbol = symbol
    st.session_state.simulation_broker = broker_profile
elif "simulation_source" not in st.session_state:
    # Compatibility with sessions created before data-source selection existed.
    st.session_state.simulation_source = "Sintetici"
    st.session_state.simulation_symbol = "NVDA"
    st.session_state.simulation_broker = "custom_flat"

if submitted:
    try:
        with st.spinner("Caricamento dati e simulazione..."):
            st.session_state.simulation_result = run_simulation(parameters)
        st.session_state.simulation_source = data_source
        st.session_state.simulation_symbol = symbol
        st.session_state.simulation_broker = broker_profile
    except (AlpacaDataError, ValueError) as exc:
        st.error(str(exc))
        st.stop()

if (
    st.session_state.get("simulation_source") != data_source
    or st.session_state.get("simulation_broker") != broker_profile
):
    st.info("Premi “Esegui simulazione” per applicare sorgente e broker selezionati.")
    st.stop()

data, trades, metrics, equity = st.session_state.simulation_result
display_symbol = st.session_state.get("simulation_symbol", "NVDA")
display_broker = BROKER_LABELS.get(
    st.session_state.get("simulation_broker", "custom_flat"),
    st.session_state.get("simulation_broker", "custom_flat"),
)

st.subheader("Risultati")
st.caption(
    f"{display_symbol} · {len(data):,} barre · "
    f"{data['session'].nunique()} sessioni · sorgente {data_source} · broker {display_broker}"
)
metric_columns = st.columns(6)
metric_columns[0].metric("Trade", f"{metrics['trade_count']}")
metric_columns[1].metric("Win rate netto", f"{metrics['win_rate']:.1%}")
metric_columns[2].metric("Expectancy", money(metrics["expectancy"]))
metric_columns[3].metric("Profit factor", ratio(metrics["profit_factor"]))
metric_columns[4].metric("Max drawdown", money(metrics["max_drawdown"]))
metric_columns[5].metric("P&L netto", money(metrics["total_net_pnl"]))

if metrics["trade_count"] and metrics["win_rate"] == 0:
    st.info(
        "Con questi parametri i costi rendono negativi anche i trade che "
        "raggiungono il target. Prova a modificare size, commissioni o target."
    )

st.subheader("Grafici")
selected_session = st.selectbox(
    "Giornata visualizzata",
    options=data["session"].drop_duplicates().tolist(),
    format_func=lambda value: value.strftime("%d/%m/%Y"),
)

day_data = data[data["session"] == selected_session]
day_trades = trades[
    trades["entry_time"].dt.date == selected_session
] if not trades.empty else trades

price_figure = go.Figure()
price_figure.add_trace(
    go.Scatter(
        x=day_data["timestamp"],
        y=day_data["close"],
        mode="lines",
        name="Prezzo",
    )
)
if not day_trades.empty:
    price_figure.add_trace(
        go.Scatter(
            x=day_trades["entry_time"],
            y=day_trades["entry_mid"],
            mode="markers",
            marker={"symbol": "triangle-up", "size": 10},
            name="Entrata",
        )
    )
    price_figure.add_trace(
        go.Scatter(
            x=day_trades["exit_time"],
            y=day_trades["exit_mid"],
            mode="markers",
            marker={"symbol": "triangle-down", "size": 10},
            text=day_trades["exit_reason"],
            hovertemplate="%{x}<br>%{y:.2f}<br>%{text}<extra>Uscita</extra>",
            name="Uscita",
        )
    )
price_figure.update_layout(
    title=f"{display_symbol}: prezzo con entrate e uscite",
    xaxis_title="Ora di New York",
    yaxis_title="Prezzo ($)",
    height=430,
    margin={"l": 20, "r": 20, "t": 50, "b": 20},
)
st.plotly_chart(price_figure, width="stretch")

if not equity.empty:
    equity_figure = go.Figure(
        go.Scatter(
            x=equity["trade_number"],
            y=equity["equity"],
            mode="lines",
            name="Capitale",
        )
    )
    equity_figure.update_layout(
        title="Equity curve",
        xaxis_title="Numero trade",
        yaxis_title="Capitale ($)",
        height=350,
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
    )
    st.plotly_chart(equity_figure, width="stretch")
else:
    st.info("Nessuna operazione generata con i parametri selezionati.")

st.subheader("Operazioni")
if trades.empty:
    st.info("Nessuna operazione da mostrare.")
else:
    trade_table = trades[
        [
            "entry_time",
            "exit_time",
            "entry_mid",
            "entry_executed",
            "exit_mid",
            "exit_executed",
            "quantity",
            "exit_reason",
            "broker_profile",
            "gross_pnl",
            "spread_cost",
            "slippage_cost",
            "broker_commission",
            "sec_fee",
            "finra_taf",
            "cat_fee",
            "total_broker_fees",
            "net_pnl",
        ]
    ].copy()
    trade_table = trade_table.rename(
        columns={
            "entry_time": "Entrata",
            "exit_time": "Uscita",
            "entry_mid": "Prezzo teorico entrata",
            "entry_executed": "Prezzo eseguito entrata",
            "exit_mid": "Prezzo teorico uscita",
            "exit_executed": "Prezzo eseguito uscita",
            "quantity": "Quantità",
            "exit_reason": "Motivo uscita",
            "broker_profile": "Profilo broker",
            "gross_pnl": "P&L lordo",
            "spread_cost": "Costo spread",
            "slippage_cost": "Costo slippage",
            "broker_commission": "Commissioni broker",
            "sec_fee": "SEC fee",
            "finra_taf": "FINRA TAF",
            "cat_fee": "CAT fee",
            "total_broker_fees": "Fee broker totali",
            "net_pnl": "P&L netto",
        }
    )
    st.dataframe(
        trade_table,
        width="stretch",
        hide_index=True,
        column_config={
            "Prezzo teorico entrata": st.column_config.NumberColumn(format="$%.4f"),
            "Prezzo eseguito entrata": st.column_config.NumberColumn(format="$%.4f"),
            "Prezzo teorico uscita": st.column_config.NumberColumn(format="$%.4f"),
            "Prezzo eseguito uscita": st.column_config.NumberColumn(format="$%.4f"),
            "P&L lordo": st.column_config.NumberColumn(format="$%.2f"),
            "Costo spread": st.column_config.NumberColumn(format="$%.2f"),
            "Costo slippage": st.column_config.NumberColumn(format="$%.2f"),
            "Commissioni broker": st.column_config.NumberColumn(format="$%.2f"),
            "SEC fee": st.column_config.NumberColumn(format="$%.2f"),
            "FINRA TAF": st.column_config.NumberColumn(format="$%.2f"),
            "CAT fee": st.column_config.NumberColumn(format="$%.2f"),
            "Fee broker totali": st.column_config.NumberColumn(format="$%.2f"),
            "P&L netto": st.column_config.NumberColumn(format="$%.2f"),
        },
    )
