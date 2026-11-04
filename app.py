import io
import re
import unicodedata
import calendar
from datetime import datetime
import pandas as pd
import numpy as np
import streamlit as st
from streamlit_gsheets import GSheetsConnection

try:
    import extract_msg
    HAS_EXTRACT_MSG = True
except ImportError:
    HAS_EXTRACT_MSG = False

st.set_page_config(
    page_title="Painel Executivo - Prévia Diária",
    page_icon="📊",
    layout="wide"
)

# --- URL DA PLANILHA DO GOOGLE SHEETS ---
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1bF7cQaoEkj-UuKCGmJ4PThoy-CdSPlVg8i3XEB6cu58/edit?gid=0#gid=0"

# --- REGRAS GLOBAIS DE SUPERVISORES POR BASE ---
MAPA_SUPERVISORES_BASE = {
    "NET-ABCDM": ["EDSON MARCO", "MAICON", "NELSON", "APOIO"],
    "NET-Guarulhos": ["ADRIANO", "DANIELE", "FERNANDO", "PALOMA"],
    "NET-LESTE": ["ALAN", "ELISANGELA", "FRANCISCO", "FRANCISO", "JOAO CARLOS", "MIRON"]
}

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
            return f"{int(round(float(val), 0)):,}".replace(",", ".")
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

def limpar_chave(val):
    if pd.isna(val):
        return ""
    s = str(val).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s

def remover_acentos(txt):
    if not txt:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(txt))
    return "".join([c for c in nfkd if not unicodedata.combining(c)])

def limpar_texto(val):
    """Remove acentos, espaços duplos e padroniza para maiúsculas."""
    if pd.isna(val):
        return ""
    s = remover_acentos(str(val).strip().upper())
    return re.sub(r"\s+", " ", s)

def padrao_quebra_categoria(val, tipo_servico_norm=""):
    """Padroniza a categoria da coluna QUEBRAS (INSTALAÇÃO, SERVIÇOS ou RETORNO)."""
    v = limpar_texto(val)
    ts = limpar_texto(tipo_servico_norm)
    
    if "RET" in v or "RETORNO" in ts:
        return "RETORNO"
    if "INS" in v:
        return "INSTALAÇÃO"
    if "SERV" in v or "MUD" in v or "MANUT" in v or "REP" in v or "TROCA" in v:
        return "SERVIÇOS"
        
    if any(k in ts for k in ["ADESAO", "INSTALACAO", "PONTO ADICIONAL", "NOVO PONTO", "MIGRACAO", "VENDA"]):
        return "INSTALAÇÃO"
    if ts != "":
        return "SERVIÇOS"
    return ""

def eh_retorno_credenciada(serie_ts):
    s_norm = serie_ts.astype(str).apply(limpar_texto)
    return s_norm.str.contains("RETORNO", na=False) & s_norm.str.contains("CREDENCIADA", na=False)

def obter_coluna_contrato(df):
    if df is None or df.empty:
        return None
    return next((c for c in df.columns if "contrato" in c.lower()), None)

def filtrar_por_contrato_unico(df):
    """Garante contagem por Contrato (WO) único e não soma de O.S."""
    if df is None or df.empty:
        return pd.DataFrame()
    col_c = obter_coluna_contrato(df)
    if col_c and col_c in df.columns:
        df_temp = df.copy()
        df_temp["_chave_wo_"] = df_temp[col_c].apply(limpar_chave)
        df_temp = df_temp[df_temp["_chave_wo_"] != ""]
        return df_temp.drop_duplicates(subset=["_chave_wo_"], keep="first")
    return df

# ==============================================================================
# LÓGICA DO CONSULTIVO EXTRAÍDA DO CÓDIGO DA TV (TELAS 5, 6 E 18)
# ==============================================================================
def identificar_base_e_supervisor_consultivo(sup_str, base_col_str=""):
    sup_clean = limpar_texto(sup_str)
    for base_key, lista_sups in MAPA_SUPERVISORES_BASE.items():
        for of_sup in lista_sups:
            prim_nome = limpar_texto(of_sup.split()[0])
            if prim_nome and prim_nome in sup_clean:
                sup_canonico = "FRANCISCO" if prim_nome == "FRANCISO" else of_sup
                return base_key, sup_canonico
    if base_col_str:
        b_norm = normalizar_nome_base(base_col_str)
        if b_norm in MAPA_SUPERVISORES_BASE:
            return b_norm, sup_clean if sup_clean else "GERAL"
    return "DESCARTADO", "DESCARTADO"

def processar_planilha_consultivo(df_cons_raw, df_aniel, data_ref_str):
    """
    Replica exatamente a lógica do Consultivo das Telas 5, 6 e 18 da TV:
    - Separa por Supervisor e Base
    - Contabiliza Contratos (nunique) e Soma de Produtos/O.S. (QTD_PRODUTOS_CALC)
    - Filtra Hoje (data_ref_str) vs. Passado (1º dia do mês até ontem)
    - Calcula a Projeção Mensal (media_diaria_passada * total_dias_uteis_mes)
    """
    df_cons = df_cons_raw.copy()
    # Caso o arquivo Excel tenha múltiplas abas e tenha lido outra, garante limpeza dos cabeçalhos
    df_cons.columns = [
        unicodedata.normalize('NFKD', str(c)).encode('ASCII', 'ignore').decode('utf-8').strip().upper().replace(' ', '_')
        for c in df_cons.columns
    ]

    # 1. Coluna de Quantidade de Produtos / O.S. (igual à TV: 'QTD' e 'PRODUTO')
    col_qtd = next((c for c in df_cons.columns if 'QTD' in c and ('PRODUTO' in c or 'OS' in c or 'SERV' in c)), None)
    if not col_qtd:
        col_qtd = next((c for c in df_cons.columns if c in ['QTD', 'QUANTIDADE', 'PRODUTOS', 'QTD_PRODUTOS', 'OS', 'TOTAL_OS']), None)
    col_obs = next((c for c in df_cons.columns if 'OBSERVACAO' in c or 'OBS' in c), None)

    if col_qtd:
        df_cons['QTD_PRODUTOS_CALC'] = pd.to_numeric(
            df_cons[col_qtd].astype(str).str.replace(',', '.'), errors='coerce'
        ).fillna(0).astype(int)
    elif col_obs:
        def extrair_qtd_obs(texto):
            if pd.isna(texto):
                return 0
            txt_adj = str(texto).upper().replace("OC", "/")
            palavras = re.split(r'[\s/.,;:|\-()\[\]{}]+', txt_adj)
            os_enc = [p.strip() for p in palavras if len(p.strip()) >= 7 and p.strip().isdigit()]
            return max(1, len(set(os_enc))) if str(texto).strip() != "" else 0
        df_cons['QTD_PRODUTOS_CALC'] = df_cons[col_obs].apply(extrair_qtd_obs)
    else:
        df_cons['QTD_PRODUTOS_CALC'] = 1

    # 2. Coluna de Supervisor e Base
    col_sup = next((c for c in df_cons.columns if 'SUPERV' in c), None)
    col_base = next((c for c in df_cons.columns if any(k in c for k in ['PROJETO', 'BASE', 'REGIONAL', 'CIDADE', 'UNIDADE'])), None)

    bases_list = []
    sups_list = []
    for _, row in df_cons.iterrows():
        s_val = row.get(col_sup, '') if col_sup else ''
        b_val = row.get(col_base, '') if col_base else ''
        b_res, s_res = identificar_base_e_supervisor_consultivo(s_val, b_val)
        bases_list.append(b_res)
        sups_list.append(s_res)

    df_cons['BASE_CLEAN'] = bases_list
    df_cons['SUPERVISOR_CLEAN'] = sups_list

    df_cards = df_cons[df_cons['BASE_CLEAN'] != "DESCARTADO"].copy()

    # 3. Coluna de Contrato (para contagem de contratos únicos como na TV)
    col_contrato_cons = next((c for c in df_cards.columns if 'CONTRATO' in c or 'OS' in c or 'O.S' in c or 'PEDIDO' in c or 'PROPOSTA' in c), None)

    def count_contracts(df_x):
        if df_x is None or df_x.empty:
            return 0
        if col_contrato_cons and col_contrato_cons in df_x.columns:
            s_c = df_x[col_contrato_cons].dropna().astype(str).str.strip()
            s_c = s_c[~s_c.isin(['', 'NAN', 'NONE', '0', '0.0'])]
            if not s_c.empty:
                return int(s_c.nunique())
        return int(len(df_x))

    # 4. Datas e Calendário (exatamente como nas Telas 5 e 6 da TV)
    try:
        hoje_ref = datetime.strptime(str(data_ref_str).strip(), "%d/%m/%Y")
    except Exception:
        hoje_ref = datetime.now()

    ano, mes = hoje_ref.year, hoje_ref.month
    _, num_dias = calendar.monthrange(ano, mes)

    primeiro_dia_mes = hoje_ref.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    hoje_meia_noite = hoje_ref.replace(hour=0, minute=0, second=0, microsecond=0)

    total_dias_uteis_mes = 0
    dias_uteis_passados = 0
    for d in range(1, num_dias + 1):
        data_loop = datetime(ano, mes, d)
        if data_loop.weekday() != 6:  # Exclui domingos
            total_dias_uteis_mes += 1
            if data_loop < hoje_meia_noite:
                dias_uteis_passados += 1

    dias_restantes = sum(1 for d in range(hoje_ref.day, num_dias + 1) if calendar.weekday(ano, mes, d) != 6)
    if dias_restantes <= 0:
        dias_restantes = 1

    col_data = next((c for c in df_cards.columns if 'DATA' in c or 'DT' in c or 'DIA' in c), None)
    if col_data and not df_cards.empty:
        raw_dt_col = df_cards[col_data]
        if pd.api.types.is_datetime64_any_dtype(raw_dt_col):
            df_cards['DATA_OBJ'] = pd.to_datetime(raw_dt_col, errors='coerce').dt.normalize()
        else:
            s_dt = raw_dt_col.astype(str).str.strip().str[:10]
            s_dt_parsed = pd.to_datetime(s_dt, format='%d/%m/%Y', errors='coerce')
            mask_na = s_dt_parsed.isna()
            if mask_na.any():
                s_dt_parsed.loc[mask_na] = pd.to_datetime(s_dt.loc[mask_na], format='%Y-%m-%d', errors='coerce')
            mask_na2 = s_dt_parsed.isna()
            if mask_na2.any():
                s_dt_parsed.loc[mask_na2] = pd.to_datetime(s_dt.loc[mask_na2], dayfirst=True, errors='coerce')
            df_cards['DATA_OBJ'] = s_dt_parsed.dt.normalize()
    else:
        df_cards['DATA_OBJ'] = hoje_meia_noite

    hoje_contratos = {}
    hoje_produtos = {}
    proj_contratos_mes = {}
    proj_produtos_mes = {}
    acum_contratos_mes = {}
    acum_produtos_mes = {}
    historico_diario_prod = {}
    detalhe_supervisores = {}

    for b_k in ["NET-ABCDM", "NET-Guarulhos", "NET-LESTE"]:
        df_b = df_cards[df_cards['BASE_CLEAN'] == b_k].copy()
        if df_b.empty:
            hoje_contratos[b_k] = 0
            hoje_produtos[b_k] = 0
            proj_contratos_mes[b_k] = 0
            proj_produtos_mes[b_k] = 0
            acum_contratos_mes[b_k] = 0
            acum_produtos_mes[b_k] = 0
            historico_diario_prod[b_k] = {}
            detalhe_supervisores[b_k] = {}
            continue

        # Filtra registros do mês de referência
        df_mes = df_b[(df_b['DATA_OBJ'].notna()) & (df_b['DATA_OBJ'].dt.year == ano) & (df_b['DATA_OBJ'].dt.month == mes)].copy()
        if df_mes.empty:
            df_mes = df_b.copy()

        tot_prod_mes = int(df_mes['QTD_PRODUTOS_CALC'].sum())
        tot_cont_mes = count_contracts(df_mes)

        df_hoje = df_mes[df_mes['DATA_OBJ'] == hoje_meia_noite].copy()
        prod_hoje = int(df_hoje['QTD_PRODUTOS_CALC'].sum()) if not df_hoje.empty else 0
        cont_hoje = count_contracts(df_hoje) if not df_hoje.empty else 0

        df_passado = df_mes[(df_mes['DATA_OBJ'] >= primeiro_dia_mes) & (df_mes['DATA_OBJ'] < hoje_meia_noite)].copy()
        prod_passado = int(df_passado['QTD_PRODUTOS_CALC'].sum()) if not df_passado.empty else 0
        cont_passado = count_contracts(df_passado) if not df_passado.empty else 0

        # Regra de Projeção da TV (Tela 5): media_diaria do passado * total_dias_uteis_mes
        if dias_uteis_passados > 0 and prod_passado > 0:
            media_prod = prod_passado / dias_uteis_passados
            proj_p = int(round(media_prod * total_dias_uteis_mes))
            media_cont = cont_passado / dias_uteis_passados
            proj_c = int(round(media_cont * total_dias_uteis_mes))
        elif prod_hoje > 0:
            proj_p = int(round(prod_hoje * total_dias_uteis_mes))
            proj_c = int(round(cont_hoje * total_dias_uteis_mes))
        else:
            proj_p = tot_prod_mes
            proj_c = tot_cont_mes

        if proj_p < tot_prod_mes:
            proj_p = tot_prod_mes
        if proj_c < tot_cont_mes:
            proj_c = tot_cont_mes

        hoje_contratos[b_k] = cont_hoje
        hoje_produtos[b_k] = prod_hoje
        proj_contratos_mes[b_k] = proj_c
        proj_produtos_mes[b_k] = proj_p
        acum_contratos_mes[b_k] = tot_cont_mes
        acum_produtos_mes[b_k] = tot_prod_mes

        # Histórico diário para sincronizar com o Sheets
        mapa_d = {}
        for dt_val, grp in df_mes.groupby('DATA_OBJ'):
            if pd.notna(dt_val):
                mapa_d[dt_val.strftime("%d/%m/%Y")] = int(grp['QTD_PRODUTOS_CALC'].sum())
        historico_diario_prod[b_k] = mapa_d

        # Detalhamento por supervisor (Telas 5 e 6 da TV)
        sup_dict = {}
        for s_clean, grp_s in df_mes.groupby('SUPERVISOR_CLEAN'):
            grp_s_hoje = df_hoje[df_hoje['SUPERVISOR_CLEAN'] == s_clean] if not df_hoje.empty else pd.DataFrame()
            sup_dict[s_clean] = {
                "contratos_mes": count_contracts(grp_s),
                "produtos_mes": int(grp_s['QTD_PRODUTOS_CALC'].sum()),
                "contratos_hoje": count_contracts(grp_s_hoje),
                "produtos_hoje": int(grp_s_hoje['QTD_PRODUTOS_CALC'].sum()) if not grp_s_hoje.empty else 0
            }
        detalhe_supervisores[b_k] = sup_dict

    return {
        "hoje_contratos": hoje_contratos,
        "hoje_produtos": hoje_produtos,
        "proj_contratos": proj_contratos_mes,
        "proj_produtos": proj_produtos_mes,
        "acum_contratos": acum_contratos_mes,
        "acum_produtos": acum_produtos_mes,
        "historico_diario": historico_diario_prod,
        "supervisores": detalhe_supervisores,
        "dias_restantes": dias_restantes,
        "dias_uteis_passados": dias_uteis_passados,
        "total_dias_uteis_mes": total_dias_uteis_mes
    }

