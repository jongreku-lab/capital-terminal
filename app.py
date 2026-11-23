from google import genai
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

# --- KONFIGURIMI I FAQES ---
st.set_page_config(
    page_title="Terminali Privat i Kapitalit", layout="wide"
)

# Stili i Erret (Dark Wall-Street Theme)
st.markdown(
    """
    <style>
    .stApp { background-color: #0b0e14; color: #e6edf3; }
    div[data-testid="stMetric"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        padding: 15px;
        border-radius: 10px;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# --- TITULLI KRYESOR ---
st.title("Terminali Privat i Kapitalit")
st.caption("Analiza e Portofolit ne Kohe Reale | Ndertuar Vecanerisht per Ditelindjen Tende")

# --- MENUJA ANESORE: CILESIMET ---
st.sidebar.header("Cilesimet e Terminalit")
tickers_input = st.sidebar.text_input(
    "Aksionet ne Ndjekje (te ndara me presje)", "NVDA, AAPL, MSFT, SPY, BTC-USD"
)
tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

timeframe = st.sidebar.selectbox(
    "Periudha e Grafikut", ["1mo", "3mo", "6mo", "1y", "5y"], index=2
)

default_key = st.secrets.get("GEMINI_API_KEY", "")
gemini_key = st.sidebar.text_input(
    "Celesi API Gemini", value=default_key, type="password"
)

# --- SEKSIONET KRYESORE (TABS) ---
tab1, tab2 = st.tabs(
    ["Terminali i Tregut & AI", "Portofoli & Fitimi/Humbja"]
)

# ==========================================
# SEKSIONI 1: TREGU NE KOHE REALE & ANALISTI AI
# ==========================================
with tab1:
  st.subheader("Pulsi i Tregut ne Kohe Reale")
  if tickers:
    cols = st.columns(len(tickers))
    for idx, ticker in enumerate(tickers):
      try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="5d")
        if len(hist) >= 2:
          current = hist["Close"].iloc[-1]
          prev = hist["Close"].iloc[-2]
          change_pct = ((current - prev) / prev) * 100
          cols[idx].metric(
              label=ticker,
              value=f"${current:,.2f}",
              delta=f"{change_pct:+.2f}%",
          )
        else:
          cols[idx].metric(label=ticker, value="N/A")
      except Exception:
        cols[idx].metric(label=ticker, value="Gabim")

  st.divider()

  col_chart, col_ai = st.columns([1.6, 1])

  with col_chart:
    selected_ticker = st.selectbox("Zgjidh Aksionin per Analize", tickers)
    df = yf.Ticker(selected_ticker).history(period=timeframe)

    if not df.empty:
      df["SMA20"] = df["Close"].rolling(window=20).mean()
      fig = go.Figure()
      fig.add_trace(
          go.Candlestick(
              x=df.index,
              open=df["Open"],
              high=df["High"],
              low=df["Low"],
              close=df["Close"],
              name="Cmimi",
          )
      )
      fig.add_trace(
          go.Scatter(
              x=df.index,
              y=df["SMA20"],
              line=dict(color="#f0b90b", width=1.5),
              name="Mesatarja Levizese 20-Ditore",
          )
      )
      fig.update_layout(
          template="plotly_dark",
          paper_bgcolor="#0b0e14",
          plot_bgcolor="#161b22",
          xaxis_rangeslider_visible=False,
          height=450,
          margin=dict(l=10, r=10, t=30, b=10),
      )
      st.plotly_chart(fig, use_container_width=True)

  with col_ai:
    st.subheader("Permbledhja Ekzekutive AI")
    st.write(f"Analiza e shpejte e lajmeve dhe levizjeve per **{selected_ticker}**:")

    if st.button(f"Gjenero Raportin AI per {selected_ticker}", type="primary"):
      if not gemini_key:
        st.warning(
            "Vendos celesin API Gemini ne menune anesore per te aktivizuar raportet AI."
        )
      else:
        with st.spinner("Duke analizuar te dhenat e tregut dhe lajmet..."):
          try:
            news_items = yf.Ticker(selected_ticker).news[:5]
            headlines = "\n".join([
                f"- {n.get('content', {}).get('title', n.get('title', ''))}"
                for n in news_items
            ])
            client = genai.Client(api_key=gemini_key)
            prompt = (
                "Ti je nje analist i larte financiar i Wall Street qe informon nje investitor privat per"
                f" {selected_ticker}. Bazuar ne keto tituj lajmesh te fundit:\n{headlines}\n\n"
                "Jep nje permbledhje ekzekutive te qarte ne shqip me 3 pika kryesore: "
                "1) Faktori Kryesor (Katalizatori), 2) Skenari Pozitiv (Bull Case), "
                "3) Rreziku qe Duhet Ndjekur. Mbaje te shkurter dhe praktik."
            )
            response = client.models.generate_content(
                model="gemini-2.5-flash", contents=prompt
            )
            st.success("Raporti eshte gati")
            st.markdown(response.text)
          except Exception as e:
            st.error(f"Nuk u arrit te gjenerohej raporti: {e}")

    st.markdown("**Lajmet e Fundit**")
    try:
      for item in yf.Ticker(selected_ticker).news[:4]:
        title = item.get("content", {}).get("title", item.get("title", ""))
        if title:
          st.caption(f"- {title}")
    except Exception:
      st.caption("Nuk u gjeten lajme te fundit.")

# ==========================================
# SEKSIONI 2: LLOGARITESI I PORTOFOLIT & FITIMIT
# ==========================================
with tab2:
  st.subheader("Menaxhimi Interaktiv i Portofolit")
  st.caption(
      "Ndrysho tabelen me poshte me sasine e aksioneve dhe cmimin mesatar te blerjes per te llogaritur fitimin ose humbjen ne kohe reale."
  )

  if "portfolio_df" not in st.session_state:
    st.session_state.portfolio_df = pd.DataFrame({
        "Aksioni": ["NVDA", "AAPL", "MSFT", "SPY"],
        "Sasia": [15.0, 25.0, 10.0, 12.0],
        "Cmimi Mesatar i Blerjes ($)": [95.00, 175.00, 380.00, 490.00],
    })

  edited_df = st.data_editor(
      st.session_state.portfolio_df,
      num_rows="dynamic",
      use_container_width=True,
  )

  if not edited_df.empty:
    results = []
    total_value = 0.0
    total_cost = 0.0

    for _, row in edited_df.iterrows():
      sym = str(row["Aksioni"]).strip().upper()
      shares = float(row["Sasia"] or 0)
      buy_price = float(row["Cmimi Mesatar i Blerjes ($)"] or 0)

      if sym and shares > 0:
        try:
          hist = yf.Ticker(sym).history(period="2d")
          live_price = float(hist["Close"].iloc[-1]) if not hist.empty else 0.0
        except Exception:
          live_price = 0.0

        current_val = shares * live_price
        cost_basis = shares * buy_price
        pnl = current_val - cost_basis
        pnl_pct = ((pnl / cost_basis) * 100) if cost_basis > 0 else 0.0

        total_value += current_val
        total_cost += cost_basis

        results.append({
            "Aksioni": sym,
            "Sasia": shares,
            "Cmimi Aktual": f"${live_price:,.2f}",
            "Vlera e Tregut": current_val,
            "Fitimi / Humbja ($)": pnl,
            "Kthimi (%)": f"{pnl_pct:+.2f}%",
        })

    if results:
      total_pnl = total_value - total_cost
      total_pnl_pct = ((total_pnl / total_cost) * 100) if total_cost > 0 else 0.0

      # Kartat Permbledhese
      m1, m2, m3 = st.columns(3)
      m1.metric("Vlera Totale e Portofolit", f"${total_value:,.2f}")
      m2.metric("Kostoja Totale e Investuar", f"${total_cost:,.2f}")
      m3.metric(
          "Fitimi / Humbja Totale",
          f"${total_pnl:+,.2f}",
          delta=f"{total_pnl_pct:+.2f}%",
      )

      st.divider()

      # Tabela e Detajuar + Grafiku Rrethor
      col_tbl, col_pie = st.columns([1.4, 1])
      res_df = pd.DataFrame(results)

      with col_tbl:
        st.markdown("**Detajet e Pozicioneve**")
        display_df = res_df.copy()
        display_df["Vlera e Tregut"] = display_df["Vlera e Tregut"].map(
            "${:,.2f}".format
        )
        display_df["Fitimi / Humbja ($)"] = display_df["Fitimi / Humbja ($)"].map(
            "${:+,.2f}".format
        )
        st.dataframe(display_df, use_container_width=True, hide_index=True)

      with col_pie:
        st.markdown("**Shperndarja e Aseteve**")
        fig_pie = px.pie(
            res_df,
            values="Vlera e Tregut",
            names="Aksioni",
            hole=0.45,
            template="plotly_dark",
        )
        fig_pie.update_layout(
            paper_bgcolor="#0b0e14",
            margin=dict(l=10, r=10, t=10, b=10),
            height=300,
        )
        st.plotly_chart(fig_pie, use_container_width=True)
