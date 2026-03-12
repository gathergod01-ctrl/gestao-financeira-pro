import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime, date

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Gestão Financeira Gabriel", layout="wide")

# --- CONEXÃO API SUPABASE ---
# Substitua pelos dados que você copiou na aba API do Supabase
URL_SVP = "https://xtrgfoiyqppqtocuwbqi.supabase.co"
KEY_SVP = "COLE_AQUI_SUA_CHAVE_ANON_PUBLIC"

supabase: Client = create_client(URL_SVP, KEY_SVP)

# --- LOGIN / SESSÃO ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.markdown("<h1 style='text-align: center;'>📊 Gestão Financeira</h1>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["🔐 Login", "📝 Cadastro"])
    
    with t1:
        e_l = st.text_input("E-mail")
        s_l = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            # Busca no banco via API
            res = supabase.table("usuarios").select("*").eq("email", e_l).eq("senha", s_l).execute()
            if res.data:
                u = res.data[0]
                if u['status'] == 'Ativo':
                    st.session_state.update({"logado": True, "user_id": u['id'], "user_nome": u['nome'], "user_nivel": u['nivel']})
                    st.rerun()
                else: st.warning("Aguarde liberação do Admin.")
            else: st.error("Usuário ou senha inválidos.")

    with t2:
        cn = st.text_input("Nome/Razão")
        ce = st.text_input("E-mail de cadastro")
        cs = st.text_input("Senha de cadastro", type="password")
        if st.button("Solicitar Acesso"):
            status = "Ativo" if ce == "gathergod01@gmail.com" else "Pendente"
            nivel = "admin" if ce == "gathergod01@gmail.com" else "cliente"
            data = {"nome": cn, "email": ce, "senha": cs, "status": status, "nivel": nivel}
            supabase.table("usuarios").insert(data).execute()
            st.success("Solicitação enviada!")

else:
    # --- APP LOGADO ---
    st.sidebar.title(f"👋 Olá, {st.session_state.user_nome}")
    menu = st.sidebar.radio("Navegação", ["Lançamentos", "DRE", "👑 Admin" if st.session_state.user_nivel == 'admin' else "Sair"])

    if menu == "Lançamentos":
        st.subheader("📝 Novo Lançamento")
        with st.form("f_lan"):
            dt = st.date_input("Data")
            tp = st.selectbox("Tipo", ["Receita", "Despesa"])
            ct = st.text_input("Categoria (Ex: Aluguel, Vendas)")
            vl = st.number_input("Valor", min_value=0.0)
            if st.form_submit_button("Salvar"):
                ins = {"user_id": st.session_state.user_id, "data": str(dt), "tipo": tp, "categoria": ct, "valor": vl}
                supabase.table("lancamentos").insert(ins).execute()
                st.success("Lançado!")

    elif menu == "DRE":
        st.subheader("📊 Resumo Financeiro")
        res = supabase.table("lancamentos").select("*").eq("user_id", st.session_state.user_id).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            st.dataframe(df)
            st.metric("Saldo Total", f"R$ {df[df['tipo']=='Receita']['valor'].sum() - df[df['tipo']=='Despesa']['valor'].sum():,.2f}")

    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.rerun()
