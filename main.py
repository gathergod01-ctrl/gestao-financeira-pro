import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date, timedelta

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Gestão Financeira Pro", layout="wide", page_icon="📊")

# --- BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect('financeiro_v12.db', check_same_thread=False)
    cursor = conn.cursor()
    # Tabela de usuários
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, email TEXT UNIQUE, senha TEXT, 
                       status TEXT, nivel TEXT DEFAULT 'cliente', tipo_pessoa TEXT, documento TEXT)''')
    # Tabela de categorias
    cursor.execute('''CREATE TABLE IF NOT EXISTS categorias 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, nome TEXT, tipo TEXT)''')
    # Tabela de lançamentos efetivados
    cursor.execute('''CREATE TABLE IF NOT EXISTS lancamentos 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, data TEXT, tipo TEXT, 
                       categoria TEXT, conta TEXT, valor REAL, hist TEXT)''')
    # NOVA TABELA: DESPESAS RECORRENTES
    cursor.execute('''CREATE TABLE IF NOT EXISTS recorrencias 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, dia_vencimento INTEGER, 
                       categoria TEXT, valor REAL, descricao TEXT)''')
    conn.commit()
    return conn

conn = init_db()

# --- ESTILIZAÇÃO ---
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; background-color: #1a237e; color: white; font-weight: bold; }
    .main-header { color: #1a237e; font-weight: bold; border-bottom: 2px solid #1a237e; padding-bottom: 10px; margin-bottom: 20px; }
    .notificacao-vencimento { background-color: #fff3e0; border-left: 5px solid #ff9800; padding: 15px; border-radius: 5px; margin-bottom: 10px; color: #e65100; font-weight: bold; }
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
        if st.button("Entrar", key="btn_l"):
            user = conn.execute("SELECT id, nome, status, nivel FROM usuarios WHERE email=? AND senha=?", (email_l, senha_l)).fetchone()
            if user:
                if user[2] == 'Ativo':
                    st.session_state.logado, st.session_state.user_id, st.session_state.user_nome, st.session_state.user_nivel = True, user[0], user[1], user[3]
                    st.rerun()
                else: st.warning("⚠️ Licença pendente.")
            else: st.error("Erro de login.")
    with tab_cad:
        c_nome = st.text_input("Nome / Razão Social", key="c_nome")
        c_tipo = st.radio("Tipo", ["PF (CPF)", "PJ (CNPJ)"], horizontal=True, key="c_tipo")
        c_doc = st.text_input("Documento", key="c_doc")
        c_email = st.text_input("E-mail", key="c_email")
        c_senha = st.text_input("Senha", type="password", key="c_senha")
        if st.button("Solicitar Acesso"):
            status = 'Ativo' if c_email == "gathergod01@gmail.com" else 'Pendente'
            nivel = 'admin' if c_email == "gathergod01@gmail.com" else 'cliente'
            try:
                conn.execute("INSERT INTO usuarios (nome, email, senha, status, nivel, tipo_pessoa, documento) VALUES (?,?,?,?,?,?,?)", (c_nome, c_email, c_senha, status, nivel, c_tipo, c_doc))
                conn.commit()
                st.success("Solicitação enviada!")
            except: st.error("E-mail já existe.")

else:
    # --- LÓGICA DE NOTIFICAÇÃO DE VENCIMENTOS ---
    hoje = date.today()
    vencimentos_hoje = conn.execute("SELECT descricao, valor FROM recorrencias WHERE user_id=? AND dia_vencimento=?", (st.session_state.user_id, hoje.day)).fetchall()
    
    if vencimentos_hoje:
        for v in vencimentos_hoje:
            st.markdown(f"<div class='notificacao-vencimento'>🚨 VENCIMENTO HOJE: {v[0]} - R$ {v[1]:,.2f}</div>", unsafe_allow_html=True)

    st.sidebar.title(f"Olá, {st.session_state.user_nome}")
    menu = st.sidebar.radio("Navegação", ["Configurações", "Lançamentos", "Despesas Recorrentes", "DRE/Relatórios", "👑 Admin" if st.session_state.user_nivel == 'admin' else None])

    # --- TELA: CONFIGURAÇÕES ---
    if menu == "Configurações":
        st.markdown("<h1 class='main-header'>⚙️ Configurações</h1>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("➕ Novo Item")
            n_cat = st.text_input("Nome do Item")
            t_cat = st.selectbox("Tipo de Categoria", ["Receita", "Despesa", "Banco/Caixa"])
            if st.button("Salvar Item"):
                code = 'R' if t_cat == "Receita" else 'D' if t_cat == "Despesa" else 'B'
                conn.execute("INSERT INTO categorias (user_id, nome, tipo) VALUES (?,?,?)", (st.session_state.user_id, n_cat, code))
                conn.commit(); st.rerun()
        with c2:
            st.subheader("🗑️ Gerenciar")
            items = pd.read_sql(f"SELECT id, nome, tipo FROM categorias WHERE user_id={st.session_state.user_id}", conn)
            st.dataframe(items, use_container_width=True)
            id_del = st.number_input("ID Categoria para remover", step=1, value=0)
            if st.button("Remover Categoria"):
                conn.execute("DELETE FROM categorias WHERE id=? AND user_id=?", (id_del, st.session_state.user_id))
                conn.commit(); st.rerun()

    # --- NOVA TELA: DESPESAS RECORRENTES ---
    elif menu == "Despesas Recorrentes":
        st.markdown("<h1 class='main-header'>🔄 Gerenciar Contas Mensais</h1>", unsafe_allow_html=True)
        desps = [r[0] for r in conn.execute("SELECT nome FROM categorias WHERE user_id=? AND tipo='D'", (st.session_state.user_id,)).fetchall()]
        
        with st.form("form_recorrente"):
            c1, c2 = st.columns(2)
            desc_r = c1.text_input("Descrição da Despesa (Ex: Internet, Aluguel)")
            dia_r = c2.number_input("Dia do Vencimento Mensal", min_value=1, max_value=31, step=1)
            val_r = c1.number_input("Valor Fixo R$", min_value=0.0, step=0.01)
            cat_r = c2.selectbox("Categoria da Despesa", desps)
            if st.form_submit_button("Cadastrar Recorrência"):
                conn.execute("INSERT INTO recorrencias (user_id, dia_vencimento, categoria, valor, descricao) VALUES (?,?,?,?,?)",
                             (st.session_state.user_id, dia_r, cat_r, val_r, desc_r))
                conn.commit(); st.success("Recorrência cadastrada!"); st.rerun()
        
        st.markdown("---")
        df_rec = pd.read_sql(f"SELECT id, dia_vencimento as 'Dia Venc.', descricao as 'Despesa', valor, categoria FROM recorrencias WHERE user_id={st.session_state.user_id}", conn)
        st.subheader("Sua Lista de Contas Recorrentes")
        st.dataframe(df_rec, use_container_width=True)
        
        id_del_r = st.number_input("ID para excluir recorrência", step=1, value=0)
        if st.button("Excluir Recorrência"):
            conn.execute("DELETE FROM recorrencias WHERE id=? AND user_id=?", (id_del_r, st.session_state.user_id))
            conn.commit(); st.rerun()

    # --- TELA: LANÇAMENTOS (Com Atalho para Recorrentes) ---
    elif menu == "Lançamentos":
        st.markdown("<h1 class='main-header'>📝 Movimentações</h1>", unsafe_allow_html=True)
        banks = [r[0] for r in conn.execute("SELECT nome FROM categorias WHERE user_id=? AND tipo='B'", (st.session_state.user_id,)).fetchall()]
        recs_list = [r[0] for r in conn.execute("SELECT nome FROM categorias WHERE user_id=? AND tipo='R'", (st.session_state.user_id,)).fetchall()]
        desps_list = [r[0] for r in conn.execute("SELECT nome FROM categorias WHERE user_id=? AND tipo='D'", (st.session_state.user_id,)).fetchall()]

        # Atalho para pagar conta recorrente
        recorrentes_lista = conn.execute("SELECT id, descricao, valor, categoria FROM recorrencias WHERE user_id=?", (st.session_state.user_id,)).fetchall()
        if recorrentes_lista:
            with st.expander("⚡ Atalho: Pagar Conta Recorrente"):
                escolha_r = st.selectbox("Selecione a conta que está pagando", [f"{r[1]} - R$ {r[2]}" for r in recorrentes_lista])
                b_pag = st.selectbox("Pagar por qual Conta/Banco?", banks, key="b_pag_rec")
                if st.button("Confirmar Pagamento da Recorrência"):
                    # Extrair dados da escolha
                    idx = [f"{r[1]} - R$ {r[2]}" for r in recorrentes_lista].index(escolha_r)
                    item_r = recorrentes_lista[idx]
                    conn.execute("INSERT INTO lancamentos (user_id, data, tipo, categoria, conta, valor, hist) VALUES (?,?,'Despesa',?,?,?,?)",
                                 (st.session_state.user_id, str(hoje), item_r[3], b_pag, item_r[2], f"Pagamento Recorrente: {item_r[1]}"))
                    conn.commit(); st.success("Pago e registrado!"); st.rerun()

        tab_ins, tab_edit = st.tabs(["🆕 Novo Lançamento", "✏️ Editar / Excluir"])
        with tab_ins:
            tipo_mov = st.radio("Fluxo", ["Comum", "🔄 Transferência"], horizontal=True)
            if tipo_mov == "Comum":
                c1, c2, c3 = st.columns(3)
                d_l, t_l, b_l = c1.date_input("Data"), c2.selectbox("Tipo", ["Receita", "Despesa"]), c3.selectbox("Conta", banks)
                cat_l = st.selectbox("Categoria", recs_list if t_l == "Receita" else desps_list)
                v_l, h_l = st.number_input("Valor", min_value=0.0), st.text_input("Histórico")
                if st.button("Lançar"):
                    conn.execute("INSERT INTO lancamentos (user_id, data, tipo, categoria, conta, valor, hist) VALUES (?,?,?,?,?,?,?)", (st.session_state.user_id, str(d_l), t_l, cat_l, b_l, v_l, h_l))
                    conn.commit(); st.rerun()
            else:
                c1, c2, c3 = st.columns(3)
                d_t, ori, dest = c1.date_input("Data"), c2.selectbox("Origem", banks), c3.selectbox("Destino", banks)
                v_t = st.number_input("Valor", min_value=0.0)
                if st.button("Transferir"):
                    conn.execute("INSERT INTO lancamentos (user_id, data, tipo, categoria, conta, valor, hist) VALUES (?,?,'Despesa','Transferência Interna',?,?,?)", (st.session_state.user_id, str(d_t), ori, v_t, f"Para {dest}"))
                    conn.execute("INSERT INTO lancamentos (user_id, data, tipo, categoria, conta, valor, hist) VALUES (?,?,'Receita','Transferência Interna',?,?,?)", (st.session_state.user_id, str(d_t), dest, v_t, f"De {ori}"))
                    conn.commit(); st.rerun()

        with tab_edit:
            df_hist = pd.read_sql(f"SELECT * FROM lancamentos WHERE user_id={st.session_state.user_id} ORDER BY id DESC", conn)
            st.dataframe(df_hist, use_container_width=True)
            st.download_button("📥 CSV Contador", data=df_hist.to_csv(index=False).encode('utf-8'), file_name="financeiro.csv")

    # --- TELA: DRE ---
    elif menu == "DRE/Relatórios":
        st.markdown("<h1 class='main-header'>📊 Resultados</h1>", unsafe_allow_html=True)
        banks_list = [r[0] for r in conn.execute("SELECT nome FROM categorias WHERE user_id=? AND tipo='B'", (st.session_state.user_id,)).fetchall()]
        c1, c2, c3 = st.columns(3)
        dt_i, dt_f = c1.date_input("Início", value=date(hoje.year, hoje.month, 1)), c2.date_input("Fim", value=hoje)
        b_sel = c3.selectbox("Banco/Conta", ["Todos"] + banks_list)
        
        df_r = pd.read_sql(f"SELECT * FROM lancamentos WHERE user_id={st.session_state.user_id}", conn)
        if not df_r.empty:
            df_r['data'] = pd.to_datetime(df_r['data']).dt.date
            df_f = df_r[(df_r['data'] >= dt_i) & (df_r['data'] <= dt_f)]
            
            # DRE Operacional
            df_c = df_f[df_f['categoria'] != 'Transferência Interna']
            if b_sel != "Todos": df_c = df_c[df_c['conta'] == b_sel]
            rt, dt = df_c[df_c['tipo'] == 'Receita']['valor'].sum(), df_c[df_c['tipo'] == 'Despesa']['valor'].sum()
            
            st.columns(3)[0].metric("Faturamento", f"R$ {rt:,.2f}")
            st.columns(3)[1].metric("Despesas", f"R$ {dt:,.2f}")
            st.columns(3)[2].metric("Lucro", f"R$ {rt-dt:,.2f}")

            # Saldo em Conta
            if b_sel != "Todos":
                df_b = df_f[df_f['conta'] == b_sel]
                eb, sb = df_b[df_b['tipo'] == 'Receita']['valor'].sum(), df_b[df_b['tipo'] == 'Despesa']['valor'].sum()
                st.markdown(f"**Saldo do Período em {b_sel}: R$ {eb-sb:,.2f}**")

    elif menu == "👑 Admin":
        st.markdown("<h1 class='main-header'>Admin</h1>", unsafe_allow_html=True)
        users = pd.read_sql("SELECT id, nome, documento, email, status FROM usuarios", conn)
        st.table(users)
        id_atv = st.number_input("ID Usuário", step=1)
        if st.button("Ativar"):
            conn.execute("UPDATE usuarios SET status='Ativo' WHERE id=?", (id_atv,)); conn.commit(); st.rerun()

    if st.sidebar.button("🚪 Sair"):
        st.session_state.clear(); st.rerun()
