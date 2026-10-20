import io
import re
import pandas as pd
import numpy as np
import streamlit as st

st.set_page_config(
    page_title="Painel Executivo Operacional",
    page_icon="📈",
    layout="wide"
)

# Estilização CSS adicional para cabeçalhos e cartões
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 15px;
        border-left: 5px solid #2e7d32;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

st.title("📈 Apresentação Gerencial de Resultados - Diretoria")
st.markdown("Visão executiva integrada com totalização geral e indicadores consolidados.")

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

BAIXAS_DICT = {
    "100 - AGENDAMENTO NAO CUMPRIDO": "IMPRODUTIVA",
    "101 - ENDERECO NAO LOCALIZADO": "IMPRODUTIVA",
    "103 - CHUVA": "IMPRODUTIVA",
    "104 - Falta De Material": "IMPRODUTIVA",
    "105 - Sem Energia Eletrica Na Regiao/Predio/Residencia": "IMPRODUTIVA",
    "106 - CLIENTE AUSENTE": "IMPRODUTIVA",
    "107 - ENTRADA NAO AUTORIZADA": "IMPRODUTIVA",
    "108 - Realizar Obra Civil ou alteracao rede eletrica": "IMPRODUTIVA",
    "110 - PROBLEMA NA TUBULACAO": "IMPRODUTIVA",
    "112 - SEM ACESSO AO DG / SOTAO / COMODO": "IMPRODUTIVA",
    "113 - Sem TV / Computador Na Residencia/ Celular": "IMPRODUTIVA",
    "114 - Habilitação telefonica não ok": "IMPRODUTIVA",
    "125 - CLIENTE DESISTE DA AGENDA": "IMPRODUTIVA",
    "203 - REDE EXTERNA COM PROBLEMA": "IMPRODUTIVA",
    "204 - Backbone Com Problema": "IMPRODUTIVA",
    "205 - Falta Tap Ou Passivo / Tap Ou Passivo Lotado": "IMPRODUTIVA",
    "206 - PREDIO SEM BACKBONE": "IMPRODUTIVA",
    "211 - FALTA NAP/NAP LOTADA": "IMPRODUTIVA",
    "217 - BACKBONE GPON COM PROBLEMA": "IMPRODUTIVA",
    "301 - TIPO DE OS INCORRETA": "IMPRODUTIVA",
    "302 - DESISTENCIA DA ASSINATURA / SERVICO": "IMPRODUTIVA",
    "303 - INST MODELO CABO CASA NAO ACEITA PELO CLIENTE": "IMPRODUTIVA",
    "305 - RUA NAO CABEADA": "IMPRODUTIVA",
    "306 - NAO RESIDE NO ENDERECO": "IMPRODUTIVA",
    "307 - Residencia Em Construcao / Reforma": "IMPRODUTIVA",
    "308 - INSTALACAO NAO CONTEMPLARA PADRAO": "IMPRODUTIVA",
    "312 - CLIENTE NAO SOLICITOU O SERVICO": "IMPRODUTIVA",
    "316 - RUA NAO CABEADA GPON": "IMPRODUTIVA",
    "328 - Entrega Concluida": "PRODUTIVA",
    "400 - Informacao / Correcao Cadastral": "IMPRODUTIVA",
    "402 - Divergencia de dados cadastrais": "IMPRODUTIVA",
    "408 - Serviço Concluído sem Movimentação de Terminal": "PRODUTIVA",
    "409 - SERVICO CONCLUIDO": "PRODUTIVA",
    "425 - Troca De Tecnologia": "PRODUTIVA",
    "430 - Equipamento Retirado": "PRODUTIVA",
    "440 - Equipamento Roubado / Furtado / Extraviado": "PRODUTIVA",
    "467 - Resolvido Durante a Vistoria": "PRODUTIVA",
    "470 - CASO IMPROCEDENTE": "PRODUTIVA",
    "474 - REPOSICIONADO O EXTENSOR": "PRODUTIVA",
    "475 - VELOCIDADE DO EXTENSOR CONFORME CONTRATADO": "PRODUTIVA",
    "477 - INSTALACAO MESH CABEADA": "PRODUTIVA",
    "500 - READEQUACAO DE SINAL - PASSIVOS": "PRODUTIVA",
    "501 - Amplificador Equalizado": "PRODUTIVA",
    "502 - Amplificador Com Defeito - Troca": "PRODUTIVA",
    "505 - Passivo Interno Queim./Degrad. - Troca": "PRODUTIVA",
    "506 - Passivo Interno Fora Do Padrão - Troca": "PRODUTIVA",
    "507 - Passivo MDU Queim./Degrad. - Troca": "PRODUTIVA",
    "509 - Cable Isolator Danificado/Queimado - Troca": "PRODUTIVA",
    "510 - Fonte Com Defeito - Troca": "PRODUTIVA",
    "514 - Envio De Hit - Habilitar Canais": "PRODUTIVA",
    "515 - Envio De Hit - Correção Do Update ID": "PRODUTIVA",
    "516 - T.T - TRAVADO": "PRODUTIVA",
    "517 - T.T - Queimado": "PRODUTIVA",
    "518 - T.T - Não Habilita / Não Sincroniza": "PRODUTIVA",
    "519 - T.T - Não Grava": "PRODUTIVA",
    "520 - T.T - Não Atualiza SW": "PRODUTIVA",
    "521 - T.T - Intermitente": "PRODUTIVA",
    "522 - T.T - IN / OUT Queimadas": "PRODUTIVA",
    "523 - T.T - Alcance Wifi": "PRODUTIVA",
    "524 - T.T - Solic. Cliente": "PRODUTIVA",
    "525 - T.T - Falha em Imagem/Quadriculando": "PRODUTIVA",
    "526 - T.T - Erro de Leitura Smart": "PRODUTIVA",
    "527 - T.T - Não Navega": "PRODUTIVA",
    "530 - T.T Por Outro Colocado No Mesmo Serviço": "PRODUTIVA",
    "533 - Reset Na Config Terminal - Travado": "PRODUTIVA",
    "534 - RESET NA CONFIG TERMINAL - SOLICIT SENHA": "PRODUTIVA",
    "535 - Reset Na Config Terminal - Não Atualiza": "PRODUTIVA",
    "536 - Reconfigurado Roteador do cliente": "PRODUTIVA",
    "537 - Reconfigurado eMTA/Roteador NET-WIFI": "PRODUTIVA",
    "538 - Reconfiguração Do Formato Da Imagem": "PRODUTIVA",
    "539 - Reconfiguração De Audio": "PRODUTIVA",
    "540 - Conector Interno Oxidado - Troca": "PRODUTIVA",
    "541 - Conector Interno Mal Feito - Troca": "PRODUTIVA",
    "542 - Conector Interno Fora Do Padrão - Troca": "PRODUTIVA",
    "544 - Conector TAP Mal Feito - Troca": "PRODUTIVA",
    "545 - Conector TAP - Fora Do Padrão - Troca": "PRODUTIVA",
    "546 - Conector MDU Oxidado - Troca": "PRODUTIVA",
    "547 - CONECTOR MDU MAL FEITO - TROCA": "PRODUTIVA",
    "549 - Velocidade Do Virtua Conforme Contratada": "PRODUTIVA",
    "551 - Sintonia Efetuada - AV/HDMI": "PRODUTIVA",
    "552 - INSTRUCOES DO USO DA INTERATIVIDADE": "PRODUTIVA",
    "553 - Instruções De Uso Do Controle Remoto": "PRODUTIVA",
    "554 - Instruções Sobre Smart Card": "PRODUTIVA",
    "555 - Sem Defeito No Produto Virtua Reclamado": "PRODUTIVA",
    "556 - Sem Defeito No Produto TV Reclamado": "PRODUTIVA",
    "557 - Sem Defeito No Produto Netfone Reclamado": "PRODUTIVA",
    "558 - Boot No Terminal": "PRODUTIVA",
    "560 - Equipamento / Rede De Dados Cliente Com Defeito": "PRODUTIVA",
    "562 - Cabo Reconectado/Identificado": "PRODUTIVA",
    "563 - RECONEXAO DOS CABOS NO EQUIPAMENTO DO CLIENTE": "PRODUTIVA",
    "564 - Cabos Especiais Com Defeito - Troca": "PRODUTIVA",
    "565 - Entrega De Cabos Especiais": "PRODUTIVA",
    "566 - Refeito Drop": "PRODUTIVA",
    "567 - Refeito Cabeamento Coaxial": "PRODUTIVA",
    "568 - Cabeamento Telefônico Refeito": "PRODUTIVA",
    "569 - Necessário Refazer Cabeamento Telefônico": "PRODUTIVA",
    "570 - Necessário Refazer Cabeamento Coaxial": "PRODUTIVA",
    "574 - CORRECAO EFETUADA NO DATA CENTER": "PRODUTIVA",
    "575 - Tomada Telefone Com Problema - Troca": "PRODUTIVA",
    "580 - Conexões De Rede De Dados Refeitas": "PRODUTIVA",
    "582 - ROTEADOR COM PROBLEMA": "PRODUTIVA",
    "584 - CONECTOR OPTICO INTERNO DANIFICADO": "PRODUTIVA",
    "590 - PTO COM DEFEITO TROCA": "PRODUTIVA",
    "EM ROTA": "EM ABERTO",
    "INICIADO": "EM ABERTO",
    "PENDENTE": "EM ABERTO",
}

