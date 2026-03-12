import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime, date, timedelta

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Gestão Financeira Gabriel", layout="wide", page_icon="📊")

# --- CONEXÃO SUPABASE ---
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

if not st.session_state.logado:
    st.markdown("<h1 style='text-align: center; color: #1a237e;'>📊 Financeiro Gabriel v22.0</h1>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["🔐 Acessar", "📝 Solicitar Conta"])
    
    with t1:
        e_l = st.text_input("E-mail")
        s_l = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            res = supabase.table("usuarios").select("*").eq("email", e_l).eq("senha", s_l).execute()
            if res.data:
                u = res.data[0]
                if u['status'] == 'Ativo' or e_l == "gathergod01@gmail.com":
                    st.session_state.update({"logado": True, "user_id": u['id'], "user_nome": u['nome'], "user_nivel": u['nivel']})
                    st.rerun()
                else: st.warning("Aguarde ativação do Admin.")
            else: st.error("Login inválido.")
            
    with t2:
        cn = st.text_input("Nome/Empresa")
        ce = st.text_input("E-mail")
        cs = st.text_input("Senha", type="password")
        if st.button("Enviar"):
            status = "Ativo" if ce == "gathergod01@gmail.com" else "Pendente"
            nivel = "admin" if ce == "gathergod01@gmail.com" else "cliente"
            supabase.table("usuarios").insert({"nome": cn, "email": ce, "senha": cs, "status": status, "nivel": nivel}).execute()
            st.success("Solicitação enviada!")

else:
    # --- INTERFACE LOGADA ---
    st.sidebar.title(f"👋 {st.session_state.user_nome}")
    menu = st.sidebar.radio("Navegação", ["Dashboard / DRE", "Lançamentos", "Despesas Recorrentes", "Configurações", "👑 Admin" if st.session_state.user_nivel == 'admin' else None])

    # --- 1. CONFIGURAÇÕES (CATEGORIAS E BANCOS) ---
    if menu == "Configurações":
        st.markdown("<h1 class='main-header'>⚙️ Configurações</h1>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            nome_cat = st.text_input("Nome (Ex: Itaú, Aluguel, Vendas)")
            tipo_cat = st.selectbox("Tipo", ["Receita", "Despesa", "Banco/Caixa"])
            if st.button("Cadastrar"):
                t_map = {'Receita':'R', 'Despesa':'D', 'Banco/Caixa':'B'}
                supabase.table("categorias").insert({"user_id": st.session_state.user_id, "nome": nome_cat, "tipo": t_map[tipo_cat]}).execute()
                st.rerun()
        with c2:
            res_c = supabase.table("categorias").select("*").eq("user_id", st.session_state.user_id).execute()
            if res_c.data:
                df_c = pd.DataFrame(res_c.data)
                st.dataframe(df_c[['id', 'nome', 'tipo']], use_container_width=True)
                id_del = st.number_input("ID para remover", step=1)
                if st.button("Excluir Categoria"):
                    supabase.table("categorias").delete().eq("id", id_del).execute()
                    st.rerun()

    # --- 2. LANÇAMENTOS ---
    elif menu == "Lançamentos":
        st.markdown("<h1 class='main-header'>📝 Lançamentos</h1>", unsafe_allow_html=True)
        # Carregar Categorias
        res_cats = supabase.table("categorias").select("*").eq("user_id", st.session_state.user_id).execute()
        df_cats = pd.DataFrame(res_cats.data) if res_cats.data else pd.DataFrame(columns=['nome', 'tipo'])
        
        banks = df_cats[df_cats['tipo']=='B']['nome'].tolist()
        recs = df_cats[df_cats['tipo']=='R']['nome'].tolist()
        desps = df_cats[df_cats['tipo']=='D']['nome'].tolist()

        t1, t2 = st.tabs(["🆕 Novo Registro", "📋 Histórico"])
        with t1:
            if not banks: st.warning("Cadastre um Banco em Configurações primeiro.")
            else:
                tp_mov = st.radio("Tipo", ["Comum", "Transferência"], horizontal=True)
                if tp_mov == "Comum":
                    c1, c2, c3 = st.columns(3)
                    dt, fl, bc = c1.date_input("Data"), c2.selectbox("Fluxo", ["Receita", "Despesa"]), c3.selectbox("Banco", banks)
                    cat = st.selectbox("Categoria", recs if fl=="Receita" else desps)
                    vl = st.number_input("Valor R$", min_value=0.0, format="%.2f")
                    hist = st.text_input("Histórico")
                    if st.button("Salvar Lançamento"):
                        dados = {"user_id": st.session_state.user_id, "data": str(dt), "tipo": fl, "categoria": cat, "conta": bc, "valor": vl, "hist": hist}
                        supabase.table("lancamentos").insert(dados).execute()
                        st.success("Lançado com sucesso!")
                else:
                    c1, c2, c3 = st.columns(3)
                    dt, ori, dest = c1.date_input("Data"), c2.selectbox("De", banks), c3.selectbox("Para", banks)
                    vt = st.number_input("Valor da Transf.")
                    if st.button("Transferir"):
                        supabase.table("lancamentos").insert({"user_id": st.session_state.user_id, "data": str(dt), "tipo": "Despesa", "categoria": "Transferência", "conta": ori, "valor": vt, "hist": f"Para {dest}"}).execute()
                        supabase.table("lancamentos").insert({"user_id": st.session_state.user_id, "data": str(dt), "tipo": "Receita", "categoria": "Transferência", "conta": dest, "valor": vt, "hist": f"De {ori}"}).execute()
                        st.success("Transferência realizada!")
        with t2:
            res_h = supabase.table("lancamentos").select("*").eq("user_id", st.session_state.user_id).order("data", desc=True).execute()
            if res_h.data:
                df_h = pd.DataFrame(res_h.data)
                st.dataframe(df_h[['id', 'data', 'tipo', 'categoria', 'conta', 'valor', 'hist']], use_container_width=True)
                id_ex = st.number_input("ID para excluir", step=1)
                if st.button("Confirmar Exclusão"):
                    supabase.table("lancamentos").delete().eq("id", id_ex).execute()
                    st.rerun()

    # --- 3. DASHBOARD / DRE / FLUXO DIÁRIO ---
    elif menu == "Dashboard / DRE":
        st.markdown("<h1 class='main-header'>📊 Inteligência Financeira</h1>", unsafe_allow_html=True)
        
        # Filtros de Data
        col_f1, col_f2 = st.columns(2)
        dt_i = col_f1.date_input("Início", date(date.today().year, date.today().month, 1))
        dt_f = col_f2.date_input("Fim", date.today())

        # Puxar dados
        res_all = supabase.table("lancamentos").select("*").eq("user_id", st.session_state.user_id).execute()
        if res_all.data:
            df_all = pd.DataFrame(res_all.data)
            df_all['data'] = pd.to_datetime(df_all['data']).dt.date
            df_all['valor'] = df_all['valor'].astype(float)

            # Saldo Inicial (Tudo antes de dt_i)
            df_prev = df_all[df_all['data'] < dt_i]
            s_ini = df_prev[df_prev['tipo']=='Receita']['valor'].sum() - df_prev[df_prev['tipo']=='Despesa']['valor'].sum()
            
            # Dados do Período
            df_p = df_all[(df_all['data'] >= dt_i) & (df_all['data'] <= dt_f)]
            df_dre = df_p[df_p['categoria'] != 'Transferência']
            
            rec_p = df_dre[df_dre['tipo']=='Receita']['valor'].sum()
            des_p = df_dre[df_dre['tipo']=='Despesa']['valor'].sum()

            # Cards de Resumo
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Saldo Inicial", f"R$ {s_ini:,.2f}")
            c2.markdown(f"<div class='card-resumo'>🟢 RECEITAS<br>R$ {rec_p:,.2f}</div>", unsafe_allow_html=True)
            c3.markdown(f"<div class='card-resumo'>🔴 DESPESAS<br>R$ {des_p:,.2f}</div>", unsafe_allow_html=True)
            c4.markdown(f"<div class='card-resumo'>💎 LUCRO<br>R$ {rec_p-des_p:,.2f}</div>", unsafe_allow_html=True)

            st.divider()
            
            # Gráficos
            g1, g2 = st.columns(2)
            with g1:
                st.subheader("Receitas por Categoria")
                st.bar_chart(df_dre[df_dre['tipo']=='Receita'].groupby('categoria')['valor'].sum())
            with g2:
                st.subheader("Despesas por Categoria")
                st.bar_chart(df_dre[df_dre['tipo']=='Despesa'].groupby('categoria')['valor'].sum())

            st.divider()
            
            # FLUXO DE CAIXA DIÁRIO
            st.subheader("🌊 Fluxo de Caixa Diário Acumulado")
            b_list = df_all['conta'].unique().tolist()
            sel_b = st.selectbox("Selecione a conta para conciliação:", b_list)
            
            if sel_b:
                # Saldo inicial específico da conta
                s_ini_b = df_prev[df_prev['conta']==sel_b][df_prev['tipo']=='Receita']['valor'].sum() - \
                          df_prev[df_prev['conta']==sel_b][df_prev['tipo']=='Despesa']['valor'].sum()
                
                df_b = df_p[df_p['conta']==sel_b].sort_values('data')
                diario = df_b.groupby('data').apply(lambda x: pd.Series({
                    'Entradas': x[x['tipo']=='Receita']['valor'].sum(),
                    'Saídas': x[x['tipo']=='Despesa']['valor'].sum(),
                    'Saldo_Dia': x[x['tipo']=='Receita']['valor'].sum() - x[x['tipo']=='Despesa']['valor'].sum()
                })).reset_index()
                
                diario['Saldo Acumulado'] = diario['Saldo_Dia'].cumsum() + s_ini_b
                st.write(f"Saldo desta conta em {dt_i}: **R$ {s_ini_b:,.2f}**")
                st.dataframe(diario, use_container_width=True)
                st.line_chart(diario.set_index('data')['Saldo Acumulado'])

    # --- 4. DESPESAS RECORRENTES ---
    elif menu == "Despesas Recorrentes":
        st.markdown("<h1 class='main-header'>🔄 Provisão de Contas</h1>", unsafe_allow_html=True)
        with st.form("rec"):
            c1, c2 = st.columns(2)
            desc, dia = c1.text_input("Descrição"), c2.number_input("Dia Vencimento", 1, 31)
            val = c1.number_input("Valor Estimado")
            if st.form_submit_button("Cadastrar Recorrência"):
                supabase.table("recorrencias").insert({"user_id": st.session_state.user_id, "dia_vencimento": dia, "valor": val, "descricao": desc}).execute()
                st.rerun()
        
        res_r = supabase.table("recorrencias").select("*").eq("user_id", st.session_state.user_id).execute()
        if res_r.data:
            df_rec = pd.DataFrame(res_r.data)
            st.table(df_rec[['descricao', 'valor', 'dia_vencimento']])
            
            st.info("💡 Estas contas são usadas para prever seu caixa nos próximos dias no Dashboard.")

    # --- 5. ADMIN ---
    elif menu == "👑 Admin":
        st.markdown("<h1 class='main-header'>Painel de Licenças</h1>", unsafe_allow_html=True)
        res_u = supabase.table("usuarios").select("*").execute()
        if res_u.data:
            df_u = pd.DataFrame(res_u.data)
            st.dataframe(df_u[['id', 'nome', 'email', 'status', 'nivel']])
            id_atv = st.number_input("ID Usuário", step=1)
            if st.button("Ativar / Tornar Admin"):
                supabase.table("usuarios").update({"status": "Ativo", "nivel": "admin"}).eq("id", id_atv).execute()
                st.rerun()

    if st.sidebar.button("🚪 Sair"):
        st.session_state.clear()
        st.rerun()
