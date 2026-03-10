import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Gestão Financeira Pro", layout="wide", page_icon="📊")

# --- BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect('financeiro_v11.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, email TEXT UNIQUE, senha TEXT, 
                       status TEXT, nivel TEXT DEFAULT 'cliente', tipo_pessoa TEXT, documento TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS categorias 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, nome TEXT, tipo TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS lancamentos 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, data TEXT, tipo TEXT, 
                       categoria TEXT, conta TEXT, valor REAL, hist TEXT)''')
    conn.commit()
    return conn

conn = init_db()

# --- ESTILIZAÇÃO ---
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; background-color: #1a237e; color: white; font-weight: bold; }
    .main-header { color: #1a237e; font-weight: bold; border-bottom: 2px solid #1a237e; padding-bottom: 10px; margin-bottom: 20px; }
    .saldo-card { background-color: #f1f3f4; padding: 20px; border-radius: 10px; text-align: center; border: 1px solid #d1d3d4; }
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
    st.sidebar.title(f"Olá, {st.session_state.user_nome}")
    menu = st.sidebar.radio("Navegação", ["Configurações", "Lançamentos", "DRE/Relatórios", "👑 Admin" if st.session_state.user_nivel == 'admin' else None])

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
                conn.commit()
                st.rerun()
        with c2:
            st.subheader("🗑️ Gerenciar")
            items = pd.read_sql(f"SELECT id, nome, tipo FROM categorias WHERE user_id={st.session_state.user_id}", conn)
            st.dataframe(items, use_container_width=True)
            id_del = st.number_input("ID Categoria para remover", step=1, value=0)
            if st.button("Remover Categoria"):
                conn.execute("DELETE FROM categorias WHERE id=? AND user_id=?", (id_del, st.session_state.user_id))
                conn.commit()
                st.rerun()

    # --- TELA: LANÇAMENTOS ---
    elif menu == "Lançamentos":
        st.markdown("<h1 class='main-header'>📝 Movimentações</h1>", unsafe_allow_html=True)
        recs = [r[0] for r in conn.execute("SELECT nome FROM categorias WHERE user_id=? AND tipo='R'", (st.session_state.user_id,)).fetchall()]
        desps = [r[0] for r in conn.execute("SELECT nome FROM categorias WHERE user_id=? AND tipo='D'", (st.session_state.user_id,)).fetchall()]
        banks = [r[0] for r in conn.execute("SELECT nome FROM categorias WHERE user_id=? AND tipo='B'", (st.session_state.user_id,)).fetchall()]

        tab_ins, tab_edit = st.tabs(["🆕 Novo Lançamento", "✏️ Editar / Excluir"])

        with tab_ins:
            tipo_mov = st.radio("Selecione o Fluxo", ["Entrada/Saída Comum", "🔄 Transferência entre Contas"], horizontal=True)
            if tipo_mov == "Entrada/Saída Comum":
                c1, c2, c3 = st.columns(3)
                d_l, t_l, b_l = c1.date_input("Data"), c2.selectbox("Tipo", ["Receita", "Despesa"], key="tipo_lan"), c3.selectbox("Conta", banks)
                lista_filtro = recs if t_l == "Receita" else desps
                cat_l = st.selectbox("Categoria", lista_filtro if lista_filtro else ["Nenhuma cadastrada"])
                v_l = st.number_input("Valor R$", min_value=0.0, step=0.01)
                h_l = st.text_input("Histórico")
                if st.button("Confirmar Lançamento"):
                    conn.execute("INSERT INTO lancamentos (user_id, data, tipo, categoria, conta, valor, hist) VALUES (?,?,?,?,?,?,?)", (st.session_state.user_id, str(d_l), t_l, cat_l, b_l, v_l, h_l))
                    conn.commit()
                    st.success("Salvo!"); st.rerun()
            else:
                c1, c2, c3 = st.columns(3)
                d_t, ori, dest = c1.date_input("Data"), c2.selectbox("Origem", banks), c3.selectbox("Destino", banks)
                v_t = st.number_input("Valor", min_value=0.0, step=0.01)
                if st.button("Transferir"):
                    if ori == dest: st.error("Contas iguais!")
                    else:
                        conn.execute("INSERT INTO lancamentos (user_id, data, tipo, categoria, conta, valor, hist) VALUES (?,?,'Despesa','Transferência Interna',?,?,?)", (st.session_state.user_id, str(d_t), ori, v_t, f"Para {dest}"))
                        conn.execute("INSERT INTO lancamentos (user_id, data, tipo, categoria, conta, valor, hist) VALUES (?,?,'Receita','Transferência Interna',?,?,?)", (st.session_state.user_id, str(d_t), dest, v_t, f"De {ori}"))
                        conn.commit(); st.success("Transferido!"); st.rerun()

        with tab_edit:
            df_hist = pd.read_sql(f"SELECT * FROM lancamentos WHERE user_id={st.session_state.user_id} ORDER BY id DESC", conn)
            st.dataframe(df_hist, use_container_width=True)
            csv = df_hist.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Baixar CSV para Contador", data=csv, file_name=f"financeiro_{date.today()}.csv", mime='text/csv')
            st.markdown("---")
            id_acao = st.number_input("ID do Lançamento", step=1, value=0)
            acao = st.selectbox("Ação", ["---", "Excluir", "Editar"])
            if acao == "Editar" and id_acao > 0:
                item = conn.execute("SELECT * FROM lancamentos WHERE id=? AND user_id=?", (id_acao, st.session_state.user_id)).fetchone()
                if item:
                    with st.expander("Editar", expanded=True):
                        nv, nh = st.number_input("Novo Valor", value=item[6]), st.text_input("Novo Histórico", value=item[7])
                        if st.button("Salvar"):
                            conn.execute("UPDATE lancamentos SET valor=?, hist=? WHERE id=?", (nv, nh, id_acao)); conn.commit(); st.rerun()
            elif acao == "Excluir" and st.button("⚠️ Confirmar"):
                conn.execute("DELETE FROM lancamentos WHERE id=? AND user_id=?", (id_acao, st.session_state.user_id)); conn.commit(); st.rerun()

    # --- TELA: DRE ---
    elif menu == "DRE/Relatórios":
        st.markdown("<h1 class='main-header'>📊 Filtros e Resultados Contábeis</h1>", unsafe_allow_html=True)
        banks_list = [r[0] for r in conn.execute("SELECT nome FROM categorias WHERE user_id=? AND tipo='B'", (st.session_state.user_id,)).fetchall()]
        
        c1, c2, c3 = st.columns(3)
        dt_i, dt_f = c1.date_input("Início", value=date(date.today().year, date.today().month, 1)), c2.date_input("Fim", value=date.today())
        b_sel = c3.selectbox("Visualizar Banco/Conta", ["Todos"] + banks_list)
        
        df_r = pd.read_sql(f"SELECT * FROM lancamentos WHERE user_id={st.session_state.user_id}", conn)
        if not df_r.empty:
            df_r['data'] = pd.to_datetime(df_r['data']).dt.date
            f = (df_r['data'] >= dt_i) & (df_r['data'] <= dt_f)
            df_final = df_r[f]

            # 1. CÁLCULO DRE (Sem transferências)
            df_contabil = df_final[df_final['categoria'] != 'Transferência Interna']
            if b_sel != "Todos": df_contabil = df_contabil[df_contabil['conta'] == b_sel]
            
            r_t = df_contabil[df_contabil['tipo'] == 'Receita']['valor'].sum()
            d_t = df_contabil[df_contabil['tipo'] == 'Despesa']['valor'].sum()
            
            st.subheader("🏁 Resultado Operacional (DRE)")
            m1, m2, m3 = st.columns(3)
            m1.metric("Faturamento Real", f"R$ {r_t:,.2f}")
            m2.metric("Despesas Reais", f"R$ {d_t:,.2f}")
            m3.metric("Lucro Líquido", f"R$ {r_t - d_t:,.2f}")

            # 2. CÁLCULO SALDO EM CONTA (Conciliação incluindo transferências)
            st.markdown("---")
            st.subheader("💰 Conciliação e Saldo em Conta")
            if b_sel == "Todos":
                st.info("Selecione um banco específico acima para ver o saldo detalhado daquela conta.")
            else:
                df_banco = df_final[df_final['conta'] == b_sel]
                ent_b = df_banco[df_banco['tipo'] == 'Receita']['valor'].sum() # Inclui Transf. Entrada
                sai_b = df_banco[df_banco['tipo'] == 'Despesa']['valor'].sum() # Inclui Transf. Saída
                
                col_s1, col_s2, col_s3 = st.columns(3)
                with col_s1: st.markdown(f"<div class='saldo-card'>📥 Entradas Totais no {b_sel}<br><b>R$ {ent_b:,.2f}</b></div>", unsafe_allow_html=True)
                with col_s2: st.markdown(f"<div class='saldo-card'>📤 Saídas Totais do {b_sel}<br><b>R$ {sai_b:,.2f}</b></div>", unsafe_allow_html=True)
                with col_s3: st.markdown(f"<div class='saldo-card' style='background-color:#e8f5e9'>💵 SALDO ATUAL EM CONTA<br><b>R$ {ent_b - sai_b:,.2f}</b></div>", unsafe_allow_html=True)

            st.markdown("---")
            st.dataframe(df_final, use_container_width=True)

    elif menu == "👑 Admin":
        st.markdown("<h1 class='main-header'>Admin</h1>", unsafe_allow_html=True)
        users = pd.read_sql("SELECT id, nome, documento, email, status FROM usuarios", conn)
        st.table(users)
        id_atv = st.number_input("ID Usuário", step=1)
        if st.button("Ativar"):
            conn.execute("UPDATE usuarios SET status='Ativo' WHERE id=?", (id_atv,)); conn.commit(); st.rerun()

    if st.sidebar.button("🚪 Sair"):
        st.session_state.clear(); st.rerun()