PONTOS_DICT = {
    "ADESAO - INSTALACAO DE ASSINATURA": 3.50,
    "ADESAO ENTREGA STREAMING": 3.50,
    "ADESAO - INSTALACAO DE ASSINATURA DIGITAL": 3.50,
    "MUDANCA DE ENDERECO - INSTALAR ASSINATURA": 3.00,
    "MUDANCA DE ENDERECO - INSTALAR ASSINATURA DIGITAL": 3.00,
    "MUDANCA DE ENDERECO - ENTREGA STREAMING": 3.00,
    "MUDANCA DE ENDERECO - ENTREGA ADC STREAMING": 3.00,
    "DESOBSTRUCAO - INSTALACAO DE ASSINATURA": 3.00,
    "ADESAO - INSTALAR PONTO VIRTUA": 2.50,
    "INSTALAR PONTO VIRTUA": 2.50,
    "REFAZER MANUTENCAO": 2.50,
    "REFAZER INSTALACAO": 2.50,
    "REFAZER MANUTENCAO PON": 2.50,
    "REFAZER INSTALACAO DIGITAL": 2.50,
    "MUDANCA DE PACOTE": 2.30,
    "MUD PACOTE ENTREGA STREAMING": 2.30,
    "MUDANCA DE PACOTE DIGITAL": 2.30,
    "MUDANCA DE PACOTE DOWN HDD": 2.30,
    "MUDANCA DE PACOTE RET HDD": 2.30,
    "INSTALACAO WIFI MESH": 2.00,
    "INSTALAR TV BASE": 2.00,
    "REINSTALACAO - ASSINATURA": 2.00,
    "INSTALAR CABEAMENTO MESH": 2.00,
    "INST PONTO EXTENSAO REDE VIRTUA": 2.00,
    "REINSTALACAO - ASSINATURA DIGITAL": 2.00,
    "VISITA TECNICA - VIRTUA": 1.80,
    "VISITA TECNICA DIGITAL": 1.80,
    "VISITA TECNICA - VOIP": 1.80,
    "VISITA TECNICA STREAMING": 1.80,
    "VISITA TECNICA": 1.80,
    "VISITA TECNICA - SMART HOME": 1.80,
    "MUDANCA DE ENDERECO - INSTALAR PONTO ADICIONAL VIRTUA": 1.60,
    "INSTALAR SERVICO CONEXAO ADICIONAL DIGITAL": 1.60,
    "MUDANCA DE LOCAL DE PONTO": 1.60,
    "MUDANCA DE LOCAL DE PONTO DIGITAL": 1.60,
    "ADESAO - INSTALAR SERVICO CONEXAO ADICIONAL DIGITAL": 1.60,
    "MUDANCA DE LOCAL DE PONTO VOIP": 1.60,
    "TROCA DECODER PARA ATUALIZACAO DIGITAL": 1.50,
    "TROCA DECODER PARA ATUALIZACAO DIGITAL 4K": 1.50,
    "TROCA DE EQUIPAMENTO HD": 1.50,
    "BASE ENTREGA STREAMING": 1.50,
    "INSTALACAO EXTENSAO VOIP": 1.50,
    "MODERNIZACAO EXTENSOR WIFI MESH": 1.50,
    "TROCA EQUIPAMENTO PARA ATUALIZACAO TECNOLOGIA": 1.50,
    "TROCA DE EQUIPAMENTO WIFI": 1.50,
    "MODERNIZACAO EQUIPAMENTO WIFI": 1.50,
    "TROCA DE EQUIPAMENTO STREAMING": 1.50,
    "MODERNIZACAO EQUIPAMENTO DIGITAL": 1.50,
    "MIGRAÇÃO GPON (adição na MP GPON)": 1.40,
    "REINSTALACAO - PONTO ADICIONAL VIRTUA": 1.40,
    "REINSTALACAO - SERVICO CONEXAO ADICIONAL DIGITAL": 1.40,
    "REINSTALACAO - ASSINATURA VOIP": 1.30,
    "REINSTALACAO ENTREGA STREAMING": 1.30,
    "REINSTALACAO ENTREGA ADC STREAMING": 1.30,
    "REINSTALACAO - PONTO ADICIONAL VOIP": 1.30,
    "MUDANCA DE ENDERECO - INSTALAR PONTO VOIP": 1.20,
    "ADESAO - INSTALAR PONTO VOIP": 1.20,
    "INSTALAR PONTO VOIP": 1.20,
    "MUDANCA ENDERECO - INSTALAR SERVICO CONEXAO ADIC DIG": 1.20,
    "ADESAO - INSTALAR PONTO PORTABILIDADE": 1.20,
    "ADESAO ENTREGA ADC STREAMING": 1.20,
    "INSTALAR PONTO PORTABILIDADE": 1.20,
    "BASE ENTREGA ADC STREAMING": 1.20,
    "MUDANCA ENDERECO - INSTALAR SERVICO CONEXAO ADIC": 1.20,
    "REINSTALACAO - SERVICO CONEXAO ADICIONAL": 1.20,
    "ENVIO DE CHIP VIA TECNICO": 0.50,
    "RETIRAR PONTO": 0.50,
    "RETIRAR PONTO VOIP": 0.50,
    "RETIRAR EQUIPAMENTO": 0.50,
    "RETIRADA WIFI MESH": 0.50,
    "ENTREGA DE CABOS ESPECIAIS E CONEXOES": 0.50,
    "RETIRAR EMTA": 0.50,
    "INSTALACAO DE CABO HFC": 0.10,
    "INSTALACAO DE CABO GPON": 0.10,
    "CONSTRUCAO MDU GPON": 0.00,
    "APOIO CONSTRUCAO GPON MDU": 0.00,
    "MANUTENCAO PREVENTIVA INDOOR I": 1.00,
    "LIMPEZA DE RUIDO INDOOR": 1.00,
    "SUBSTITUICAO DE CONTROLE REMOTO DIGITAL": 1.00,
    "MODERNIZACAO BL": 1.00,
    "RETORNO DE CREDENCIADA": 0.00,
    "BLINDAGEM TV ATUALIZACAO DIG": 1.00,
    "MANUTENCAO REPARO NO DROP": 1.00,
    "VISITA TECNICA WIFI MESH": 1.00,
    "MANUTENCAO CORRETIVA - DEGRADACAO MDU": 1.00,
    "MANUTENCAO CORRETIVA - MDU": 1.00,
    "MANUTENCAO CORRETIVA - MDU GPON": 1.00,
    "ATENDIMENTO PRIORITARIO MANUTENCAO": 1.00,
    "CONFIGURACAO STREAMING": 1.00,
    "MUDANCA DE ENDERECO - RETIRAR PONTOS": 1.00,
}

