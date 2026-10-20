import io
import re
import pandas as pd
import numpy as np
import streamlit as st

st.set_page_config(
    page_title="Painel Operacional - Tratamento Aniel",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Painel Operacional - Tratamento da Base Aniel")
st.write("Carregue a base Aniel e os arquivos do TOA para tratamento e cruzamento automático.")

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
        raise ValueError(f"Não foi possível ler o arquivo: {e}")

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
    s = re.sub(r"\s+", " ", s)
    return s

def converter_para_float(val):
    if pd.isna(val):
        return None
    s = str(val).strip()
    if s == "" or s.lower() == "nan":
        return None
    s = s.replace(" ", "")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None

# Dicionários de referência integrados
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

# Uploaders
uploaded_aniel = st.file_uploader("Carregar Ficheiro ANIEL (.xlsx ou .xlsm)", type=["xlsx", "xlsm", "csv"], key="aniel")
uploaded_toa = st.file_uploader("Carregar Ficheiros do TOA (Pode selecionar os três ficheiros)", type=["xlsx", "xlsm", "csv"], accept_multiple_files=True, key="toa")

if uploaded_aniel is not None:
    try:
        with st.spinner("A processar os dados e estruturar as colunas..."):
            df_aniel = ler_arquivo_seguro(uploaded_aniel)
            df_aniel.columns = [str(c).strip() for c in df_aniel.columns]

            colunas_obrigatorias = ["ST1", "ST2", "ST3", "CANCELADAS", "PME"]
            for col in colunas_obrigatorias:
                if col not in df_aniel.columns:
                    df_aniel[col] = ""

            # Unindo e filtrando as colunas do TOA
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

            # Cruzamento TOA -> ANIEL
            if df_toa is not None and not df_toa.empty:
                col_chave_toa = "Contrato" if "Contrato" in df_toa.columns else df_toa.columns[1]

                df_toa_clean = df_toa.copy()
                df_toa_clean["_chave_"] = df_toa_clean[col_chave_toa].apply(limpar_chave).astype(str)
                df_toa_clean = df_toa_clean[df_toa_clean["_chave_"] != ""]
                df_toa_clean = df_toa_clean.drop_duplicates(subset=["_chave_"], keep="first")
                toa_dict = df_toa_clean.set_index("_chave_").to_dict(orient="index")

                col_chave_aniel = "Contrato Cliente"
                if col_chave_aniel not in df_aniel.columns:
                    for c in df_aniel.columns:
                        if "contrato" in c.lower():
                            col_chave_aniel = c
                            break

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

            # Dicionários normalizados em maiúsculas e sem espaços extras
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

                # N/A ou vazio -> PROCV Baixas
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

                # EM ABERTO com ST1 vazio -> SAIU DO TOA
                if tipo_os == "EM ABERTO" and st1_val == "":
                    tipo_os = "SAIU DO TOA"

                # ST2 Liberado/Cancelado NETSMS com EM ABERTO -> CANCELADO
                if ("liberado no sistema netsms" in st2_val or "cancelado no sistema netsms" in st2_val) and tipo_os == "EM ABERTO":
                    tipo_os = "CANCELADO"

                # ST2 Executado NETSMS -> PRODUTIVA
                if "executado no sistema netsms" in st2_val:
                    tipo_os = "PRODUTIVA"

                df_aniel.at[idx, "Tipo de OS"] = tipo_os

                # Regra CANCELADAS
                if "cancelado" in st2_val:
                    df_aniel.at[idx, "CANCELADAS"] = "CANCELADO"
                else:
                    df_aniel.at[idx, "CANCELADAS"] = ""

                # QUEBRAS e ATIVIDADES
                tipo_servico_raw = str(row.get("Tipo de Serviço", "")).strip()
                tipo_servico_norm = limpar_texto(tipo_servico_raw)

                obs1_raw = str(row.get("Observação 1", "")).strip()
                obs1 = "" if obs1_raw.lower() == "nan" else obs1_raw.lower()

                # Quebras
                quebra_val = ""
                if tipo_servico_norm in desc_norm:
                    quebra_val = desc_norm[tipo_servico_norm]
                else:
                    for k_desc, v_desc in desc_norm.items():
                        if tipo_servico_norm != "" and (tipo_servico_norm in k_desc or k_desc in tipo_servico_norm):
                            quebra_val = v_desc
                            break
                df_aniel.at[idx, "QUEBRAS"] = quebra_val

                # Atividades
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

                # --- PROCV ROBUSTO: Pontos Prev. ---
                pontos_atual = converter_para_float(row.get("Pontos Prev."))
                
                # Se for nulo, vazio ou igual a zero, faz o PROCV
                if pontos_atual is None or pontos_atual == 0.0:
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
                    else:
                        df_aniel.at[idx, "Pontos Prev."] = 0.0
                else:
                    df_aniel.at[idx, "Pontos Prev."] = float(pontos_atual)

            # Manter exclusivamente as 16 colunas finais alinhadas
            colunas_finais = [
                "Data Agendamento", "Projeto", "Cidade", "Contrato Cliente",
                "Tipo de OS", "ST1", "ST2", "ST3", "CANCELADAS", "PME",
                "Supervisor", "Pontos Prev.", "Tipo de Serviço",
                "Observação 1", "QUEBRAS", "ATIVIDADES"
            ]

            for col in colunas_finais:
                if col not in df_aniel.columns:
                    df_aniel[col] = ""

            df_aniel = df_aniel[colunas_finais]

            st.success("Tratamento concluído com sucesso!")
            st.dataframe(df_aniel.head(25))

            output = io.BytesIO()
            try:
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    df_aniel.to_excel(writer, sheet_name="ANIEL", index=False)
                processed_data = output.getvalue()
                st.download_button(
                    label="📥 Descarregar Planilha Tratada (.xlsx)",
                    data=processed_data,
                    file_name="Planilha_Aniel_Tratada.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception:
                csv_data = df_aniel.to_csv(index=False, sep=";", encoding="utf-8-sig")
                st.download_button(
                    label="📥 Descarregar Planilha Tratada (.csv)",
                    data=csv_data,
                    file_name="Planilha_Aniel_Tratada.csv",
                    mime="text/csv"
                )

    except Exception as e:
        st.error(f"Ocorreu um erro ao processar os ficheiros: {e}")
