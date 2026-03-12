import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime, date, timedelta

# --- CONFIGURAÇÕES ---
st.set_page_config(page_title="Financeiro Gabriel", layout="wide")

URL_SVP = "https://xtrgfoiyqppqtocuwbqi.supabase.co"
KEY_SVP = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inh0cmdmb2l5cXBwcXRvY3V3YnFpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzMzMTgxMTEsImV4cCI6MjA4ODg5NDExMX0.Cgg41ITX7z-FWs8JVMDz1hC1_6JA7Cma89CKsPNb93k"
supabase: Client = create_client(URL_SVP, KEY_SVP)

if 'logado' not in st.session_state:
    st.session_state.logado = False

# --- TELA DE ACESSO ---
if not st.session_state.logado:
    st.title("📊 Gestão Financeira v23.0")
    t1, t2 = st.tabs(["🔐 Entrar", "📝 Criar Conta"])
    
    with t1:
        e_l = st.text_input("E-mail", key="l_email")
        s_l = st.text_input("Senha", type="password", key="l_senha")
        if st.button("Acessar", key="btn_l"):
            res = supabase.table("usuarios").select("*").eq("email", e_l).eq("senha", s_l).execute()
            if res.data:
                u = res.data[0]
                st.session_state.update({"logado": True, "user_id": u['id'], "user_nome": u['nome'], "user_nivel": u.get('nivel', 'cliente')})
                st.rerun()
            else: st.error("Dados incorretos.")

    with t2:
        cn = st.text_input("Nome", key="c_nome")
        ce = st.text_input("E-mail comercial", key="c_email")
        cs = st.text_input("Crie uma Senha", type="password", key="c_senha")
        if st.button("Enviar Cadastro", key="btn_c"):
            try:
                # Tentativa de inserção simplificada para validar
                dados = {"nome": cn, "email": ce, "senha": cs, "status": "Ativo", "nivel": "cliente"}
                supabase.table("usuarios").insert(dados).execute()
                st.success("✅ Sucesso! Agora faça o login na outra aba.")
            except Exception as ex:
                st.error(f"Erro no Banco: {ex}")

else:
    # --- SISTEMA LOGADO ---
    st.sidebar.title(f"Olá, {st.session_state.user_nome}")
    menu = st.sidebar.radio("Navegação", ["Dashboard / DRE", "Lançamentos", "Configurações", "Admin"])

    if menu == "Configurações":
        st.subheader("⚙️ Categorias e Bancos")
        c1, c2 = st.columns(2)
        with c1:
            n_cat = st.text_input("Nome do Item", key="n_cat")
            t_cat = st.selectbox("Tipo", ["Receita", "Despesa", "Banco/Caixa"], key="t_cat")
            if st.button("Salvar Categoria", key="btn_cat"):
                tipo = {'Receita':'R', 'Despesa':'D', 'Banco/Caixa':'B'}[t_cat]
                supabase.table("categorias").insert({"user_id": st.session_state.user_id, "nome": n_cat, "tipo": tipo}).execute()
                st.rerun()
        with c2:
            res_c = supabase.table("categorias").select("*").eq("user_id", st.session_state.user_id).execute()
            if res_c.data: st.table(pd.DataFrame(res_c.data)[['nome', 'tipo']])

    elif menu == "Lançamentos":
        st.subheader("📝 Lançamentos")
        # Busca bancos e categorias
        res_cat = supabase.table("categorias").select("*").eq("user_id", st.session_state.user_id).execute()
        df_cat = pd.DataFrame(res_cat.data) if res_cat.data else pd.DataFrame(columns=['nome', 'tipo'])
        
        banks = df_cat[df_cat['tipo']=='B']['nome'].tolist()
        if not banks: 
            st.warning("Cadastre um Banco em Configurações primeiro!")
        else:
            with st.form("l_form"):
                d1, d2, d3 = st.columns(3)
                f_data = d1.date_input("Data")
                f_tipo = d2.selectbox("Fluxo", ["Receita", "Despesa"])
                f_banco = d3.selectbox("Conta", banks)
                f_cat = st.selectbox("Categoria", df_cat[df_cat['tipo'] == ('R' if f_tipo=='Receita' else 'D')]['nome'].tolist())
                f_val = st.number_input("Valor", min_value=0.0)
                f_hist = st.text_input("Histórico")
                if st.form_submit_button("Salvar"):
                    ins = {"user_id": st.session_state.user_id, "data": str(f_data), "tipo": f_tipo, "categoria": f_cat, "conta": f_banco, "valor": f_val, "hist": f_hist}
                    supabase.table("lancamentos").insert(ins).execute()
                    st.success("Salvo!")

    elif menu == "Dashboard / DRE":
        st.subheader("📊 Inteligência Financeira")
        # Filtro de data
        dt_i = st.date_input("Início", date(date.today().year, date.today().month, 1))
        dt_f = st.date_input("Fim", date.today())
        
        # Puxa tudo do usuário
        res = supabase.table("lancamentos").select("*").eq("user_id", st.session_state.user_id).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df['data'] = pd.to_datetime(df['data']).dt.date
            # Filtra no DataFrame para ser mais rápido
            df_p = df[(df['data'] >= dt_i) & (df['data'] <= dt_f)]
            df_p['valor'] = df_p['valor'].astype(float)
            
            r = df_p[df_p['tipo']=='Receita']['valor'].sum()
            d = df_p[df_p['tipo']=='Despesa']['valor'].sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Receitas", f"R$ {r:,.2f}")
            c2.metric("Despesas", f"R$ {d:,.2f}")
            c3.metric("Resultado", f"R$ {r-d:,.2f}")
            
            st.bar_chart(df_p.groupby('categoria')['valor'].sum())
        else: st.info("Sem lançamentos para o período.")

    if st.sidebar.button("🚪 Sair"):
        st.session_state.clear()
        st.rerun()