DESC_OS_DICT = {
    "ADESAO - INSTALACAO DE ASSINATURA": "INSTALAÇÃO",
    "ADESAO - INSTALACAO DE ASSINATURA DIGITAL": "INSTALAÇÃO",
    "ADESAO - INSTALAR PONTO PORTABILIDADE": "INSTALAÇÃO",
    "ADESAO - INSTALAR PONTO VIRTUA": "INSTALAÇÃO",
    "ADESAO - INSTALAR PONTO VOIP": "INSTALAÇÃO",
    "ADESAO - INSTALAR SERVICO CONEXAO ADICIONAL": "INSTALAÇÃO",
    "ADESAO - INSTALAR SERVICO CONEXAO ADICIONAL DIGITAL": "INSTALAÇÃO",
    "INSTALAR PONTO PORTABILIDADE": "INSTALAÇÃO",
    "INSTALAR PONTO VIRTUA": "INSTALAÇÃO",
    "INSTALAR PONTO VOIP": "INSTALAÇÃO",
    "INSTALAR SERVICO CONEXAO ADICIONAL": "INSTALAÇÃO",
    "INSTALAR SERVICO CONEXAO ADICIONAL DIGITAL": "INSTALAÇÃO",
    "ADESAO ENTREGA STREAMING": "INSTALAÇÃO",
    "DESOBSTRUCAO - INSTALACAO DE ASSINATURA": "INSTALAÇÃO",
    "ADESAO ENTREGA ADC STREAMING": "INSTALAÇÃO",
    "RETORNO DE CREDENCIADA": "RETORNO",
    "ENTREGA EQUIPAMENTO HDD": "SERVIÇOS",
    "ENVIO DE CHIP VIA TECNICO": "INSTALAÇÃO",
    "INSTALACAO EXTENSAO VOIP": "SERVIÇOS",
    "MUDANCA DE ENDERECO - INSTALAR ASSINATURA": "SERVIÇOS",
    "MUDANCA DE ENDERECO - INSTALAR ASSINATURA DIGITAL": "SERVIÇOS",
    "MUDANCA DE ENDERECO - INSTALAR PONTO ADICIONAL VIRTUA": "SERVIÇOS",
    "MUDANCA DE BASE": "SERVIÇOS",
    "MUDANCA DE ENDERECO - INSTALAR PONTO VOIP": "SERVIÇOS",
    "MUDANCA DE LOCAL DE PONTO": "SERVIÇOS",
    "MUDANCA DE LOCAL DE PONTO DIGITAL": "SERVIÇOS",
    "MUDANCA DE LOCAL DE PONTO VOIP": "SERVIÇOS",
    "MUDANCA DE PACOTE": "SERVIÇOS",
    "MUDANCA DE PACOTE DIGITAL": "SERVIÇOS",
    "MUDANCA ENDERECO - INSTALAR SERVICO CONEXAO ADIC": "SERVIÇOS",
    "MUDANCA ENDERECO - INSTALAR SERVICO CONEXAO ADIC DIG": "SERVIÇOS",
    "REFAZER INSTALACAO": "SERVIÇOS",
    "REFAZER INSTALACAO DIGITAL": "SERVIÇOS",
    "REFAZER MANUTENCAO": "SERVIÇOS",
    "REINSTALACAO - ASSINATURA": "SERVIÇOS",
    "REINSTALACAO - ASSINATURA DIGITAL": "SERVIÇOS",
    "REINSTALACAO - ASSINATURA VOIP": "SERVIÇOS",
    "REINSTALACAO - PONTO ADICIONAL VIRTUA": "SERVIÇOS",
    "REINSTALACAO - PONTO ADICIONAL VOIP": "SERVIÇOS",
    "REINSTALACAO - SERVICO CONEXAO ADICIONAL DIGITAL": "SERVIÇOS",
    "RETIRAR PONTO": "SERVIÇOS",
    "RETIRAR PONTO VOIP": "SERVIÇOS",
    "TROCA DE EQUIPAMENTO WIFI": "SERVIÇOS",
    "TROCA DE EQUIPAMENTO PARA ATUALIZACAO TECNOLOGIA": "SERVIÇOS",
    "TROCA TECNOLOGIA SMART": "SERVIÇOS",
    "INSTALAR TV BASE": "INSTALAÇÃO",
    "INST PONTO EXTENSAO REDE VIRTUA": "INSTALAÇÃO",
    "MUDANCA DE PACOTE UP HDD": "SERVIÇOS",
    "BASE ENTREGA STREAMING": "SERVIÇOS",
    "ENTREGA DE CABOS ESPECIAIS E CONEXOES": "SERVIÇOS",
    "MUDANCA DE ENDERECO - ENTREGA STREAMING": "SERVIÇOS",
    "MUDANCA DE PACOTE DOWN HDD": "SERVIÇOS",
    "MODERNIZACAO EQUIPAMENTO WIFI": "SERVIÇOS",
    "INSTALACAO WIFI MESH": "INSTALAÇÃO",
    "MUD PACOTE ENTREGA STREAMING": "SERVIÇOS",
    "VISTORIA DE CASOS ESPECIAIS EPO": "SERVIÇOS",
    "MUDANCA DE PACOTE RET HDD": "SERVIÇOS",
    "VISITA TECNICA - VIRTUA": "SERVIÇOS",
    "VISITA TECNICA DIGITAL": "SERVIÇOS",
    "VISITA TECNICA - VOIP": "SERVIÇOS",
    "DESOBSTRUCAO - INSTALACAO PONTO ADICIONAL": "SERVIÇOS",
    "REINSTALACAO ENTREGA STREAMING": "SERVIÇOS",
    "REINSTALACAO - SERVICO CONEXAO ADICIONAL": "SERVIÇOS",
    "BASE ENTREGA ADC STREAMING": "SERVIÇOS",
    "INSTALAR CABEAMENTO MESH": "INSTALAÇÃO",
    "REINSTALACAO ENTREGA ADC STREAMING": "SERVIÇOS",
    "MUDANCA DE ENDERECO - ENTREGA ADC STREAMING": "SERVIÇOS",
    "VISITA TECNICA WIFI MESH": "SERVIÇOS",
    "TROCA DECODER PARA ATUALIZACAO DIGITAL": "SERVIÇOS",
    "INSTALACAO DE CABO GPON": "INSTALAÇÃO",
    "SUBS DE CONTROLE REMOTO VOZ TV": "SERVIÇOS",
    "INSTALACAO DE CABO HFC": "INSTALAÇÃO",
    "MUDANCA DE ENDERECO - RETIRAR PONTOS": "SERVIÇOS",
    "CONFIGURACAO STREAMING": "SERVIÇOS",
    "SUBSTITUICAO DE CONTROLE REMOTO DIGITAL": "SERVIÇOS",
    "ADESAO - INSTALAR SERVICO CONEXAO ADICIONAL DIGITA": "INSTALAÇÃO",
    "TROCA DECODER PARA ATUALIZACAO DIGITAL 4K": "SERVIÇOS",
    "VISITA TECNICA": "SERVIÇOS",
    "REFAZER MANUTENCAO PON": "SERVIÇOS",
    "ENTREGA DE CONTROLE REMOTO VOZ": "SERVIÇOS",
    "LIMPEZA DE RUIDO INDOOR": "SERVIÇOS",
    "MANUTENCAO RETORNO COP": "SERVIÇOS",
    "INSTALACAO CABO DE REDE STREAMING": "INSTALAÇÃO",
    "MANUTENCAO PREVENTIVA INDOOR": "SERVIÇOS",
    "INSTALACAO WIFI 360": "INSTALAÇÃO",
    "TROCA DE EQUIPAMENTO HD": "SERVIÇOS",
    "TROCA DE EQUIPAMENTO STREAMING": "SERVIÇOS",
    "ENTREGA EXPRESS CAMERA ADICIONAL": "SERVIÇOS",
    "DESOBSTRUCAO - REINSTALACAO DE ASSINATURA": "SERVIÇOS",
    "ADESAO - INSTALAR KIT MONITORAMENTO": "INSTALAÇÃO",
    "TROCA PARA ATUALIZACAO DECODER": "SERVIÇOS",
    "SUBS DE CONTROLE REMOTO VOZ": "SERVIÇOS",
    "MODERNIZACAO EXTENSOR WIFI MESH": "SERVIÇOS",
    "RETIRADA WIFI MESH": "SERVIÇOS",
    "BLINDAGEM TV ATUALIZACAO DIG": "SERVIÇOS",
    "MANUTENCAO REPARO NO DROP": "SERVIÇOS",
    "MODERNIZACAO EQUIPAMENTO DIGITAL": "SERVIÇOS",
    "SUBS CONTROLE REMOTO STREAMING": "SERVIÇOS",
    "APOIO CONSTRUCAO GPON MDU": "SERVIÇOS",
    "CONSTRUCAO MDU GPON": "SERVIÇOS",
    "MANUTENCAO CORRETIVA - DEGRADACAO MDU": "SERVIÇOS",
    "MANUTENCAO CORRETIVA - MDU": "SERVIÇOS",
    "MANUTENCAO PREVENTIVA INDOOR I": "SERVIÇOS",
    "VISITA TECNICA STREAMING": "SERVIÇOS",
    "VISTORIA DE CASOS ESPECIAIS IAT": "SERVIÇOS",
    "MANUTENCAO CORRETIVA - MDU GPON": "SERVIÇOS",
    "EXECUCAO MDU": "SERVIÇOS",
    "VISITA TECNICA - SMART HOME": "SERVIÇOS",
    "CONSTRUCAO MDU GPON ME": "SERVIÇOS",
    "MUDANCA DE ENDERECO - INSTALAR PONTO ADICIONAL VIR": "SERVIÇOS",
    "MODERNIZACAO BL": "SERVIÇOS",
    "ATENDIMENTO PRIORITARIO MANUTENCAO": "SERVIÇOS",
    "VISITA TECNICA NOW": "SERVIÇOS",
}

