import streamlit as st
import pandas as pd
from supabase import create_client
import plotly.express as px
import plotly.graph_objects as go

# Configurações de Página
st.set_page_config(page_title="Data Insight - Gestão", layout="wide")

# --- INJEÇÃO DE ESTILO CSS (DARK PREMIUM) ---
st.markdown("""
<style>
    /* 1. Esconder o menu de desenvolvedor e o rodapé padrão do Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* 2. Estilizar os cartões de métricas (st.metric) para visual de dashboard */
    div[data-testid="stMetric"] {
        background-color: #1E1E24;
        border-left: 4px solid #00E676; /* Detalhe lateral verde neon */
        padding: 10px 15px;
        border-radius: 6px;
        box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.3);
    }

    /* Suavizar a cor do texto do título da métrica */
    div[data-testid="stMetricLabel"] {
        color: #A0A0A0 !important;
        font-size: 14px !important;
    }

    /* 3. Classes de texto customizadas para títulos */
    .title-glow {
        font-size: 42px;
        font-weight: 900;
        background: -webkit-linear-gradient(45deg, #00E676, #00B0FF);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
        padding-bottom: 0px;
    }
    
    .subtitle-glow {
        color: #888888;
        font-size: 16px;
        font-weight: 500;
        margin-top: -10px;
        margin-bottom: 30px;
    }
</style>
""", unsafe_allow_html=True)

# Conexão
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
except Exception as e:
    st.error(f"Erro de conexão: {e}")
    st.stop()

# --- FUNÇÕES DE APOIO ---


def get_banca_data():
    res = supabase.table("config_banca").select("*").limit(1).execute()
    return res.data[0] if res.data else {
        "banca_fixa": 1000.0,
        "banca_kelly_estatica": 1000.0,
        "banca_kelly_dinamica": 1000.0,
        "id": None
    }


def get_exposicao():
    res = supabase.table("historico_bets").select(
        "stake_kelly_dinamica_aplicada").eq("status", "Apostado").execute()
    return sum(item['stake_kelly_dinamica_aplicada'] for item in res.data) if res.data else 0.0


def get_historico_completo():
    res = supabase.table("historico_bets").select(
        "*").filter("status", "in", '("Green","Red","Void")').order("created_at").execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()


# --- SIDEBAR (CONFIGURAÇÕES E IMPORTAÇÃO) ---
with st.sidebar:
    st.markdown('<p style="font-size: 26px; font-weight: 800; text-align: center; color: white;">⚙️ RedScore<span style="color: #00E676;"><br>Analytics</span></p>', unsafe_allow_html=True)

    banca_info = get_banca_data()
    banca_real = banca_info.get('banca_kelly_dinamica', 1000.0)
    banca_id = banca_info['id']

    exposicao = get_exposicao()
    saldo_disponivel = banca_real - exposicao

    st.metric("Banca Real (Dinâmica)", f"R$ {banca_real:.2f}")
    st.metric("Saldo Disponível", f"R$ {saldo_disponivel:.2f}",
              delta=f"-{exposicao:.2f} em jogo", delta_color="inverse")

    st.caption(
        f"Banca Fixa Simulada: R$ {banca_info.get('banca_fixa', 1000.0):.2f}")
    st.caption(
        f"Banca Estática Simulada: R$ {banca_info.get('banca_kelly_estatica', 1000.0):.2f}")

    st.divider()
    perc_fixa = st.number_input("Stake Fixa (%)", 0.1, 10.0, 1.0, step=0.1)

    st.divider()
    st.subheader("📥 Importar Dados")
    uploaded_file = st.file_uploader(
        "Arraste o CSV de hoje", type="csv", label_visibility="collapsed")

    if uploaded_file:
        df_new = pd.read_csv(uploaded_file)
        colunas_csv = df_new.columns.tolist()

        if st.sidebar.button("🚀 Confirmar Carga", use_container_width=True):
            rows = []
            for _, r in df_new.iterrows():
                col_metodo = "Tipo de Aposta" if "Tipo de Aposta" in colunas_csv else "tipo de aposta"
                metodo = str(r[col_metodo]).replace("Casa", "Home").replace(
                    "Fora", "Away").replace("Empate", "Draw")

                # Definimos a banca base inicial para as estratégias não-dinâmicas
                BANCA_BASE_INICIAL = 1000.0

                rows.append({
                    "data": r['Data'], "liga": r['Liga'], "horario": r['Horário'],
                    "time_casa": r['Time Casa'], "time_visitante": r['Time Visitante'],
                    "tipo_aposta": metodo,
                    "odd_mercado": r['Odd Mercado'], "prob_ia": r['Prob. IA (%)'],
                    "stake_kelly_porcentagem": r['Stake Kelly (%)'],

                    # Stake Fixa é sempre a % sobre a Banca Inicial (Unidade Flat)
                    "stake_fixa_aplicada": BANCA_BASE_INICIAL * (perc_fixa / 100),

                    # Kelly Estático é a % recomendada, mas SEMPRE sobre a Banca Inicial
                    "stake_kelly_estatica_aplicada": (r['Stake Kelly (%)'] / 100) * BANCA_BASE_INICIAL,

                    # Kelly Dinâmico continua sendo a única que aplica juros compostos sobre o Saldo atual
                    "stake_kelly_dinamica_aplicada": (r['Stake Kelly (%)'] / 100) * saldo_disponivel,

                    "status": "Pendente"
                })

            supabase.table("historico_bets").upsert(rows).execute()
            st.sidebar.success("Jogos carregados com sucesso!")
            st.rerun()