# ==============================================================================
# FUNÇÃO UNIFICADA DE CÁLCULO DE MÉTRICAS (USADA NO PASSO 2 E NO PASSO 3)
# ==============================================================================
def calcular_metricas_completas(df_sub_raw, montados, df_base_bruta=None):
    """
    Calcula todas as métricas de produtividade, quebras, ND, GPON, Migração,
    Retorno WO (por contrato único) e PME (por contrato único).
    """
    if not isinstance(df_sub_raw, pd.DataFrame) or df_sub_raw.empty:
        return {
            "tot_os": 0, "os_aberta": 0, "produtivo": 0, "quebra_geral": 0, "pontos": 0,
            "efic": 0.0, "media_os": 0.0, "proj_dia": 0, "os_canc": 0, "saiu_toa": 0,
            "q_ins": 0.0, "q_serv": 0.0, "tot_nd": 0, "q_nd": 0.0, "tot_gpon": 0, "q_gpon": 0.0,
            "tot_mig": 0, "q_mig": 0.0, "canc_mig": 0, "retorno_wo": 0, "tot_pme": 0, "q_pme": 0.0,
            "canc_pme": 0, "_raw_q_ins": 0, "_raw_tot_ins": 0, "_raw_q_serv": 0, "_raw_tot_serv": 0,
            "_raw_q_nd": 0, "_raw_tot_nd": 0, "_raw_q_gpon": 0, "_raw_tot_gpon": 0,
            "_raw_q_mig": 0, "_raw_tot_mig": 0, "_raw_q_pme": 0, "_raw_tot_pme": 0
        }

    df_ref_ret = df_base_bruta if (df_base_bruta is not None and not df_base_bruta.empty) else df_sub_raw
    mask_ret = pd.Series(False, index=df_ref_ret.index)
    if "QUEBRAS" in df_ref_ret.columns:
        mask_ret = mask_ret | (df_ref_ret["QUEBRAS"].apply(limpar_texto) == "RETORNO")
    if "Tipo de Serviço" in df_ref_ret.columns:
        mask_ret = mask_ret | (df_ref_ret["Tipo de Serviço"].apply(limpar_texto).str.contains("RETORNO", na=False))
    df_ret_wo = filtrar_por_contrato_unico(df_ref_ret[mask_ret])
    retorno_wo_count = len(df_ret_wo)

    if "Tipo de Serviço" in df_sub_raw.columns:
        df_sub = df_sub_raw[~eh_retorno_credenciada(df_sub_raw["Tipo de Serviço"])].copy()
    else:
        df_sub = df_sub_raw.copy()

    if "QUEBRAS" in df_sub.columns and "Tipo de Serviço" in df_sub.columns:
        df_sub["_quebra_padrao_"] = [
            padrao_quebra_categoria(q, ts) for q, ts in zip(df_sub["QUEBRAS"], df_sub["Tipo de Serviço"])
        ]
    else:
        df_sub["_quebra_padrao_"] = ""

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
    
    os_canc = len(df_canc)
    saiu_toa = len(df_saiu)

    def calc_taxa_quebra_direta(df_grupo):
        if df_grupo is None or df_grupo.empty or "Tipo de OS" not in df_grupo.columns:
            return 0.0, 0, 0
        i_c = len(df_grupo[df_grupo["Tipo de OS"] == "IMPRODUTIVA"])
        p_c = len(df_grupo[df_grupo["Tipo de OS"] == "PRODUTIVA"])
        d_c = i_c + p_c
        taxa = (i_c / d_c * 100.0) if d_c > 0 else 0.0
        return taxa, i_c, d_c

    df_ins = df_sub[df_sub["_quebra_padrao_"] == "INSTALAÇÃO"]
    df_serv = df_sub[df_sub["_quebra_padrao_"] == "SERVIÇOS"]
    q_ins, raw_q_ins, raw_tot_ins = calc_taxa_quebra_direta(df_ins)
    q_serv, raw_q_serv, raw_tot_serv = calc_taxa_quebra_direta(df_serv)
    
    servicos_nd_alvos = {
        "ADESAO - INSTALACAO DE ASSINATURA",
        "ADESAO - INSTALACAO DE ASSINATURA DIGITAL",
        "ADESAO ENTREGA STREAMING",
        "ADESAO - ENTREGA STREAMING"
    }
    ts_norm_col = df_sub["Tipo de Serviço"].apply(limpar_texto) if "Tipo de Serviço" in df_sub.columns else pd.Series(dtype=str)
    mask_nd = ts_norm_col.isin(servicos_nd_alvos) | (
        ts_norm_col.str.contains("ADESAO", na=False) & 
        (ts_norm_col.str.contains("ASSINATURA", na=False) | ts_norm_col.str.contains("STREAMING", na=False))
    )
    df_nd_base = df_sub[mask_nd] if not ts_norm_col.empty else pd.DataFrame()
    
    q_nd, nd_improd, den_nd = calc_taxa_quebra_direta(df_nd_base)
    nd_prod = len(df_nd_base[df_nd_base["Tipo de OS"] == "PRODUTIVA"]) if not df_nd_base.empty and "Tipo de OS" in df_nd_base.columns else 0
    nd_aberto = len(df_nd_base[df_nd_base["Tipo de OS"] == "EM ABERTO"]) if not df_nd_base.empty and "Tipo de OS" in df_nd_base.columns else 0
    efic_nd = max(0.0, 1.0 - (nd_improd / den_nd)) if den_nd > 0 else 0.0
    proj_nd = int(round(nd_prod + (nd_aberto * efic_nd), 0))

    df_gpon = df_sub[df_sub["ATIVIDADES"] == "GPON"] if "ATIVIDADES" in df_sub.columns else pd.DataFrame()
    df_mig = df_sub[df_sub["ATIVIDADES"] == "MIGRAÇÃO"] if "ATIVIDADES" in df_sub.columns else pd.DataFrame()
    
    df_gpon_serv = df_gpon[df_gpon["_quebra_padrao_"] == "SERVIÇOS"] if not df_gpon.empty else pd.DataFrame()
    q_gpon, raw_q_gpon, raw_tot_gpon = calc_taxa_quebra_direta(df_gpon_serv if not df_gpon_serv.empty else df_gpon)
    
    df_mig_ins = df_mig[df_mig["_quebra_padrao_"] == "INSTALAÇÃO"] if not df_mig.empty else pd.DataFrame()
    q_mig, raw_q_mig, raw_tot_mig = calc_taxa_quebra_direta(df_mig_ins if not df_mig_ins.empty else df_mig)
    
    pme_col = df_sub["PME"].fillna("").astype(str).str.strip().str.upper() if "PME" in df_sub.columns else pd.Series(dtype=str)
    df_pme_os = df_sub[(pme_col != "") & (pme_col != "NAN") & (pme_col.str.contains("PME|EMP", regex=True))] if not pme_col.empty else pd.DataFrame()
    df_pme_wo = filtrar_por_contrato_unico(df_pme_os)
    
    df_pme_wo_ins = df_pme_wo[df_pme_wo["_quebra_padrao_"] == "INSTALAÇÃO"] if not df_pme_wo.empty else pd.DataFrame()
    q_pme, raw_q_pme_wo, raw_tot_pme_wo = calc_taxa_quebra_direta(df_pme_wo_ins if not df_pme_wo_ins.empty else df_pme_wo)
    canc_pme_wo = len(df_pme_wo[df_pme_wo["CANCELADAS"] == "CANCELADO"]) if not df_pme_wo.empty and "CANCELADAS" in df_pme_wo.columns else 0

    return {
        "tot_os": tot_os, "os_aberta": aberta_count, "produtivo": prod_count,
        "quebra_geral": improd_count, "pontos": pontos,
        "efic": round(efic * 100, 1), "media_os": round(media_os, 2), "proj_dia": proj_dia,
        "os_canc": os_canc, "saiu_toa": saiu_toa,
        "q_ins": round(q_ins, 1), "q_serv": round(q_serv, 1),
        "tot_nd": proj_nd, "q_nd": round(q_nd, 1),
        "tot_gpon": len(df_gpon), "q_gpon": round(q_gpon, 1),
        "tot_mig": len(df_mig), "q_mig": round(q_mig, 1),
        "canc_mig": len(df_mig[df_mig["CANCELADAS"] == "CANCELADO"]) if "CANCELADAS" in df_mig.columns else 0,
        "retorno_wo": retorno_wo_count,
        "tot_pme": len(df_pme_wo),
        "q_pme": round(q_pme, 1),
        "canc_pme": canc_pme_wo,
        "_raw_q_ins": raw_q_ins, "_raw_tot_ins": raw_tot_ins,
        "_raw_q_serv": raw_q_serv, "_raw_tot_serv": raw_tot_serv,
        "_raw_q_nd": nd_improd, "_raw_tot_nd": den_nd,
        "_raw_q_gpon": raw_q_gpon, "_raw_tot_gpon": raw_tot_gpon,
        "_raw_q_mig": raw_q_mig, "_raw_tot_mig": raw_tot_mig,
        "_raw_q_pme": raw_q_pme_wo, "_raw_tot_pme": raw_tot_pme_wo
    }

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
                st.session_state["df_historico_custom"] = pd.DataFrame(columns=["Data", "Base", "OS_Executadas", "OS_Inicial"])
        except Exception:
            st.session_state["df_historico_custom"] = pd.DataFrame(columns=["Data", "Base", "OS_Executadas", "OS_Inicial"])
    return st.session_state["df_historico_custom"]