# --- BARRA LATERAL: ENTRADAS E CALENDÁRIO ---
st.sidebar.header("📁 Carregamento de Bases")
uploaded_aniel = st.sidebar.file_uploader("Ficheiro ANIEL (.xlsx ou .xlsm)", type=["xlsx", "xlsm", "csv"], key="aniel")
uploaded_toa = st.sidebar.file_uploader("Ficheiros TOA (Múltiplos)", type=["xlsx", "xlsm", "csv"], accept_multiple_files=True, key="toa")

st.sidebar.markdown("---")
st.sidebar.header("📅 Calendário de Projeção")
dias_uteis_mes = st.sidebar.number_input("Dias Úteis no Mês (Seg a Sáb)", min_value=20, max_value=31, value=27)
dias_trabalhados = st.sidebar.number_input("Dias Úteis Trabalhados até Hoje", min_value=1, max_value=dias_uteis_mes, value=16)

bases_padrao = ["NET-ABCDM", "NET-Guarulhos", "NET-LESTE"]
inputs_base = {}

dados_iniciais = {
    "NET-ABCDM": {"parados": 4, "montados": 68, "meta_os": 11800, "meta_cons": 552, "hoje_cons": 12, "ganho_os": 27, "media_os_mes": 366.5},
    "NET-Guarulhos": {"parados": 6, "montados": 76, "meta_os": 12200, "meta_cons": 608, "hoje_cons": 19, "ganho_os": 40, "media_os_mes": 397.2},
    "NET-LESTE": {"parados": 5, "montados": 80, "meta_os": 12200, "meta_cons": 656, "hoje_cons": 39, "ganho_os": 42, "media_os_mes": 379.5}
}

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Parâmetros por Base")
for base in bases_padrao:
    st.sidebar.subheader(f"Base: {base}")
    d_init = dados_iniciais.get(base, {"parados": 0, "montados": 0, "meta_os": 0, "meta_cons": 0, "hoje_cons": 0, "ganho_os": 0, "media_os_mes": 0.0})
    p = st.sidebar.number_input(f"Parados ({base})", value=d_init["parados"], key=f"par_{base}")
    m = st.sidebar.number_input(f"Montados ({base})", value=d_init["montados"], key=f"mon_{base}")
    meta_os = st.sidebar.number_input(f"Meta O.S. Mês ({base})", value=d_init["meta_os"], key=f"meta_os_{base}")
    
    med_input = st.sidebar.number_input(
        f"Média Diária Acumulada G3 ({base})",
        value=float(d_init["media_os_mes"]),
        step=0.1,
        key=f"med_{base}"
    )
    
    meta_cons = st.sidebar.number_input(f"Meta Consultivo ({base})", value=d_init["meta_cons"], key=f"meta_cons_{base}")
    hoje_cons = st.sidebar.number_input(f"Consultivo Hoje ({base})", value=d_init["hoje_cons"], key=f"hoje_cons_{base}")
    ganho_os = st.sidebar.number_input(f"Ganho O.S. ({base})", value=d_init["ganho_os"], key=f"ganho_{base}")
    
    inputs_base[base] = {
        "parados": p, "montados": m, "meta_os": meta_os,
        "media_os_mes": med_input, "meta_cons": meta_cons,
        "hoje_cons": hoje_cons, "ganho_os": ganho_os
    }

