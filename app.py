import io
import re
import pandas as pd
import numpy as np
import streamlit as st

st.set_page_config(
    page_title="Painel Executivo - Prévia Diária",
    page_icon="📊",
    layout="wide"
)

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
    /* Cores dos cabeçalhos idênticas à imagem */
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
    
    /* Linhas de Base e Total */
    .tr-base { background-color: #eafaf1; font-weight: bold; color: #145a32; }
    .tr-sup { background-color: #ffffff; color: #2c3e50; }
    .tr-total { background-color: #d4efdf; font-weight: 900; color: #145a32; border-top: 2px solid #27ae60; }
    .red-text { color: #c0392b; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# Inicialização de variáveis globais de estado
if "pagina" not in st.session_state:
    st.session_state.pagina = "1. Upload de Arquivos"
if "df_valido" not in st.session_state:
    st.session_state.df_valido = None
if "df_aniel_full" not in st.session_state:
    st.session_state.df_aniel_full = None
if "supervisores_por_base" not in st.session_state:
    st.session_state.supervisores_por_base = {}

# Menu lateral de navegação
st.sidebar.title("Navegação")
etapas = ["1. Upload de Arquivos", "2. Dados Manuais por Base", "3. Visualização da Prévia"]
st.session_state.pagina = st.sidebar.radio("Ir para:", etapas, index=etapas.index(st.session_state.pagina))

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

bases_padrao = ["NET-ABCDM", "NET-Guarulhos", "NET-LESTE"]

# ==============================================================================
# PÁGINA 1: UPLOAD DE ARQUIVOS
# ==============================================================================
if st.session_state.pagina == "1. Upload de Arquivos":
    st.subheader("📁 Passo 1: Upload e Cruzamento das Bases")
    st.write("Faça o upload do arquivo do ANIEL e dos arquivos do TOA para iniciar o processamento.")
    
    col_u1, col_u2 = st.columns(2)
    with col_u1:
        up_aniel = st.file_uploader("Arquivo ANIEL (.xlsx ou .xlsm)", type=["xlsx", "xlsm", "csv"], key="u_aniel")
    with col_u2:
        up_toa = st.file_uploader("Arquivos do TOA (Pode selecionar os três)", type=["xlsx", "xlsm", "csv"], accept_multiple_files=True, key="u_toa")
        
    if up_aniel is not None:
        if st.button("🚀 Processar Arquivos e Cruzar Bases", type="primary"):
            with st.spinner("Lendo arquivos, cruzando bases e tratando regras operacionais..."):
                try:
                    df_aniel = ler_arquivo_seguro(up_aniel)
                    df_aniel.columns = [str(c).strip() for c in df_aniel.columns]

                    # Filtro Projeto VT
                    col_proj = next((c for c in df_aniel.columns if c.lower() == "projeto"), "Projeto")
                    if col_proj in df_aniel.columns:
                        df_aniel = df_aniel[
                            ~df_aniel[col_proj].astype(str).str.upper().str.contains(r"\bVT\b|VT", regex=True, na=False)
                        ].reset_index(drop=True)

                    # Leitura TOA
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

                    # Conversão Pontos Prev.
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

                    # Exclui vazios e IVAN
                    df_valido = df_aniel[
                        (df_aniel["Supervisor"] != "") &
                        (df_aniel["Tipo de Serviço"] != "") &
                        (~df_aniel["Supervisor"].str.contains("IVAN", na=False))
                    ].copy()

                    # Guarda em sessão
                    st.session_state.df_valido = df_valido
                    st.session_state.df_aniel_full = df_aniel

                    # Mapeia supervisores reais de cada base
                    sup_map = {}
                    for b in bases_padrao:
                        sups = sorted(df_valido[df_valido["Projeto"].str.upper() == b.upper()]["Supervisor"].unique().tolist())
                        sup_map[b] = sups
                    st.session_state.supervisores_por_base = sup_map

                    st.success("✅ Arquivos processados com sucesso! Os dados foram tratados e cruzados.")
                    st.info("👉 Por favor, avance para a aba '2. Dados Manuais por Base' no menu à esquerda ou clique no botão abaixo:")
                    if st.button("Ir para Dados Manuais ➡️"):
                        st.session_state.pagina = "2. Dados Manuais por Base"
                        st.rerun()

                except Exception as e:
                    st.error(f"Erro ao processar arquivos: {e}")

# ==============================================================================
# PÁGINA 2: ENTRADA DE DADOS MANUAIS
# ==============================================================================
elif st.session_state.pagina == "2. Dados Manuais por Base":
    st.subheader("⚙️ Passo 2: Preenchimento de Dados Manuais por Base")
    st.write("Insira os dados de Parados, Montados, Metas e Consultivo para cada regional.")

    if st.session_state.df_valido is None:
        st.warning("⚠️ Nenhum arquivo foi processado ainda. Volte para a página '1. Upload de Arquivos' e carregue as bases primeiro.")
    else:
        # Configuração de calendário
        c_cal1, c_cal2 = st.columns(2)
        with c_cal1:
            dias_uteis = st.number_input("Dias Úteis do Mês (Seg a Sáb)", value=27, min_value=20, max_value=31, key="cfg_dias_uteis")
        with c_cal2:
            dias_trab = st.number_input("Dias Úteis Trabalhados até Hoje", value=16, min_value=1, max_value=dias_uteis, key="cfg_dias_trab")

        st.markdown("---")
        
        # Valores iniciais padrão
        defaults = {
            "NET-ABCDM": {"parados": 4, "montados": 68, "meta_os": 11800, "meta_cons": 552, "hoje_cons": 12, "ganho_os": 27, "media_g3": 366.5,
                          "sup_parados": {"EDSON MARCO PINHEIRO": 3, "MAICON APARECIDO FARIA": 1, "NELSON ALVES OLIVEIRA JUNIOR": 0},
                          "sup_montados": {"EDSON MARCO PINHEIRO": 23, "MAICON APARECIDO FARIA": 22, "NELSON ALVES OLIVEIRA JUNIOR": 23}},
            "NET-Guarulhos": {"parados": 6, "montados": 76, "meta_os": 12200, "meta_cons": 608, "hoje_cons": 19, "ganho_os": 40, "media_g3": 397.2,
                              "sup_parados": {"ADRIANO NASCIMENTO DA SILVA": 0, "DANIELE BARBOSA DE OLIVEIRA": 3, "FERNANDO CESAR COELHO RAMOS": 2, "PALOMA REGINA SILVA BATISTA": 1},
                              "sup_montados": {"ADRIANO NASCIMENTO DA SILVA": 20, "DANIELE BARBOSA DE OLIVEIRA": 20, "FERNANDO CESAR COELHO RAMOS": 19, "PALOMA REGINA SILVA BATISTA": 19}},
            "NET-LESTE": {"parados": 5, "montados": 80, "meta_os": 12200, "meta_cons": 656, "hoje_cons": 39, "ganho_os": 42, "media_g3": 379.5,
                          "sup_parados": {"ALAN DE ANDRADE DIAS": 2, "ELISANGELA CASSIMIRO GONCALVES": 0, "FRANCISCO GERALDO CARVALHO JUNIOR": 0, "JOAO CARLOS FERREIRA MIRON": 3},
                          "sup_montados": {"ALAN DE ANDRADE DIAS": 26, "ELISANGELA CASSIMIRO GONCALVES": 11, "FRANCISCO GERALDO CARVALHO JUNIOR": 26, "JOAO CARLOS FERREIRA MIRON": 17}}
        }

        # Cria abas para cada base
        tabs = st.tabs(["NET-ABCDM", "NET-Guarulhos", "NET-LESTE"])
        
        for i, b in enumerate(bases_padrao):
            with tabs[i]:
                d = defaults.get(b, {})
                st.markdown(f"#### 🏢 Indicadores da Base: {b}")
                
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    p_val = st.number_input(f"Total Parados ({b})", value=d.get("parados", 0), key=f"inp_par_{b}")
                    m_val = st.number_input(f"Total Montados ({b})", value=d.get("montados", 0), key=f"inp_mon_{b}")
                with c2:
                    meta_os = st.number_input(f"Meta O.S. Mês ({b})", value=d.get("meta_os", 0), key=f"inp_meta_os_{b}")
                    med_g3 = st.number_input(f"Média O.S. (G3) ({b})", value=float(d.get("media_g3", 0.0)), step=0.1, key=f"inp_g3_{b}")
                with c3:
                    meta_c = st.number_input(f"Meta Consultivo ({b})", value=d.get("meta_cons", 0), key=f"inp_meta_c_{b}")
                    hoje_c = st.number_input(f"Hoje Consultivo ({b})", value=d.get("hoje_cons", 0), key=f"inp_hoje_c_{b}")
                with c4:
                    ganho = st.number_input(f"Ganho O.S. ({b})", value=d.get("ganho_os", 0), key=f"inp_ganho_{b}")
                
                # Detalhamento por Supervisor (Parados e Montados)
                st.markdown("##### 👥 Equipe de Supervisores da Base:")
                sups_base = st.session_state.supervisores_por_base.get(b, [])
                
                col_s1, col_s2 = st.columns(2)
                for sup in sups_base:
                    def_p = d.get("sup_parados", {}).get(sup, 0)
                    def_m = d.get("sup_montados", {}).get(sup, 20)
                    with col_s1:
                        st.number_input(f"Parados: {sup}", value=def_p, key=f"p_{b}_{sup}")
                    with col_s2:
                        st.number_input(f"Montados: {sup}", value=def_m, key=f"m_{b}_{sup}")

        st.markdown("---")
        if st.button("💾 Gravar Dados e Ver Prévia da Diretoria", type="primary"):
            st.session_state.pagina = "3. Visualização da Prévia"
            st.rerun()

# ==============================================================================
# PÁGINA 3: VISUALIZAÇÃO DA PRÉVIA (DIRETORIA)
# ==============================================================================
elif st.session_state.pagina == "3. Visualização da Prévia":
    st.subheader("📊 Passo 3: Apresentação da Prévia Diária - Diretoria")

    if st.session_state.df_valido is None:
        st.warning("⚠️ Nenhum dado disponível. Complete o Passo 1 (Upload) e o Passo 2 (Dados Manuais).")
    else:
        df_valido = st.session_state.df_valido
        dias_uteis = st.session_state.get("cfg_dias_uteis", 27)
        dias_trab = st.session_state.get("cfg_dias_trab", 16)

        servicos_nd = [
            "ADESAO ENTREGA STREAMING",
            "ADESAO - INSTALACAO DE ASSINATURA",
            "ADESAO - INSTALACAO DE ASSINATURA DIGITAL"
        ]

        def calcular_metricas(df_sub, montados, hoje_c):
            tot_os = len(df_sub)
            os_aberta = len(df_sub[df_sub["Tipo de OS"] == "EM ABERTO"])
            produtivo = len(df_sub[df_sub["Tipo de OS"] == "PRODUTIVA"])
            quebra_geral = len(df_sub[df_sub["Tipo de OS"].isin(["IMPRODUTIVA", "CANCELADO"])])
            
            # Fórmulas
            den_geral = quebra_geral + produtivo
            pct_quebra_geral = (quebra_geral / den_geral) if den_geral > 0 else 0.0
            efic = max(0.0, 1.0 - pct_quebra_geral)
            proj_dia = produtivo + (os_aberta * efic)
            pontos = df_sub[df_sub["Tipo de OS"] == "PRODUTIVA"]["Pontos Prev."].sum()
            media_os = (produtivo / montados) if montados > 0 else 0.0
            os_sem_c = max(0, produtivo - hoje_c)
            os_canc = len(df_sub[df_sub["CANCELADAS"] == "CANCELADO"])
            saiu_toa = len(df_sub[df_sub["Tipo de OS"] == "SAIU DO TOA"])

            def calc_q(df_item):
                q = len(df_item[df_item["Tipo de OS"].isin(["IMPRODUTIVA", "CANCELADO"])])
                p = len(df_item[df_item["Tipo de OS"] == "PRODUTIVA"])
                d = q + p
                return (q / d * 100) if d > 0 else 0.0

            # Quebras específicas
            df_ins = df_sub[df_sub["QUEBRAS"] == "INSTALAÇÃO"]
            q_ins = calc_q(df_ins)

            df_serv = df_sub[df_sub["QUEBRAS"] == "SERVIÇOS"]
            q_serv = calc_q(df_serv)

            df_nd = df_sub[df_sub["Tipo de Serviço"].isin(servicos_nd)]
            tot_nd = len(df_nd)
            q_nd = calc_q(df_nd)

            df_gpon = df_sub[df_sub["ATIVIDADES"] == "GPON"]
            tot_gpon = len(df_gpon)
            q_gpon = calc_q(df_gpon)

            df_mig = df_sub[df_sub["ATIVIDADES"] == "MIGRAÇÃO"]
            tot_mig = len(df_mig)
            q_mig = calc_q(df_mig)
            canc_mig = len(df_mig[df_mig["CANCELADAS"] == "CANCELADO"])

            df_ret = df_sub[df_sub["QUEBRAS"] == "RETORNO"]
            retorno_wo = len(df_ret)

            df_pme = df_sub[df_sub["PME"].astype(str).str.strip() != ""]
            tot_pme = len(df_pme)
            q_pme = calc_q(df_pme)
            canc_pme = len(df_pme[df_pme["CANCELADAS"] == "CANCELADO"])

            return {
                "tot_os": tot_os, "os_aberta": os_aberta, "produtivo": produtivo,
                "quebra_geral": quebra_geral, "pontos": int(round(pontos, 0)),
                "efic": efic * 100, "media_os": media_os, "proj_dia": proj_dia,
                "os_sem_c": os_sem_c, "q_ins": q_ins, "q_serv": q_serv,
                "tot_nd": tot_nd, "q_nd": q_nd, "os_canc": os_canc, "saiu_toa": saiu_toa,
                "tot_gpon": tot_gpon, "q_gpon": q_gpon, "tot_mig": tot_mig,
                "q_mig": q_mig, "canc_mig": canc_mig, "retorno_wo": retorno_wo,
                "tot_pme": tot_pme, "q_pme": q_pme, "canc_pme": canc_pme,
                "_raw_q_ins": len(df_ins[df_ins["Tipo de OS"].isin(["IMPRODUTIVA", "CANCELADO"])]),
                "_raw_tot_ins": len(df_ins),
                "_raw_q_serv": len(df_serv[df_serv["Tipo de OS"].isin(["IMPRODUTIVA", "CANCELADO"])]),
                "_raw_tot_serv": len(df_serv),
                "_raw_q_nd": len(df_nd[df_nd["Tipo de OS"].isin(["IMPRODUTIVA", "CANCELADO"])]),
                "_raw_q_gpon": len(df_gpon[df_gpon["Tipo de OS"].isin(["IMPRODUTIVA", "CANCELADO"])]),
                "_raw_q_mig": len(df_mig[df_mig["Tipo de OS"].isin(["IMPRODUTIVA", "CANCELADO"])]),
                "_raw_q_pme": len(df_pme[df_pme["Tipo de OS"].isin(["IMPRODUTIVA", "CANCELADO"])])
            }

            # Montagem estruturada das linhas para apresentação
        tabela_html = []
        
        # Cabeçalho idêntico à planilha
        tabela_html.append(f"""
        <table class="custom-table">
            <thead>
                <tr>
                    <th rowspan="2" class="th-data">19/10/2026</th>
                    <th rowspan="2" class="th-data">Parados</th>
                    <th rowspan="2" class="th-data">Montados</th>
                    <th colspan="2" class="th-qtd-os">QTDE. DE O.S. OUTUBRO</th>
                    <th colspan="4" class="th-consult">CONSULTIVO OUTUBRO</th>
                    <th colspan="8" class="th-prod">PRODUTIVIDADE (Projeção)</th>
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
                    <th class="th-prod">Média O.S.</th>
                    <th class="th-prod">O.S. Exec.</th>
                    <th class="th-prod">O.S Sem Consult</th>
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
        """)

        # Totais globais para linha TOTAL INSTALAÇÃO
        g_parados = 0; g_montados = 0; g_meta_os = 0; g_proj_os = 0
        g_meta_cons = 0; g_proj_cons = 0; g_hoje_cons = 0; g_os_cons = 0
        g_tot_os = 0; g_aberta = 0; g_pontos = 0; g_prod = 0; g_quebra = 0
        g_sem_cons = 0; g_nd = 0; g_canc = 0; g_saiu_toa = 0; g_ganho = 0
        g_gpon = 0; g_mig = 0; g_mig_canc = 0; g_retorno = 0; g_pme = 0; g_pme_canc = 0
        g_raw_ins_q = 0; g_raw_ins_tot = 0; g_raw_serv_q = 0; g_raw_serv_tot = 0
        g_raw_nd_q = 0; g_raw_gpon_q = 0; g_raw_mig_q = 0; g_raw_pme_q = 0

        for b in bases_padrao:
            df_b = df_valido[df_valido["Projeto"].str.upper() == b.upper()]
            sups_b = st.session_state.supervisores_por_base.get(b, [])

            p_base = st.session_state.get(f"inp_par_{b}", 0)
            m_base = st.session_state.get(f"inp_mon_{b}", 0)
            meta_os_b = st.session_state.get(f"inp_meta_os_{b}", 0)
            g3_b = st.session_state.get(f"inp_g3_{b}", 0.0)
            meta_c_b = st.session_state.get(f"inp_meta_c_{b}", 0)
            hoje_c_b = st.session_state.get(f"inp_hoje_c_{b}", 0)
            ganho_b = st.session_state.get(f"inp_ganho_{b}", 0)

            res_b = calcular_metricas(df_b, m_base, hoje_c_b)
            
            # Projeção O.S. = G3 * 27
            proj_os_b = int(round(g3_b * dias_uteis)) if g3_b > 0 else int(round(res_b["proj_dia"] * dias_uteis))
            proj_c_b = int(round((hoje_c_b / dias_trab) * dias_uteis)) if dias_trab > 0 else 0
            os_consult_b = hoje_c_b * 2  # valor de OS consultivo

            # Acumula totais
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

            # Linha consolidada da Base
            num_linhas_span = len(sups_b) + 1
            tabela_html.append(f"""
            <tr class="tr-base">
                <td style="text-align: left; padding-left: 8px;">{b}</td>
                <td>{p_base}</td>
                <td>{m_base}</td>
                <td rowspan="{num_linhas_span}">{meta_os_b:,.0f}</td>
                <td rowspan="{num_linhas_span}" class="red-text">{proj_os_b:,.0f}</td>
                <td rowspan="{num_linhas_span}">{meta_c_b}</td>
                <td rowspan="{num_linhas_span}" class="red-text">{proj_c_b}</td>
                <td rowspan="{num_linhas_span}">{hoje_c_b}</td>
                <td rowspan="{num_linhas_span}">{os_consult_b}</td>
                <td>{res_b['tot_os']}</td>
                <td>{res_b['os_aberta']}</td>
                <td>{res_b['pontos']}</td>
                <td>{res_b['efic']:.1f}%</td>
                <td>{res_b['media_os']:.1f}</td>
                <td>{res_b['produtivo']}</td>
                <td rowspan="{num_linhas_span}">{res_b['os_sem_c']}</td>
                <td>{res_b['q_ins']:.1f}%</td>
                <td>{res_b['q_serv']:.1f}%</td>
                <td>{res_b['q_nd']:.1f}%</td>
                <td rowspan="{num_linhas_span}">{res_b['tot_nd']}</td>
                <td>{res_b['os_canc']}</td>
                <td>{res_b['saiu_toa']}</td>
                <td rowspan="{num_linhas_span}">{ganho_b}</td>
                <td rowspan="{num_linhas_span}">{res_b['tot_gpon']}</td>
                <td rowspan="{num_linhas_span}">{res_b['q_gpon']:.1f}%</td>
                <td rowspan="{num_linhas_span}">{res_b['tot_mig']}</td>
                <td rowspan="{num_linhas_span}">{res_b['q_mig']:.1f}%</td>
                <td rowspan="{num_linhas_span}">{res_b['canc_mig']}</td>
                <td rowspan="{num_linhas_span}">{res_b['retorno_wo']}</td>
                <td>{res_b['tot_pme']}</td>
                <td>{res_b['q_pme']:.1f}%</td>
                <td>{res_b['canc_pme']}</td>
            </tr>
            """)

            # Linhas dos Supervisores
            for s in sups_b:
                df_s = df_b[df_b["Supervisor"] == s]
                p_sup = st.session_state.get(f"p_{b}_{s}", 0)
                m_sup = st.session_state.get(f"m_{b}_{s}", 20)
                res_s = calcular_metricas(df_s, m_sup, 0)
                
                tabela_html.append(f"""
                <tr class="tr-sup">
                    <td style="text-align: left; padding-left: 20px;">{s}</td>
                    <td>{p_sup}</td>
                    <td>{m_sup}</td>
                    <td>{res_s['tot_os']}</td>
                    <td>{res_s['os_aberta']}</td>
                    <td>{res_s['pontos']}</td>
                    <td>{res_s['efic']:.1f}%</td>
                    <td>{res_s['media_os']:.1f}</td>
                    <td>{res_s['produtivo']}</td>
                    <td>{res_s['q_ins']:.1f}%</td>
                    <td>{res_s['q_serv']:.1f}%</td>
                    <td>{res_s['q_nd']:.1f}%</td>
                    <td>{res_s['os_canc']}</td>
                    <td>{res_s['saiu_toa']}</td>
                    <td>{res_s['tot_pme']}</td>
                    <td>{res_s['q_pme']:.1f}%</td>
                    <td>{res_s['canc_pme']}</td>
                </tr>
                """)

        # Linha Final: TOTAL INSTALAÇÃO
        g_den_geral = g_quebra + g_prod
        g_efic = (max(0.0, 1.0 - (g_quebra / g_den_geral)) * 100) if g_den_geral > 0 else 0.0
        g_media_os = (g_prod / g_montados) if g_montados > 0 else 0.0
        g_q_ins = (g_raw_ins_q / g_raw_ins_tot * 100) if g_raw_ins_tot > 0 else 0.0
        g_q_serv = (g_raw_serv_q / g_raw_serv_tot * 100) if g_raw_serv_tot > 0 else 0.0
        g_q_nd = (g_raw_nd_q / g_nd * 100) if g_nd > 0 else 0.0
        g_q_gpon = (g_raw_gpon_q / g_gpon * 100) if g_gpon > 0 else 0.0
        g_q_mig = (g_raw_mig_q / g_mig * 100) if g_mig > 0 else 0.0
        g_q_pme = (g_raw_pme_q / g_pme * 100) if g_pme > 0 else 0.0

        tabela_html.append(f"""
        <tr class="tr-total">
            <td style="text-align: left; padding-left: 8px;">TOTAL INSTALAÇÃO</td>
            <td>{g_parados}</td>
            <td>{g_montados}</td>
            <td>{g_meta_os:,.0f}</td>
            <td class="red-text">{g_proj_os:,.0f}</td>
            <td>{g_meta_cons}</td>
            <td class="red-text">{g_proj_cons}</td>
            <td>{g_hoje_cons}</td>
            <td>{g_os_cons}</td>
            <td>{g_tot_os}</td>
            <td>{g_aberta}</td>
            <td>{g_pontos}</td>
            <td>{g_efic:.1f}%</td>
            <td>{g_media_os:.1f}</td>
            <td>{g_prod}</td>
            <td>{g_sem_cons}</td>
            <td>{g_q_ins:.1f}%</td>
            <td>{g_q_serv:.1f}%</td>
            <td>{g_q_nd:.1f}%</td>
            <td>{g_nd}</td>
            <td>{g_canc}</td>
            <td>{g_saiu_toa}</td>
            <td>{g_ganho}</td>
            <td>{g_gpon}</td>
            <td>{g_q_gpon:.1f}%</td>
            <td>{g_mig}</td>
            <td>{g_q_mig:.1f}%</td>
            <td>{g_mig_canc}</td>
            <td>{g_retorno}</td>
            <td>{g_pme}</td>
            <td>{g_q_pme:.1f}%</td>
            <td>{g_pme_canc}</td>
        </tr>
        </tbody>
        </table>
        """)

        # Renderização da Tabela Executiva
        st.markdown("".join(tabela_html), unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        # Botão para Baixar a Planilha Excel
        if st.session_state.df_aniel_full is not None:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                st.session_state.df_aniel_full.to_excel(writer, sheet_name="BASE_TRATADA", index=False)
            
            st.download_button(
                label="📥 Baixar Base ANIEL Tratada (.xlsx)",
                data=output.getvalue(),
                file_name="Planilha_Tratada_Aniel.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