# ==========================================
# HEADER PRINCIPAL E MÉTRICAS GLOBAIS
# ==========================================
col_dash1, col_dash2 = st.columns([4, 1])

with col_dash1:
    st.markdown('<p class="title-glow" style="font-size: 48px;">📊 Dashboard Principal</p>',
                unsafe_allow_html=True)
    st.markdown('<p class="subtitle-glow">Performance Oficial do Modelo | Operador: Rafael Almeida</p>',
                unsafe_allow_html=True)

with col_dash2:
    st.write("")
    st.markdown('<div style="text-align: right; padding-top: 15px;"><span style="color: #00E676; font-weight: bold;">● Sistema Online</span></div>', unsafe_allow_html=True)

# 1. Puxa os dados globais ANTES das abas para calcular as métricas principais
df_hist = get_historico_completo()

if not df_hist.empty:
    # Prepara a matemática da evolução
    df_hist['lucro_fixa'] = df_hist.apply(lambda r: (r['stake_fixa_aplicada'] * r['odd_mercado'] - r['stake_fixa_aplicada'])
                                          if r['status'] == 'Green' else (-r['stake_fixa_aplicada'] if r['status'] == 'Red' else 0), axis=1)
    df_hist['lucro_estatica'] = df_hist.apply(lambda r: (r['stake_kelly_estatica_aplicada'] * r['odd_mercado'] - r['stake_kelly_estatica_aplicada'])
                                              if r['status'] == 'Green' else (-r['stake_kelly_estatica_aplicada'] if r['status'] == 'Red' else 0), axis=1)
    df_hist['lucro_dinamica'] = df_hist['lucro_real']

    def build_curve(series):
        return [1000] + (1000 + series.cumsum()).tolist()

    df_evolucao = pd.DataFrame({
        "Aposta": range(len(df_hist) + 1),
        "Fixa": build_curve(df_hist['lucro_fixa']),
        "Kelly Estática": build_curve(df_hist['lucro_estatica']),
        "Kelly Dinâmica": build_curve(df_hist['lucro_dinamica'])
    })

    # Seletor Global
    opcao_banca = st.selectbox(
        "Analisar métricas baseadas em qual gestão?",
        options=["Kelly Dinâmica", "Kelly Estática", "Stake Fixa"],
        index=0,
        key="filtro_banca_global"
    )

    # Roteamento das colunas
    if opcao_banca == "Kelly Dinâmica":
        col_lucro, col_stake = "lucro_dinamica", "stake_kelly_dinamica_aplicada"
    elif opcao_banca == "Kelly Estática":
        col_lucro, col_stake = "lucro_estatica", "stake_kelly_estatica_aplicada"
    else:
        opcao_banca = "Fixa"
        col_lucro, col_stake = "lucro_fixa", "stake_fixa_aplicada"
        col_evolucao = "Stake Fixa"

    # Cálculos
    lucro_total = df_hist[col_lucro].sum()
    total_staked = df_hist[col_stake].sum()
    roi = (lucro_total / 1000.0) * 100
    yield_perc = (lucro_total / total_staked) * 100 if total_staked > 0 else 0

    total_bets = len(df_hist)
    greens = len(df_hist[df_hist['status'] == 'Green'])
    reds = len(df_hist[df_hist['status'] == 'Red'])
    voids = len(df_hist[df_hist['status'] == 'Void'])
    apostas_validas = total_bets - voids
    win_rate = (greens / apostas_validas) * 100 if apostas_validas > 0 else 0
    odd_media = df_hist['odd_mercado'].mean()

    saldos_serie = df_evolucao[opcao_banca]
    picos_historicos = saldos_serie.cummax()
    drawdowns = (saldos_serie - picos_historicos) / picos_historicos * 100
    max_drawdown = drawdowns.min()

    # RENDERIZAÇÃO DOS CARDS (Acima das abas)
    st.info(
        f"📊 {total_bets} Entradas | {greens} Green 🟢 | {reds} Red 🔴 | {voids} Void ⚪")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(label="Lucro Líquido",
                value=f"R$ {lucro_total:.2f}", delta=f"ROI: {roi:.1f}%")
    col2.metric(label="Yield (Eficiência)",
                value=f"{yield_perc:.2f}%", delta="Lucro / Investimento", delta_color="off")
    col3.metric(label="Max Drawdown",
                value=f"{max_drawdown:.2f}%", delta="Risco Máximo", delta_color="inverse")
    col4.metric(label="Taxa de Acerto",
                value=f"{win_rate:.1f}%", delta=f"Odd Média: {odd_media:.2f}", delta_color="off")

    st.write("")  # Pequeno espaço