if uploaded_aniel is not None:
    try:
        with st.spinner("Processando indicadores executivos e gerando tabelas coloridas..."):
            df_aniel = ler_arquivo_seguro(uploaded_aniel)
            df_aniel.columns = [str(c).strip() for c in df_aniel.columns]

            # 1. Filtro Projeto VT
            col_proj = next((c for c in df_aniel.columns if c.lower() == "projeto"), "Projeto")
            if col_proj in df_aniel.columns:
                df_aniel = df_aniel[
                    ~df_aniel[col_proj].astype(str).str.upper().str.contains(r"\bVT\b|VT", regex=True, na=False)
                ].reset_index(drop=True)

            # 2. Leitura TOA
            df_toa = None
            if uploaded_toa:
                colunas_uteis_toa = [
                    "Data", "Contrato", "Status da Atividade", "Motivo de Fechamento Externo",
                    "Cidade", "Início", "Categorias da Capacidade", "Cód de Baixa 1",
                    "Tipo O.S 1", "Total de tarefas"
                ]
                toa_dfs = []
                for file in uploaded_toa:
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

            # Cruzamento TOA
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
                    else:
                        df_aniel.at[idx, "ST1"] = ""
                        df_aniel.at[idx, "ST2"] = ""
                        df_aniel.at[idx, "ST3"] = ""
                        df_aniel.at[idx, "PME"] = ""

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

            # REGRA: Excluir vazios e IVAN
            df_valido = df_aniel[
                (df_aniel["Supervisor"] != "") &
                (df_aniel["Tipo de Serviço"] != "") &
                (~df_aniel["Supervisor"].str.contains("IVAN", na=False))
            ].copy()

            servicos_nd = [
                "ADESAO ENTREGA STREAMING",
                "ADESAO - INSTALACAO DE ASSINATURA",
                "ADESAO - INSTALACAO DE ASSINATURA DIGITAL"
            ]

            def calcular_resumo_grupo(df_grp, montados, hoje_cons):
                tot_os = len(df_grp)
                os_aberta = len(df_grp[df_grp["Tipo de OS"] == "EM ABERTO"])
                produtivo = len(df_grp[df_grp["Tipo de OS"] == "PRODUTIVA"])
                
                quebra_geral = len(df_grp[df_grp["Tipo de OS"].isin(["IMPRODUTIVA", "CANCELADO"])])
                denom_geral = (quebra_geral + produtivo)
                pct_quebra_geral = (quebra_geral / denom_geral) if denom_geral > 0 else 0.0
                
                eficiencia = max(0.0, 1.0 - pct_quebra_geral)
                proj_exec_dia = produtivo + (os_aberta * eficiencia)
                
                pontos = df_grp[df_grp["Tipo de OS"] == "PRODUTIVA"]["Pontos Prev."].sum()
                media_os = (produtivo / montados) if montados > 0 else 0.0
                os_sem_consult = max(0, produtivo - hoje_cons)
                
                os_canc = len(df_grp[df_grp["CANCELADAS"] == "CANCELADO"])
                saiu_toa = len(df_grp[df_grp["Tipo de OS"] == "SAIU DO TOA"])

                def calc_quebra_pct(df_sub):
                    q = len(df_sub[df_sub["Tipo de OS"].isin(["IMPRODUTIVA", "CANCELADO"])])
                    p = len(df_sub[df_sub["Tipo de OS"] == "PRODUTIVA"])
                    den = q + p
                    return (q / den * 100) if den > 0 else 0.0

                df_ins = df_grp[df_grp["QUEBRAS"] == "INSTALAÇÃO"]
                quebra_ins = calc_quebra_pct(df_ins)

                df_serv = df_grp[df_grp["QUEBRAS"] == "SERVIÇOS"]
                quebra_serv = calc_quebra_pct(df_serv)

                df_nd = df_grp[df_grp["Tipo de Serviço"].isin(servicos_nd)]
                tot_nd = len(df_nd)
                quebra_nd_pct = calc_quebra_pct(df_nd)

                df_gpon = df_grp[df_grp["ATIVIDADES"] == "GPON"]
                tot_gpon = len(df_gpon)
                quebra_gpon = calc_quebra_pct(df_gpon)

                df_mig = df_grp[df_grp["ATIVIDADES"] == "MIGRAÇÃO"]
                tot_mig = len(df_mig)
                quebra_mig = calc_quebra_pct(df_mig)
                mig_canc = len(df_mig[df_mig["CANCELADAS"] == "CANCELADO"])

                df_ret = df_grp[df_grp["QUEBRAS"] == "RETORNO"]
                retorno_wo = len(df_ret)

                df_pme = df_grp[df_grp["PME"].astype(str).str.strip() != ""]
                tot_pme = len(df_pme)
                quebra_pme = calc_quebra_pct(df_pme)
                pme_canc = len(df_pme[df_pme["CANCELADAS"] == "CANCELADO"])

                return {
                    "TOTAL O.S.": tot_os,
                    "O.S. ABERTA": os_aberta,
                    "Pontos": int(round(pontos, 0)),
                    "Efic. (%)": round(eficiencia * 100, 1),
                    "Média O.S.": round(media_os, 1),
                    "O.S. Exec.": produtivo,
                    "Proj. Dia": round(proj_exec_dia, 1),
                    "O.S Sem Consult": os_sem_consult,
                    "Quebra INS (%)": round(quebra_ins, 1),
                    "Quebra SERV (%)": round(quebra_serv, 1),
                    "ND": tot_nd,
                    "Quebra ND (%)": round(quebra_nd_pct, 1),
                    "O.S. Canc.": os_canc,
                    "Saiu TOA": saiu_toa,
                    "Total GPON": tot_gpon,
                    "Quebra GPON": round(quebra_gpon, 1),
                    "Total MIG": tot_mig,
                    "Quebra MIG": round(quebra_mig, 1),
                    "Canc. MIG": mig_canc,
                    "Retorno WO": retorno_wo,
                    "Total PME": tot_pme,
                    "Quebra PME": round(quebra_pme, 1),
                    "Canc. PME": pme_canc,
                    # Dados brutos
                    "_raw_tot_os": tot_os,
                    "_raw_os_aberta": os_aberta,
                    "_raw_produtivo": produtivo,
                    "_raw_quebra_geral": quebra_geral,
                    "_raw_proj_dia": proj_exec_dia,
                    "_raw_pontos": pontos,
                    "_raw_tot_ins": len(df_ins),
                    "_raw_q_ins": len(df_ins[df_ins["Tipo de OS"].isin(["IMPRODUTIVA", "CANCELADO"])]),
                    "_raw_tot_serv": len(df_serv),
                    "_raw_q_serv": len(df_serv[df_serv["Tipo de OS"].isin(["IMPRODUTIVA", "CANCELADO"])]),
                    "_raw_tot_nd": tot_nd,
                    "_raw_q_nd": len(df_nd[df_nd["Tipo de OS"].isin(["IMPRODUTIVA", "CANCELADO"])]),
                    "_raw_tot_gpon": tot_gpon,
                    "_raw_q_gpon": len(df_gpon[df_gpon["Tipo de OS"].isin(["IMPRODUTIVA", "CANCELADO"])]),
                    "_raw_tot_mig": tot_mig,
                    "_raw_q_mig": len(df_mig[df_mig["Tipo de OS"].isin(["IMPRODUTIVA", "CANCELADO"])]),
                    "_raw_tot_pme": tot_pme,
                    "_raw_q_pme": len(df_pme[df_pme["Tipo de OS"].isin(["IMPRODUTIVA", "CANCELADO"])]),
                }

            linhas_gerenciais = []
            for base in bases_padrao:
                df_b = df_valido[df_valido["Projeto"].str.upper() == base.upper()]
                inp = inputs_base[base]
                res_base = calcular_resumo_grupo(df_b, inp["montados"], inp["hoje_cons"])
                
                # Projeção = G3 * 27 (sem a coluna Media G3 exibida)
                media_g3 = inp["media_os_mes"] if inp["media_os_mes"] > 0 else res_base["_raw_proj_dia"]
                proj_os_mes = int(round(media_g3 * dias_uteis_mes))
                proj_cons = int(round((inp["hoje_cons"] / dias_trabalhados) * dias_uteis_mes)) if dias_trabalhados > 0 else 0

                linhas_gerenciais.append({
                    "Base": base,
                    "Supervisor": "CONSOLIDADO",
                    "Parados": inp["parados"],
                    "Montados": inp["montados"],
                    "Meta O.S.": inp["meta_os"],
                    "Proj. O.S.": proj_os_mes,
                    "Meta Consult": inp["meta_cons"],
                    "Proj. Consult": proj_cons,
                    "Hoje Consult": inp["hoje_cons"],
                    "Ganho O.S.": inp["ganho_os"],
                    **res_base
                })

                supervisores = sorted([s for s in df_b["Supervisor"].unique() if s != ""])
                for sup in supervisores:
                    df_s = df_b[df_b["Supervisor"] == sup]
                    m_sup = round(inp["montados"] / len(supervisores)) if len(supervisores) > 0 else 1
                    res_sup = calcular_resumo_grupo(df_s, m_sup, 0)
                    proj_sup_mes = int(round(res_sup["_raw_proj_dia"] * dias_uteis_mes))
                    
                    linhas_gerenciais.append({
                        "Base": base,
                        "Supervisor": sup,
                        "Parados": 0,
                        "Montados": m_sup,
                        "Meta O.S.": 0,
                        "Proj. O.S.": proj_sup_mes,
                        "Meta Consult": 0,
                        "Proj. Consult": 0,
                        "Hoje Consult": 0,
                        "Ganho O.S.": 0,
                        **res_sup
                    })

            # --- LINHA CONSOLIDADA GERAL: TOTAL INSTALAÇÃO ---
            tot_parados_global = sum(inputs_base[b]["parados"] for b in bases_padrao)
            tot_montados_global = sum(inputs_base[b]["montados"] for b in bases_padrao)
            tot_meta_os_global = sum(inputs_base[b]["meta_os"] for b in bases_padrao)
            tot_proj_os_global = sum(i["Proj. O.S."] for i in linhas_gerenciais if i["Supervisor"] == "CONSOLIDADO")
            tot_meta_cons_global = sum(inputs_base[b]["meta_cons"] for b in bases_padrao)
            tot_proj_cons_global = sum(i["Proj. Consult"] for i in linhas_gerenciais if i["Supervisor"] == "CONSOLIDADO")
            tot_hoje_cons_global = sum(inputs_base[b]["hoje_cons"] for b in bases_padrao)
            tot_ganho_os_global = sum(inputs_base[b]["ganho_os"] for b in bases_padrao)

            tot_os_global = sum(i["_raw_tot_os"] for i in linhas_gerenciais if i["Supervisor"] == "CONSOLIDADO")
            tot_aberta_global = sum(i["_raw_os_aberta"] for i in linhas_gerenciais if i["Supervisor"] == "CONSOLIDADO")
            tot_prod_global = sum(i["_raw_produtivo"] for i in linhas_gerenciais if i["Supervisor"] == "CONSOLIDADO")
            tot_quebra_global = sum(i["_raw_quebra_geral"] for i in linhas_gerenciais if i["Supervisor"] == "CONSOLIDADO")
            tot_pontos_global = sum(i["_raw_pontos"] for i in linhas_gerenciais if i["Supervisor"] == "CONSOLIDADO")
            tot_proj_dia_global = sum(i["_raw_proj_dia"] for i in linhas_gerenciais if i["Supervisor"] == "CONSOLIDADO")
            tot_sem_consult_global = sum(i["O.S Sem Consult"] for i in linhas_gerenciais if i["Supervisor"] == "CONSOLIDADO")
            tot_canc_global = sum(i["O.S. Canc."] for i in linhas_gerenciais if i["Supervisor"] == "CONSOLIDADO")
            tot_saiu_toa_global = sum(i["Saiu TOA"] for i in linhas_gerenciais if i["Supervisor"] == "CONSOLIDADO")

            # Totais tecnológicos
            tot_nd_global = sum(i["ND"] for i in linhas_gerenciais if i["Supervisor"] == "CONSOLIDADO")
            tot_gpon_global = sum(i["Total GPON"] for i in linhas_gerenciais if i["Supervisor"] == "CONSOLIDADO")
            tot_mig_global = sum(i["Total MIG"] for i in linhas_gerenciais if i["Supervisor"] == "CONSOLIDADO")
            tot_mig_canc_global = sum(i["Canc. MIG"] for i in linhas_gerenciais if i["Supervisor"] == "CONSOLIDADO")
            tot_retorno_wo_global = sum(i["Retorno WO"] for i in linhas_gerenciais if i["Supervisor"] == "CONSOLIDADO")
            tot_pme_global = sum(i["Total PME"] for i in linhas_gerenciais if i["Supervisor"] == "CONSOLIDADO")
            tot_pme_canc_global = sum(i["Canc. PME"] for i in linhas_gerenciais if i["Supervisor"] == "CONSOLIDADO")

            # Percentuais Globais recalculados por fórmula
            den_geral_global = tot_quebra_global + tot_prod_global
            pct_quebra_global = (tot_quebra_global / den_geral_global) if den_geral_global > 0 else 0.0
            efic_global = max(0.0, 1.0 - pct_quebra_global) * 100
            media_os_global = (tot_prod_global / tot_montados_global) if tot_montados_global > 0 else 0.0

            raw_ins_tot = sum(i["_raw_tot_ins"] for i in linhas_gerenciais if i["Supervisor"] == "CONSOLIDADO")
            raw_ins_q = sum(i["_raw_q_ins"] for i in linhas_gerenciais if i["Supervisor"] == "CONSOLIDADO")
            quebra_ins_global = (raw_ins_q / raw_ins_tot * 100) if raw_ins_tot > 0 else 0.0

            raw_serv_tot = sum(i["_raw_tot_serv"] for i in linhas_gerenciais if i["Supervisor"] == "CONSOLIDADO")
            raw_serv_q = sum(i["_raw_q_serv"] for i in linhas_gerenciais if i["Supervisor"] == "CONSOLIDADO")
            quebra_serv_global = (raw_serv_q / raw_serv_tot * 100) if raw_serv_tot > 0 else 0.0

            raw_nd_q = sum(i["_raw_q_nd"] for i in linhas_gerenciais if i["Supervisor"] == "CONSOLIDADO")
            quebra_nd_global = (raw_nd_q / tot_nd_global * 100) if tot_nd_global > 0 else 0.0

            raw_gpon_q = sum(i["_raw_q_gpon"] for i in linhas_gerenciais if i["Supervisor"] == "CONSOLIDADO")
            quebra_gpon_global = (raw_gpon_q / tot_gpon_global * 100) if tot_gpon_global > 0 else 0.0

            raw_mig_q = sum(i["_raw_q_mig"] for i in linhas_gerenciais if i["Supervisor"] == "CONSOLIDADO")
            quebra_mig_global = (raw_mig_q / tot_mig_global * 100) if tot_mig_global > 0 else 0.0

            raw_pme_q = sum(i["_raw_q_pme"] for i in linhas_gerenciais if i["Supervisor"] == "CONSOLIDADO")
            quebra_pme_global = (raw_pme_q / tot_pme_global * 100) if tot_pme_global > 0 else 0.0

            linha_total_instalacao = {
                "Base": "TOTAL INSTALAÇÃO",
                "Supervisor": "TOTAL GERAL",
                "Parados": tot_parados_global,
                "Montados": tot_montados_global,
                "Meta O.S.": tot_meta_os_global,
                "Proj. O.S.": tot_proj_os_global,
                "Meta Consult": tot_meta_cons_global,
                "Proj. Consult": tot_proj_cons_global,
                "Hoje Consult": tot_hoje_cons_global,
                "Ganho O.S.": tot_ganho_os_global,
                "TOTAL O.S.": tot_os_global,
                "O.S. ABERTA": tot_aberta_global,
                "Pontos": int(round(tot_pontos_global, 0)),
                "Efic. (%)": round(efic_global, 1),
                "Média O.S.": round(media_os_global, 1),
                "O.S. Exec.": tot_prod_global,
                "Proj. Dia": round(tot_proj_dia_global, 1),
                "O.S Sem Consult": tot_sem_consult_global,
                "Quebra INS (%)": round(quebra_ins_global, 1),
                "Quebra SERV (%)": round(quebra_serv_global, 1),
                "ND": tot_nd_global,
                "Quebra ND (%)": round(quebra_nd_global, 1),
                "O.S. Canc.": tot_canc_global,
                "Saiu TOA": tot_saiu_toa_global,
                "Total GPON": tot_gpon_global,
                "Quebra GPON": round(quebra_gpon_global, 1),
                "Total MIG": tot_mig_global,
                "Quebra MIG": round(quebra_mig_global, 1),
                "Canc. MIG": tot_mig_canc_global,
                "Retorno WO": tot_retorno_wo_global,
                "Total PME": tot_pme_global,
                "Quebra PME": round(quebra_pme_global, 1),
                "Canc. PME": tot_pme_canc_global
            }

            df_painel_todos = pd.DataFrame(linhas_gerenciais)

            # --- CARDS DE DESTAQUE EXECUTIVO ---
            st.markdown("### 📌 Visão Consolidada Geral (Total Instalação)")
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            c1.metric("Total O.S.", f"{tot_os_global:,}".replace(",", "."))
            c2.metric("O.S. Executadas", f"{tot_prod_global:,}".replace(",", "."))
            c3.metric(f"Projeção Mês ({dias_uteis_mes} d.u.)", f"{tot_proj_os_global:,}".replace(",", "."))
            c4.metric("Efic. Global", f"{efic_global:.1f}%")
            c5.metric("Média O.S. / Téc", f"{media_os_global:.1f}")
            c6.metric("Técnicos Montados", tot_montados_global)

            st.markdown("---")

            # --- TABELA 1: RESUMO POR BASE (COM TOTAL NO FINAL) ---
            st.markdown("### 🏢 Resumo Consolidado por Base Operacional")
            cols_base = [
                "Base", "Parados", "Montados", "Meta O.S.", "Proj. O.S.", "Meta Consult", "Proj. Consult", "Hoje Consult",
                "TOTAL O.S.", "O.S. ABERTA", "Pontos", "Efic. (%)", "Média O.S.", "O.S. Exec.", "Proj. Dia", "O.S Sem Consult",
                "Quebra INS (%)", "Quebra SERV (%)", "Quebra ND (%)", "O.S. Canc.", "Saiu TOA", "Ganho O.S.",
                "Total GPON", "Quebra GPON", "Total MIG", "Quebra MIG", "Total PME", "Quebra PME"
            ]

            df_base_display = df_painel_todos[df_painel_todos["Supervisor"] == "CONSOLIDADO"][cols_base].copy()
            # Adiciona a linha de TOTAL INSTALAÇÃO no final
            df_base_display.loc[len(df_base_display)] = [linha_total_instalacao[c] for c in cols_base]

            # Função de Estilização Profissional com Cores e Destaques
            def colorir_tabela_executiva(df):
                styles = pd.DataFrame("", index=df.index, columns=df.columns)
                for idx, row in df.iterrows():
                    is_total = (row["Base"] == "TOTAL INSTALAÇÃO")
                    for col in df.columns:
                        css = []
                        if is_total:
                            css.append("background-color: #263238; color: #ffffff; font-weight: bold; border-top: 2px solid #000000;")
                        else:
                            # Cores por blocos temáticos
                            if col in ["Montados", "O.S. Exec.", "Proj. Dia", "Proj. O.S."]:
                                css.append("background-color: #e8f5e9; font-weight: 500;") # Verde suave (produtivo)
                            elif col in ["Efic. (%)"]:
                                css.append("background-color: #c8e6c9; font-weight: bold;") # Verde destaque
                            elif "Quebra" in col or col in ["O.S. Canc.", "Saiu TOA"]:
                                css.append("background-color: #fff3e0;") # Laranja suave (quebras)
                            elif col in ["Total GPON", "Total MIG", "Total PME"]:
                                css.append("background-color: #e1f5fe;") # Azul suave (tecnologias)
                        styles.at[idx, col] = "; ".join(css)
                return styles

            # Formatações elegantes de percentual e inteiros
            format_dict = {
                "Parados": "{:,.0f}",
                "Montados": "{:,.0f}",
                "Meta O.S.": "{:,.0f}",
                "Proj. O.S.": "{:,.0f}",
                "Meta Consult": "{:,.0f}",
                "Proj. Consult": "{:,.0f}",
                "Hoje Consult": "{:,.0f}",
                "TOTAL O.S.": "{:,.0f}",
                "O.S. ABERTA": "{:,.0f}",
                "Pontos": "{:,.0f}",
                "Efic. (%)": "{:.1f}%",
                "Média O.S.": "{:.1f}",
                "O.S. Exec.": "{:,.0f}",
                "Proj. Dia": "{:.1f}",
                "O.S Sem Consult": "{:,.0f}",
                "Quebra INS (%)": "{:.1f}%",
                "Quebra SERV (%)": "{:.1f}%",
                "Quebra ND (%)": "{:.1f}%",
                "O.S. Canc.": "{:,.0f}",
                "Saiu TOA": "{:,.0f}",
                "Ganho O.S.": "{:,.0f}",
                "Total GPON": "{:,.0f}",
                "Quebra GPON": "{:.1f}%",
                "Total MIG": "{:,.0f}",
                "Quebra MIG": "{:.1f}%",
                "Total PME": "{:,.0f}",
                "Quebra PME": "{:.1f}%"
            }

            st.dataframe(
                df_base_display.style.apply(colorir_tabela_executiva, axis=None).format(format_dict, na_rep=""),
                use_container_width=True
            )

            # --- TABELA 2: DETALHAMENTO POR SUPERVISOR ---
            st.markdown("---")
            st.markdown("### 👥 Detalhamento Completo por Base e Supervisor")
            base_selecionada = st.selectbox("Filtrar Exibição de Supervisores:", ["TODAS"] + bases_padrao)

            cols_sup = [
                "Base", "Supervisor", "Montados", "TOTAL O.S.", "O.S. ABERTA", "Pontos", "Efic. (%)",
                "Média O.S.", "O.S. Exec.", "Proj. Dia", "Proj. O.S.", "Quebra INS (%)", "Quebra SERV (%)", "Quebra ND (%)",
                "O.S. Canc.", "Saiu TOA", "Total GPON", "Total MIG", "Total PME", "Quebra PME"
            ]

            if base_selecionada == "TODAS":
                df_sup_display = df_painel_todos[cols_sup].copy()
            else:
                df_sup_display = df_painel_todos[df_painel_todos["Base"] == base_selecionada][cols_sup].copy()

            # Adiciona a linha de total ao final da visualização de supervisores
            df_sup_display.loc[len(df_sup_display)] = [linha_total_instalacao[c] for c in cols_sup]

            st.dataframe(
                df_sup_display.style.apply(colorir_tabela_executiva, axis=None).format(format_dict, na_rep=""),
                use_container_width=True
            )

            # --- EXPORTAÇÃO EXCEL COMPLETA ---
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                # Aba 1: Resumo Formatado da Apresentação
                df_base_display.to_excel(writer, sheet_name="RESUMO_DIRETORIA", index=False)
                # Aba 2: Detalhamento por Supervisor
                df_sup_display.to_excel(writer, sheet_name="DETALHE_SUPERVISORES", index=False)
                # Aba 3: Base ANIEL Tratada
                df_aniel.to_excel(writer, sheet_name="BASE_TRATADA", index=False)

            st.download_button(
                label="📥 Baixar Apresentação e Planilha Formatada (.xlsx)",
                data=output.getvalue(),
                file_name="Apresentacao_Resultados_Diretoria.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.error(f"Ocorreu um erro ao processar os indicadores gerenciais: {e}")