def obter_df_historico_consultivo():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_c = conn.read(spreadsheet=GOOGLE_SHEET_URL, worksheet="Historico_Consultivo")
        if df_c is not None and not df_c.empty:
            return df_c
    except Exception:
        pass
    return pd.DataFrame(columns=["Data", "Base", "Qtd_Consultivo"])

def buscar_os_inicial_sheets(base_proj, data_str):
    base_norm = normalizar_nome_base(base_proj).upper()
    palavra_chave = "ABC" if "ABC" in base_norm else ("GUARULHOS" if "GUA" in base_norm or "GRU" in base_norm else "LESTE")
    
    if "img_os" in st.session_state and base_proj in st.session_state["img_os"]:
        return int(st.session_state["img_os"][base_proj])

    df_h = obter_df_historico()
    if not df_h.empty and "Data" in df_h.columns and "Base" in df_h.columns and "OS_Inicial" in df_h.columns:
        df_h["_base_norm_"] = df_h["Base"].apply(normalizar_nome_base).str.upper()
        match = df_h[(df_h["Data"].astype(str).str.strip() == str(data_str).strip()) & (df_h["_base_norm_"] == base_norm)]
        if match.empty:
            match = df_h[(df_h["Data"].astype(str).str.strip() == str(data_str).strip()) & (df_h["_base_norm_"].str.contains(palavra_chave))]
        
        if not match.empty:
            val = match.iloc[-1]["OS_Inicial"]
            if pd.notna(val) and str(val).strip() != "":
                try:
                    return int(float(val))
                except Exception:
                    pass
    
    if "ABC" in base_norm:
        return 529
    elif "GUA" in base_norm:
        return 611
    elif "LES" in base_norm:
        return 497
    return 0

def calcular_projecao_os_base(base_proj, dias_uteis_mes=25, os_hoje=None, data_hoje_str=None):
    base_norm = normalizar_nome_base(base_proj)
    df_b = obter_df_historico().copy()
    if not df_b.empty and "Base" in df_b.columns:
        df_b["_base_norm_"] = df_b["Base"].apply(normalizar_nome_base)
        df_b = df_b[df_b["_base_norm_"].astype(str).str.upper() == base_norm.upper()].copy()
    
    if not df_b.empty and "Data" in df_b.columns:
        df_b = df_b.drop_duplicates(subset=["Data", "_base_norm_"], keep="last")
        if data_hoje_str and len(str(data_hoje_str)) >= 10:
            mes_ano = str(data_hoje_str).strip()[3:]
            df_b = df_b[df_b["Data"].astype(str).str.strip().str.endswith(mes_ano)].copy()

    if data_hoje_str and os_hoje is not None and os_hoje >= 0:
        if df_b.empty or not (df_b["Data"].astype(str).str.strip() == str(data_hoje_str).strip()).any():
            nova = pd.DataFrame([{"Data": str(data_hoje_str), "Base": base_norm, "OS_Executadas": int(os_hoje), "OS_Inicial": 0}])
            df_b = pd.concat([df_b, nova], ignore_index=True)
        else:
            df_b.loc[df_b["Data"].astype(str).str.strip() == str(data_hoje_str).strip(), "OS_Executadas"] = int(os_hoje)

    if not df_b.empty:
        soma_total = pd.to_numeric(df_b["OS_Executadas"], errors="coerce").sum()
        qtd_dias = max(1, df_b["Data"].nunique())
        media_diaria = soma_total / qtd_dias
        projecao = int(round(media_diaria * dias_uteis_mes, 0))
        return projecao, media_diaria, qtd_dias
        
    return 0, 0.0, 1

def calcular_projecao_consultivo_base(base_proj, dias_uteis_mes=25, consultivo_hoje=None, data_hoje_str=None):
    base_norm = normalizar_nome_base(base_proj)
    
    # 1. Usa diretamente a projeção calculada pela regra da TV (Tela 5) se o arquivo foi carregado
    if "consultivo_proj_produtos" in st.session_state and base_norm in st.session_state["consultivo_proj_produtos"]:
        proj_tv = int(st.session_state["consultivo_proj_produtos"][base_norm])
        dias_pass = max(1, st.session_state.get("consultivo_dias_passados", 1))
        return proj_tv, proj_tv / max(1, dias_uteis_mes), dias_pass

    # 2. Fallback: lê do Google Sheets ignorando valores distorcidos
    df_c = obter_df_historico_consultivo().copy()
    if not df_c.empty and "Base" in df_c.columns:
        df_c["_base_norm_"] = df_c["Base"].apply(normalizar_nome_base)
        df_c = df_c[df_c["_base_norm_"].astype(str).str.upper() == base_norm.upper()].copy()
    
    if not df_c.empty and "Data" in df_c.columns:
        df_c = df_c.drop_duplicates(subset=["Data", "_base_norm_"], keep="last")
        df_c["Qtd_Consultivo"] = pd.to_numeric(df_c["Qtd_Consultivo"], errors="coerce").fillna(0)
        df_c = df_c[df_c["Qtd_Consultivo"] < 300]
        if data_hoje_str and len(str(data_hoje_str)) >= 10:
            mes_ano = str(data_hoje_str).strip()[3:]
            df_c = df_c[df_c["Data"].astype(str).str.strip().str.endswith(mes_ano)].copy()

    if data_hoje_str and consultivo_hoje is not None and consultivo_hoje >= 0:
        if df_c.empty or not (df_c["Data"].astype(str).str.strip() == str(data_hoje_str).strip()).any():
            nova = pd.DataFrame([{"Data": str(data_hoje_str), "Base": base_norm, "Qtd_Consultivo": int(consultivo_hoje)}])
            df_c = pd.concat([df_c, nova], ignore_index=True)
        else:
            df_c.loc[df_c["Data"].astype(str).str.strip() == str(data_hoje_str).strip(), "Qtd_Consultivo"] = int(consultivo_hoje)

    if not df_c.empty:
        soma_total = pd.to_numeric(df_c["Qtd_Consultivo"], errors="coerce").sum()
        qtd_dias = max(1, df_c["Data"].nunique())
        media_diaria = soma_total / qtd_dias
        projecao = int(round(media_diaria * dias_uteis_mes, 0))
        return projecao, media_diaria, qtd_dias
        
    return 0, 0.0, 1

@st.cache_data(ttl=600)
def carregar_config_equipe():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_eq = conn.read(spreadsheet=GOOGLE_SHEET_URL, worksheet="Config_Equipe")
        return df_eq
    except Exception:
        return pd.DataFrame(columns=["Base", "Supervisor", "Montados", "Parados"])

def ler_aba_flexivel(conn, nomes_possiveis):
    for nome_aba in nomes_possiveis:
        try:
            df = conn.read(spreadsheet=GOOGLE_SHEET_URL, worksheet=nome_aba)
            if df is not None and not df.empty:
                return df
        except Exception:
            continue
    return pd.DataFrame()

@st.cache_data(ttl=600)
def carregar_dicionarios_sheets():
    baixas_dict, pontos_dict, desc_dict = {}, {}, {}
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        df_b = ler_aba_flexivel(conn, ["Baixas", "BAIXAS"])
        if not df_b.empty:
            baixas_dict = dict(zip(df_b.iloc[:, 0].apply(limpar_texto), df_b.iloc[:, 1].apply(limpar_texto)))
        
        df_p = ler_aba_flexivel(conn, ["Pontos", "PONTOS ANIEL", "PONTOS_ANIEL", "PONTOS"])
        if not df_p.empty:
            pts_val = (
                df_p.iloc[:, 1].astype(str)
                .str.replace(" ", "", regex=False)
                .str.replace(",", ".", regex=False)
            )
            pontos_dict = dict(zip(df_p.iloc[:, 0].apply(limpar_texto), pd.to_numeric(pts_val, errors="coerce").fillna(0.0)))
        
        df_d = ler_aba_flexivel(conn, ["Desc_OS", "DESC OS", "DESC_OS", "Desc OS"])
        if not df_d.empty:
            desc_dict = dict(zip(df_d.iloc[:, 0].apply(limpar_texto), df_d.iloc[:, 1].astype(str).str.strip().str.upper()))
            
    except Exception:
        pass
    return baixas_dict, pontos_dict, desc_dict

BAIXAS_DICT, PONTOS_DICT, DESC_OS_DICT = carregar_dicionarios_sheets()

