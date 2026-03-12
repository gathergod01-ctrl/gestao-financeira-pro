import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime, date, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Gestão Financeira Pro", layout="wide", page_icon="📊")

# --- CONEXÃO SUPABASE (POSTGRES) ---
# Substitua SUA_SENHA_AQUI pela senha que você definiu no projeto do Supabase
DB_URI = "postgresql://postgres:SUA_SENHA_AQUI@db.xtrgfoiyqppqtocuwbqi.supabase.co:5432/postgres"
engine = create_engine(DB_URI)

def query_db(sql, params=None, commit=False):
    """Função mestre para executar comandos no Supabase"""
    with engine.connect() as conn:
        result = conn.execute(text(sql), params or {})
        if commit:
            conn.commit()
        if result.returns_rows:
            return result.fetchall()
        return None

# --- ESTILIZAÇÃO ---
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; background-color: #1a237e; color: white; font-weight: bold; }
    .main-header { color: #1a237e; font-weight: bold; border-bottom: 2px solid #1a237e; padding-bottom: 10px; margin-bottom: 20px; }
    .card-resumo { background-color: #ffffff; padding: 20px; border-radius: 10px; box-shadow: 2px 2px 10px rgba(0,0,0,0.1); border-top: 5px solid #1a237e; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- LOGIN / SESSÃO ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.markdown("<h1 style='text-align: center; color: #1a237e;'>📊 Gestão Financeira Gabriel</h1>", unsafe_allow_html=True)
    tab_login, tab_cad = st.tabs(["🔐 Acessar", "📝 Criar Conta"])
    
    with tab_login:
        email_l = st.text_input("E-mail", key="l_email")
        senha_l = st.text_input("Senha", type="password", key="l_senha")
        if st.button("Entrar"):
            user = query_db("SELECT id, nome, status, nivel FROM usuarios WHERE email = :email AND senha = :senha", 
                            {"email": email_l, "senha": senha_l})
            if user:
                user = user[0]
                if user[2] == 'Ativo':
                    st.session_state.update({"logado": True, "user_id": user[0], "user_nome": user[1], "user_nivel": user[3]})
                    st.rerun()
                else: st.warning("⚠️ Licença pendente.")
            else: st.error("Login inválido.")

    with tab_cad:
        cn = st.text_input("Nome/Razão Social", key="cad_nome")
        ct = st.radio("Tipo", ["PF", "PJ"], horizontal=True, key="cad_tipo")
        cd = st.text_input("CPF/CNPJ", key="cad_doc")
        ce = st.text_input("E-mail", key="cad_email")
        cs = st.text_input("Senha", type="password", key="cad_senha")
        if st.button("Solicitar Acesso"):
            stus, nvl = ("Ativo", "admin") if ce == "gathergod01@gmail.com" else ("Pendente", "cliente")
            try:
                query_db("INSERT INTO usuarios (nome, email, senha, status, nivel, tipo_pessoa, documento) VALUES (:n, :e, :s, :st, :nv, :tp, :doc)",
                         {"n": cn, "e": ce, "s": cs, "st": stus, "nv": nvl, "tp": ct, "doc": cd}, commit=True)
                st.success("✅ Solicitação enviada!")
            except Exception as ex: st.error(f"Erro: {ex}")

else:
    # --- APP LOGADO ---
    st.sidebar.title(f"Olá, {st.session_state.user_nome}")
    menu = st.sidebar.radio("Navegação", ["Configurações", "Lançamentos", "DRE / Dashboard", "👑 Admin" if st.session_state.user_nivel == 'admin' else None])

    # --- TELA: CONFIGURAÇÕES ---
    if menu == "Configurações":
        st.markdown("<h1 class='main-header'>⚙️ Configurações</h1>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            n = st.text_input("Nome do Item")
            t = st.selectbox("Tipo", ["Receita", "Despesa", "Banco/Caixa"])
            if st.button("Salvar"):
                tipo_map = {'Receita':'R', 'Despesa':'D', 'Banco/Caixa':'B'}
                query_db("INSERT INTO categorias (user_id, nome, tipo) VALUES (:uid, :n, :t)", 
                         {"uid": st.session_state.user_id, "n": n, "t": tipo_map[t]}, commit=True)
                st.rerun()
        with c2:
            res = query_db("SELECT id, nome, tipo FROM categorias WHERE user_id = :uid", {"uid": st.session_state.user_id})
            df_c = pd.DataFrame(res, columns=['id', 'nome', 'tipo']) if res else pd.DataFrame()
            st.dataframe(df_c, use_container_width=True)
            id_del = st.number_input("ID remover", step=1)
            if st.button("Remover"):
                query_db("DELETE FROM categorias WHERE id = :id AND user_id = :uid", {"id": id_del, "uid": st.session_state.user_id}, commit=True)
                st.rerun()

    # --- TELA: LANÇAMENTOS ---
    elif menu == "Lançamentos":
        st.markdown("<h1 class='main-header'>📝 Movimentações</h1>", unsafe_allow_html=True)
        r_cats = query_db("SELECT nome FROM categorias WHERE user_id=:u AND tipo='R'", {"u": st.session_state.user_id})
        d_cats = query_db("SELECT nome FROM categorias WHERE user_id=:u AND tipo='D'", {"u": st.session_state.user_id})
        b_cats = query_db("SELECT nome FROM categorias WHERE user_id=:u AND tipo='B'", {"u": st.session_state.user_id})
        
        banks = [r[0] for r in b_cats] if b_cats else []
        recs = [r[0] for r in r_cats] if r_cats else []
        desps = [r[0] for r in d_cats] if d_cats else []

        t1, t2 = st.tabs(["Lançar", "Histórico"])
        with t1:
            tp_m = st.radio("Tipo", ["Comum", "Transferência"], horizontal=True)
            if tp_m == "Comum":
                c1, c2, c3 = st.columns(3)
                dt, tl = c1.date_input("Data"), c2.selectbox("Fluxo", ["Receita", "Despesa"])
                bl = c3.selectbox("Banco", banks)
                cl = st.selectbox("Categoria", recs if tl=="Receita" else desps)
                vl, hl = st.number_input("Valor"), st.text_input("Histórico")
                if st.button("Salvar Lançamento"):
                    query_db("INSERT INTO lancamentos (user_id, data, tipo, categoria, conta, valor, hist) VALUES (:u, :d, :t, :c, :ct, :v, :h)",
                             {"u": st.session_state.user_id, "d": str(dt), "t": tl, "c": cl, "ct": bl, "v": vl, "h": hl}, commit=True)
                    st.rerun()
            else:
                c1, c2, c3 = st.columns(3)
                dt, ori, dest = c1.date_input("Data"), c2.selectbox("Origem", banks), c3.selectbox("Destino", banks)
                vt = st.number_input("Valor Transferência")
                if st.button("Executar Transferência"):
                    query_db("INSERT INTO lancamentos (user_id, data, tipo, categoria, conta, valor, hist) VALUES (:u, :d, 'Despesa', 'Transferência Interna', :ct, :v, :h)",
                             {"u": st.session_state.user_id, "d": str(dt), "ct": ori, "v": vt, "h": f"Para {dest}"}, commit=True)
                    query_db("INSERT INTO lancamentos (user_id, data, tipo, categoria, conta, valor, hist) VALUES (:u, :d, 'Receita', 'Transferência Interna', :ct, :v, :h)",
                             {"u": st.session_state.user_id, "d": str(dt), "ct": dest, "v": vt, "h": f"De {ori}"}, commit=True)
                    st.rerun()
        with t2:
            res_h = query_db("SELECT id, data, tipo, categoria, conta, valor, hist FROM lancamentos WHERE user_id = :u ORDER BY id DESC", {"u": st.session_state.user_id})
            df_h = pd.DataFrame(res_h, columns=['id', 'data', 'tipo', 'categoria', 'conta', 'valor', 'hist']) if res_h else pd.DataFrame()
            st.dataframe(df_h)
            id_ex = st.number_input("ID para excluir", step=1)
            if st.button("Confirmar Exclusão"):
                query_db("DELETE FROM lancamentos WHERE id = :id", {"id": id_ex}, commit=True)
                st.rerun()

    # --- TELA: DRE / DASHBOARD ---
    elif menu == "DRE / Dashboard":
        st.markdown("<h1 class='main-header'>📊 Inteligência Financeira</h1>", unsafe_allow_html=True)
        c_f1, c_f2 = st.columns(2)
        dt_i = c_f1.date_input("Início", value=date(date.today().year, date.today().month, 1))
        dt_f = c_f2.date_input("Fim", value=date.today())
        
        # Saldo Inicial
        prev = query_db("SELECT tipo, valor FROM lancamentos WHERE user_id = :u AND data < :d", {"u": st.session_state.user_id, "d": str(dt_i)})
        s_ini = sum([float(r[1]) if r[0]=='Receita' else -float(r[1]) for r in prev]) if prev else 0.0
        st.metric("Saldo Inicial no Período", f"R$ {s_ini:,.2f}")

        # DRE
        res_p = query_db("SELECT tipo, valor, categoria, conta, data FROM lancamentos WHERE user_id = :u AND data >= :di AND data <= :df", 
                         {"u": st.session_state.user_id, "di": str(dt_i), "df": str(dt_f)})
        if res_p:
            df_p = pd.DataFrame(res_p, columns=['tipo', 'valor', 'categoria', 'conta', 'data'])
            df_p['valor'] = df_p['valor'].astype(float)
            df_dre = df_p[df_p['categoria'] != 'Transferência Interna']
            rt, dt = df_dre[df_dre['tipo']=='Receita']['valor'].sum(), df_dre[df_dre['tipo']=='Despesa']['valor'].sum()
            
            cm1, cm2, cm3 = st.columns(3)
            with cm1: st.markdown(f"<div class='card-resumo'>🟢 RECEITA<br><h3>R$ {rt:,.2f}</h3></div>", unsafe_allow_html=True)
            with cm2: st.markdown(f"<div class='card-resumo'>🔴 DESPESA<br><h3>R$ {dt:,.2f}</h3></div>", unsafe_allow_html=True)
            with cm3: st.markdown(f"<div class='card-resumo'>💎 LUCRO<br><h3>R$ {rt-dt:,.2f}</h3></div>", unsafe_allow_html=True)
            
            st.bar_chart(df_dre.groupby('categoria')['valor'].sum())
        else: st.info("Sem movimentações no período.")

    elif menu == "👑 Admin":
        st.markdown("<h1 class='main-header'>👑 Gestão de Licenças</h1>", unsafe_allow_html=True)
        res_u = query_db("SELECT id, nome, documento, email, status FROM usuarios WHERE nivel = 'cliente'")
        if res_u:
            st.table(pd.DataFrame(res_u, columns=['id', 'nome', 'documento', 'email', 'status']))
            id_a = st.number_input("ID para ativar", step=1)
            if st.button("Ativar"):
                query_db("UPDATE usuarios SET status='Ativo' WHERE id=:id", {"id": id_a}, commit=True)
                st.rerun()

    if st.sidebar.button("Sair"): st.session_state.clear(); st.rerun()
