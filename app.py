import io
import re
import calendar
from datetime import datetime
import pandas as pd
import numpy as np
import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.set_page_config(
    page_title="Painel Executivo - Prévia Diária",
    page_icon="📊",
    layout="wide"
)

# --- URL DA PLANILHA DO GOOGLE SHEETS ---
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1bF7cQaoEkj-UuKCGmJ4PThoy-CdSPlVg8i3XEB6cu58/edit?gid=0#gid=0"

# --- FUNÇÕES DE NAVEGAÇÃO ---
def ir_para_passo_2():
    st.session_state["pagina_atual"] = "2. Dados Operacionais por Base"

def ir_para_passo_3():
    st.session_state["pagina_atual"] = "3. Visualização da Prévia"

# --- FUNÇÃO DE FORMATAÇÃO PADRÃO BRASILEIRO ---
def fmt_br(val, decimais=0):
    try:
        if pd.isna(val):
            val = 0.0
        if decimais > 0:
            s = f"{float(val):,.{decimais}f}"
            s = s.replace(",", "X").replace(".", ",").replace("X", ".")
            return s
        else:
            return f"{int(round(float(val), 0)):,}".replace(".", ".")
    except Exception:
        return str(val)

# --- CSS DE ESTILIZAÇÃO PROFISSIONAL EXECUTIVA ---
st.markdown("""
<style>
    .reportview-container .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }
    .custom-table {
        width: 100%;
        border-collapse: collapse;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-size: 11px;
        text-align: center;
        margin-bottom: 1rem;
    }
    .custom-table th {
        border: 1px solid #7f8c8d;
        padding: 5px 3px;
        font-weight: 700;
    }
    .custom-table td {
        border: 1px solid #bdc3c7;
        padding: 4px 3px;
    }
    .th-data { background-color: #f2f4f4; color: #2c3e50; }
    .th-qtd-os { background-color: #a9dfbf; color: #145a32; }
    .th-consult { background-color: #d5dbdb; color: #212f3d; }
    .th-prod { background-color: #a0824b; color: #ffffff; }
    .th-quebra-claro { background-color: #f9e79f; color: #7d6608; }
    .th-ganho { background-color: #a9dfbf; color: #145a32; }
    .th-gpon { background-color: #f9e79f; color: #7d6608; }
    .th-mig { background-color: #f5b7b1; color: #78281f; }
    .th-retorno { background-color: #a9dfbf; color: #145a32; }
    .th-pme { background-color: #aed6f1; color: #1b4f72; }
    
    .col-destaque-amarelo { background-color: #fcf3cf !important; font-weight: bold; color: #7d6608; }
    .col-destaque-azul { background-color: #d4efdf !important; font-weight: bold; color: #145a32; }
    
    .tr-base { background-color: #eafaf1; font-weight: bold; color: #145a32; font-size: 13px; }
    .tr-sup { background-color: #ffffff; color: #2c3e50; font-size: 11px; }
    .tr-total { background-color: #d4efdf; font-weight: 900; color: #145a32; font-size: 13px; border-top: 2px solid #27ae60; }
    .red-text { color: #c0392b; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

def normalizar_nome_base(val):
    s = str(val).strip().upper()
    if "ABC" in s:
        return "NET-ABCDM"
    elif "GUA" in s or "GRU" in s:
        return "NET-Guarulhos"
    elif "LES" in s:
        return "NET-LESTE"
    return s

def calcular_calendario_automatico(ref_date=None):
    if ref_date is None:
        ref_date = datetime.now()
    ano = ref_date.year
    mes = ref_date.month
    dia_atual = ref_date.day
    
    total_dias_mes = calendar.monthrange(ano, mes)[1]
    dias_uteis_mes = sum(1 for d in range(1, total_dias_mes + 1) if datetime(ano, mes, d).weekday() != 6)
    dias_trab_ate_hoje = sum(1 for d in range(1, dia_atual + 1) if datetime(ano, mes, d).weekday() != 6)
    
    return dias_uteis_mes, max(1, dias_trab_ate_hoje), ref_date.strftime("%d/%m/%Y")

def obter_df_historico():
    if "df_historico_custom" not in st.session_state:
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            df_h = conn.read(spreadsheet=GOOGLE_SHEET_URL, worksheet="Historico_OS")
            if df_h is not None and not df_h.empty:
                st.session_state["df_historico_custom"] = df_h
            else:
                st.session_state["df_historico_custom"] = pd.DataFrame(columns=["Data", "Base", "OS_Executadas"])
        except Exception:
            st.session_state["df_historico_custom"] = pd.DataFrame(columns=["Data", "Base", "OS_Executadas"])
    return st.session_state["df_historico_custom"]

def adicionar_historico_dia(data_str, base, os_exec):
    df_hist = obter_df_historico()
    base_norm = normalizar_nome_base(base)
    if os_exec > 0:
        if not df_hist.empty and "Data" in df_hist.columns and "Base" in df_hist.columns:
            df_hist = df_hist[~((df_hist["Data"].astype(str) == str(data_str)) & (df_hist["Base"].astype(str).str.upper() == base_norm))]
        nova_linha = pd.DataFrame([{"Data": str(data_str), "Base": base_norm, "OS_Executadas": int(os_exec)}])
        st.session_state["df_historico_custom"] = pd.concat([df_hist, nova_linha], ignore_index=True)

def calcular_projecao_os_base(base_proj, dias_uteis_mes=27, os_hoje=None, data_hoje_str=None):
    base_norm = normalizar_nome_base(base_proj)
    df_b = obter_df_historico().copy()
    if not df_b.empty and "Base" in df_b.columns:
        df_b = df_b[df_b["Base"].astype(str).str.upper() == base_norm].copy()
    
    if data_hoje_str and os_hoje is not None and os_hoje > 0:
        if df_b.empty or not (df_b["Data"].astype(str) == str(data_hoje_str)).any():
            nova = pd.DataFrame([{"Data": str(data_hoje_str), "Base": base_norm, "OS_Executadas": int(os_hoje)}])
            df_b = pd.concat([df_b, nova], ignore_index=True)
        else:
            df_b.loc[df_b["Data"].astype(str) == str(data_hoje_str), "OS_Executadas"] = int(os_hoje)

    if not df_b.empty:
        soma_total = pd.to_numeric(df_b["OS_Executadas"], errors="coerce").sum()
        qtd_dias = max(1, df_b["Data"].nunique())
        media_diaria = soma_total / qtd_dias
        projecao = int(round(media_diaria * dias_uteis_mes, 0))
        return projecao, media_diaria, qtd_dias
        
    return 0, 0.0, 1

# --- FUNÇÃO PARA CARREGAR CONFIGURAÇÃO DE EQUIPE DO GOOGLE SHEETS ---
@st.cache_data(ttl=600)
def carregar_config_equipe():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_eq = conn.read(spreadsheet=GOOGLE_SHEET_URL, worksheet="Config_Equipe")
        return df_eq
    except Exception:
        return pd.DataFrame(columns=["Base", "Supervisor", "Montados", "Parados"])

# --- LEITURA DOS DICIONÁRIOS DO GOOGLE SHEETS ---
@st.cache_data(ttl=600)
def carregar_dicionarios_sheets():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_b = conn.read(spreadsheet=GOOGLE_SHEET_URL, worksheet="Baixas")
        baixas_dict = dict(zip(df_b.iloc[:, 0].astype(str).str.strip().str.upper(), df_b.iloc[:, 1].astype(str).str.strip().str.upper()))
        
        df_p = conn.read(spreadsheet=GOOGLE_SHEET_URL, worksheet="Pontos")
        pontos_dict = dict(zip(df_p.iloc[:, 0].astype(str).str.strip().str.upper(), pd.to_numeric(df_p.iloc[:, 1], errors="coerce").fillna(0.0)))
        
        df_d = conn.read(spreadsheet=GOOGLE_SHEET_URL, worksheet="Desc_OS")
        desc_dict = dict(zip(df_d.iloc[:, 0].astype(str).str.strip().str.upper(), df_d.iloc[:, 1].astype(str).str.strip().str.upper()))
        
        return baixas_dict, pontos_dict, desc_dict
    except Exception:
        return {}, {}, {}

BAIXAS_DICT, PONTOS_DICT, DESC_OS_DICT = carregar_dicionarios_sheets()

# --- INICIALIZAÇÃO DE ESTADO E NAVEGAÇÃO ---
etapas = ["1. Upload de Arquivos", "2. Dados Operacionais por Base", "3. Visualização da Prévia"]

if "pagina_atual" not in st.session_state:
    st.session_state["pagina_atual"] = "1. Upload de Arquivos"

if st.session_state.get("ir_para_passo_3_ativo", False):
    st.session_state["pagina_atual"] = "3. Visualização da Prévia"
    st.session_state["ir_para_passo_3_ativo"] = False

if "df_valido" not in st.session_state:
    st.session_state.df_valido = None
if "df_aniel_full" not in st.session_state:
    st.session_state.df_aniel_full = None
if "supervisores_por_base" not in st.session_state:
    st.session_state.supervisores_por_base = {}
if "processado_sucesso" not in st.session_state:
    st.session_state.processado_sucesso = False

bases_config = [
    {"label": "ABCDM", "projeto": "NET-ABCDM"},
    {"label": "Guarulhos", "projeto": "NET-Guarulhos"},
    {"label": "Leste", "projeto": "NET-LESTE"}
]

# --- MENU LATERAL ---
st.sidebar.title("Navegação")
st.sidebar.radio(
    "Ir para:",
    etapas,
    key="pagina_atual"
)

data_selecionada = None
if st.session_state["pagina_atual"] == "3. Visualização da Prévia":
    st.sidebar.markdown("---")
    st.sidebar.subheader("📅 Histórico")
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_historico_previas = conn.read(spreadsheet=GOOGLE_SHEET_URL, worksheet="Previas_Diarias")
    except Exception:
        df_historico_previas = pd.DataFrame()

    if df_historico_previas is not None and not df_historico_previas.empty and "Data" in df_historico_previas.columns:
        datas_disponiveis = sorted(df_historico_previas["Data"].astype(str).unique().tolist(), reverse=True)
        data_selecionada = st.sidebar.selectbox("Selecionar Data:", datas_disponiveis)
    else:
        data_selecionada = st.session_state.get("data_formatada", "22/10/2026")

def ler_arquivo_seguro(uploaded_file):
    uploaded_file.seek(0)
    nome = uploaded_file.name.lower()
    if nome.endswith(".csv"):
        try:
            return pd.read_csv(uploaded_file, sep=None, engine="python")
        except Exception:
            uploaded_file.seek(0)
            return pd.read_csv(uploaded_file, sep=";", encoding="latin1", on_bad_lines="skip")
    try:
        uploaded_file.seek(0)
        return pd.read_excel(uploaded_file, engine="openpyxl")
    except Exception:
        pass
    try:
        uploaded_file.seek(0)
        return pd.read_excel(uploaded_file)
    except Exception:
        pass
    try:
        uploaded_file.seek(0)
        return pd.read_csv(uploaded_file, sep=None, engine="python", encoding="utf-8")
    except Exception:
        pass
    try:
        uploaded_file.seek(0)
        return pd.read_csv(uploaded_file, sep="\t", encoding="latin1")
    except Exception:
        pass
    try:
        uploaded_file.seek(0)
        dfs = pd.read_html(uploaded_file)
        if dfs:
            return dfs[0]
    except Exception as e:
        raise ValueError(f"Erro na leitura: {e}")

def limpar_chave(val):
    if pd.isna(val):
        return ""
    s = str(val).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s

def limpar_texto(val):
    if pd.isna(val):
        return ""
    s = str(val).strip().upper()
    return re.sub(r"\s+", " ", s)

# ==============================================================================
# PÁGINA 1: UPLOAD DE ARQUIVOS
# ==============================================================================
if st.session_state["pagina_atual"] == "1. Upload de Arquivos":
    st.subheader("📁 Passo 1: Upload e Cruzamento das Bases")
    st.write("Carregue o ficheiro do ANIEL e os ficheiros do TOA para processar o dia.")
    
    col_u1, col_u2 = st.columns(2)
    with col_u1:
        up_aniel = st.file_uploader("Ficheiro ANIEL (.xlsx ou .xlsm)", type=["xlsx", "xlsm", "csv"], key="u_aniel")
    with col_u2:
        up_toa = st.file_uploader("Ficheiros do TOA (Pode selecionar os três)", type=["xlsx", "xlsm", "csv"], accept_multiple_files=True, key="u_toa")
        
    if up_aniel is not None:
        if st.button("🚀 Processar Arquivos e Cruzar Bases", type="primary"):
            with st.spinner("Processando cruzamento e tratando dados..."):
                try:
                    df_aniel = ler_arquivo_seguro(up_aniel)
                    df_aniel.columns = [str(c).strip() for c in df_aniel.columns]

                    col_proj = next((c for c in df_aniel.columns if c.lower() == "projeto"), "Projeto")
                    if col_proj in df_aniel.columns:
                        df_aniel = df_aniel[
                            ~df_aniel[col_proj].astype(str).str.upper().str.contains(r"\bVT\b|VT", regex=True, na=False)
                        ].reset_index(drop=True)

                    df_toa = None
                    if up_toa:
                        colunas_uteis_toa = [
                            "Data", "Contrato", "Status da Atividade", "Motivo de Fechamento Externo",
                            "Cidade", "Início", "Categorias da Capacidade", "Cód de Baixa 1",
                            "Tipo O.S 1", "Total de tarefas"
                        ]
                        toa_dfs = []
                        for file in up_toa:
                            tdf = ler_arquivo_seguro(file)
                            tdf.columns = [str(c).strip() for c in tdf.columns]
                            cols_presentes = [c for c in colunas_uteis_toa if c in tdf.columns]
                            if cols_presentes:
                                tdf = tdf[cols_presentes]
                            toa_dfs.append(tdf)
                        df_toa = pd.concat(toa_dfs, ignore_index=True)

                    for col in ["ST1", "ST2", "ST3", "CANCELADAS", "PME"]:
                        if col not in df_aniel.columns:
                            df_aniel[col] = ""

                    if df_toa is not None and not df_toa.empty:
                        col_chave_toa = "Contrato" if "Contrato" in df_toa.columns else df_toa.columns[1]
                        df_toa_clean = df_toa.copy()
                        df_toa_clean["_chave_"] = df_toa_clean[col_chave_toa].apply(limpar_chave).astype(str)
                        df_toa_clean = df_toa_clean[df_toa_clean["_chave_"] != ""]
                        df_toa_clean = df_toa_clean.drop_duplicates(subset=["_chave_"], keep="first")
                        toa_dict = df_toa_clean.set_index("_chave_").to_dict(orient="index")

                        col_chave_aniel = next((c for c in df_aniel.columns if "contrato" in c.lower()), "Contrato Cliente")

                        for idx, row in df_aniel.iterrows():
                            contrato = limpar_chave(row.get(col_chave_aniel, ""))
                            if contrato in toa_dict:
                                match = toa_dict[contrato]
                                df_aniel.at[idx, "ST1"] = str(match.get("Status da Atividade", "")).replace("nan", "").strip()
                                df_aniel.at[idx, "ST2"] = str(match.get("Motivo de Fechamento Externo", "")).replace("nan", "").strip()
                                df_aniel.at[idx, "ST3"] = str(match.get("Cód de Baixa 1", "")).replace("nan", "").strip()
                                df_aniel.at[idx, "PME"] = str(match.get("Categorias da Capacidade", "")).replace("nan", "").strip()
                                df_aniel.at[idx, "Cidade"] = str(match.get("Cidade", "")).replace("nan", "").strip()

                    if "Projeto" in df_aniel.columns and "Cidade" in df_aniel.columns and "Supervisor" in df_aniel.columns:
                        mask_apoio = (
                            (df_aniel["Projeto"].astype(str).str.upper().str.contains("ABCDM")) &
                            (df_aniel["Cidade"].astype(str).str.upper().str.strip() == "SAO PAULO")
                        )
                        df_aniel.loc[mask_apoio, "Supervisor"] = "APOIO SÃO PAULO"

                    if "Pontos Prev." not in df_aniel.columns:
                        df_aniel["Pontos Prev."] = 0.0
                    else:
                        df_aniel["Pontos Prev."] = (
                            df_aniel["Pontos Prev."]
                            .astype(str)
                            .str.replace(" ", "", regex=False)
                            .str.replace(".", "", regex=False)
                            .str.replace(",", ".", regex=False)
                        )
                        df_aniel["Pontos Prev."] = pd.to_numeric(df_aniel["Pontos Prev."], errors="coerce").fillna(0.0)

                    baixas_norm = {limpar_texto(k): v for k, v in BAIXAS_DICT.items()}
                    desc_norm = {limpar_texto(k): v for k, v in DESC_OS_DICT.items()}
                    pontos_norm = {limpar_texto(k): float(v) for k, v in PONTOS_DICT.items()}

                    for idx, row in df_aniel.iterrows():
                        tipo_os_raw = str(row.get("Tipo de OS", "")).strip()
                        tipo_os = "" if tipo_os_raw.lower() == "nan" else tipo_os_raw.upper()

                        st1_raw = str(row.get("ST1", "")).strip()
                        st1_val = "" if st1_raw.lower() == "nan" else st1_raw

                        st2_raw = str(row.get("ST2", "")).strip()
                        st2_val = "" if st2_raw.lower() == "nan" else st2_raw.lower()

                        st3_raw = str(row.get("ST3", "")).strip()
                        st3_val = "" if st3_raw.lower() == "nan" else st3_raw.upper()
                        st3_norm = limpar_texto(st3_val)

                        if tipo_os in ["N/A", "#N/A", ""]:
                            encontrou = False
                            if st3_norm != "":
                                if st3_norm in baixas_norm:
                                    tipo_os = baixas_norm[st3_norm]
                                    encontrou = True
                                else:
                                    for k_baixa, v_baixa in baixas_norm.items():
                                        if st3_norm in k_baixa or k_baixa in st3_norm:
                                            tipo_os = v_baixa
                                            encontrou = True
                                            break
                            if not encontrou:
                                tipo_os = "EM ABERTO"

                        if tipo_os == "EM ABERTO" and st1_val == "":
                            tipo_os = "SAIU DO TOA"

                        if ("liberado no sistema netsms" in st2_val or "cancelado no sistema netsms" in st2_val) and tipo_os == "EM ABERTO":
                            tipo_os = "CANCELADO"

                        if "executado no sistema netsms" in st2_val:
                            tipo_os = "PRODUTIVA"

                        df_aniel.at[idx, "Tipo de OS"] = tipo_os

                        if "cancelado" in st2_val:
                            df_aniel.at[idx, "CANCELADAS"] = "CANCELADO"
                        else:
                            df_aniel.at[idx, "CANCELADAS"] = ""

                        tipo_servico_raw = str(row.get("Tipo de Serviço", "")).strip()
                        tipo_servico_norm = limpar_texto(tipo_servico_raw)
                        obs1_raw = str(row.get("Observação 1", "")).strip()
                        obs1 = "" if obs1_raw.lower() == "nan" else obs1_raw.lower()

                        quebra_val = ""
                        if tipo_servico_norm in desc_norm:
                            quebra_val = desc_norm[tipo_servico_norm]
                        else:
                            for k_desc, v_desc in desc_norm.items():
                                if tipo_servico_norm != "" and (tipo_servico_norm in k_desc or k_desc in tipo_servico_norm):
                                    quebra_val = v_desc
                                    break
                        df_aniel.at[idx, "QUEBRAS"] = quebra_val

                        ts_lower = tipo_servico_norm.lower()
                        status_ativ = ""
                        if "const" in ts_lower:
                            status_ativ = "CONSTRUÇÃO"
                        elif "pon " in obs1 or "fibra" in obs1 or "virtua pon" in obs1 or "gpon" in obs1:
                            status_ativ = "GPON"
                            if "instalacao de cabo gpon" in ts_lower or "mudanca de pacote" in ts_lower:
                                status_ativ = "MIGRAÇÃO"

                        if status_ativ == "":
                            status_ativ = "HFC"

                        if status_ativ == "HFC" and "instalacao de cabo gpon" in ts_lower:
                            status_ativ = "MIGRAÇÃO"

                        df_aniel.at[idx, "ATIVIDADES"] = status_ativ

                        pontos_val = float(df_aniel.at[idx, "Pontos Prev."])
                        if pontos_val == 0.0:
                            ponto_encontrado = None
                            if tipo_servico_norm in pontos_norm:
                                ponto_encontrado = pontos_norm[tipo_servico_norm]
                            else:
                                for k_ponto, v_ponto in pontos_norm.items():
                                    if tipo_servico_norm != "" and (tipo_servico_norm in k_ponto or k_ponto in tipo_servico_norm):
                                        ponto_encontrado = v_ponto
                                        break
                            if ponto_encontrado is not None:
                                df_aniel.at[idx, "Pontos Prev."] = float(ponto_encontrado)

                    df_aniel["Supervisor"] = df_aniel["Supervisor"].fillna("").astype(str).str.strip().str.upper()
                    df_aniel["Tipo de Serviço"] = df_aniel["Tipo de Serviço"].fillna("").astype(str).str.strip().str.upper()

                    df_valido = df_aniel[
                        (df_aniel["Supervisor"] != "") &
                        (df_aniel["Tipo de Serviço"] != "") &
                        (~df_aniel["Supervisor"].str.contains("IVAN", na=False))
                    ].copy()

                    st.session_state.df_valido = df_valido
                    st.session_state.df_aniel_full = df_aniel

                    # --- EXTRAÇÃO RIGOROSA DE SUPERVISORES POR PROJETO/BASE (COM FILTRO DE LIMPEZA) ---
                    sup_map = {}
                    for item in bases_config:
                        b_proj = item["projeto"]
                        df_base_temp = df_valido[df_valido["Projeto"].str.upper() == b_proj.upper()]
                        sups_brutos = sorted(df_base_temp["Supervisor"].unique().tolist())
                        
                        sups_filtrados = []
                        for s in sups_brutos:
                            s_up = str(s).strip().upper()
                            if "ABCDM" in b_proj.upper():
                                if any(sub in s_up for sub in ["EDSON", "MAICON", "NELSON", "APOIO"]):
                                    sups_filtrados.append(s_up)
                            elif "LESTE" in b_proj.upper():
                                if any(sub in s_up for sub in ["ALAN", "ELISANGELA", "FRANCISCO", "JOAO CARLOS", "MIRON"]):
                                    sups_filtrados.append(s_up)
                            elif "GUARULHOS" in b_proj.upper():
                                if any(sub in s_up for sub in ["ADRIANO", "DANIELE", "FERNANDO", "PALOMA"]):
                                    sups_filtrados.append(s_up)
                            else:
                                sups_filtrados.append(s_up)
                                
                        sup_map[b_proj] = sorted(list(set(sups_filtrados)))

                    st.session_state.supervisores_por_base = sup_map
                    st.session_state.processado_sucesso = True

                except Exception as e:
                    st.session_state.processado_sucesso = False
                    st.error(f"Erro ao processar: {e}")

    if st.session_state.processado_sucesso and st.session_state.df_valido is not None:
        st.success("✅ Arquivos carregados e tratados com sucesso!")
        st.button(
            "Ir para Dados Operacionais ➡️",
            type="primary",
            on_click=ir_para_passo_2,
            key="btn_ir_dados"
        )

# ==============================================================================
# PÁGINA 2: ENTRADA DE DADOS OPERACIONAIS
# ==============================================================================
elif st.session_state["pagina_atual"] == "2. Dados Operacionais por Base":
    st.subheader("⚙️ Passo 2: Dados Operacionais por Base")
    
    if st.session_state.df_valido is None:
        st.warning("⚠️ Carregue os arquivos primeiro no Passo 1.")
    else:
        data_base_ref = datetime.now()
        if "Data Agendamento" in st.session_state.df_valido.columns:
            try:
                datas_unicas = pd.to_datetime(st.session_state.df_valido["Data Agendamento"], dayfirst=True, errors='coerce').dropna()
                if not datas_unicas.empty:
                    data_base_ref = datas_unicas.iloc[0]
            except Exception:
                pass

        dias_uteis_auto, dias_trab_auto, data_formatada = calcular_calendario_automatico(data_base_ref)
        st.info(f"📅 **Data de Referência:** {data_formatada} | **Dias Úteis do Mês (Seg a Sáb):** {dias_uteis_auto} dias | **Dias Úteis Trabalhados até Hoje:** {dias_trab_auto} dias (Calculado automaticamente)")
        
        st.session_state["dias_uteis_auto"] = dias_uteis_auto
        st.session_state["dias_trab_auto"] = dias_trab_auto
        st.session_state["data_formatada"] = data_formatada

        df_config_eq = carregar_config_equipe()

        tabs = st.tabs(["ABCDM", "Guarulhos", "Leste"])
        for i, item in enumerate(bases_config):
            b_label = item["label"]
            b_proj = item["projeto"]
            with tabs[i]:
                # Obter montados e parados da base a partir do Config_Equipe do Sheets se existir
                df_b_eq = df_config_eq[df_config_eq["Base"].astype(str).str.upper() == b_proj.upper()] if not df_config_eq.empty else pd.DataFrame()
                
                def_montados_base = int(df_b_eq["Montados"].sum()) if not df_b_eq.empty and "Montados" in df_b_eq.columns else (68 if "ABCDM" in b_proj else (76 if "Guarulhos" in b_proj else 80))
                def_parados_base = int(df_b_eq["Parados"].sum()) if not df_b_eq.empty and "Parados" in df_b_eq.columns else (4 if "ABCDM" in b_proj else (6 if "Guarulhos" in b_proj else 5))
                
                c1, c2, c3, c4 = st.columns(4)
                
                with c1:
                    montados_val = st.number_input(f"Total Montados ({b_label})", value=def_montados_base, key=f"inp_mon_{b_proj}")
                    parados_val = st.number_input(f"Total Parados ({b_label})", value=def_parados_base, key=f"inp_par_{b_proj}")
                
                with c2:
                    meta_os_val = st.number_input(f"Meta O.S. Mês ({b_label})", value=11800 if "ABCDM" in b_proj else 12200, key=f"inp_meta_os_{b_proj}")
                    
                    df_b_temp = st.session_state.df_valido[st.session_state.df_valido["Projeto"].str.upper() == b_proj.upper()]
                    if "Tipo de Serviço" in df_b_temp.columns:
                        df_b_temp = df_b_temp[~df_b_temp["Tipo de Serviço"].astype(str).str.upper().str.contains("RETORNO DE CREDENCIADA", na=False)]
                    prod_hoje_temp = len(df_b_temp[df_b_temp["Tipo de OS"] == "PRODUTIVA"])
                    proj_os_val, media_d, qtd_d = calcular_projecao_os_base(b_proj, dias_uteis_auto, prod_hoje_temp, data_formatada)
                    
                    st.markdown(f"**Projeção de O.S. (Mês):**\n### {fmt_br(proj_os_val)}\n*(Média: {fmt_br(media_d, 0)}/dia em {qtd_d} dias)*")

                with c3:
                    meta_cons_auto = int(montados_val * 8)
                    st.markdown(f"**Meta do Consultivo (Automático):**\n### {fmt_br(meta_cons_auto)}")
                    st.session_state[f"inp_meta_c_{b_proj}"] = meta_cons_auto

                    hoje_cons_temp = st.session_state.get(f"inp_hoje_c_{b_proj}", 12 if "ABCDM" in b_proj else (19 if "Guarulhos" in b_proj else 39))
                    proj_cons_val = int(round((hoje_cons_temp / max(1, dias_trab_auto)) * dias_uteis_auto, 0))
                    st.markdown(f"**Projeção do Consultivo:**\n### {fmt_br(proj_cons_val)}")

                with c4:
                    hoje_cons_val = st.number_input(f"Hoje Consultivo (Total do Dia) ({b_label})", value=hoje_cons_temp, key=f"inp_hoje_c_{b_proj}")
                    os_consult_val = hoje_cons_val * 2
                    st.markdown(f"**Total O.S. do Consultivo:**\n### {fmt_br(os_consult_val)}")

                st.markdown("---")
                st.markdown(f"##### 👥 Equipa de Supervisores da Base {b_label} (Carregados do Sheets):")
                sups_base = st.session_state.supervisores_por_base.get(b_proj, [])
                
                if sups_base:
                    col_s1, col_s2 = st.columns(2)
                    for sup in sups_base:
                        # Buscar valores do Sheets se houver
                        sup_eq = df_b_eq[df_b_eq["Supervisor"].astype(str).str.upper().str.strip() == sup.strip().upper()] if not df_b_eq.empty and "Supervisor" in df_b_eq.columns else pd.DataFrame()
                        m_def = int(sup_eq["Montados"].values[0]) if not sup_eq.empty and pd.notna(sup_eq["Montados"].values[0]) else 20
                        p_def = int(sup_eq["Parados"].values[0]) if not sup_eq.empty and pd.notna(sup_eq["Parados"].values[0]) else 0

                        with col_s1:
                            st.number_input(f"Montados: {sup}", value=m_def, key=f"m_{b_proj}_{sup}")
                        with col_s2:
                            st.number_input(f"Parados: {sup}", value=p_def, key=f"p_{b_proj}_{sup}")
                else:
                    st.info(f"Nenhum supervisor encontrado para o projeto {b_proj} no arquivo ANIEL carregado.")

        st.markdown("---")
        
        # --- BOTÃO DE SINCRONIZAÇÃO SEGURO COM LEITURA E APPEND PARA NÃO APAGAR NADA ---
        if st.button("📊 Sincronizar Google Sheets e Gerar Prévia Executiva", type="primary"):
            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                
                # 1. ATUALIZAR ABA 'Historico_OS'
                try:
                    df_hist_sheet = conn.read(spreadsheet=GOOGLE_SHEET_URL, worksheet="Historico_OS")
                    if df_hist_sheet is None:
                        df_hist_sheet = pd.DataFrame(columns=["Data", "Base", "OS_Executadas"])
                except Exception:
                    df_hist_sheet = pd.DataFrame(columns=["Data", "Base", "OS_Executadas"])

                for item in bases_config:
                    b_proj = item["projeto"]
                    df_b = st.session_state.df_valido[st.session_state.df_valido["Projeto"].str.upper() == b_proj.upper()]
                    if "Tipo de Serviço" in df_b.columns:
                        df_b = df_b[~df_b["Tipo de Serviço"].astype(str).str.upper().str.contains("RETORNO DE CREDENCIADA", na=False)]
                    prod_hoje = len(df_b[df_b["Tipo de OS"] == "PRODUTIVA"])
                    base_norm = normalizar_nome_base(b_proj)
                    
                    if prod_hoje > 0:
                        if not df_hist_sheet.empty and "Data" in df_hist_sheet.columns and "Base" in df_hist_sheet.columns:
                            df_hist_sheet = df_hist_sheet[~((df_hist_sheet["Data"].astype(str) == str(data_formatada)) & (df_hist_sheet["Base"].astype(str).str.upper() == base_norm))]
                        nova_h = pd.DataFrame([{"Data": str(data_formatada), "Base": base_norm, "OS_Executadas": int(prod_hoje)}])
                        df_hist_sheet = pd.concat([df_hist_sheet, nova_h], ignore_index=True)

                conn.update(spreadsheet=GOOGLE_SHEET_URL, worksheet="Historico_OS", data=df_hist_sheet)
                st.session_state["df_historico_custom"] = df_hist_sheet

                # 2. ATUALIZAR ABA 'Historico_Equipe'
                try:
                    df_hist_eq_sheet = conn.read(spreadsheet=GOOGLE_SHEET_URL, worksheet="Historico_Equipe")
                    if df_hist_eq_sheet is None:
                        df_hist_eq_sheet = pd.DataFrame(columns=["Data", "Base", "Supervisor", "Montados", "Parados"])
                except Exception:
                    df_hist_eq_sheet = pd.DataFrame(columns=["Data", "Base", "Supervisor", "Montados", "Parados"])

                linhas_nova_equipe = []
                for item in bases_config:
                    b_label = item["label"]
                    b_proj = item["projeto"]
                    sups_b = st.session_state.supervisores_por_base.get(b_proj, [])
                    for s in sups_b:
                        m_s = st.session_state.get(f"m_{b_proj}_{s}", 20)
                        p_s = st.session_state.get(f"p_{b_proj}_{s}", 0)
                        linhas_nova_equipe.append({
                            "Data": data_formatada,
                            "Base": b_label,
                            "Supervisor": s,
                            "Montados": m_s,
                            "Parados": p_s
                        })
                
                df_novo_hist_eq = pd.DataFrame(linhas_nova_equipe)
                if not df_hist_eq_sheet.empty and "Data" in df_hist_eq_sheet.columns:
                    df_hist_eq_sheet = df_hist_eq_sheet[df_hist_eq_sheet["Data"].astype(str) != str(data_formatada)]
                    df_hist_eq_final = pd.concat([df_hist_eq_sheet, df_novo_hist_eq], ignore_index=True)
                else:
                    df_hist_eq_final = df_novo_hist_eq

                conn.update(spreadsheet=GOOGLE_SHEET_URL, worksheet="Historico_Equipe", data=df_hist_eq_final)

                # 3. ATUALIZAR ABA 'Previas_Diarias'
                try:
                    df_previas_sheet = conn.read(spreadsheet=GOOGLE_SHEET_URL, worksheet="Previas_Diarias")
                    if df_previas_sheet is None:
                        df_previas_sheet = pd.DataFrame()
                except Exception:
                    df_previas_sheet = pd.DataFrame()

                novas_linhas_previa = []
                dias_uteis = st.session_state.get("dias_uteis_auto", 27)
                dias_trab = st.session_state.get("dias_trab_auto", 19)

                for item in bases_config:
                    b_label = item["label"]
                    b_proj = item["projeto"]
                    df_b = st.session_state.df_valido[st.session_state.df_valido["Projeto"].str.upper() == b_proj.upper()]
                    if "Tipo de Serviço" in df_b.columns:
                        df_b = df_b[~df_b["Tipo de Serviço"].astype(str).str.upper().str.contains("RETORNO DE CREDENCIADA", na=False)]
                    
                    p_base = st.session_state.get(f"inp_par_{b_proj}", 4)
                    m_base = st.session_state.get(f"inp_mon_{b_proj}", 68)
                    meta_os_b = st.session_state.get(f"inp_meta_os_{b_proj}", 11800)
                    meta_c_b = int(m_base * 8)
                    hoje_c_b = st.session_state.get(f"inp_hoje_c_{b_proj}", 12)
                    ganho_b = st.session_state.get(f"inp_ganho_{b_proj}", 27)

                    def calc_exp_met(df_sub, montados, hoje_c):
                        tot_os = len(df_sub)
                        df_prod = df_sub[df_sub["Tipo de OS"] == "PRODUTIVA"] if "Tipo de OS" in df_sub.columns else pd.DataFrame()
                        df_improd = df_sub[df_sub["Tipo de OS"] == "IMPRODUTIVA"] if "Tipo de OS" in df_sub.columns else pd.DataFrame()
                        df_aberto = df_sub[df_sub["Tipo de OS"] == "EM ABERTO"] if "Tipo de OS" in df_sub.columns else pd.DataFrame()
                        df_canc = df_sub[df_sub["Tipo de OS"] == "CANCELADO"] if "Tipo de OS" in df_sub.columns else pd.DataFrame()
                        df_saiu = df_sub[df_sub["Tipo de OS"] == "SAIU DO TOA"] if "Tipo de OS" in df_sub.columns else pd.DataFrame()

                        prod_count = len(df_prod)
                        improd_count = len(df_improd)
                        aberta_count = len(df_aberto)
                        
                        den_quebra = improd_count + prod_count
                        quebra_pct = (improd_count / den_quebra) if den_quebra > 0 else 0.0
                        efic = max(0.0, 1.0 - quebra_pct)
                        proj_os_exec = prod_count + (aberta_count * efic)
                        proj_dia = int(round(proj_os_exec, 0))
                        
                        pontos_prod = df_prod["Pontos Prev."].sum() if "Pontos Prev." in df_prod.columns else 0.0
                        pontos_improd = df_improd["Pontos Prev."].sum() if "Pontos Prev." in df_improd.columns else 0.0
                        pontos_aberto = df_aberto["Pontos Prev."].sum() if "Pontos Prev." in df_aberto.columns else 0.0
                        den_pts = pontos_improd + pontos_prod
                        efic_pts = max(0.0, 1.0 - (pontos_improd / den_pts)) if den_pts > 0 else 0.0
                        pontos = int(round(pontos_prod + (pontos_aberto * efic_pts), 0))
                        
                        media_os = (proj_dia / montados) if montados > 0 else 0.0

                        def c_sub(df_item):
                            if "Tipo de OS" not in df_item.columns: return 0.0
                            i = len(df_item[df_item["Tipo de OS"] == "IMPRODUTIVA"])
                            p = len(df_item[df_item["Tipo de OS"] == "PRODUTIVA"])
                            d = i + p
                            return (i / d * 100) if d > 0 else 0.0

                        df_ins = df_sub[df_sub["QUEBRAS"] == "INSTALAÇÃO"] if "QUEBRAS" in df_sub.columns else pd.DataFrame()
                        df_serv = df_sub[df_sub["QUEBRAS"] == "SERVIÇOS"] if "QUEBRAS" in df_sub.columns else pd.DataFrame()
                        df_gpon = df_sub[df_sub["ATIVIDADES"] == "GPON"] if "ATIVIDADES" in df_sub.columns else pd.DataFrame()
                        df_mig = df_sub[df_sub["ATIVIDADES"] == "MIGRAÇÃO"] if "ATIVIDADES" in df_sub.columns else pd.DataFrame()
                        df_ret = df_sub[df_sub["QUEBRAS"] == "RETORNO"] if "QUEBRAS" in df_sub.columns else pd.DataFrame()
                        
                        pme_col = df_sub["PME"].fillna("").astype(str).str.strip().str.upper() if "PME" in df_sub.columns else pd.Series()
                        df_pme = df_sub[(pme_col != "") & (pme_col != "NAN") & (pme_col.str.contains("PME|EMP", regex=True))] if not pme_col.empty else pd.DataFrame()

                        servicos_nd_alvos = [
                            "ADESAO - INSTALACAO DE ASSINATURA",
                            "ADESAO - INSTALACAO DE ASSINATURA DIGITAL",
                            "ADESAO ENTREGA STREAMING"
                        ]
                        ts_col = df_sub["Tipo de Serviço"].astype(str).str.upper().str.strip() if "Tipo de Serviço" in df_sub.columns else pd.Series()
                        df_nd_base = df_sub[ts_col.isin([s.upper() for s in servicos_nd_alvos])] if not ts_col.empty else pd.DataFrame()
                        
                        nd_prod = len(df_nd_base[df_nd_base["Tipo de OS"] == "PRODUTIVA"]) if "Tipo de OS" in df_nd_base.columns else 0
                        nd_improd = len(df_nd_base[df_nd_base["Tipo de OS"] == "IMPRODUTIVA"]) if "Tipo de OS" in df_nd_base.columns else 0
                        nd_aberto = len(df_nd_base[df_nd_base["Tipo de OS"] == "EM ABERTO"]) if "Tipo de OS" in df_nd_base.columns else 0
                        den_nd = nd_improd + nd_prod
                        efic_nd = max(0.0, 1.0 - (nd_improd / den_nd)) if den_nd > 0 else 0.0
                        proj_nd = int(round(nd_prod + (nd_aberto * efic_nd), 0))

                        return {
                            "tot_os": tot_os, "os_aberta": aberta_count, "pontos": pontos,
                            "efic": round(efic * 100, 1), "media_os": round(media_os, 2), "proj_dia": proj_dia,
                            "q_ins": round(c_sub(df_ins), 1), "q_serv": round(c_sub(df_serv), 1),
                            "tot_nd": proj_nd, "q_nd": round(c_sub(df_nd_base), 1),
                            "os_canc": len(df_canc), "saiu_toa": len(df_saiu),
                            "tot_gpon": len(df_gpon), "q_gpon": round(c_sub(df_gpon), 1),
                            "tot_mig": len(df_mig), "q_mig": round(c_sub(df_mig), 1),
                            "canc_mig": len(df_mig[df_mig["CANCELADAS"] == "CANCELADO"]) if "CANCELADAS" in df_mig.columns else 0,
                            "retorno_wo": len(df_ret), "tot_pme": len(df_pme),
                            "q_pme": round(c_sub(df_pme), 1),
                            "canc_pme": len(df_pme[df_pme["CANCELADAS"] == "CANCELADO"]) if "CANCELADAS" in df_pme.columns else 0
                        }

                    res_b = calc_exp_met(df_b, m_base, hoje_c_b)
                    proj_os_b, _, _ = calcular_projecao_os_base(b_proj, dias_uteis, res_b["produtivo"] if "produtivo" in res_b else 0, data_formatada)
                    proj_c_b = int(round((hoje_c_b / dias_trab) * dias_uteis)) if dias_trab > 0 else 0
                    os_consult_b = hoje_c_b * 2
                    os_sem_consult_val = int(round(res_b["proj_dia"] - os_consult_b, 0))

                    novas_linhas_previa.append({
                        "Data": data_formatada,
                        "Base": b_label,
                        "Parados": p_base,
                        "Montados": m_base,
                        "Meta O.S.": meta_os_b,
                        "Projeção O.S.": proj_os_b,
                        "Meta Consultivo": meta_c_b,
                        "Projeção Consultivo": proj_c_b,
                        "Hoje Consultivo": hoje_c_b,
                        "O.S. Consultivo": os_consult_b,
                        "Total O.S.": res_b["tot_os"],
                        "O.S. Aberta": res_b["os_aberta"],
                        "Pontos": res_b["pontos"],
                        "Efic (%)": res_b["efic"],
                        "Média O.S.": res_b["media_os"],
                        "O.S. Exec. (Proj)": res_b["proj_dia"],
                        "O.S. Sem Consult": os_sem_consult_val,
                        "Quebra INS (%)": res_b["q_ins"],
                        "Quebra SERV (%)": res_b["q_serv"],
                        "Quebra ND (%)": res_b["q_nd"],
                        "O.S. Canc.": res_b["os_canc"],
                        "Saiu TOA": res_b["saiu_toa"],
                        "Ganho O.S.": ganho_b,
                        "GPON Total": res_b["tot_gpon"],
                        "GPON Quebra (%)": res_b["q_gpon"],
                        "Migração Total": res_b["tot_mig"],
                        "Migração Quebra (%)": res_b["q_mig"],
                        "Migração Canc.": res_b["canc_mig"],
                        "Retorno WO": res_b["retorno_wo"],
                        "PME WO": res_b["tot_pme"],
                        "PME Quebra (%)": res_b["q_pme"],
                        "PME Canc.": res_b["canc_pme"]
                    })

                df_nova_previa = pd.DataFrame(novas_linhas_previa)
                
                if not df_previas_sheet.empty and "Data" in df_previas_sheet.columns and "Base" in df_previas_sheet.columns:
                    df_previas_sheet = df_previas_sheet[
                        ~((df_previas_sheet["Data"].astype(str) == str(data_formatada)) & 
                          (df_previas_sheet["Base"].isin([b["label"] for b in bases_config])))
                    ]
                    df_previa_final = pd.concat([df_previas_sheet, df_nova_previa], ignore_index=True)
                else:
                    df_previa_final = df_nova_previa

                conn.update(spreadsheet=GOOGLE_SHEET_URL, worksheet="Previas_Diarias", data=df_previa_final)
                st.success("✅ Histórico preservado e prévia completa sincronizada com sucesso no Google Sheets!")
                
            except Exception as e:
                st.error(f"Erro ao conectar ou escrever no Google Sheets: {e}")
            
            st.session_state["ir_para_passo_3_ativo"] = True
            st.rerun()

# ==============================================================================
# PÁGINA 3: VISUALIZAÇÃO DA PRÉVIA (COM HISTÓRICO E SUPERVISORES)
# ==============================================================================
elif st.session_state["pagina_atual"] == "3. Visualização da Prévia":
    st.subheader("📊 Passo 3: Apresentação da Prévia Diária - Diretoria")

    df_valido = st.session_state.df_valido if st.session_state.df_valido is not None else obter_df_historico()
    dias_uteis = st.session_state.get("dias_uteis_auto", 27)
    dias_trab = st.session_state.get("dias_trab_auto", 19)
    data_formatada = data_selecionada

    def calcular_metricas(df_sub, montados, hoje_c):
        if isinstance(df_sub, pd.DataFrame) and not df_sub.empty:
            if "Tipo de Serviço" in df_sub.columns:
                df_sub = df_sub[~df_sub["Tipo de Serviço"].astype(str).str.upper().str.contains("RETORNO DE CREDENCIADA", na=False)].copy()

            tot_os = len(df_sub)
            df_prod = df_sub[df_sub["Tipo de OS"] == "PRODUTIVA"] if "Tipo de OS" in df_sub.columns else pd.DataFrame()
            df_improd = df_sub[df_sub["Tipo de OS"] == "IMPRODUTIVA"] if "Tipo de OS" in df_sub.columns else pd.DataFrame()
            df_aberto = df_sub[df_sub["Tipo de OS"] == "EM ABERTO"] if "Tipo de OS" in df_sub.columns else pd.DataFrame()
            df_canc = df_sub[df_sub["Tipo de OS"] == "CANCELADO"] if "Tipo de OS" in df_sub.columns else pd.DataFrame()
            df_saiu = df_sub[df_sub["Tipo de OS"] == "SAIU DO TOA"] if "Tipo de OS" in df_sub.columns else pd.DataFrame()

            prod_count = len(df_prod)
            improd_count = len(df_improd)
            aberta_count = len(df_aberto)
            os_aberta = aberta_count
            
            den_quebra = improd_count + prod_count
            quebra_pct = (improd_count / den_quebra) if den_quebra > 0 else 0.0
            efic = max(0.0, 1.0 - quebra_pct)
            
            proj_os_exec = prod_count + (aberta_count * efic)
            proj_dia = int(round(proj_os_exec, 0))
            
            pontos_prod = df_prod["Pontos Prev."].sum() if "Pontos Prev." in df_prod.columns else 0.0
            pontos_improd = df_improd["Pontos Prev."].sum() if "Pontos Prev." in df_improd.columns else 0.0
            pontos_aberto = df_aberto["Pontos Prev."].sum() if "Pontos Prev." in df_aberto.columns else 0.0
            
            den_pts = pontos_improd + pontos_prod
            efic_pts = max(0.0, 1.0 - (pontos_improd / den_pts)) if den_pts > 0 else 0.0
            pontos = int(round(pontos_prod + (pontos_aberto * efic_pts), 0))
            
            media_os = (proj_dia / montados) if montados > 0 else 0.0
            
            os_canc = len(df_canc)
            saiu_toa = len(df_saiu)

            def calc_q_sub(df_item):
                if "Tipo de OS" not in df_item.columns: return 0.0
                i_c = len(df_item[df_item["Tipo de OS"] == "IMPRODUTIVA"])
                p_c = len(df_item[df_item["Tipo de OS"] == "PRODUTIVA"])
                d_c = i_c + p_c
                return (i_c / d_c * 100) if d_c > 0 else 0.0

            df_ins = df_sub[df_sub["QUEBRAS"] == "INSTALAÇÃO"] if "QUEBRAS" in df_sub.columns else pd.DataFrame()
            df_serv = df_sub[df_sub["QUEBRAS"] == "SERVIÇOS"] if "QUEBRAS" in df_sub.columns else pd.DataFrame()
            
            servicos_nd_alvos = [
                "ADESAO - INSTALACAO DE ASSINATURA",
                "ADESAO - INSTALACAO DE ASSINATURA DIGITAL",
                "ADESAO ENTREGA STREAMING"
            ]
            ts_col = df_sub["Tipo de Serviço"].astype(str).str.upper().str.strip() if "Tipo de Serviço" in df_sub.columns else pd.Series()
            df_nd_base = df_sub[ts_col.isin([s.upper() for s in servicos_nd_alvos])] if not ts_col.empty else pd.DataFrame()
            
            nd_prod = len(df_nd_base[df_nd_base["Tipo de OS"] == "PRODUTIVA"]) if "Tipo de OS" in df_nd_base.columns else 0
            nd_improd = len(df_nd_base[df_nd_base["Tipo de OS"] == "IMPRODUTIVA"]) if "Tipo de OS" in df_nd_base.columns else 0
            nd_aberto = len(df_nd_base[df_nd_base["Tipo de OS"] == "EM ABERTO"]) if "Tipo de OS" in df_nd_base.columns else 0
            den_nd = nd_improd + nd_prod
            efic_nd = max(0.0, 1.0 - (nd_improd / den_nd)) if den_nd > 0 else 0.0
            proj_nd = int(round(nd_prod + (nd_aberto * efic_nd), 0))

            df_gpon = df_sub[df_sub["ATIVIDADES"] == "GPON"] if "ATIVIDADES" in df_sub.columns else pd.DataFrame()
            df_mig = df_sub[df_sub["ATIVIDADES"] == "MIGRAÇÃO"] if "ATIVIDADES" in df_sub.columns else pd.DataFrame()
            df_ret = df_sub[df_sub["QUEBRAS"] == "RETORNO"] if "QUEBRAS" in df_sub.columns else pd.DataFrame()
            
            pme_col = df_sub["PME"].fillna("").astype(str).str.strip().str.upper() if "PME" in df_sub.columns else pd.Series()
            df_pme = df_sub[(pme_col != "") & (pme_col != "NAN") & (pme_col.str.contains("PME|EMP", regex=True))] if not pme_col.empty else pd.DataFrame()

            return {
                "tot_os": tot_os, "os_aberta": os_aberta, "produtivo": prod_count,
                "quebra_geral": improd_count, "pontos": pontos,
                "efic": efic * 100, "media_os": media_os, "proj_dia": proj_dia,
                "os_canc": os_canc, "saiu_toa": saiu_toa,
                "q_ins": calc_q_sub(df_ins), "q_serv": calc_q_sub(df_serv),
                "tot_nd": proj_nd, "q_nd": calc_q_sub(df_nd_base),
                "tot_gpon": len(df_gpon), "q_gpon": calc_q_sub(df_gpon),
                "tot_mig": len(df_mig), "q_mig": calc_q_sub(df_mig),
                "canc_mig": len(df_mig[df_mig["CANCELADAS"] == "CANCELADO"]) if "CANCELADAS" in df_mig.columns else 0,
                "retorno_wo": len(df_ret), "tot_pme": len(df_pme),
                "q_pme": calc_q_sub(df_pme),
                "canc_pme": len(df_pme[df_pme["CANCELADAS"] == "CANCELADO"]) if "CANCELADAS" in df_pme.columns else 0,
                "_raw_q_ins": len(df_ins[df_ins["Tipo de OS"] == "IMPRODUTIVA"]) if "Tipo de OS" in df_ins.columns else 0,
                "_raw_tot_ins": len(df_ins[df_ins["Tipo de OS"].isin(["PRODUTIVA", "IMPRODUTIVA"])]) if "Tipo de OS" in df_ins.columns else 0,
                "_raw_q_serv": len(df_serv[df_serv["Tipo de OS"] == "IMPRODUTIVA"]) if "Tipo de OS" in df_serv.columns else 0,
                "_raw_tot_serv": len(df_serv[df_serv["Tipo de OS"].isin(["PRODUTIVA", "IMPRODUTIVA"])]) if "Tipo de OS" in df_serv.columns else 0,
                "_raw_q_nd": nd_improd,
                "_raw_q_gpon": len(df_gpon[df_gpon["Tipo de OS"] == "IMPRODUTIVA"]) if "Tipo de OS" in df_gpon.columns else 0,
                "_raw_q_mig": len(df_mig[df_mig["Tipo de OS"] == "IMPRODUTIVA"]) if "Tipo de OS" in df_mig.columns else 0,
                "_raw_q_pme": len(df_pme[df_pme["Tipo de OS"] == "IMPRODUTIVA"]) if "Tipo de OS" in df_pme.columns else 0
            }
        return {
            "tot_os": 0, "os_aberta": 0, "produtivo": 0, "quebra_geral": 0, "pontos": 0,
            "efic": 0.0, "media_os": 0.0, "proj_dia": 0, "os_canc": 0, "saiu_toa": 0,
            "q_ins": 0.0, "q_serv": 0.0, "tot_nd": 0, "q_nd": 0.0, "tot_gpon": 0, "q_gpon": 0.0,
            "tot_mig": 0, "q_mig": 0.0, "canc_mig": 0, "retorno_wo": 0, "tot_pme": 0, "q_pme": 0.0,
            "canc_pme": 0, "_raw_q_ins": 0, "_raw_tot_ins": 0, "_raw_q_serv": 0, "_raw_tot_serv": 0,
            "_raw_q_nd": 0, "_raw_q_gpon": 0, "_raw_q_mig": 0, "_raw_q_pme": 0
        }

    def gerar_cabecalho_html():
        return f"""
        <table class="custom-table">
            <thead>
                <tr>
                    <th rowspan="2" class="th-data">{data_formatada}</th>
                    <th rowspan="2" class="th-data">Parados</th>
                    <th rowspan="2" class="th-data col-destaque-amarelo">Montados</th>
                    <th colspan="2" class="th-qtd-os">QTDE. DE O.S. OUTUBRO</th>
                    <th colspan="4" class="th-consult">CONSULTIVO OUTUBRO</th>
                    <th colspan="10" class="th-prod">PRODUTIVIDADE (Projeção)</th>
                    <th rowspan="2" class="th-prod">ND</th>
                    <th colspan="2" class="th-quebra-claro">QUEBRA CLARO</th>
                    <th rowspan="2" class="th-ganho">GANHO<br>O.S.</th>
                    <th colspan="2" class="th-gpon">GPON</th>
                    <th colspan="3" class="th-mig">MIGRAÇÃO</th>
                    <th rowspan="2" class="th-retorno">RETORNO<br>WO</th>
                    <th colspan="3" class="th-pme">PME</th>
                </tr>
                <tr>
                    <th class="th-qtd-os">Meta</th>
                    <th class="th-qtd-os">Projeção</th>
                    <th class="th-consult">Meta</th>
                    <th class="th-consult">Projeção</th>
                    <th class="th-consult">Hoje</th>
                    <th class="th-consult">O.S</th>
                    <th class="th-prod">TOTAL O.S.</th>
                    <th class="th-prod">O.S. ABERTA</th>
                    <th class="th-prod">Pontos</th>
                    <th class="th-prod">Efic. (%)</th>
                    <th class="th-prod col-destaque-azul">Média O.S.</th>
                    <th class="th-prod">O.S. Exec.</th>
                    <th class="th-prod col-destaque-amarelo">O.S Sem Consult</th>
                    <th class="th-prod">Quebra INS (%)</th>
                    <th class="th-prod">Quebra SERV (%)</th>
                    <th class="th-prod">Quebra ND (%)</th>
                    <th class="th-quebra-claro">O.S. Canc.</th>
                    <th class="th-quebra-claro">Saiu TOA</th>
                    <th class="th-gpon">Total O.S.</th>
                    <th class="th-gpon">Quebra</th>
                    <th class="th-mig">Total O.S.</th>
                    <th class="th-mig">Quebra</th>
                    <th class="th-mig">Canc.</th>
                    <th class="th-pme">WO</th>
                    <th class="th-pme">Quebra</th>
                    <th class="th-pme">Canc.</th>
                </tr>
            </thead>
            <tbody>
        """

    g_parados = 0; g_montados = 0; g_meta_os = 0; g_proj_os = 0
    g_meta_cons = 0; g_proj_cons = 0; g_hoje_cons = 0; g_os_cons = 0
    g_tot_os = 0; g_aberta = 0; g_pontos = 0; g_prod = 0; g_quebra = 0
    g_sem_cons = 0; g_nd = 0; g_canc = 0; g_saiu_toa = 0; g_ganho = 0
    g_gpon = 0; g_mig = 0; g_mig_canc = 0; g_retorno = 0; g_pme = 0; g_pme_canc = 0
    g_raw_ins_q = 0; g_raw_ins_tot = 0; g_raw_serv_q = 0; g_raw_serv_tot = 0
    g_raw_nd_q = 0; g_raw_gpon_q = 0; g_raw_mig_q = 0; g_raw_pme_q = 0

    metricas_bases = {}

    df_config_eq_l = carregar_config_equipe()

    for item in bases_config:
        b_label = item["label"]
        b_proj = item["projeto"]
        
        df_b = df_valido[df_valido["Projeto"].str.upper() == b_proj.upper()] if isinstance(df_valido, pd.DataFrame) and "Projeto" in df_valido.columns else pd.DataFrame()
        if not df_b.empty and "Tipo de Serviço" in df_b.columns:
            df_b = df_b[~df_b["Tipo de Serviço"].astype(str).str.upper().str.contains("RETORNO DE CREDENCIADA", na=False)]
        
        df_b_eq_l = df_config_eq_l[df_config_eq_l["Base"].astype(str).str.upper() == b_proj.upper()] if not df_config_eq_l.empty else pd.DataFrame()
        m_base = int(df_b_eq_l["Montados"].sum()) if not df_b_eq_l.empty and "Montados" in df_b_eq_l.columns else (68 if "ABCDM" in b_proj else (76 if "Guarulhos" in b_proj else 80))
        p_base = int(df_b_eq_l["Parados"].sum()) if not df_b_eq_l.empty and "Parados" in df_b_eq_l.columns else (4 if "ABCDM" in b_proj else (6 if "Guarulhos" in b_proj else 5))

        meta_os_b = 11800 if "ABCDM" in b_proj else 12200
        meta_c_b = int(m_base * 8)
        hoje_c_b = 12 if "ABCDM" in b_proj else (19 if "Guarulhos" in b_proj else 39)
        ganho_b = 27 if "ABCDM" in b_proj else (40 if "Guarulhos" in b_proj else 42)

        res_b = calcular_metricas(df_b, m_base, hoje_c_b)
        
        os_sem_consult_val = int(round(res_b["proj_dia"] - (hoje_c_b * 2), 0))
        res_b["os_sem_c"] = os_sem_consult_val

        proj_os_b, _, _ = calcular_projecao_os_base(b_proj, dias_uteis, res_b["produtivo"], data_formatada)
        
        proj_c_b = int(round((hoje_c_b / dias_trab) * dias_uteis)) if dias_trab > 0 else 0
        os_consult_b = hoje_c_b * 2

        g_parados += p_base; g_montados += m_base; g_meta_os += meta_os_b; g_proj_os += proj_os_b
        g_meta_cons += meta_c_b; g_proj_cons += proj_c_b; g_hoje_cons += hoje_c_b; g_os_cons += os_consult_b
        g_tot_os += res_b["tot_os"]; g_aberta += res_b["os_aberta"]; g_pontos += res_b["pontos"]; g_prod += res_b["produtivo"]
        g_quebra += res_b["quebra_geral"]; g_sem_cons += res_b["os_sem_c"]; g_nd += res_b["tot_nd"]
        g_canc += res_b["os_canc"]; g_saiu_toa += res_b["saiu_toa"]; g_ganho += ganho_b
        g_gpon += res_b["tot_gpon"]; g_mig += res_b["tot_mig"]; g_mig_canc += res_b["canc_mig"]
        g_retorno += res_b["retorno_wo"]; g_pme += res_b["tot_pme"]; g_pme_canc += res_b["canc_pme"]
        g_raw_ins_q += res_b["_raw_q_ins"]; g_raw_ins_tot += res_b["_raw_tot_ins"]
        g_raw_serv_q += res_b["_raw_q_serv"]; g_raw_serv_tot += res_b["_raw_tot_serv"]
        g_raw_nd_q += res_b["_raw_q_nd"]; g_raw_gpon_q += res_b["_raw_q_gpon"]
        g_raw_mig_q += res_b["_raw_q_mig"]; g_raw_pme_q += res_b["_raw_q_pme"]

        metricas_bases[b_proj] = {
            "res": res_b, "p_base": p_base, "m_base": m_base, "meta_os": meta_os_b,
            "proj_os": proj_os_b, "meta_c": meta_c_b, "proj_c": proj_c_b, "hoje_c": hoje_c_b,
            "os_consult": os_consult_b, "ganho": ganho_b, "label": b_label
        }

    # --- TABELA PRINCIPAL CONSOLIDADA DA DIRETORIA ---
    tabela_html = [gerar_cabecalho_html()]

    for item in bases_config:
        b_label = item["label"]
        b_proj = item["projeto"]
        m = metricas_bases[b_proj]
        res = m["res"]
        
        tabela_html.append(
            f'<tr class="tr-base">'
            f'<td style="text-align: left; padding-left: 8px;">{b_label}</td>'
            f'<td>{fmt_br(m["p_base"])}</td>'
            f'<td class="col-destaque-amarelo">{fmt_br(m["m_base"])}</td>'
            f'<td>{fmt_br(m["meta_os"])}</td>'
            f'<td class="red-text">{fmt_br(m["proj_os"])}</td>'
            f'<td>{fmt_br(m["meta_c"])}</td>'
            f'<td class="red-text">{fmt_br(m["proj_c"])}</td>'
            f'<td>{fmt_br(m["hoje_c"])}</td>'
            f'<td>{fmt_br(m["os_consult"])}</td>'
            f'<td>{fmt_br(res["tot_os"])}</td>'
            f'<td>{fmt_br(res["os_aberta"])}</td>'
            f'<td>{fmt_br(res["pontos"])}</td>'
            f'<td>{fmt_br(res["efic"], 1)}%</td>'
            f'<td class="col-destaque-azul">{fmt_br(res["media_os"], 2)}</td>'
            f'<td>{fmt_br(res["proj_dia"])}</td>'
            f'<td class="col-destaque-amarelo">{fmt_br(res["os_sem_c"])}</td>'
            f'<td>{fmt_br(res["q_ins"], 1)}%</td>'
            f'<td>{fmt_br(res["q_serv"], 1)}%</td>'
            f'<td>{fmt_br(res["q_nd"], 1)}%</td>'
            f'<td>{fmt_br(res["tot_nd"])}</td>'
            f'<td>{fmt_br(res["os_canc"])}</td>'
            f'<td>{fmt_br(res["saiu_toa"])}</td>'
            f'<td>{fmt_br(m["ganho"])}</td>'
            f'<td>{fmt_br(res["tot_gpon"])}</td>'
            f'<td>{fmt_br(res["q_gpon"], 1)}%</td>'
            f'<td>{fmt_br(res["tot_mig"])}</td>'
            f'<td>{fmt_br(res["q_mig"], 1)}%</td>'
            f'<td>{fmt_br(res["canc_mig"])}</td>'
            f'<td>{fmt_br(res["retorno_wo"])}</td>'
            f'<td>{fmt_br(res["tot_pme"])}</td>'
            f'<td>{fmt_br(res["q_pme"], 1)}%</td>'
            f'<td>{fmt_br(res["canc_pme"])}</td>'
            f'</tr>'
        )

    g_den_quebra = g_quebra + g_prod
    g_efic = (max(0.0, 1.0 - (g_quebra / g_den_quebra)) * 100) if g_den_quebra > 0 else 0.0
    g_proj_exec_total = int(round(g_prod + (g_aberta * (g_efic / 100.0)), 0))
    g_media_os = (g_proj_exec_total / g_montados) if g_montados > 0 else 0.0
    g_os_sem_c_total = g_proj_exec_total - g_os_cons
    g_q_ins = (g_raw_ins_q / g_raw_ins_tot * 100) if g_raw_ins_tot > 0 else 0.0
    g_q_serv = (g_raw_serv_q / g_raw_serv_tot * 100) if g_raw_serv_tot > 0 else 0.0
    g_q_nd = (g_raw_nd_q / g_nd * 100) if g_nd > 0 else 0.0
    g_q_gpon = (g_raw_gpon_q / g_gpon * 100) if g_gpon > 0 else 0.0
    g_q_mig = (g_raw_mig_q / g_mig * 100) if g_mig > 0 else 0.0
    g_q_pme = (g_raw_pme_q / g_pme * 100) if g_pme > 0 else 0.0

    tabela_html.append(
        f'<tr class="tr-total">'
        f'<td style="text-align: left; padding-left: 8px;">TOTAL INSTALAÇÃO</td>'
        f'<td>{fmt_br(g_parados)}</td>'
        f'<td class="col-destaque-amarelo">{fmt_br(g_montados)}</td>'
        f'<td>{fmt_br(g_meta_os)}</td>'
        f'<td class="red-text">{fmt_br(g_proj_os)}</td>'
        f'<td>{fmt_br(g_meta_cons)}</td>'
        f'<td class="red-text">{fmt_br(g_proj_cons)}</td>'
        f'<td>{fmt_br(g_hoje_cons)}</td>'
        f'<td>{fmt_br(g_os_cons)}</td>'
        f'<td>{fmt_br(g_tot_os)}</td>'
        f'<td>{fmt_br(g_aberta)}</td>'
        f'<td>{fmt_br(g_pontos)}</td>'
        f'<td>{fmt_br(g_efic, 1)}%</td>'
        f'<td class="col-destaque-azul">{fmt_br(g_media_os, 2)}</td>'
        f'<td>{fmt_br(g_proj_exec_total)}</td>'
        f'<td class="col-destaque-amarelo">{fmt_br(g_os_sem_c_total)}</td>'
        f'<td>{fmt_br(g_q_ins, 1)}%</td>'
        f'<td>{fmt_br(g_q_serv, 1)}%</td>'
        f'<td>{fmt_br(g_q_nd, 1)}%</td>'
        f'<td>{fmt_br(g_nd)}</td>'
        f'<td>{fmt_br(g_canc)}</td>'
        f'<td>{fmt_br(g_saiu_toa)}</td>'
        f'<td>{fmt_br(g_ganho)}</td>'
        f'<td>{fmt_br(g_gpon)}</td>'
        f'<td>{fmt_br(g_q_gpon, 1)}%</td>'
        f'<td>{fmt_br(g_mig)}</td>'
        f'<td>{fmt_br(g_q_mig, 1)}%</td>'
        f'<td>{fmt_br(g_mig_canc)}</td>'
        f'<td>{fmt_br(g_retorno)}</td>'
        f'<td>{fmt_br(g_pme)}</td>'
        f'<td>{fmt_br(g_q_pme, 1)}%</td>'
        f'<td>{fmt_br(g_pme_canc)}</td>'
        f'</tr>'
        f'</tbody>'
        f'</table>'
    )

    st.markdown("".join(tabela_html), unsafe_allow_html=True)
    st.markdown("<br><hr><br>", unsafe_allow_html=True)

    # --- BLOCOS INDEPENDENTES POR BASE COM OS SUPERVISORES ---
    st.markdown("### 🏢 Detalhamento Operacional Separado por Base")

    for item in bases_config:
        b_label = item["label"]
        b_proj = item["projeto"]
        m = metricas_bases[b_proj]
        res_b = m["res"]
        
        with st.expander(f"📂 Base: {b_label} (Clique para Expandir/Recolher Detalhamento)"):
            df_b = df_valido[df_valido["Projeto"].str.upper() == b_proj.upper()] if isinstance(df_valido, pd.DataFrame) and "Projeto" in df_valido.columns else pd.DataFrame()
            if not df_b.empty and "Tipo de Serviço" in df_b.columns:
                df_b = df_b[~df_b["Tipo de Serviço"].astype(str).str.upper().str.contains("RETORNO DE CREDENCIADA", na=False)]
            sups_b = st.session_state.supervisores_por_base.get(b_proj, [])
            
            tabela_bloco_html = [
                gerar_cabecalho_html(),
                f'<tr class="tr-base">'
                f'<td style="text-align: left; padding-left: 8px;">{b_label}</td>'
                f'<td>{fmt_br(m["p_base"])}</td>'
                f'<td class="col-destaque-amarelo">{fmt_br(m["m_base"])}</td>'
                f'<td>{fmt_br(m["meta_os"])}</td>'
                f'<td class="red-text">{fmt_br(m["proj_os"])}</td>'
                f'<td>{fmt_br(m["meta_c"])}</td>'
                f'<td class="red-text">{fmt_br(m["proj_c"])}</td>'
                f'<td>{fmt_br(m["hoje_c"])}</td>'
                f'<td>{fmt_br(m["os_consult"])}</td>'
                f'<td>{fmt_br(res_b["tot_os"])}</td>'
                f'<td>{fmt_br(res_b["os_aberta"])}</td>'
                f'<td>{fmt_br(res_b["pontos"])}</td>'
                f'<td>{fmt_br(res_b["efic"], 1)}%</td>'
                f'<td class="col-destaque-azul">{fmt_br(res_b["media_os"], 2)}</td>'
                f'<td>{fmt_br(res_b["proj_dia"])}</td>'
                f'<td class="col-destaque-amarelo">{fmt_br(res_b["os_sem_c"])}</td>'
                f'<td>{fmt_br(res_b["q_ins"], 1)}%</td>'
                f'<td>{fmt_br(res_b["q_serv"], 1)}%</td>'
                f'<td>{fmt_br(res_b["q_nd"], 1)}%</td>'
                f'<td>{fmt_br(res_b["tot_nd"])}</td>'
                f'<td>{fmt_br(res_b["os_canc"])}</td>'
                f'<td>{fmt_br(res_b["saiu_toa"])}</td>'
                f'<td>{fmt_br(m["ganho"])}</td>'
                f'<td>{fmt_br(res_b["tot_gpon"])}</td>'
                f'<td>{fmt_br(res_b["q_gpon"], 1)}%</td>'
                f'<td>{fmt_br(res_b["tot_mig"])}</td>'
                f'<td>{fmt_br(res_b["q_mig"], 1)}%</td>'
                f'<td>{fmt_br(res_b["canc_mig"])}</td>'
                f'<td>{fmt_br(res_b["retorno_wo"])}</td>'
                f'<td>{fmt_br(res_b["tot_pme"])}</td>'
                f'<td>{fmt_br(res_b["q_pme"], 1)}%</td>'
                f'<td>{fmt_br(res_b["canc_pme"])}</td>'
                f'</tr>'
            ]

            for s in sups_b:
                df_s = df_b[df_b["Supervisor"] == s] if not df_b.empty and "Supervisor" in df_b.columns else pd.DataFrame()
                p_sup = st.session_state.get(f"p_{b_proj}_{s}", 0)
                m_sup = st.session_state.get(f"m_{b_proj}_{s}", 20)
                res_s = calcular_metricas(df_s, m_sup, 0)
                primeiro_nome = s.split()[0]
                
                tabela_bloco_html.append(
                    f'<tr class="tr-sup">'
                    f'<td style="text-align: left; padding-left: 20px;">{primeiro_nome}</td>'
                    f'<td>{fmt_br(p_sup)}</td>'
                    f'<td class="col-destaque-amarelo">{fmt_br(m_sup)}</td>'
                    f'<td></td><td></td><td></td><td></td><td></td><td></td>'
                    f'<td>{fmt_br(res_s["tot_os"])}</td>'
                    f'<td>{fmt_br(res_s["os_aberta"])}</td>'
                    f'<td>{fmt_br(res_s["pontos"])}</td>'
                    f'<td>{fmt_br(res_s["efic"], 1)}%</td>'
                    f'<td class="col-destaque-azul">{fmt_br(res_s["media_os"], 2)}</td>'
                    f'<td>{fmt_br(res_s["proj_dia"])}</td>'
                    f'<td></td>'
                    f'<td>{fmt_br(res_s["q_ins"], 1)}%</td>'
                    f'<td>{fmt_br(res_s["q_serv"], 1)}%</td>'
                    f'<td>{fmt_br(res_s["q_nd"], 1)}%</td>'
                    f'<td>{fmt_br(res_s["tot_nd"])}</td>'
                    f'<td>{fmt_br(res_s["os_canc"])}</td>'
                    f'<td>{fmt_br(res_s["saiu_toa"])}</td>'
                    f'<td></td><td></td><td></td><td></td><td></td><td></td><td></td>'
                    f'<td>{fmt_br(res_s["tot_pme"])}</td>'
                    f'<td>{fmt_br(res_s["q_pme"], 1)}%</td>'
                    f'<td>{fmt_br(res_s["canc_pme"])}</td>'
                    f'</tr>'
                )

            tabela_bloco_html.append('</tbody></table>')
            st.markdown("".join(tabela_bloco_html), unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

    if st.session_state.get("df_aniel_full") is not None:
        try:
            df_export = st.session_state["df_aniel_full"]
            if not df_export.empty:
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    df_export.to_excel(output, index=False)
                
                st.download_button(
                    label="📥 Baixar Planilha ANIEL Tratada (.xlsx)",
                    data=output.getvalue(),
                    file_name="Planilha_Tratada_Aniel.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        except Exception:
            pass