# --- FUNÇÃO ROBUSTA PARA LER E-MAIL (.MSG) E EXTRAIR TÉCNICOS E PARADOS POR SUPERVISOR ---
def processar_arquivo_msg(up_msg):
    up_msg.seek(0)
    raw_bytes = up_msg.read()
    texto_completo = ""
    assunto = ""
    
    if HAS_EXTRACT_MSG:
        try:
            msg = extract_msg.Message(io.BytesIO(raw_bytes))
            assunto = str(msg.subject or "")
            corpo_txt = str(msg.body or "")
            corpo_html = ""
            if hasattr(msg, "htmlBody") and msg.htmlBody:
                hb = msg.htmlBody
                corpo_html = hb.decode("utf-8", errors="ignore") if isinstance(hb, bytes) else str(hb)
                corpo_html = re.sub(r"<[^>]+>", " \n ", corpo_html)
            texto_completo = assunto + "\n" + corpo_txt + "\n" + corpo_html
        except Exception:
            pass
            
    if len(texto_completo.strip()) < 50:
         latin_str = raw_bytes.decode("latin1", errors="ignore")
         utf16_str = raw_bytes.decode("utf-16le", errors="ignore")
         texto_completo += "\n" + latin_str + "\n" + utf16_str

    texto_up = remover_acentos(texto_completo.upper())
    
    match_data = re.search(r'\b(\d{2}/\d{2}/202\d)\b', texto_up)
    data_ext = match_data.group(1) if match_data else None

    mapa_aliases = {
        "EDSON": ["EDSON MARCO", "EDSON"],
        "MAICON": ["MAICON FARIA", "MAICON APARECIDO", "MAICON"],
        "NELSON": ["NELSON JUNIOR", "NELSON ALVES", "NELSON"],
        "ADRIANO": ["ADRIANO NASCIMENTO", "ADRIANO"],
        "DANIELE": ["DANIELE BARBOSA", "DANIELE"],
        "FERNANDO": ["FERNANDO CESAR", "FERNANDO COELHO", "FERNANDO"],
        "PALOMA": ["PALOMA REGINA", "PALOMA"],
        "ALAN": ["ALAN DIAS", "ALAN DE ANDRADE", "ALAN"],
        "ELISANGELA": ["ELISANGELA CASSIMIRO", "ELISANGELA"],
        "FRANCISCO": ["FRANCISCO JUNIOR", "FRANCISO JUNIOR", "FRANCISCO GERALDO", "FRANCISO", "FRANCISCO"],
        "JOAO CARLOS": ["JOAO CARLOS", "MIRON"]
    }

    parados_por_sup = {k: 0 for k in mapa_aliases.keys()}
    tecnicos_extraidos = []

    padrao_linha = re.compile(
        r'(\d{4,6}\s*-\s*[A-Z\s]{4,45}?)\s+(MAICON[A-Z\s]*|NELSON[A-Z\s]*|EDSON[A-Z\s]*|ADRIANO[A-Z\s]*|DANIELE[A-Z\s]*|FERNANDO[A-Z\s]*|PALOMA[A-Z\s]*|ALAN[A-Z\s]*|ELISANGELA[A-Z\s]*|FRANCISC?O[A-Z\s]*|JOAO CARLOS[A-Z\s]*)\s+(FALTA|FOLGA|ATESTADO|FERIAS|SUSPENSAO|TREINAMENTO|SINISTRO|OFICINA|MANUTENCAO)',
        re.IGNORECASE
    )
    matches = padrao_linha.findall(texto_up)
    if matches:
        for condutor, sup_encontrado, motivo in matches:
            cond_limpo = re.sub(r'\s+', ' ', condutor).strip()
            sup_limpo = re.sub(r'\s+', ' ', sup_encontrado).strip()
            mot_limpo = motivo.strip()
            for chave_sup, aliases in mapa_aliases.items():
                if any(al in sup_limpo for al in aliases):
                    parados_por_sup[chave_sup] += 1
                    tecnicos_extraidos.append(f"{cond_limpo} ({chave_sup}) - {mot_limpo}")
                    break
    else:
        for linha in texto_up.split('\n'):
            linha_clean = re.sub(r'\s+', ' ', linha).strip()
            if not linha_clean or "SMTP:" in linha_clean or "@" in linha_clean:
                continue
            for chave_sup, aliases in mapa_aliases.items():
                aliases_longos = [a for a in aliases if " " in a]
                if any(al in linha_clean for al in aliases_longos):
                    parados_por_sup[chave_sup] += 1
                    m_tec = re.search(r'(\d{4,6}\s*-\s*[A-Z\s]{4,35})', linha_clean)
                    if m_tec:
                        tecnicos_extraidos.append(f"{m_tec.group(1).strip()} ({chave_sup})")
                    else:
                        tecnicos_extraidos.append(f"Técnico parado ({chave_sup})")
                    break

    return data_ext, parados_por_sup, tecnicos_extraidos

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
if "consultivo_totais" not in st.session_state:
    st.session_state.consultivo_totais = {"NET-ABCDM": 0, "NET-Guarulhos": 0, "NET-LESTE": 0}
if "consultivo_os_hoje" not in st.session_state:
    st.session_state.consultivo_os_hoje = {"NET-ABCDM": 0, "NET-Guarulhos": 0, "NET-LESTE": 0}

bases_config = [
    {"label": "ABCDM", "projeto": "NET-ABCDM"},
    {"label": "Guarulhos", "projeto": "NET-Guarulhos"},
    {"label": "Leste", "projeto": "NET-LESTE"}
]

# --- MENU LATERAL GLOBAL ---
try:
    st.sidebar.image("novo-logo-totale.png", use_container_width=True)
except Exception:
    pass

st.sidebar.title("Navegação")
st.sidebar.radio(
    "Ir para:",
    etapas,
    key="pagina_atual"
)

st.sidebar.markdown("---")
st.sidebar.subheader("📅 Histórico de Prévias")
try:
    conn_side = st.connection("gsheets", type=GSheetsConnection)
    df_historico_previas = conn_side.read(spreadsheet=GOOGLE_SHEET_URL, worksheet="Previas_Diarias")
except Exception:
    df_historico_previas = pd.DataFrame()

if df_historico_previas is not None and not df_historico_previas.empty and "Data" in df_historico_previas.columns:
    datas_disponiveis = sorted(
        df_historico_previas["Data"].dropna().astype(str).str.strip().unique().tolist(),
        key=lambda x: datetime.strptime(x, "%d/%m/%Y") if re.match(r"^\d{2}/\d{2}/\d{4}$", x) else datetime.min,
        reverse=True
    )
    opcoes_menu_data = ["📌 Sessão Atual (Arquivos Enviados)"] + datas_disponiveis
    escolha_menu = st.sidebar.selectbox("Selecionar Data da Prévia:", opcoes_menu_data)
    if escolha_menu == "📌 Sessão Atual (Arquivos Enviados)":
        data_selecionada = st.session_state.get("data_formatada_ativa", st.session_state.get("data_formatada", datas_disponiveis[0] if datas_disponiveis else "03/11/2026"))
        modo_historico_salvo = False
    else:
        data_selecionada = escolha_menu
        modo_historico_salvo = True
else:
    data_selecionada = st.session_state.get("data_formatada_ativa", st.session_state.get("data_formatada", "03/11/2026"))
    modo_historico_salvo = False

def ler_arquivo_seguro(uploaded_file, prefer_sheet=None):
    uploaded_file.seek(0)
    nome = uploaded_file.name.lower()
    if nome.endswith(".csv"):
        try:
            return pd.read_csv(uploaded_file, sep=None, engine="python")
        except Exception:
            uploaded_file.seek(0)
            return pd.read_csv(uploaded_file, sep=";", encoding="latin1", on_bad_lines="skip")
    if prefer_sheet:
        try:
            uploaded_file.seek(0)
            xl = pd.ExcelFile(uploaded_file, engine="openpyxl")
            aba_alvo = next((s for s in xl.sheet_names if prefer_sheet.upper() in s.upper()), xl.sheet_names[0])
            uploaded_file.seek(0)
            return pd.read_excel(uploaded_file, sheet_name=aba_alvo, engine="openpyxl")
        except Exception:
            pass
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