st.divider()

# --- CRIANDO AS ABAS ---
tab_operacoes, tab_relatorios, tab_historico = st.tabs(
    ["⚽ Operações", "📊 Relatórios", "📑 Histórico"])

# ==========================================
# ABA 1: OPERAÇÕES (Fica igual)
# ==========================================
with tab_operacoes:
    col_titulo, col_botao = st.columns([3, 1])

    with col_titulo:
        st.markdown(
            '<p class="title-glow" style="font-size: 32px;">⚽ Terminal de Operações</p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="subtitle-glow">Controle de Entradas e Atualização de Resultados</p>', unsafe_allow_html=True)

    res = supabase.table("historico_bets").select(
        "*").filter("status", "in", '("Pendente","Apostado")').order("horario").execute()

    if res.data:
        df_ops = pd.DataFrame(res.data)

        # Cria uma máscara para aplicar o recálculo APENAS aos jogos Pendentes
        mask_pendente = df_ops['status'] == 'Pendente'

        # Atualiza as stakes na tela apenas onde a máscara for Verdadeira
        if mask_pendente.any():
            df_ops.loc[mask_pendente,
                       'stake_fixa_aplicada'] = 1000.0 * (perc_fixa / 100)
            df_ops.loc[mask_pendente, 'stake_kelly_estatica_aplicada'] = (
                df_ops.loc[mask_pendente, 'stake_kelly_porcentagem'] / 100) * 1000.0
            df_ops.loc[mask_pendente, 'stake_kelly_dinamica_aplicada'] = (
                df_ops.loc[mask_pendente, 'stake_kelly_porcentagem'] / 100) * saldo_disponivel

        with col_botao:
            st.write("")
            salvar_clicado = st.button(
                "💾 Salvar Alterações", type="primary", use_container_width=True)

        edited_df = st.data_editor(
            df_ops,
            column_order=("horario", "liga", "time_casa", "time_visitante", "tipo_aposta", "odd_mercado",
                          "stake_fixa_aplicada", "stake_kelly_estatica_aplicada", "stake_kelly_dinamica_aplicada", "status"),
            column_config={
                "horario": "Horário", "liga": "Liga", "time_casa": "Casa", "time_visitante": "Visitante", "tipo_aposta": "Método",
                "odd_mercado": st.column_config.NumberColumn("Odd", format="%.2f"),
                "stake_fixa_aplicada": st.column_config.NumberColumn("Fixa (R$)", format="R$ %.2f"),
                "stake_kelly_estatica_aplicada": st.column_config.NumberColumn("Kelly Est. (R$)", format="R$ %.2f"),
                "stake_kelly_dinamica_aplicada": st.column_config.NumberColumn("Kelly Din. (R$)", format="R$ %.2f"),
                "status": st.column_config.SelectboxColumn("Ação", options=["Pendente", "Apostado", "Green", "Red", "Void"]),
            },
            disabled=["stake_fixa_aplicada", "stake_kelly_estatica_aplicada",
                      "stake_kelly_dinamica_aplicada"],
            hide_index=True, use_container_width=True
        )

        if salvar_clicado:
            bancas = get_banca_data()
            jogos_para_atualizar = []

            for i, row in edited_df.iterrows():
                status_atual = row['status']
                lucro_dinamica_calc = 0

                if status_atual in ['Green', 'Red', 'Void']:
                    def calc_profit(s, o, st):
                        if st == 'Green':
                            return (s * o) - s
                        if st == 'Red':
                            return -s
                        return 0

                    lucro_fixa = calc_profit(
                        row['stake_fixa_aplicada'], row['odd_mercado'], status_atual)
                    lucro_estatica = calc_profit(
                        row['stake_kelly_estatica_aplicada'], row['odd_mercado'], status_atual)
                    lucro_dinamica_calc = calc_profit(
                        row['stake_kelly_dinamica_aplicada'], row['odd_mercado'], status_atual)

                    bancas['banca_fixa'] += lucro_fixa
                    bancas['banca_kelly_estatica'] += lucro_estatica
                    bancas['banca_kelly_dinamica'] += lucro_dinamica_calc

                row_dict = row.to_dict()
                row_dict['status'] = status_atual
                row_dict['lucro_real'] = lucro_dinamica_calc
                jogos_para_atualizar.append(row_dict)

            if jogos_para_atualizar:
                supabase.table("historico_bets").upsert(
                    jogos_para_atualizar).execute()

            supabase.table("config_banca").update({
                "banca_fixa": bancas['banca_fixa'], "banca_kelly_estatica": bancas['banca_kelly_estatica'], "banca_kelly_dinamica": bancas['banca_kelly_dinamica']
            }).eq("id", bancas['id']).execute()

            st.success("Operações processadas em lote com sucesso! ⚡")
            st.rerun()
    else:
        st.info(
            "Nenhum jogo pendente. Utilize a barra lateral para importar o arquivo do dia.")

