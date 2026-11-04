import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# Configuração da página do aplicativo
st.set_page_config(page_title="Controle Bar & Estética", page_icon="🚗", layout="wide")

st.title("📊 Gestão Integrada com Google Planilhas")
st.caption("Controle diário de vendas integrado ao seu Google Drive em Real (R$)")

# ==========================================
# CONEXÃO COM GOOGLE PLANILHAS (Configuração)
# ==========================================
def conectar_google_sheets():
    try:
        escopos = [
            "https://googleapis.com",
            "https://googleapis.com"
        ]
        info_credenciais = st.secrets["gcp_service_account"]
        credenciais = Credentials.from_service_account_info(info_credenciais, scopes=escopos)
        cliente = gspread.authorize(credenciais)
        planilha = cliente.open("Controle_Financeiro_Parceria").sheet1
        return planilha
    except Exception as e:
        return None

sheet = conectar_google_sheets()

if 'vendas_df' not in st.session_state:
    st.session_state.vendas_df = pd.DataFrame(columns=["Data", "Categoria", "Descrição", "Valor (R$)", "Indicação da Vizinha"])

if sheet is not None:
    try:
        dados_sheets = sheet.get_all_records()
        if dados_sheets:
            st.session_state.vendas_df = pd.DataFrame(dados_sheets)
    except:
        pass

# ==========================================
# ABA 1: SIMULADOR DE METAS (Painel Lateral)
# ==========================================
st.sidebar.header("🎯 Simulador de Metas")
meta_lucro = st.sidebar.number_input("Sua Meta de Lucro Mensal (R$)", min_value=0.0, value=3000.0, step=100.0)
dias_trabalhados = st.sidebar.number_input("Dias Trabalhados no Mês", min_value=1, max_value=31, value=26)
ticket_medio = st.sidebar.number_input("Ticket Médio por Cliente (R$)", min_value=1.0, value=60.0, step=5.0)

faturamento_diario_nec = (meta_lucro) / dias_trabalhados
clientes_por_dia = faturamento_diario_nec / ticket_medio

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Meta de Faturamento Diário:** R$ {faturamento_diario_nec:.2f}")
st.sidebar.markdown(f"**Clientes por Dia necessários:** ~ {clientes_por_dia:.1f}")

tab1, tab2, tab3 = st.tabs(["➕ Lançamento Diário", "📋 Histórico de Caixa", "💰 Painel de Divisão (Lucros)"])