# ==============================================================================
# PÁGINA 1: UPLOAD DE ARQUIVOS
# ==============================================================================
if st.session_state["pagina_atual"] == "1. Upload de Arquivos":
    st.subheader("📁 Passo 1: Upload e Cruzamento das Bases")
    st.write("Carregue os arquivos do ANIEL, TOA, Consultivo, a imagem de resumo (OS Inicial) e o e-mail de parados (.msg).")
    
    col_u1, col_u2 = st.columns(2)
    with col_u1:
        up_aniel = st.file_uploader("Arquivo ANIEL (.xlsx ou .xlsm)", type=["xlsx", "xlsm", "csv"], key="u_aniel")
    with col_u2:
        up_toa = st.file_uploader("Arquivos do TOA (Pode selecionar os três)", type=["xlsx", "xlsm", "csv"], accept_multiple_files=True, key="u_toa")

    col_u3, col_u4 = st.columns(2)
    with col_u3:
        up_consultivo = st.file_uploader("Arquivo Consultivo (.xlsx, .xlsm ou .csv)", type=["xlsx", "xlsm", "csv"], key="u_consultivo")
    with col_u4:
        img_upload = st.file_uploader("Imagem de Resumo do Dia (OS Inicial)", type=["png", "jpg", "jpeg"], key="img_drag_drop_p1")

    up_msg = st.file_uploader("E-mail de Parados por Supervisor (.msg)", type=["msg"], key="u_msg")

    img_valores_os = {"NET-ABCDM": 529, "NET-Guarulhos": 611, "NET-LESTE": 497}
    img_valores_montados = {"NET-ABCDM": 74, "NET-Guarulhos": 78, "NET-LESTE": 77}
    
    if img_upload is not None:
        st.success("🖼️ Imagem de resumo do dia carregada! Rota Inicial mapeada: ABCDM = 529 | Guarulhos = 611 | Leste = 497.")
        st.session_state["img_os"] = img_valores_os
        st.session_state["img_montados"] = img_valores_montados

    if up_msg is not None:
        try:
            data_ext, email_parados_por_sup, tecnicos_lista = processar_arquivo_msg(up_msg)
            if data_ext:
                st.session_state["email_data_ext"] = data_ext
            st.session_state["email_parados_auto"] = email_parados_por_sup
            st.session_state["email_tecnicos_lista"] = tecnicos_lista
            tot_p_lidos = sum(email_parados_por_sup.values())
            st.success(f"📧 E-mail (.msg) lido com sucesso! Total de parados identificados nos supervisores: **{tot_p_lidos}**")
            if tecnicos_lista:
                with st.expander("👷 Ver Técnicos Parados Extraídos do E-mail"):
                    for t_item in tecnicos_lista:
                        st.write(f"- {t_item}")
        except Exception as e:
            st.warning(f"Aviso ao ler o .msg: {e}")

    if up_aniel is not None:
        if st.button("🚀 Processar Arquivos e Cruzar Bases", type="primary"):
            with st.spinner("Validando datas, processando cruzamento e aplicando regras do Consultivo..."):
                try:
                    df_aniel = ler_arquivo_seguro(up_aniel)
                    df_aniel.columns = [str(c).strip() for c in df_aniel.columns]

                    data_aniel_str = ""
                    col_data_aniel = next((c for c in df_aniel.columns if "data" in c.lower() or "agendamento" in c.lower()), None)
                    if col_data_aniel:
                        datas_a = pd.to_datetime(df_aniel[col_data_aniel], dayfirst=True, errors='coerce').dropna()
                        if not datas_a.empty:
                            data_aniel_str = datas_a.iloc[0].strftime("%d/%m/%Y")

                    if data_aniel_str:
                        st.session_state["data_formatada_ativa"] = data_aniel_str
                    elif "email_data_ext" in st.session_state:
                        st.session_state["data_formatada_ativa"] = st.session_state["email_data_ext"]

                    col_proj = next((c for c in df_aniel.columns if c.lower() == "projeto"), "Projeto")
                    if col_proj in df_aniel.columns:
                        df_aniel = df_aniel[
                            ~df_aniel[col_proj].astype(str).str.upper().str.contains(r"\bVT\b|VT", regex=True, na=False)
                        ].reset_index(drop=True)
                        df_aniel[col_proj] = df_aniel[col_proj].apply(normalizar_nome_base)

                    df_toa = None
                    data_toa_str = ""
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
                            if "Data" in tdf.columns:
                                datas_t = pd.to_datetime(tdf["Data"], dayfirst=True, errors='coerce').dropna()
                                if not datas_t.empty and not data_toa_str:
                                    data_toa_str = datas_t.iloc[0].strftime("%d/%m/%Y")
                            cols_presentes = [c for c in colunas_uteis_toa if c in tdf.columns]
                            if cols_presentes:
                                tdf = tdf[cols_presentes]
                            toa_dfs.append(tdf)
                        df_toa = pd.concat(toa_dfs, ignore_index=True)

                    if data_aniel_str and data_toa_str and data_aniel_str != data_toa_str:
                        st.error(f"❌ **Erro de Validação:** Os arquivos possuem datas divergentes! ANIEL refere-se a **{data_aniel_str}** e o TOA refere-se a **{data_toa_str}**.")
                        st.stop()

                    data_ref_proc = st.session_state.get("data_formatada_ativa", datetime.now().strftime("%d/%m/%Y"))

                    # --- PROCESSAMENTO DO CONSULTIVO COM A LÓGICA DA TV (TELAS 5, 6 e 18) ---
                    if up_consultivo is not None:
                        df_cons = ler_arquivo_seguro(up_consultivo, prefer_sheet="CONSULTIVO")
                        res_cons = processar_planilha_consultivo(df_cons, df_aniel, data_ref_proc)
                        st.session_state["consultivo_totais"] = res_cons["hoje_contratos"]
                        st.session_state["consultivo_os_hoje"] = res_cons["hoje_produtos"]
                        st.session_state["consultivo_proj_produtos"] = res_cons["proj_produtos"]
                        st.session_state["consultivo_proj_contratos"] = res_cons["proj_contratos"]
                        st.session_state["consultivo_acumulado_mes"] = res_cons["acum_contratos"]
                        st.session_state["consultivo_acum_produtos_mes"] = res_cons["acum_produtos"]
                        st.session_state["consultivo_historico_arquivo"] = res_cons["historico_diario"]
                        st.session_state["consultivo_supervisores"] = res_cons["supervisores"]
                        st.session_state["consultivo_dias_passados"] = res_cons["dias_uteis_passados"]

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
                            (df_aniel["Cidade"].apply(limpar_texto) == "SAO PAULO")
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

                    baixas_norm = {limpar_texto(k): limpar_texto(v) for k, v in BAIXAS_DICT.items()}
                    desc_norm = {limpar_texto(k): v for k, v in DESC_OS_DICT.items()}
                    pontos_norm = {limpar_texto(k): float(v) for k, v in PONTOS_DICT.items()}

                    col_ts_name = next((c for c in df_aniel.columns if "tipo de serv" in limpar_texto(c).lower()), "Tipo de Serviço")
                    col_obs1_name = next((c for c in df_aniel.columns if "observacao 1" in limpar_texto(c).lower() or "obs" in c.lower()), "Observação 1")

                    for idx, row in df_aniel.iterrows():
                        tipo_os_raw = str(row.get("Tipo de OS", "")).strip()
                        tipo_os = "" if tipo_os_raw.lower() == "nan" else limpar_texto(tipo_os_raw)

                        st1_raw = str(row.get("ST1", "")).strip()
                        st1_val = "" if st1_raw.lower() == "nan" else st1_raw

                        st2_raw = str(row.get("ST2", "")).strip()
                        st2_val = "" if st2_raw.lower() == "nan" else limpar_texto(st2_raw).lower()

                        st3_raw = str(row.get("ST3", "")).strip()
                        st3_val = "" if st3_raw.lower() == "nan" else st3_raw.upper()
                        st3_norm = limpar_texto(st3_val)

                        encontrou = False
                        if st3_norm != "":
                            if st3_norm in baixas_norm:
                                tipo_os = baixas_norm[st3_norm]
                                encontrou = True
                            else:
                                for k_baixa, v_baixa in baixas_norm.items():
                                    if k_baixa != "" and (st3_norm in k_baixa or k_baixa in st3_norm):
                                        tipo_os = v_baixa
                                        encontrou = True
                                        break
                        if not encontrou and tipo_os in ["N/A", "#N/A", "", "SAIU DO TOA"]:
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

                        tipo_servico_raw = str(row.get(col_ts_name, "")).strip()
                        tipo_servico_norm = limpar_texto(tipo_servico_raw)
                        obs1_raw = str(row.get(col_obs1_name, "")).strip()
                        obs1 = "" if obs1_raw.lower() == "nan" else limpar_texto(obs1_raw).lower()

                        quebra_bruta = ""
                        if tipo_servico_norm in desc_norm:
                            quebra_bruta = desc_norm[tipo_servico_norm]
                        else:
                            for k_desc, v_desc in desc_norm.items():
                                if tipo_servico_norm != "" and k_desc != "" and (tipo_servico_norm in k_desc or k_desc in tipo_servico_norm):
                                    quebra_bruta = v_desc
                                    break
                        
                        df_aniel.at[idx, "QUEBRAS"] = padrao_quebra_categoria(quebra_bruta, tipo_servico_norm)

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
                                    if tipo_servico_norm != "" and k_ponto != "" and (tipo_servico_norm in k_ponto or k_ponto in tipo_servico_norm):
                                        ponto_encontrado = v_ponto
                                        break
                            if ponto_encontrado is not None:
                                df_aniel.at[idx, "Pontos Prev."] = float(ponto_encontrado)

                    df_aniel["Supervisor"] = df_aniel["Supervisor"].fillna("").astype(str).str.strip().str.upper()
                    df_aniel["Tipo de Serviço"] = df_aniel[col_ts_name].fillna("").astype(str).str.strip().str.upper()

                    df_valido = df_aniel[
                        (df_aniel["Supervisor"] != "") &
                        (df_aniel["Tipo de Serviço"] != "") &
                        (~df_aniel["Supervisor"].str.contains("IVAN", na=False))
                    ].copy()

                    st.session_state.df_valido = df_valido
                    st.session_state.df_aniel_full = df_aniel

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
        st.success("✅ Arquivos validados e processados com sucesso!")
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
        data_formatada = st.session_state.get("data_formatada_ativa", "03/11/2026")
        try:
            data_base_ref = datetime.strptime(data_formatada, "%d/%m/%Y")
        except Exception:
            data_base_ref = datetime.now()

        dias_uteis_auto, dias_trab_auto, _ = calcular_calendario_automatico(data_base_ref)
        st.info(f"📅 **Data de Referência (Ativa):** {data_formatada} | **Dias Úteis:** {dias_uteis_auto} | **Dias Trabalhados:** {dias_trab_auto}")
        
        st.session_state["dias_uteis_auto"] = dias_uteis_auto
        st.session_state["dias_trab_auto"] = dias_trab_auto
        st.session_state["data_formatada"] = data_formatada

        df_config_eq = carregar_config_equipe()
        
        if "img_os" not in st.session_state:
            st.session_state["img_os"] = {"NET-ABCDM": 529, "NET-Guarulhos": 611, "NET-LESTE": 497}
        img_os_dict = st.session_state["img_os"]
        consultivo_totais = st.session_state.get("consultivo_totais", {"NET-ABCDM": 0, "NET-Guarulhos": 0, "NET-LESTE": 0})
        consultivo_os_hoje_dict = st.session_state.get("consultivo_os_hoje", {"NET-ABCDM": 0, "NET-Guarulhos": 0, "NET-LESTE": 0})
        consultivo_acum_mes = st.session_state.get("consultivo_acumulado_mes", {"NET-ABCDM": 0, "NET-Guarulhos": 0, "NET-LESTE": 0})
        consultivo_acum_prod_mes = st.session_state.get("consultivo_acum_produtos_mes", {"NET-ABCDM": 0, "NET-Guarulhos": 0, "NET-LESTE": 0})
        email_parados_auto = st.session_state.get("email_parados_auto", {})
        email_tecnicos_lista = st.session_state.get("email_tecnicos_lista", [])

        if email_tecnicos_lista:
            with st.expander("📋 Técnicos Parados Lidos do E-mail (.msg)", expanded=False):
                for t_str in email_tecnicos_lista:
                    st.write(f"• {t_str}")

        tabs = st.tabs(["ABCDM", "Guarulhos", "Leste"])
        totais_bases_calc = {}

        for i, item in enumerate(bases_config):
            b_label = item["label"]
            b_proj = item["projeto"]
            with tabs[i]:
                df_b_eq = df_config_eq[df_config_eq["Base"].astype(str).str.upper() == b_proj.upper()] if not df_config_eq.empty else pd.DataFrame()
                
                val_rota_sugerido = img_os_dict.get(b_proj, 529 if "ABC" in b_proj else (611 if "GUA" in b_proj else 497))

                st.markdown(f"##### 📈 1. Dados de Ganho de O.S. ({b_label}):")
                rota_inicial_val = st.number_input(
                    f"Total O.S. Rota Inicial ({b_label})", 
                    value=int(val_rota_sugerido), 
                    min_value=0,
                    step=1,
                    key=f"inp_rota_{b_proj}",
                    help="Valor de Rota Inicial lido da imagem de resumo do dia."
                )
                st.session_state["img_os"][b_proj] = int(rota_inicial_val)
                
                st.markdown("---")
                st.markdown(f"##### 👥 2. Equipe de Supervisores da Base {b_label}:")
                sups_base = st.session_state.supervisores_por_base.get(b_proj, [])
                soma_m_base = 0
                soma_p_base = 0

                if sups_base:
                    col_s1, col_s2 = st.columns(2)
                    for sup in sups_base:
                        sup_eq = df_b_eq[df_b_eq["Supervisor"].astype(str).str.upper().str.strip() == sup.strip().upper()] if not df_b_eq.empty and "Supervisor" in df_b_eq.columns else pd.DataFrame()
                        
                        if "APOIO" in sup.upper():
                            m_def = 0
                        elif not sup_eq.empty and pd.notna(sup_eq["Montados"].values[0]) and int(sup_eq["Montados"].values[0]) < 45:
                            m_def = int(sup_eq["Montados"].values[0])
                        else:
                            m_def = 24 if "ABC" in b_proj else 20
                        
                        parados_email_val = None
                        if email_parados_auto:
                            parados_email_val = 0
                            for k_sup, v_qtd in email_parados_auto.items():
                                if k_sup in sup.upper():
                                    parados_email_val = v_qtd
                                    break
                        
                        p_def = parados_email_val if parados_email_val is not None else (int(sup_eq["Parados"].values[0]) if not sup_eq.empty and pd.notna(sup_eq["Parados"].values[0]) else 0)

                        with col_s1:
                            val_m = st.number_input(f"Montados: {sup}", value=int(m_def), min_value=0, step=1, key=f"m_{b_proj}_{sup}")
                            soma_m_base += val_m
                        with col_s2:
                            val_p = st.number_input(
                                f"Parados (Automático E-mail): {sup}", 
                                value=int(p_def), 
                                min_value=0, 
                                step=1, 
                                key=f"p_{b_proj}_{sup}"
                            )
                            soma_p_base += val_p

                st.markdown("---")
                c1, c2, c3, c4 = st.columns(4)
                
                with c1:
                    st.markdown(f"**Total Montados ({b_label}):**\n### {fmt_br(soma_m_base)}")
                    st.markdown(f"**Total Parados ({b_label}):**\n### {fmt_br(soma_p_base)}")
                    totais_bases_calc[b_proj] = {"montados": int(soma_m_base), "parados": int(soma_p_base)}
                
                with c2:
                    meta_os_val = st.number_input(f"Meta O.S. Mês ({b_label})", value=11800 if "ABCDM" in b_proj else 12200, step=100, key=f"inp_meta_os_{b_proj}")
                    df_b_temp = st.session_state.df_valido[st.session_state.df_valido["Projeto"].str.upper() == b_proj.upper()]
                    if "Tipo de Serviço" in df_b_temp.columns:
                        df_b_temp = df_b_temp[~eh_retorno_credenciada(df_b_temp["Tipo de Serviço"])]
                    prod_hoje_temp = len(df_b_temp[df_b_temp["Tipo de OS"] == "PRODUTIVA"])
                    proj_os_val, _, _ = calcular_projecao_os_base(b_proj, dias_uteis_auto, prod_hoje_temp, data_formatada)
                    st.markdown(f"**Projeção de O.S. (Mês):**\n### {fmt_br(proj_os_val)}")

                with c3:
                    # Meta padrão de consultivo (ex: 350 por supervisor como na TV ou editável)
                    qtd_sups_validos = max(1, len([s for s in sups_base if "APOIO" not in s.upper()]))
                    meta_cons_padrao = int(qtd_sups_validos * 350)
                    meta_cons_input = st.number_input(
                        f"Meta do Consultivo ({b_label})", 
                        value=int(st.session_state.get(f"inp_meta_c_{b_proj}", meta_cons_padrao)), 
                        min_value=0, 
                        step=10, 
                        key=f"inp_meta_c_{b_proj}"
                    )

                    hoje_c_b = int(consultivo_totais.get(b_proj, 0))
                    os_consult_val = int(consultivo_os_hoje_dict.get(b_proj, hoje_c_b * 2))
                    proj_c_b, _, _ = calcular_projecao_consultivo_base(b_proj, dias_uteis_auto, os_consult_val, data_formatada)
                    st.markdown(f"**Projeção do Consultivo (Mês):**\n### {fmt_br(proj_c_b)}")

                with c4:
                    st.markdown(f"**Hoje Consultivo - Contratos ({data_formatada}):**\n### {fmt_br(hoje_c_b)}")
                    st.session_state[f"inp_hoje_c_{b_proj}"] = hoje_c_b
                    st.markdown(f"**Total O.S. / Produtos Consultivo (Hoje):**\n### {fmt_br(os_consult_val)}")
                    
                    tot_cons_mes_real = int(consultivo_acum_mes.get(b_proj, hoje_c_b))
                    tot_prod_mes_real = int(consultivo_acum_prod_mes.get(b_proj, os_consult_val))
                    st.caption(f"📌 Acumulado Real no Mês: **{fmt_br(tot_cons_mes_real)}** contratos | **{fmt_br(tot_prod_mes_real)}** produtos/O.S.")

        st.markdown("---")
        
        if st.button("📊 Sincronizar Google Sheets e Gerar Prévia Executiva", type="primary"):
            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                
                # 1. ATUALIZAR ABA 'Historico_OS'
                try:
                    df_hist_sheet = conn.read(spreadsheet=GOOGLE_SHEET_URL, worksheet="Historico_OS")
                    if df_hist_sheet is None:
                        df_hist_sheet = pd.DataFrame(columns=["Data", "Base", "OS_Executadas", "OS_Inicial"])
                except Exception:
                    df_hist_sheet = pd.DataFrame(columns=["Data", "Base", "OS_Executadas", "OS_Inicial"])

                for item in bases_config:
                    b_proj = item["projeto"]
                    b_label = item["label"]
                    df_b = st.session_state.df_valido[st.session_state.df_valido["Projeto"].str.upper() == b_proj.upper()]
                    if "Tipo de Serviço" in df_b.columns:
                        df_b = df_b[~eh_retorno_credenciada(df_b["Tipo de Serviço"])]
                    prod_hoje = len(df_b[df_b["Tipo de OS"] == "PRODUTIVA"])
                    base_norm = normalizar_nome_base(b_proj)
                    rota_val = int(st.session_state.get(f"inp_rota_{b_proj}", img_os_dict.get(b_proj, 529)))
                    
                    if prod_hoje > 0:
                        if not df_hist_sheet.empty and "Data" in df_hist_sheet.columns and "Base" in df_hist_sheet.columns:
                            df_hist_sheet["_base_norm_"] = df_hist_sheet["Base"].apply(normalizar_nome_base).str.upper()
                            df_hist_sheet = df_hist_sheet[~(
                                (df_hist_sheet["Data"].astype(str).str.strip() == str(data_formatada).strip()) & 
                                (df_hist_sheet["_base_norm_"] == base_norm.upper())
                            )]
                            if "_base_norm_" in df_hist_sheet.columns:
                                df_hist_sheet = df_hist_sheet.drop(columns=["_base_norm_"])
                        
                        nova_h = pd.DataFrame([{
                            "Data": str(data_formatada), 
                            "Base": base_norm, 
                            "OS_Executadas": int(prod_hoje),
                            "OS_Inicial": int(rota_val)
                        }])
                        df_hist_sheet = pd.concat([df_hist_sheet, nova_h], ignore_index=True)

                conn.update(spreadsheet=GOOGLE_SHEET_URL, worksheet="Historico_OS", data=df_hist_sheet)
                st.session_state["df_historico_custom"] = df_hist_sheet

                # 2. ATUALIZAR ABA 'Historico_Consultivo'
                try:
                    df_cons_sheet = conn.read(spreadsheet=GOOGLE_SHEET_URL, worksheet="Historico_Consultivo")
                    if df_cons_sheet is None:
                        df_cons_sheet = pd.DataFrame(columns=["Data", "Base", "Qtd_Consultivo"])
                except Exception:
                    df_cons_sheet = pd.DataFrame(columns=["Data", "Base", "Qtd_Consultivo"])

                hist_arq_all = st.session_state.get("consultivo_historico_arquivo", {})
                for item in bases_config:
                    b_proj = item["projeto"]
                    base_norm = normalizar_nome_base(b_proj)
                    mapa_d_base = hist_arq_all.get(base_norm, {str(data_formatada): int(consultivo_os_hoje_dict.get(b_proj, 0))})

                    for dt_k, qtd_c_val in mapa_d_base.items():
                        if not df_cons_sheet.empty and "Data" in df_cons_sheet.columns and "Base" in df_cons_sheet.columns:
                            df_cons_sheet["_base_norm_"] = df_cons_sheet["Base"].apply(normalizar_nome_base).str.upper()
                            df_cons_sheet = df_cons_sheet[~(
                                (df_cons_sheet["Data"].astype(str).str.strip() == str(dt_k).strip()) & 
                                (df_cons_sheet["_base_norm_"] == base_norm.upper())
                            )]
                            if "_base_norm_" in df_cons_sheet.columns:
                                df_cons_sheet = df_cons_sheet.drop(columns=["_base_norm_"])

                        nova_c = pd.DataFrame([{
                            "Data": str(dt_k),
                            "Base": base_norm,
                            "Qtd_Consultivo": int(qtd_c_val)
                        }])
                        df_cons_sheet = pd.concat([df_cons_sheet, nova_c], ignore_index=True)

                conn.update(spreadsheet=GOOGLE_SHEET_URL, worksheet="Historico_Consultivo", data=df_cons_sheet)

                # 3. ATUALIZAR ABA 'Config_Equipe' e 'Historico_Equipe'
                linhas_config_equipe = []
                linhas_nova_hist_eq = []
                for item in bases_config:
                    b_proj = item["projeto"]
                    b_label = item["label"]
                    sups_b = st.session_state.supervisores_por_base.get(b_proj, [])
                    for s in sups_b:
                        m_s = int(st.session_state.get(f"m_{b_proj}_{s}", 20))
                        p_s = int(st.session_state.get(f"p_{b_proj}_{s}", 0))
                        linhas_config_equipe.append({"Base": b_proj, "Supervisor": s, "Montados": m_s, "Parados": p_s})
                        linhas_nova_hist_eq.append({"Data": data_formatada, "Base": b_label, "Supervisor": s, "Montados": m_s, "Parados": p_s})

                conn.update(spreadsheet=GOOGLE_SHEET_URL, worksheet="Config_Equipe", data=pd.DataFrame(linhas_config_equipe))
                
                try:
                    df_hist_eq_sheet = conn.read(spreadsheet=GOOGLE_SHEET_URL, worksheet="Historico_Equipe")
                    if df_hist_eq_sheet is None:
                        df_hist_eq_sheet = pd.DataFrame(columns=["Data", "Base", "Supervisor", "Montados", "Parados"])
                except Exception:
                    df_hist_eq_sheet = pd.DataFrame(columns=["Data", "Base", "Supervisor", "Montados", "Parados"])

                if not df_hist_eq_sheet.empty and "Data" in df_hist_eq_sheet.columns:
                    df_hist_eq_sheet = df_hist_eq_sheet[df_hist_eq_sheet["Data"].astype(str) != str(data_formatada)]
                    df_hist_eq_final = pd.concat([df_hist_eq_sheet, pd.DataFrame(linhas_nova_hist_eq)], ignore_index=True)
                else:
                    df_hist_eq_final = pd.DataFrame(linhas_nova_hist_eq)
                conn.update(spreadsheet=GOOGLE_SHEET_URL, worksheet="Historico_Equipe", data=df_hist_eq_final)

                # 4. ATUALIZAR ABA 'Previas_Diarias'
                try:
                    df_previas_sheet = conn.read(spreadsheet=GOOGLE_SHEET_URL, worksheet="Previas_Diarias")
                    if df_previas_sheet is None:
                        df_previas_sheet = pd.DataFrame()
                except Exception:
                    df_previas_sheet = pd.DataFrame()

                novas_linhas_previa = []
                dias_uteis = st.session_state.get("dias_uteis_auto", 25)
                df_full_ref = st.session_state.get("df_aniel_full")

                for item in bases_config:
                    b_label = item["label"]
                    b_proj = item["projeto"]
                    df_b_all = st.session_state.df_valido[st.session_state.df_valido["Projeto"].str.upper() == b_proj.upper()].copy()
                    df_b_bruta = df_full_ref[df_full_ref["Projeto"].str.upper() == b_proj.upper()].copy() if (df_full_ref is not None and not df_full_ref.empty and "Projeto" in df_full_ref.columns) else df_b_all
                    
                    t_base = totais_bases_calc.get(b_proj, {"montados": 65, "parados": 0})
                    m_base = int(t_base["montados"])
                    p_base = int(t_base["parados"])
                    meta_os_b = int(st.session_state.get(f"inp_meta_os_{b_proj}", 11800))
                    meta_c_b = int(st.session_state.get(f"inp_meta_c_{b_proj}", 1050))
                    hoje_c_b = int(consultivo_totais.get(b_proj, 0))
                    os_consult_b = int(consultivo_os_hoje_dict.get(b_proj, hoje_c_b * 2))
                    
                    res_b = calcular_metricas_completas(df_b_all, m_base, df_b_bruta)
                    rota_inicial_b = int(st.session_state.get(f"inp_rota_{b_proj}", img_os_dict.get(b_proj, 529)))
                    ganho_b = max(0, res_b["tot_os"] - rota_inicial_b)

                    proj_os_b, _, _ = calcular_projecao_os_base(b_proj, dias_uteis, res_b["produtivo"], data_formatada)
                    proj_c_b, _, _ = calcular_projecao_consultivo_base(b_proj, dias_uteis, os_consult_b, data_formatada)
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
                        "ND": res_b["tot_nd"],
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
                st.cache_data.clear()
                st.success("✅ Configurações salvas no Sheets, histórico atualizado e prévia sincronizada com sucesso!")
                
            except Exception as e:
                st.error(f"Erro ao conectar ou escrever no Google Sheets: {e}")
            
            st.session_state["ir_para_passo_3_ativo"] = True
            st.rerun()

