import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime, date, timedelta

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Gestão Financeira Gabriel", layout="wide", page_icon="📊")

# --- CONEXÃO API SUPABASE ---
URL_SVP = "https://xtrgfoiyqppqtocuwbqi.supabase.co"
KEY_SVP = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inh0cmdmb2l5cXBwcXRvY3V3YnFpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzMzMTgxMTEsImV4cCI6MjA4ODg5NDExMX0.Cgg41ITX7z-FWs8JVMDz1hC1_6JA7Cma89CKsPNb93k"
supabase: Client = create_client(URL_SVP, KEY_SVP)

# --- ESTILIZAÇÃO ---
st.markdown("""
    <style>
    .main-header { color: #1a237e; font-weight: bold; border-bottom: 2px solid #1a237e; padding-bottom: 10px; margin-bottom: 20px; }
    .card-resumo { background-color: #ffffff; padding: 20px; border-radius: 10px; box-shadow: 2px 2px 10px rgba(0,0,0,0.1); border-top: 5px solid #1a237e; text-align: center; }
    .stButton>button { width: 100%; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONTROLE DE SESSÃO ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

# --- FLUXO DE ACESSO (LOGIN/CADASTRO) ---
if not st.session_state.logado:
    st.markdown("<h1 style='text-align: center; color: #1a237e;'>📊 Financeiro Gabriel v24.2</h1>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["🔐 Acessar", "📝 Solicitar Conta"])
    
    with t1:
        e_l = st.text_input("E-mail", key="l_email")
        s_l = st.text_input("Senha", type="password", key="l_senha")
        if st.button("Entrar", key="btn_l"):
            try:
                res = supabase.table("usuarios").select("*").eq("email", e_l).eq("senha", s_l).execute()
                if res.data:
                    u = res.data[0]
                    if u.get('status') == 'Ativo' or e_l == "gathergod01@gmail.com":
                        st.session_state.update({"logado": True, "user_id": u['id'], "user_nome": u['nome'], "user_nivel": u.get('nivel', 'cliente')})
                        st.rerun()
                    else: st.warning("Aguarde ativação do administrador.")
                else: st.error("Login inválido.")
            except Exception as e: st.error(f"Erro de conexão: {e}")
            
    with t2:
        cn = st.text_input("Nome/Razão", key="c_nome")
        ce = st.text_input("E-mail", key="c_email")
        cs = st.text_input("Senha", type="password", key="c_senha")
        if st.button("Enviar Cadastro", key="btn_c"):
            try:
                stus = "Ativo" if ce == "gathergod01@gmail.com" else "Pendente"
                nvl = "admin" if ce == "gathergod01@gmail.com" else "cliente"
                supabase.table("usuarios").insert({"nome": cn, "email": ce, "senha": cs, "status": stus, "nivel": nvl}).execute()
                st.success("✅ Solicitação enviada! Tente logar.")
            except Exception as e: st.error(f"Erro ao cadastrar: {e}")

# --- SISTEMA PRINCIPAL (APÓS LOGIN) ---
else:
    st.sidebar.title(f"👋 {st.session_state.user_nome}")
    menu = st.sidebar.radio("Navegação", ["DRE / Dashboard", "Lançamentos", "Despesas Recorrentes", "Configurações", "👑 Admin" if st.session_state.user_nivel == 'admin' else None])

    if menu == "Configurações":
        st.markdown("<h1 class='main-header'>⚙️ Configurações</h1>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            nome_cat = st.text_input("Nome (Ex: Itaú, Aluguel, Vendas)", key="cfg_n")
            tipo_cat = st.selectbox("Tipo", ["Receita", "Despesa", "Banco/Caixa"], key="cfg_t")
            if st.button("Cadastrar Categoria"):
                t_map = {'Receita':'R', 'Despesa':'D', 'Banco/Caixa':'B'}
                supabase.table("categorias").insert({"user_id": st.session_state.user_id, "nome": nome_cat, "tipo": t_map[tipo_cat]}).execute()
                st.rerun()
        with c2:
            res_c = supabase.table("categorias").select("*").eq("user_id", st.session_state.user_id).execute()
            if res_c.data:
                df_c = pd.DataFrame(res_c.data)
                st.dataframe(df_c[['id', 'nome', 'tipo']], use_container_width=True)
                id_del = st.number_input("ID para remover", step=1, key="cfg_del")
                if st.button("Excluir Categoria", key="btn_cfg_del"):
                    supabase.table("categorias").delete().eq("id", id_del).execute()
                    st.rerun()

    elif menu == "Lançamentos":
        st.markdown("<h1 class='main-header'>📝 Movimentações</h1>", unsafe_allow_html=True)
        res_cats = supabase.table("categorias").select("*").eq("user_id", st.session_state.user_id).execute()
        df_cats = pd.DataFrame(res_cats.data) if res_cats.data else pd.DataFrame(columns=['nome', 'tipo'])
        
        banks = df_cats[df_cats['tipo']=='B']['nome'].tolist()
        recs = df_cats[df_cats['tipo']=='R']['nome'].tolist()
        desps = df_cats[df_cats['tipo']=='D']['nome'].tolist()

        t1, t2 = st.tabs(["🆕 Novo Lançamento", "📋 Histórico"])
        with t1:
            if not banks: st.warning("Cadastre um Banco em Configurações primeiro!")
            else:
                tp_m = st.radio("Tipo", ["Comum", "Transferência"], horizontal=True, key="lan_tp")
                if tp_m == "Comum":
                    c1, c2, c3 = st.columns(3)
                    dt, fl, bc = c1.date_input("Data"), c2.selectbox("Fluxo", ["Receita", "Despesa"]), c3.selectbox("Banco", banks)
                    cat = st.selectbox("Categoria", recs if fl=="Receita" else desps)
                    vl = st.number_input("Valor R$", min_value=0.0, format="%.2f")
                    hist = st.text_input("Histórico")
                    if st.button("Salvar Registro"):
                        supabase.table("lancamentos").insert({"user_id": st.session_state.user_id, "data": str(dt), "tipo": fl, "categoria": cat, "conta": bc, "valor": vl, "hist": hist}).execute()
                        st.success("Lançado!")
                else:
                    c1, c2, c3 = st.columns(3)
                    dt, ori, dest = c1.date_input("Data"), c2.selectbox("De", banks), c3.selectbox("Para", banks)
                    vt = st.number_input("Valor da Transf.")
                    if st.button("Executar Transferência"):
                        supabase.table("lancamentos").insert({"user_id": st.session_state.user_id, "data": str(dt), "tipo": "Despesa", "categoria": "Transferência Interna", "conta": ori, "valor": vt, "hist": f"Para {dest}"}).execute()
                        supabase.table("lancamentos").insert({"user_id": st.session_state.user_id, "data": str(dt), "tipo": "Receita", "categoria": "Transferência Interna", "conta": dest, "valor": vt, "hist": f"De {ori}"}).execute()
                        st.success("Transferência realizada!")
        with t2:
            res_h = supabase.table("lancamentos").select("*").eq("user_id", st.session_state.user_id).order("data", desc=True).execute()
            if res_h.data:
                df_h = pd.DataFrame(res_h.data)
                st.dataframe(df_h[['id', 'data', 'tipo', 'categoria', 'conta', 'valor', 'hist']], use_container_width=True)
                id_ex = st.number_input("ID para excluir", step=1, key="lan_del")
                if st.button("Confirmar Exclusão"):
                    supabase.table("lancamentos").delete().eq("id", id_ex).execute()
                    st.rerun()

    elif menu == "DRE / Dashboard":
        st.markdown("<h1 class='main-header'>📊 Inteligência Financeira</h1>", unsafe_allow_html=True)
        col_f1, col_f2, col_f3 = st.columns([2, 2, 2])
        dt_i = col_f1.date_input("Data Início", value=date(date.today().year, date.today().month, 1))
        dt_f = col_f2.date_input("Data Fim", value=date.today())
        
        res_all = supabase.table("lancamentos").select("*").eq("user_id", st.session_state.user_id).execute()
        if res_all.data:
            df_all = pd.DataFrame(res_all.data)
            df_all['data'] = pd.to_datetime(df_all['data']).dt.date
            df_all['valor'] = df_all['valor'].astype(float)

            # SALDO RETROATIVO
            df_prev = df_all[df_all['data'] < dt_i]
            s_ini_total = df_prev[df_prev['tipo']=='Receita']['valor'].sum() - df_prev[df_prev['tipo']=='Despesa']['valor'].sum()
            col_f3.metric("Saldo Inicial", f"R$ {s_ini_total:,.2f}")

            # DRE
            df_periodo = df_all[(df_all['data'] >= dt_i) & (df_all['data'] <= dt_f)]
            df_dre = df_periodo[df_periodo['categoria'] != 'Transferência Interna']
            rec_real = df_dre[df_dre['tipo'] == 'Receita']['valor'].sum()
            des_real = df_dre[df_dre['tipo'] == 'Despesa']['valor'].sum()
            
            c_m1, c_m2, c_m3 = st.columns(3)
            with c_m1: st.markdown(f"<div class='card-resumo'>🟢 RECEITA<br><h3>R$ {rec_real:,.2f}</h3></div>", unsafe_allow_html=True)
            with c_m2: st.markdown(f"<div class='card-resumo'>🔴 DESPESA<br><h3>R$ {des_real:,.2f}</h3></div>", unsafe_allow_html=True)
            with c_m3: st.markdown(f"<div class='card-resumo'>💎 LUCRO<br><h3>R$ {rec_real - des_real:,.2f}</h3></div>", unsafe_allow_html=True)

            st.bar_chart(df_dre.groupby('categoria')['valor'].sum())

            # FLUXO ACUMULADO
            st.markdown("### 🌊 Fluxo de Caixa Diário")
            b_list = df_all['conta'].unique().tolist()
            sel_b = st.selectbox("Conta:", b_list)
            if sel_b:
                s_ini_b = df_prev[df_prev['conta']==sel_b][df_prev['tipo']=='Receita']['valor'].sum() - \
                          df_prev[df_prev['conta']==sel_b][df_prev['tipo']=='Despesa']['valor'].sum()
                df_b_p = df_periodo[df_periodo['conta'] == sel_b].sort_values('data')
                diario = df_b_p.groupby('data').apply(lambda x: pd.Series({
                    'Saldo_Dia': x[x['tipo']=='Receita']['valor'].sum() - x[x['tipo']=='Despesa']['valor'].sum()
                })).reset_index()
                diario['Acumulado'] = diario['Saldo_Dia'].cumsum() + s_ini_b
                st.line_chart(diario.set_index('data')['Acumulado'])
        else: st.info("Sem dados no período.")

    elif menu == "Despesas Recorrentes":
        st.markdown("<h1 class='main-header'>🔄 Provisões</h1>", unsafe_allow_html=True)
        with st.form("f_rec"):
            c1, c2 = st.columns(2)
            desc = c1.text_input("Descrição")
            dia = c2.number_input("Dia Vencimento", 1, 31)
            val = c1.number_input("Valor")
            if st.form_submit_button("Salvar"):
                supabase.table("recorrencias").insert({"user_id": st.session_state.user_id, "dia_vencimento": dia, "valor": val, "descricao": desc}).execute()
                st.rerun()

    if st.sidebar.button("🚪 Sair"):
        st.session_state.clear()
        st.rerun()
