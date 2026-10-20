import io
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Painel Operacional - Tratamento Aniel", page_icon="📊", layout="wide"
)

st.title("📊 Painel Operacional - Tratamento da Base Aniel")
st.write(
    "Carregue os ficheiros operacionais necessários (Aniel, TOA, Baixas, etc.)"
    " para aplicar todas as regras de cruzamento."
)

# Uploaders separados para cada base necessária
uploaded_aniel = st.file_uploader(
    "Carregar Ficheiro ANIEL (.xlsx ou .xlsm)",
    type=["xlsx", "xlsm"],
    key="aniel",
)
uploaded_toa = st.file_uploader(
    "Carregar Ficheiros do TOA (Pode selecionar os três ficheiros)",
    type=["xlsx", "xlsm", "csv"],
    accept_multiple_files=True,
    key="toa",
)
uploaded_aux = st.file_uploader(
    "Carregar Ficheiro Auxiliar (Baixas, Desc OS, Pontos Aniel - Opcional)",
    type=["xlsx", "xlsm"],
    key="aux",
)

if uploaded_aniel is not None:
  try:
    with st.spinner("A processar os dados... Por favor, aguarde."):
      # Lendo a base Aniel
      df_aniel = pd.read_excel(uploaded_aniel)

      # Unindo os ficheiros do TOA se houver mais do que um
      df_toa = None
      if uploaded_toa:
        toa_dfs = []
        for file in uploaded_toa:
          if file.name.endswith(".csv"):
            toa_dfs.append(pd.read_csv(file))
          else:
            toa_dfs.append(pd.read_excel(file))
        df_toa = pd.concat(toa_dfs, ignore_index=True)

      # Lendo abas auxiliares se o ficheiro auxiliar foi enviado
      df_desc_os = None
      df_pontos = None
      df_baixas = None
      if uploaded_aux:
        xls_aux = pd.ExcelFile(uploaded_aux)
        if "DESC OS" in xls_aux.sheet_names:
          df_desc_os = pd.read_excel(xls_aux, sheet_name="DESC OS")
        if "PONTOS ANIEL" in xls_aux.sheet_names:
          df_pontos = pd.read_excel(xls_aux, sheet_name="PONTOS ANIEL")
        if "BAIXAS" in xls_aux.sheet_names:
          df_baixas = pd.read_excel(xls_aux, sheet_name="BAIXAS")

      # 1. Cruzamento com o TOA
      if df_toa is not None and not df_toa.empty:
        toa_dict = df_toa.set_index(df_toa.columns[1]).to_dict(orient="index")

        for idx, row in df_aniel.iterrows():
          contrato = str(row.get("Contrato Cliente", "")).strip()
          if contrato in toa_dict:
            match = toa_dict[contrato]
            df_aniel.at[idx, "ST1"] = match.get(df_toa.columns[2], "")
            df_aniel.at[idx, "ST2"] = match.get(df_toa.columns[3], "")
            df_aniel.at[idx, "ST3"] = match.get(df_toa.columns[7], "")
            df_aniel.at[idx, "CANCELADAS_TEMP"] = match.get(
                df_toa.columns[5], ""
            )
            df_aniel.at[idx, "PME"] = match.get(df_toa.columns[6], "")
          else:
            df_aniel.at[idx, "ST1"] = np.nan
            df_aniel.at[idx, "ST2"] = np.nan
            df_aniel.at[idx, "ST3"] = np.nan
            df_aniel.at[idx, "CANCELADAS_TEMP"] = np.nan
            df_aniel.at[idx, "PME"] = np.nan

      # 2. Tratamento "N/A" -> PROCV ST3 na aba Baixas
      if df_baixas is not None and not df_baixas.empty:
        baixas_dict = (
            df_baixas.set_index(df_baixas.columns[0]).iloc[:, 0].to_dict()
        )
        for idx, row in df_aniel.iterrows():
          tipo_os = str(row.get("Tipo de OS", "")).strip().upper()
          if tipo_os in ["N/A", "#N/A", ""]:
            st3_val = str(row.get("ST3", "")).strip()
            if st3_val in baixas_dict:
              df_aniel.at[idx, "Tipo de OS"] = baixas_dict[st3_val]
            else:
              df_aniel.at[idx, "Tipo de OS"] = "EM ABERTO"

      # 3. Tratamento "EM ABERTO" com ST1 vazio -> "SAIU DO TOA"
      for idx, row in df_aniel.iterrows():
        tipo_os = str(row.get("Tipo de OS", "")).strip().upper()
        st1_val = str(row.get("ST1", "")).strip()
        if tipo_os == "EM ABERTO" and st1_val == "":
          df_aniel.at[idx, "Tipo de OS"] = "SAIU DO TOA"

      # 4. Tratamento ST2 Liberado/Cancelado NETSMS -> "CANCELADO"
      for idx, row in df_aniel.iterrows():
        tipo_os = str(row.get("Tipo de OS", "")).strip().upper()
        st2_val = str(row.get("ST2", "")).lower()
        if (
            "liberado no sistema netsms" in st2_val
            or "cancelado no sistema netsms" in st2_val
        ) and tipo_os == "EM ABERTO":
          df_aniel.at[idx, "Tipo de OS"] = "CANCELADO"

      # 5. Tratamento ST2 Executado NETSMS -> "PRODUTIVA"
      for idx, row in df_aniel.iterrows():
        st2_val = str(row.get("ST2", "")).lower()
        if "executado no sistema netsms" in st2_val:
          df_aniel.at[idx, "Tipo de OS"] = "PRODUTIVA"

      # 6. Regra da coluna Canceladas
      for idx, row in df_aniel.iterrows():
        st2_val = str(row.get("ST2", "")).lower()
        if "cancelado" in st2_val:
          df_aniel.at[idx, "CANCELADAS"] = "CANCELADO"
        else:
          df_aniel.at[idx, "CANCELADAS"] = ""

      # 7. Criar colunas Quebras e Atividades
      desc_dict = (
          df_desc_os.set_index(df_desc_os.columns[0])[df_desc_os.columns[1]]
          .to_dict()
          if df_desc_os is not None
          else {}
      )
      pontos_dict = (
          df_pontos.set_index(df_pontos.columns[0])[df_pontos.columns[1]]
          .to_dict()
          if df_pontos is not None
          else {}
      )

      for idx, row in df_aniel.iterrows():
        tipo_servico = str(row.get("Tipo de Serviço", "")).strip()
        obs1 = str(row.get("Observação 1", "")).lower()
        tipo_servico_lower = tipo_servico.lower()

        if tipo_servico in desc_dict:
          df_aniel.at[idx, "QUEBRAS"] = desc_dict[tipo_servico]

        status_ativ = ""
        if "const" in tipo_servico_lower:
          status_ativ = "CONSTRUÇÃO"
        elif (
            "pon " in obs1
            or "fibra" in obs1
            or "virtua pon" in obs1
            or "gpon" in obs1
        ):
          status_ativ = "GPON"
          if (
              "instalacao de cabo gpon" in tipo_servico_lower
              or "mudanca de pacote" in tipo_servico_lower
          ):
            status_ativ = "MIGRAÇÃO"

        if status_ativ == "":
          status_ativ = "HFC"

        if (
            status_ativ == "HFC"
            and "instalacao de cabo gpon" in tipo_servico_lower
        ):
          status_ativ = "MIGRAÇÃO"

        df_aniel.at[idx, "ATIVIDADES"] = status_ativ

        # Pontos Previstos
        pontos_prev = row.get("Pontos Prev.", 0)
        if pd.isna(pontos_prev) or pontos_prev == 0 or pontos_prev == "":
          if tipo_servico in pontos_dict:
            df_aniel.at[idx, "Pontos Prev."] = pontos_dict[tipo_servico]

        try:
          val_p = (
              str(df_aniel.at[idx, "Pontos Prev."])
              .replace(".", "")
              .replace(",", ".")
          )
          df_aniel.at[idx, "Pontos Prev."] = float(val_p)
        except:
          pass

      st.success("Processamento concluído com sucesso!")
      st.dataframe(df_aniel.head(20))

      # Botão para exportar o resultado tratado
      output = io.BytesIO()
      with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_aniel.to_excel(writer, sheet_name="ANIEL", index=False)
      processed_data = output.getvalue()

      st.download_button(
          label="📥 Descarregar Planilha Tratada",
          data=processed_data,
          file_name="Planilha_Aniel_Tratada.xlsx",
          mime=(
              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          ),
      )

  except Exception as e:
    st.error(f"Ocorreu um erro ao processar os ficheiros: {e}")