# ==========================================
# ABA 2: RELATÓRIOS (Agora bem mais enxuta)
# ==========================================
with tab_relatorios:
    st.markdown('<p class="title-glow" style="font-size: 32px;">📊 Gráficos Analíticos</p>',
                unsafe_allow_html=True)

    if not df_hist.empty:
        sub_tab_geral, sub_tab_ligas = st.tabs(
            ["🎯 Visão Geral & Métodos", "🏆 Ranking de Ligas"])

        with sub_tab_geral:
            # --- GRÁFICO DA EQUITY CURVE ---
            st.markdown("#### 📈 Evolução Patrimonial")
            df_melted = df_evolucao.melt(
                id_vars=['Aposta'], var_name='Estratégia', value_name='Saldo')

            fig_line = px.line(df_melted, x='Aposta', y='Saldo', color='Estratégia',
                               markers=True,
                               color_discrete_map={"Fixa": "#A0A0A0", "Kelly Estática": "#FF9900", "Kelly Dinâmica": "#00E676"})

            fig_line.update_layout(
                hovermode="x unified",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                yaxis_title="Saldo (R$)",
                xaxis_title="Número de Apostas"
            )
            st.plotly_chart(fig_line, use_container_width=True)

            st.divider()

            # --- GRÁFICO DE LUCRO POR MÉTODO ---
            st.markdown("#### 🎯 Lucro por Método")

            lucro_metodo = df_hist.groupby('tipo_aposta')[
                col_lucro].sum().reset_index()
            lucro_metodo = lucro_metodo.sort_values(
                by=col_lucro, ascending=False)
            lucro_metodo['Cor'] = lucro_metodo[col_lucro].apply(
                lambda x: '#00E676' if x >= 0 else '#FF3D00')

            fig_met = px.bar(lucro_metodo, x='tipo_aposta',
                             y=col_lucro, text_auto='.2f')
            fig_met.update_traces(
                marker_color=lucro_metodo['Cor'], textposition='outside')
            fig_met.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                                  xaxis_title="Método", yaxis_title="Lucro (R$)")
            st.plotly_chart(fig_met, use_container_width=True)

        with sub_tab_ligas:
            st.markdown("#### 🌍 Destaques por Liga (Top 3 vs Bottom 3)")
            lucro_liga = df_hist.groupby('liga')[col_lucro].sum(
            ).reset_index().sort_values(by=col_lucro, ascending=False)

            col_top, col_bot = st.columns(2)

            with col_top:
                st.success("🔝 3 Ligas Mais Lucrativas")
                top_3 = lucro_liga.head(3)
                fig_top = px.bar(top_3, x=col_lucro, y='liga',
                                 orientation='h', color_discrete_sequence=['#00E676'])
                fig_top.update_layout(height=250, margin=dict(l=150), plot_bgcolor="rgba(0,0,0,0)",
                                      paper_bgcolor="rgba(0,0,0,0)", xaxis_title="Lucro (R$)", yaxis_title="")
                st.plotly_chart(fig_top, use_container_width=True)

            with col_bot:
                st.error("🔻 3 Ligas Menos Lucrativas")
                bot_3 = lucro_liga.tail(3)
                fig_bot = px.bar(bot_3, x=col_lucro, y='liga',
                                 orientation='h', color_discrete_sequence=['#FF3D00'])
                fig_bot.update_layout(height=250, margin=dict(l=150), plot_bgcolor="rgba(0,0,0,0)",
                                      paper_bgcolor="rgba(0,0,0,0)", xaxis_title="Lucro (R$)", yaxis_title="")
                st.plotly_chart(fig_bot, use_container_width=True)

            st.divider()
            with st.expander("📂 Ver Ranking Completo (Todas as Ligas)"):
                st.dataframe(lucro_liga, use_container_width=True,
                             hide_index=True)
    else:
        st.info("Ainda não existem dados para gerar gráficos.")

