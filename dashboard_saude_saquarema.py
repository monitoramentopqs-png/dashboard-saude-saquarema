
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date
import numpy as np

try:
    from streamlit import cache_data as cache_decorator
except ImportError:
    cache_decorator = st.cache

st.set_page_config(
    page_title="Dashboard Saúde Saquarema",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
        padding: 1rem;
        background: linear-gradient(90deg, #f0f2f6, #ffffff);
        border-radius: 10px;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #1f77b4;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

@cache_decorator
def load_data():
    try:
        df = pd.read_csv('dados_saude.csv')
        return df
    except FileNotFoundError:
        st.error("Arquivo dados_saude.csv não encontrado.")
        return None

def process_data(df):
    data_extracao = date(2025, 8, 5)
    dias_passados = 5
    dias_total_mes = 30
    percentual_esperado = (dias_passados / dias_total_mes) * 100

    df_grouped = df.groupby(['Unidade', 'Indicador', 'Meta'])['Producao'].sum().reset_index()

    df_grouped['Percentual_Atingido'] = np.where(
        df_grouped['Meta'] != 0,
        (df_grouped['Producao'] / df_grouped['Meta']) * 100,
        0
    )
    df_grouped['Meta_Esperada'] = df_grouped['Meta'] * (percentual_esperado / 100)

    df_grouped['Status_Proporcional'] = np.where(
        percentual_esperado != 0,
        (df_grouped['Percentual_Atingido'] / percentual_esperado) * 100,
        0
    )

    def definir_status(row):
        if row['Status_Proporcional'] >= 100:
            return "🔵 Acima do esperado"
        elif row['Status_Proporcional'] >= 85:
            return "🟢 No prazo"
        else:
            return "🔴 Abaixo do esperado"

    df_grouped['Status'] = df_grouped.apply(definir_status, axis=1)
    return df_grouped, percentual_esperado, data_extracao

def main():
    st.markdown('<h1 class="main-header">📊 Dashboard de Acompanhamento de Metas - Saúde Saquarema</h1>', unsafe_allow_html=True)

    df = load_data()
    if df is None:
        return

    df_processed, percentual_esperado, data_extracao = process_data(df)

    st.sidebar.header("🔍 Filtros")

    unidades_selecionadas = st.sidebar.multiselect(
        "Selecione as Unidades:",
        options=sorted(df_processed['Unidade'].unique()),
        default=sorted(df_processed['Unidade'].unique())
    )

    indicadores_selecionados = st.sidebar.multiselect(
        "Selecione os Indicadores:",
        options=sorted(df_processed['Indicador'].unique()),
        default=sorted(df_processed['Indicador'].unique())
    )

    df_filtered = df_processed[
        (df_processed['Unidade'].isin(unidades_selecionadas)) &
        (df_processed['Indicador'].isin(indicadores_selecionados))
    ]

    col_info1, col_info2, col_info3 = st.columns(3)

    with col_info1:
        st.info(f"📅 Data da Extração: {data_extracao.strftime('%d/%m/%Y')}")

    with col_info2:
        st.info(f"📈 Progresso do Mês: {percentual_esperado:.1f}% (5 de 30 dias)")

    with col_info3:
        total_unidades = len(df_filtered['Unidade'].unique())
        st.info(f"🏥 Unidades Monitoradas: {total_unidades}")

    st.header("🎯 Resumo Geral de Performance")

    resumo_indicadores = df_filtered.groupby('Indicador').agg({
        'Meta': 'sum',
        'Producao': 'sum',
        'Percentual_Atingido': 'mean'
    }).reset_index()

    resumo_indicadores['Status_vs_Esperado'] = np.where(
        percentual_esperado != 0,
        resumo_indicadores['Percentual_Atingido'] / percentual_esperado * 100,
        0
    )

    resumo_indicadores = resumo_indicadores.sort_values("Status_vs_Esperado", ascending=False)

    for _, row in resumo_indicadores.iterrows():
        col_metrics1, col_metrics2, col_metrics3, col_metrics4 = st.columns(4)

        with col_metrics1:
            st.metric(
                label=f"📋 {row['Indicador']}",
                value=f"{row['Producao']:.0f}",
                delta=f"Meta: {row['Meta']:.0f}"
            )

        with col_metrics2:
            st.metric(
                label="% Atingido",
                value=f"{row['Percentual_Atingido']:.1f}%"
            )

        with col_metrics3:
            st.metric(
                label="% Esperado",
                value=f"{percentual_esperado:.1f}%"
            )

        with col_metrics4:
            status_color = "🔵" if row['Status_vs_Esperado'] >= 100 else "🔴" if row['Status_vs_Esperado'] < 85 else "🟢"
            st.metric(
                label="Status",
                value=f"{status_color} {row['Status_vs_Esperado']:.0f}%"
            )

    st.header("📊 Visualizações")

    col_viz1, col_viz2 = st.columns(2)

    with col_viz1:
        st.subheader("Status Proporcional por Indicador")

        fig_donut = go.Figure(data=[go.Pie(
            labels=resumo_indicadores['Indicador'],
            values=resumo_indicadores['Status_vs_Esperado'],
            hole=0.4,
            textinfo='label+percent',
            textposition='outside'
        )])

        fig_donut.update_layout(
            title="Status vs Meta Esperada (%)",
            height=400,
            showlegend=True
        )

        st.plotly_chart(fig_donut, use_container_width=True)

    with col_viz2:
        st.subheader("Performance por Unidade")

        perf_unidade = df_filtered.groupby('Unidade')['Status_Proporcional'].mean().reset_index()
        perf_unidade = perf_unidade.sort_values('Status_Proporcional', ascending=True)

        fig_bar = px.bar(
            perf_unidade,
            x='Status_Proporcional',
            y='Unidade',
            orientation='h',
            title="% Performance vs Esperado por Unidade",
            color='Status_Proporcional',
            color_continuous_scale='RdYlBu'
        )

        fig_bar.add_shape(
            type="line",
            x0=100, x1=100,
            y0=0, y1=1,
            xref='x',
            yref='paper',
            line=dict(color="red", width=2, dash="dash")
        )
        fig_bar.add_annotation(
            x=100, y=1,
            xref='x', yref='paper',
            showarrow=False,
            text="Meta Esperada",
            font=dict(color="red")
        )

        fig_bar.update_layout(height=400)
        st.plotly_chart(fig_bar, use_container_width=True)

    st.header("📋 Detalhamento por Unidade e Indicador")

    df_display = df_filtered.copy()
    df_display = df_display.sort_values(['Unidade', 'Indicador'])

    df_display['% Atingido'] = df_display['Percentual_Atingido'].apply(lambda x: f"{x:.1f}%")
    df_display['Meta Esperada'] = df_display['Meta_Esperada'].apply(lambda x: f"{x:.0f}")
    df_display['Performance'] = df_display['Status_Proporcional'].apply(lambda x: f"{x:.0f}%")

    colunas_exibir = ['Unidade', 'Indicador', 'Meta', 'Producao', '% Atingido', 'Meta Esperada', 'Performance', 'Status']

    st.dataframe(df_display[colunas_exibir], use_container_width=True, height=400)

    st.header("💡 Principais Insights")

    col_insight1, col_insight2 = st.columns(2)

    with col_insight1:
        st.subheader("✅ Pontos Positivos")
        top_unidades = df_filtered.groupby('Unidade')['Status_Proporcional'].mean().nlargest(3)

        for unidade, performance in top_unidades.items():
            st.success(f"{unidade}: {performance:.0f}% de performance")

    with col_insight2:
        st.subheader("⚠️ Pontos de Atenção")
        bottom_unidades = df_filtered.groupby('Unidade')['Status_Proporcional'].mean().nsmallest(3)

        for unidade, performance in bottom_unidades.items():
            st.error(f"{unidade}: {performance:.0f}% de performance")

    st.header("📥 Download dos Dados")
    csv = df_filtered.to_csv(index=False)
    st.download_button(
        label="📊 Baixar dados processados (CSV)",
        data=csv,
        file_name=f"dashboard_saude_saquarema_{data_extracao.strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

if __name__ == "__main__":
    main()