# ==========================================
# ABA 1: LANÇAMENTO DIÁRIO
# ==========================================
with tab1:
    if sheet is None:
        st.warning("⚠️ O aplicativo está rodando em modo offline (Sem salvar no Google Planilhas). Configure os 'Secrets' no Streamlit Cloud para ativar a nuvem.")
    else:
        st.success("✅ Conectado ao Google Planilhas com sucesso!")

    st.subheader("Registrar Nova Movimentação")
    with st.form("form_registro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            data_venda = st.date_input("Data", datetime.today())
            categoria = st.selectbox("Categoria", [
                "Bar - Venda (Bebidas/Salgados)", 
                "Bar - Custo (Reposição/Estoque)", 
                "Estética Automotiva"
            ])
        with col2:
            descricao = st.text_input("Descrição do Item / Serviço", placeholder="Ex: Lavagem Simples, Cerveja, Água")
            valor = st.number_input("Valor Total (R$)", min_value=0.0, value=0.0, step=1.0)
        
        indicacao = "Não"
        if categoria == "Estética Automotiva":
            indicacao = st.radio("A vizinha indicou este cliente da Estética?", ["Sim", "Não"], horizontal=True)
            
        botao_enviar = st.form_submit_button("Salvar Registro")
        
        if botao_enviar:
            if valor > 0 and descricao != "":
                data_formatada = data_venda.strftime('%d/%m/%Y')
                ind_v_texto = indicacao if categoria == "Estética Automotiva" else "-"
                
                if sheet is not None:
                    try:
                        sheet.append_row([data_formatada, categoria, descricao, valor, ind_v_texto])
                        st.success("Lançamento salvo diretamente no Google Planilhas!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar no Google: {e}")
                else:
                    novo_registro = pd.DataFrame([{
                        "Data": data_formatada,
                        "Categoria": categoria,
                        "Descrição": descricao,
                        "Valor (R$)": valor,
                        "Indicação da Vizinha": ind_v_texto
                    }])
                    st.session_state.vendas_df = pd.concat([st.session_state.vendas_df, novo_registro], ignore_index=True)
                    st.success("Salvo na memória local do app!")
            else:
                st.error("Por favor, preencha a descrição e um valor maior que R$ 0.")

# ==========================================
# ABA 2: HISTÓRICO DE CAIXA
# ==========================================
with tab2:
    st.subheader("Todas as Movimentações Registradas")
    df = st.session_state.vendas_df
    if df.empty:
        st.info("Nenhum registro encontrado.")
    else:
        st.dataframe(df, use_container_width=True)

# ==========================================
# ABA 3: PAINEL DE DIVISÃO (LUCROS)
# ==========================================
with tab3:
    st.subheader("Fechamento de Valores e Comissões")
    df = st.session_state.vendas_df
    
    if not df.empty:
        df['Valor (R$)'] = pd.to_numeric(df['Valor (R$)'], errors='coerce').fillna(0.0)
        
        bar_vendas = df[df['Categoria'] == "Bar - Venda (Bebidas/Salgados)"]['Valor (R$)'].sum()
        bar_custos = df[df['Categoria'] == "Bar - Custo (Reposição/Estoque)"]['Valor (R$)'].sum()
        bar_lucro_liquido = bar_vendas - bar_custos
        parceira_bar_cada = bar_lucro_liquido / 2 if bar_lucro_liquido > 0 else 0.0
        
        estetica_total = df[df['Categoria'] == "Estética Automotiva"]['Valor (R$)'].sum()
        estetica_com_indicacao = df[(df['Categoria'] == "Estética Automotiva") & (df['Indicação da Vizinha'] == "Sim")]['Valor (R$)'].sum()
        comissao_vizinha_estetica = estetica_com_indicacao * 0.10
        seu_ganho_estetica = estetica_total - comissao_vizinha_estetica

        seu_total_geral = seu_ganho_estetica + (parceira_bar_cada if bar_lucro_liquido > 0 else 0)
        total_vizinha_geral = comissao_vizinha_estetica + (parceira_bar_cada if bar_lucro_liquido > 0 else 0)
    else:
        bar_vendas = bar_custos = bar_lucro_liquido = parceira_bar_cada = 0.0
        estetica_total = estetica_com_indicacao = comissao_vizinha_estetica = seu_ganho_estetica = 0.0
        seu_total_geral = total_vizinha_geral = 0.0

    st.markdown("### 🏪 Resumo Financeiro do Bar")
    c1, c2, c3 = st.columns(3)
    c1.metric("Vendas Brutas (Bar)", f"R$ {bar_vendas:.2f}")
    c2.metric("Custos de Reposição (Bar)", f"R$ {bar_custos:.2f}")
    c3.metric("Lucro Líquido do Bar", f"R$ {bar_lucro_liquido:.2f}")
    
    st.markdown("### 🚗 Resumo da Estética Automotiva")
    e1, e2, e3 = st.columns(3)
    e1.metric("Faturamento Estética", f"R$ {estetica_total:.2f}")
    e2.metric("Serviços por Indicação", f"R$ {estetica_com_indicacao:.2f}")
    e3.metric("Comissão da Vizinha (10%)", f"R$ {comissao_vizinha_estetica:.2f}")
    
    st.markdown("---")
    st.markdown("## 💰 Divisão Final do Caixa")
    
    col_voce, col_vizinha = st.columns(2)
    with col_voce:
        st.success(f"### **Seu Ganho Total: R$ {seu_total_geral:.2f}**")
        st.write(f"- 90% dos seus serviços + 100% sem indicação: R$ {seu_ganho_estetica:.2f}")
        st.write(f"- 50% do lucro líquido do bar: R$ {parceira_bar_cada:.2f}")
        
    with col_vizinha:
        st.warning(f"### **Parte da Vizinha: R$ {total_vizinha_geral:.2f}**")
        st.write(f"- 10% de comissão pelas indicações de carros: R$ {comissao_vizinha_estetica:.2f}")
        st.write(f"- 50% do lucro líquido do bar: R$ {parceira_bar_cada:.2f}")