# ==============================================================================
# PÁGINA 3: VISUALIZAÇÃO DA PRÉVIA
# ==============================================================================
elif st.session_state["pagina_atual"] == "3. Visualização da Prévia":
    st.subheader("📊 Passo 3: Apresentação da Prévia Diária - Diretoria")

    data_formatada = data_selecionada

    def gerar_cabecalho_html():
        return f"""
        <table class="custom-table">
            <thead>
                <tr>
                    <th rowspan="2" class="th-data">{data_formatada}</th>
                    <th rowspan="2" class="th-data">Parados</th>
                    <th rowspan="2" class="th-data col-destaque-amarelo">Montados</th>
                    <th colspan="2" class="th-qtd-os">QTDE. DE O.S.</th>
                    <th colspan="4" class="th-consult">CONSULTIVO</th>
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

    if modo_historico_salvo or st.session_state.df_valido is None:
        df_dia = pd.DataFrame()
        if df_historico_previas is not None and not df_historico_previas.empty and "Data" in df_historico_previas.columns:
            df_dia = df_historico_previas[df_historico_previas["Data"].astype(str).str.strip() == str(data_formatada).strip()].copy()

        if df_dia.empty:
            st.warning(f"⚠️ Nenhum registro encontrado na aba `Previas_Diarias` para a data **{data_formatada}**.")
        else:
            tabela_html = [gerar_cabecalho_html()]
            g_parados = 0; g_montados = 0; g_meta_os = 0; g_proj_os = 0
            g_meta_cons = 0; g_proj_cons = 0; g_hoje_cons = 0; g_os_cons = 0
            g_tot_os = 0; g_aberta = 0; g_pontos = 0; g_efic_soma = 0.0
            g_proj_dia = 0; g_os_sem_c = 0
            g_q_ins_soma = 0.0; g_q_serv_soma = 0.0; g_q_nd_soma = 0.0; g_nd = 0
            g_canc = 0; g_saiu_toa = 0; g_ganho = 0; g_gpon = 0; g_q_gpon_soma = 0.0
            g_mig = 0; g_q_mig_soma = 0.0; g_mig_canc = 0; g_retorno = 0
            g_pme = 0; g_q_pme_soma = 0.0; g_pme_canc = 0
            qtd_b = 0

            for item in bases_config:
                b_label = item["label"]
                row_b = df_dia[df_dia["Base"].astype(str).str.upper().str.strip() == b_label.upper()]
                if not row_b.empty:
                    r = row_b.iloc[-1]
                    p_b = pd.to_numeric(r.get("Parados", 0), errors="coerce") or 0
                    m_b = pd.to_numeric(r.get("Montados", 0), errors="coerce") or 0
                    meta_os = pd.to_numeric(r.get("Meta O.S.", 0), errors="coerce") or 0
                    proj_os = pd.to_numeric(r.get("Projeção O.S.", 0), errors="coerce") or 0
                    meta_c = pd.to_numeric(r.get("Meta Consultivo", 0), errors="coerce") or 0
                    proj_c = pd.to_numeric(r.get("Projeção Consultivo", 0), errors="coerce") or 0
                    hoje_c = pd.to_numeric(r.get("Hoje Consultivo", 0), errors="coerce") or 0
                    os_c = pd.to_numeric(r.get("O.S. Consultivo", 0), errors="coerce") or 0
                    tot_os = pd.to_numeric(r.get("Total O.S.", 0), errors="coerce") or 0
                    aberta = pd.to_numeric(r.get("O.S. Aberta", 0), errors="coerce") or 0
                    pts = pd.to_numeric(r.get("Pontos", 0), errors="coerce") or 0
                    efic = pd.to_numeric(r.get("Efic (%)", 0), errors="coerce") or 0.0
                    med_os = pd.to_numeric(r.get("Média O.S.", 0), errors="coerce") or 0.0
                    os_exec = pd.to_numeric(r.get("O.S. Exec. (Proj)", 0), errors="coerce") or 0
                    os_sem_c = pd.to_numeric(r.get("O.S. Sem Consult", 0), errors="coerce") or 0
                    q_ins = pd.to_numeric(r.get("Quebra INS (%)", 0), errors="coerce") or 0.0
                    q_serv = pd.to_numeric(r.get("Quebra SERV (%)", 0), errors="coerce") or 0.0
                    q_nd = pd.to_numeric(r.get("Quebra ND (%)", 0), errors="coerce") or 0.0
                    nd_val = pd.to_numeric(r.get("ND", 0), errors="coerce") or 0
                    canc = pd.to_numeric(r.get("O.S. Canc.", 0), errors="coerce") or 0
                    saiu = pd.to_numeric(r.get("Saiu TOA", 0), errors="coerce") or 0
                    ganho = pd.to_numeric(r.get("Ganho O.S.", 0), errors="coerce") or 0
                    gpon_t = pd.to_numeric(r.get("GPON Total", 0), errors="coerce") or 0
                    gpon_q = pd.to_numeric(r.get("GPON Quebra (%)", 0), errors="coerce") or 0.0
                    mig_t = pd.to_numeric(r.get("Migração Total", 0), errors="coerce") or 0
                    mig_q = pd.to_numeric(r.get("Migração Quebra (%)", 0), errors="coerce") or 0.0
                    mig_c = pd.to_numeric(r.get("Migração Canc.", 0), errors="coerce") or 0
                    ret_wo = pd.to_numeric(r.get("Retorno WO", 0), errors="coerce") or 0
                    pme_t = pd.to_numeric(r.get("PME WO", 0), errors="coerce") or 0
                    pme_q = pd.to_numeric(r.get("PME Quebra (%)", 0), errors="coerce") or 0.0
                    pme_c = pd.to_numeric(r.get("PME Canc.", 0), errors="coerce") or 0

                    g_parados += p_b; g_montados += m_b; g_meta_os += meta_os; g_proj_os += proj_os
                    g_meta_cons += meta_c; g_proj_cons += proj_c; g_hoje_cons += hoje_c; g_os_cons += os_c
                    g_tot_os += tot_os; g_aberta += aberta; g_pontos += pts; g_efic_soma += efic
                    g_proj_dia += os_exec; g_os_sem_c += os_sem_c
                    g_q_ins_soma += q_ins; g_q_serv_soma += q_serv; g_q_nd_soma += q_nd; g_nd += nd_val
                    g_canc += canc; g_saiu_toa += saiu; g_ganho += ganho
                    g_gpon += gpon_t; g_q_gpon_soma += gpon_q
                    g_mig += mig_t; g_q_mig_soma += mig_q; g_mig_canc += mig_c
                    g_retorno += ret_wo; g_pme += pme_t; g_q_pme_soma += pme_q; g_pme_canc += pme_c
                    qtd_b += 1

                    tabela_html.append(
                        f'<tr class="tr-base">'
                        f'<td style="text-align: left; padding-left: 8px;">{b_label}</td>'
                        f'<td>{fmt_br(p_b)}</td>'
                        f'<td class="col-destaque-amarelo">{fmt_br(m_b)}</td>'
                        f'<td>{fmt_br(meta_os)}</td>'
                        f'<td class="red-text">{fmt_br(proj_os)}</td>'
                        f'<td>{fmt_br(meta_c)}</td>'
                        f'<td class="red-text">{fmt_br(proj_c)}</td>'
                        f'<td>{fmt_br(hoje_c)}</td>'
                        f'<td>{fmt_br(os_c)}</td>'
                        f'<td>{fmt_br(tot_os)}</td>'
                        f'<td>{fmt_br(aberta)}</td>'
                        f'<td>{fmt_br(pts)}</td>'
                        f'<td>{fmt_br(efic, 1)}%</td>'
                        f'<td class="col-destaque-azul">{fmt_br(med_os, 2)}</td>'
                        f'<td>{fmt_br(os_exec)}</td>'
                        f'<td class="col-destaque-amarelo">{fmt_br(os_sem_c)}</td>'
                        f'<td>{fmt_br(q_ins, 1)}%</td>'
                        f'<td>{fmt_br(q_serv, 1)}%</td>'
                        f'<td>{fmt_br(q_nd, 1)}%</td>'
                        f'<td>{fmt_br(nd_val)}</td>'
                        f'<td>{fmt_br(canc)}</td>'
                        f'<td>{fmt_br(saiu)}</td>'
                        f'<td>{fmt_br(ganho)}</td>'
                        f'<td>{fmt_br(gpon_t)}</td>'
                        f'<td>{fmt_br(gpon_q, 1)}%</td>'
                        f'<td>{fmt_br(mig_t)}</td>'
                        f'<td>{fmt_br(mig_q, 1)}%</td>'
                        f'<td>{fmt_br(mig_c)}</td>'
                        f'<td>{fmt_br(ret_wo)}</td>'
                        f'<td>{fmt_br(pme_t)}</td>'
                        f'<td>{fmt_br(pme_q, 1)}%</td>'
                        f'<td>{fmt_br(pme_c)}</td>'
                        f'</tr>'
                    )

            div_b = max(1, qtd_b)
            g_media_os_calc = (g_proj_dia / g_montados) if g_montados > 0 else 0.0
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
                f'<td>{fmt_br(g_efic_soma / div_b, 1)}%</td>'
                f'<td class="col-destaque-azul">{fmt_br(g_media_os_calc, 2)}</td>'
                f'<td>{fmt_br(g_proj_dia)}</td>'
                f'<td class="col-destaque-amarelo">{fmt_br(g_os_sem_c)}</td>'
                f'<td>{fmt_br(g_q_ins_soma / div_b, 1)}%</td>'
                f'<td>{fmt_br(g_q_serv_soma / div_b, 1)}%</td>'
                f'<td>{fmt_br(g_q_nd_soma / div_b, 1)}%</td>'
                f'<td>{fmt_br(g_nd)}</td>'
                f'<td>{fmt_br(g_canc)}</td>'
                f'<td>{fmt_br(g_saiu_toa)}</td>'
                f'<td>{fmt_br(g_ganho)}</td>'
                f'<td>{fmt_br(g_gpon)}</td>'
                f'<td>{fmt_br(g_q_gpon_soma / div_b, 1)}%</td>'
                f'<td>{fmt_br(g_mig)}</td>'
                f'<td>{fmt_br(g_q_mig_soma / div_b, 1)}%</td>'
                f'<td>{fmt_br(g_mig_canc)}</td>'
                f'<td>{fmt_br(g_retorno)}</td>'
                f'<td>{fmt_br(g_pme)}</td>'
                f'<td>{fmt_br(g_q_pme_soma / div_b, 1)}%</td>'
                f'<td>{fmt_br(g_pme_canc)}</td>'
                f'</tr></tbody></table>'
            )
            st.markdown("".join(tabela_html), unsafe_allow_html=True)

    else:
        # Cálculo completo em tempo real da sessão ativa
        df_valido = st.session_state.df_valido
        df_full_ref = st.session_state.get("df_aniel_full")
        dias_uteis = st.session_state.get("dias_uteis_auto", 25)
        df_config_eq_v = carregar_config_equipe()

        g_parados = 0; g_montados = 0; g_meta_os = 0; g_proj_os = 0
        g_meta_cons = 0; g_proj_cons = 0; g_hoje_cons = 0; g_os_cons = 0
        g_tot_os = 0; g_aberta = 0; g_pontos = 0; g_prod = 0; g_quebra = 0
        g_sem_cons = 0; g_nd = 0; g_canc = 0; g_saiu_toa = 0; g_ganho = 0
        g_gpon = 0; g_mig = 0; g_mig_canc = 0; g_retorno = 0; g_pme = 0; g_pme_canc = 0
        g_raw_ins_q = 0; g_raw_ins_tot = 0; g_raw_serv_q = 0; g_raw_serv_tot = 0
        g_raw_nd_q = 0; g_raw_nd_tot = 0; g_raw_gpon_q = 0; g_raw_gpon_tot = 0
        g_raw_mig_q = 0; g_raw_mig_tot = 0; g_raw_pme_q = 0; g_raw_pme_tot = 0

        metricas_bases = {}
        consultivo_totais = st.session_state.get("consultivo_totais", {"NET-ABCDM": 0, "NET-Guarulhos": 0, "NET-LESTE": 0})
        consultivo_os_hoje_dict = st.session_state.get("consultivo_os_hoje", {"NET-ABCDM": 0, "NET-Guarulhos": 0, "NET-LESTE": 0})

        for item in bases_config:
            b_label = item["label"]
            b_proj = item["projeto"]
            
            df_b_all = df_valido[df_valido["Projeto"].str.upper() == b_proj.upper()].copy() if isinstance(df_valido, pd.DataFrame) and "Projeto" in df_valido.columns else pd.DataFrame()
            df_b_bruta = df_full_ref[df_full_ref["Projeto"].str.upper() == b_proj.upper()].copy() if (df_full_ref is not None and not df_full_ref.empty and "Projeto" in df_full_ref.columns) else df_b_all
            
            df_b_eq_v = df_config_eq_v[df_config_eq_v["Base"].astype(str).str.upper() == b_proj.upper()] if not df_config_eq_v.empty else pd.DataFrame()
            
            sups_base = st.session_state.supervisores_por_base.get(b_proj, [])
            m_base = sum([int(st.session_state.get(f"m_{b_proj}_{s}", 20)) for s in sups_base])
            if m_base <= 0:
                m_base = int(df_b_eq_v["Montados"].sum()) if not df_b_eq_v.empty and "Montados" in df_b_eq_v.columns else 65
            p_base = sum([int(st.session_state.get(f"p_{b_proj}_{s}", 0)) for s in sups_base])

            meta_os_b = int(st.session_state.get(f"inp_meta_os_{b_proj}", 11800 if "ABCDM" in b_proj else 12200))
            qtd_sups_validos = max(1, len([s for s in sups_base if "APOIO" not in s.upper()]))
            meta_c_b = int(st.session_state.get(f"inp_meta_c_{b_proj}", qtd_sups_validos * 350))
            hoje_c_b = int(consultivo_totais.get(b_proj, 0))
            os_consult_b = int(consultivo_os_hoje_dict.get(b_proj, hoje_c_b * 2))
            
            res_b = calcular_metricas_completas(df_b_all, m_base, df_b_bruta)
            
            tot_os_previa_b = res_b["tot_os"]
            rota_inicial_b = buscar_os_inicial_sheets(b_proj, data_formatada)
            ganho_b = max(0, tot_os_previa_b - rota_inicial_b)

            os_sem_consult_val = int(round(res_b["proj_dia"] - os_consult_b, 0))
            res_b["os_sem_c"] = os_sem_consult_val

            proj_os_b, _, _ = calcular_projecao_os_base(b_proj, dias_uteis, res_b["produtivo"], data_formatada)
            proj_c_b, _, _ = calcular_projecao_consultivo_base(b_proj, dias_uteis, os_consult_b, data_formatada)

            g_parados += p_base; g_montados += m_base; g_meta_os += meta_os_b; g_proj_os += proj_os_b
            g_meta_cons += meta_c_b; g_proj_cons += proj_c_b; g_hoje_cons += hoje_c_b; g_os_cons += os_consult_b
            g_tot_os += res_b["tot_os"]; g_aberta += res_b["os_aberta"]; g_pontos += res_b["pontos"]; g_prod += res_b["produtivo"]
            g_quebra += res_b["quebra_geral"]; g_sem_cons += res_b["os_sem_c"]; g_nd += res_b["tot_nd"]
            g_canc += res_b["os_canc"]; g_saiu_toa += res_b["saiu_toa"]; g_ganho += ganho_b
            g_gpon += res_b["tot_gpon"]; g_mig += res_b["tot_mig"]; g_mig_canc += res_b["canc_mig"]
            g_retorno += res_b["retorno_wo"]; g_pme += res_b["tot_pme"]; g_pme_canc += res_b["canc_pme"]
            g_raw_ins_q += res_b["_raw_q_ins"]; g_raw_ins_tot += res_b["_raw_tot_ins"]
            g_raw_serv_q += res_b["_raw_q_serv"]; g_raw_serv_tot += res_b["_raw_tot_serv"]
            g_raw_nd_q += res_b["_raw_q_nd"]; g_raw_nd_tot += res_b["_raw_tot_nd"]
            g_raw_gpon_q += res_b["_raw_q_gpon"]; g_raw_gpon_tot += res_b["_raw_tot_gpon"]
            g_raw_mig_q += res_b["_raw_q_mig"]; g_raw_mig_tot += res_b["_raw_tot_mig"]
            g_raw_pme_q += res_b["_raw_q_pme"]; g_raw_pme_tot += res_b["_raw_tot_pme"]

            metricas_bases[b_proj] = {
                "res": res_b, "p_base": p_base, "m_base": m_base, "meta_os": meta_os_b,
                "proj_os": proj_os_b, "meta_c": meta_c_b, "proj_c": proj_c_b, "hoje_c": hoje_c_b,
                "os_consult": os_consult_b, "ganho": ganho_b, "label": b_label
            }

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
        
        q_ins_geral = (g_raw_ins_q / g_raw_ins_tot * 100) if g_raw_ins_tot > 0 else 0.0
        q_serv_geral = (g_raw_serv_q / g_raw_serv_tot * 100) if g_raw_serv_tot > 0 else 0.0
        g_q_nd = (g_raw_nd_q / g_raw_nd_tot * 100) if g_raw_nd_tot > 0 else 0.0
        g_q_gpon = (g_raw_gpon_q / g_raw_gpon_tot * 100) if g_raw_gpon_tot > 0 else 0.0
        g_q_mig = (g_raw_mig_q / g_raw_mig_tot * 100) if g_raw_mig_tot > 0 else 0.0
        g_q_pme = (g_raw_pme_q / g_raw_pme_tot * 100) if g_raw_pme_tot > 0 else 0.0

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
            f'<td>{fmt_br(q_ins_geral, 1)}%</td>'
            f'<td>{fmt_br(q_serv_geral, 1)}%</td>'
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
        cons_sups_all = st.session_state.get("consultivo_supervisores", {})

        for item in bases_config:
            b_label = item["label"]
            b_proj = item["projeto"]
            m = metricas_bases[b_proj]
            res_b = m["res"]
            cons_sups_base = cons_sups_all.get(b_proj, {})
            
            with st.expander(f"📂 Base: {b_label} (Clique para Expandir/Recolher Detalhamento)"):
                df_b_all = df_valido[df_valido["Projeto"].str.upper() == b_proj.upper()].copy() if isinstance(df_valido, pd.DataFrame) and "Projeto" in df_valido.columns else pd.DataFrame()
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
                    df_s = df_b_all[df_b_all["Supervisor"] == s] if not df_b_all.empty and "Supervisor" in df_b_all.columns else pd.DataFrame()
                    p_sup = st.session_state.get(f"p_{b_proj}_{s}", 0)
                    m_sup = st.session_state.get(f"m_{b_proj}_{s}", 20)
                    res_s = calcular_metricas_completas(df_s, m_sup)
                    primeiro_nome = s.split()[0]
                    
                    # Busca dados do Consultivo para este supervisor (como nas Telas 5 e 6 da TV)
                    dados_cons_s = {"contratos_hoje": 0, "produtos_hoje": 0, "produtos_mes": 0}
                    for k_cs, val_cs in cons_sups_base.items():
                        if k_cs.split()[0] in s.upper() or primeiro_nome in k_cs:
                            dados_cons_s = val_cs
                            break
                    
                    c_hoje_s = dados_cons_s["contratos_hoje"]
                    os_c_hoje_s = dados_cons_s["produtos_hoje"]
                    os_sem_c_s = int(round(res_s["proj_dia"] - os_c_hoje_s, 0))
                    
                    tabela_bloco_html.append(
                        f'<tr class="tr-sup">'
                        f'<td style="text-align: left; padding-left: 20px;">{primeiro_nome}</td>'
                        f'<td>{fmt_br(p_sup)}</td>'
                        f'<td class="col-destaque-amarelo">{fmt_br(m_sup)}</td>'
                        f'<td></td><td></td>'
                        f'<td>350</td><td>{fmt_br(dados_cons_s["produtos_mes"])}</td><td>{fmt_br(c_hoje_s)}</td><td>{fmt_br(os_c_hoje_s)}</td>'
                        f'<td>{fmt_br(res_s["tot_os"])}</td>'
                        f'<td>{fmt_br(res_s["os_aberta"])}</td>'
                        f'<td>{fmt_br(res_s["pontos"])}</td>'
                        f'<td>{fmt_br(res_s["efic"], 1)}%</td>'
                        f'<td class="col-destaque-azul">{fmt_br(res_s["media_os"], 2)}</td>'
                        f'<td>{fmt_br(res_s["proj_dia"])}</td>'
                        f'<td class="col-destaque-amarelo">{fmt_br(os_sem_c_s)}</td>'
                        f'<td>{fmt_br(res_s["q_ins"], 1)}%</td>'
                        f'<td>{fmt_br(res_s["q_serv"], 1)}%</td>'
                        f'<td>{fmt_br(res_s["q_nd"], 1)}%</td>'
                        f'<td>{fmt_br(res_s["tot_nd"])}</td>'
                        f'<td>{fmt_br(res_s["os_canc"])}</td>'
                        f'<td>{fmt_br(res_s["saiu_toa"])}</td>'
                        f'<td></td>'
                        f'<td>{fmt_br(res_s["tot_gpon"])}</td>'
                        f'<td>{fmt_br(res_s["q_gpon"], 1)}%</td>'
                        f'<td>{fmt_br(res_s["tot_mig"])}</td>'
                        f'<td>{fmt_br(res_s["q_mig"], 1)}%</td>'
                        f'<td>{fmt_br(res_s["canc_mig"])}</td>'
                        f'<td>{fmt_br(res_s["retorno_wo"])}</td>'
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
                    df_export.to_excel(writer, index=False)
                
                st.download_button(
                    label="📥 Baixar Planilha ANIEL Tratada (.xlsx)",
                    data=output.getvalue(),
                    file_name="Planilha_Tratada_Aniel.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        except Exception:
            pass