# O seu código da ABA 3: HISTÓRICO continua logo abaixo daqui...

# ==========================================
# ABA 3: HISTÓRICO (DIÁRIO DE APOSTAS)
# ==========================================
with tab_historico:
    # 1. Cabeçalho
    col_titulo_hist, col_botao_hist = st.columns([3, 2])

    with col_titulo_hist:
        st.markdown('<p class="title-glow">📑 Diário de Apostas</p>',
                    unsafe_allow_html=True)
        st.markdown(
            '<p class="subtitle-glow">Edite o passado e o sistema reescreverá a sua curva de capital</p>', unsafe_allow_html=True)

    # --- NOVO: FILTRO DE DATA ---
    st.markdown("#### 📅 Filtro de Período")

    # Define o padrão: Últimos 7 dias até hoje
    hoje = pd.Timestamp.now().date()
    sete_dias_atras = hoje - pd.Timedelta(days=7)

    datas_selecionadas = st.date_input(
        "Selecione o intervalo de datas:",
        value=(sete_dias_atras, hoje),
        format="DD/MM/YYYY"
    )

    # 2. Busca histórico completo do banco
    res_hist = supabase.table("historico_bets").select(
        "*").order("created_at", desc=True).execute()

    if res_hist.data:
        df_hist_full = pd.DataFrame(res_hist.data)

        # --- LÓGICA DO FILTRO VISUAL ---
        # Cria uma coluna temporária só com a data para facilitar o filtro
        df_hist_full['data_filtro'] = pd.to_datetime(
            df_hist_full['created_at']).dt.date

        if len(datas_selecionadas) == 2:
            data_inicio, data_fim = datas_selecionadas
            # Filtra o dataframe para mostrar apenas o período selecionado
            df_visivel = df_hist_full[(df_hist_full['data_filtro'] >= data_inicio) & (
                df_hist_full['data_filtro'] <= data_fim)].copy()
        else:
            df_visivel = df_hist_full.copy()

        # Limpa a coluna temporária
        df_visivel = df_visivel.drop(columns=['data_filtro'])

        with col_botao_hist:
            st.write("")
            btn_recalcular = st.button(
                "♻️ Sincronizar e Recalcular Todo o Passado", type="primary", use_container_width=True)

        if df_visivel.empty:
            st.warning("Nenhum jogo encontrado neste período.")
        else:
            # 3. Tabela liberada para edição (Mostra apenas o período filtrado)
            edited_hist = st.data_editor(
                df_visivel,
                column_order=("data", "horario", "liga", "time_casa", "time_visitante",
                              "tipo_aposta", "odd_mercado", "status", "lucro_real"),
                column_config={
                    "data": "Data", "horario": "Horário", "liga": "Liga", "time_casa": "Casa", "time_visitante": "Visitante",
                    "tipo_aposta": "Método",
                    "odd_mercado": st.column_config.NumberColumn("Odd", format="%.2f"),
                    "status": st.column_config.SelectboxColumn("Ação", options=["Pendente", "Apostado", "Green", "Red", "Void"]),
                    "lucro_real": st.column_config.NumberColumn("Lucro da Dinâmica", disabled=True, format="R$ %.2f"),
                },
                disabled=["lucro_real", "id", "created_at"],
                hide_index=True,
                use_container_width=True,
                key="editor_historico"
            )

        # 4. O Motor de Reprocessamento Temporal (À Prova de Falhas)
        if btn_recalcular:
            # PASSO A: Salva no banco as edições que você fez APENAS nos jogos filtrados
            if not df_visivel.empty:
                supabase.table("historico_bets").upsert(
                    edited_hist.to_dict(orient='records')).execute()

            # PASSO B: Baixa o histórico DE NOVO, agora com a sua correção aplicada
            res_atualizado = supabase.table("historico_bets").select(
                "*").order("created_at", desc=False).execute()
            df_calc = pd.DataFrame(res_atualizado.data)

            # PASSO C: Recalcula tudo desde o dia 1
            bancas = get_banca_data()
            b_fixa, b_estatica, b_dinamica = 1000.0, 1000.0, 1000.0
            jogos_atualizados = []

            for i, row in df_calc.iterrows():
                status_atual = row['status']
                lucro_dinamica_calc = 0

                if status_atual in ['Green', 'Red', 'Void']:
                    stake_fixa = 1000.0 * (perc_fixa / 100)
                    stake_est = (row['stake_kelly_porcentagem'] / 100) * 1000.0
                    stake_din = (
                        row['stake_kelly_porcentagem'] / 100) * b_dinamica

                    def calc_profit(stake, odd, status):
                        if status == 'Green':
                            return (stake * odd) - stake
                        if status == 'Red':
                            return -stake
                        return 0

                    lucro_f = calc_profit(
                        stake_fixa, row['odd_mercado'], status_atual)
                    lucro_e = calc_profit(
                        stake_est, row['odd_mercado'], status_atual)
                    lucro_d = calc_profit(
                        stake_din, row['odd_mercado'], status_atual)

                    b_fixa += lucro_f
                    b_estatica += lucro_e
                    b_dinamica += lucro_d
                    lucro_dinamica_calc = lucro_d

                row_dict = row.to_dict()
                row_dict['lucro_real'] = lucro_dinamica_calc
                jogos_atualizados.append(row_dict)

            # PASSO D: Salva o novo lucro real de TODOS os jogos no banco
            if jogos_atualizados:
                supabase.table("historico_bets").upsert(
                    jogos_atualizados).execute()

            # PASSO E: Atualiza a banca central
            supabase.table("config_banca").update({
                "banca_fixa": b_fixa,
                "banca_kelly_estatica": b_estatica,
                "banca_kelly_dinamica": b_dinamica
            }).eq("id", bancas['id']).execute()

            st.success(
                "Máquina do tempo ativada! Passado reescrito e bancas atualizadas. ⚡")
            st.rerun()

    else:
        st.info("A sua base de dados histórica está vazia.")
