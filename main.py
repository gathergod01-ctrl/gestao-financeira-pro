import streamlit as st
import pandas as pd
import sqlite3
import smtplib
from datetime import datetime, date
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Gestão Financeira Pro", layout="wide", page_icon="📊")

# --- BANCO DE DATAS ---
def init_db():
    conn = sqlite3.connect('financeiro_web.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, email TEXT UNIQUE, senha TEXT, status TEXT, nivel TEXT DEFAULT 'cliente')''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS categorias 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, nome TEXT, tipo TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS lancamentos 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, data TEXT, tipo TEXT, categoria TEXT, conta TEXT, valor REAL, hist TEXT)''')
    conn.commit()
    return conn

conn = init_db()

# --- ESTILIZAÇÃO ---
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #1a237e; color: white; }
    .stDownloadButton>button { width: 100%; }
    .main-header { color: #1a237e; font-weight: bold; border-bottom: 2px solid #1a237e; padding-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- LOGIN ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    tab1, tab2 = st.tabs(["🔐 Login", "📝 Solicitar Acesso"])
    with tab1:
        email = st.text_input("E-mail")
        senha = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            user = conn.execute("SELECT id, nome, status, nivel FROM usuarios WHERE email=? AND senha=?", (email, senha)).fetchone()
            if user:
                if user[2] == 'Ativo':
                    st.session_state.logado = True
                    st.session_state.user_id = user[0]
                    st.session_state.user_nome = user[1]
                    st.session_state.user_nivel = user[3]
                    st.rerun()
                else: st.warning("⚠️ Licença pendente de aprovação.")
            else: st.error("E-mail ou senha incorretos.")
    with tab2:
        novo_nome = st.text_input("Nome Completo")
        novo_email = st.text_input("E-mail")
        nova_senha = st.text_input("Senha", type="password")
        if st.button("Solicitar Licença"):
            status = 'Ativo' if novo_email == 'gathergod01@gmail.com' else 'Pendente'
            nivel = 'admin' if novo_email == 'gathergod01@gmail.com' else 'cliente'
            try:
                conn.execute("INSERT INTO usuarios (nome, email, senha, status, nivel) VALUES (?,?,?,?,?)", (novo_nome, novo_email, nova_senha, status, nivel))
                conn.commit()
                st.success("Solicitação enviada!")
            except: st.error("E-mail já cadastrado.")

else:
    # --- APP LOGADO ---
    st.sidebar.title(f"👋 Olá, {st.session_state.user_nome}")
    opcoes_menu = ["Configurações", "Lançamentos", "DRE"]
    if st.session_state.user_nivel == 'admin':
        opcoes_menu.append("Painel Admin")
    
    menu = st.sidebar.radio("Navegação", opcoes_menu)

    # --- TELA 1: CONFIGURAÇÕES ---
    if menu == "Configurações":
        st.markdown("<h1 class='main-header'>⚙️ Configurações e Plano de Contas</h1>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("➕ Adicionar Novo")
            nome_cat = st.text_input("Nome do Item")
            tipo_cat = st.selectbox("Tipo", ["Receita", "Despesa", "Banco/Caixa"])
            if st.button("Salvar Categoria"):
                tipo_cod = 'R' if tipo_cat == "Receita" else 'D' if tipo_cat == "Despesa" else 'B'
                conn.execute("INSERT INTO categorias (user_id, nome, tipo) VALUES (?,?,?)", (st.session_state.user_id, nome_cat, tipo_cod))
                conn.commit()
                st.success(f"{nome_cat} adicionado!")

        with col2:
            st.subheader("🗑️ Remover Existente")
            # Busca categorias atuais
            res_cats = conn.execute("SELECT nome FROM categorias WHERE user_id=?", (st.session_state.user_id,)).fetchall()
            lista_nomes = [r[0] for r in res_cats]
            cat_para_remover = st.selectbox("Selecione para excluir", [""] + lista_nomes)
            if st.button("Excluir Selecionado") and cat_para_remover != "":
                conn.execute("DELETE FROM categorias WHERE user_id=? AND nome=?", (st.session_state.user_id, cat_para_remover))
                conn.commit()
                st.warning(f"{cat_para_remover} removido.")
                st.rerun()

    # --- TELA 2: LANÇAMENTOS ---
    elif menu == "Lançamentos":
        st.markdown("<h1 class='main-header'>📝 Lançamentos Financeiros</h1>", unsafe_allow_html=True)
        
        # Busca listas para os selects
        rec_list = [r[0] for r in conn.execute("SELECT nome FROM categorias WHERE user_id=? AND tipo='R'", (st.session_state.user_id,)).fetchall()]
        desp_list = [r[0] for r in conn.execute("SELECT nome FROM categorias WHERE user_id=? AND tipo='D'", (st.session_state.user_id,)).fetchall()]
        bank_list = [r[0] for r in conn.execute("SELECT nome FROM categorias WHERE user_id=? AND tipo='B'", (st.session_state.user_id,)).fetchall()]

        with st.form("form_lancamento", clear_on_submit=True):
            col_a, col_b, col_c = st.columns(3)
            data_l = col_a.date_input("Data", value=date.today())
            tipo_l = col_b.selectbox("Tipo", ["Receita", "Despesa"])
            conta_l = col_c.selectbox("Banco/Caixa", bank_list if bank_list else ["Cadastre um banco primeiro"])
            
            cat_l = st.selectbox("Categoria", rec_list if tipo_l == "Receita" else desp_list)
            valor_l = st.number_input("Valor R$", min_value=0.0, step=0.01)
            hist_l = st.text_input("Histórico / Detalhes")
            
            if st.form_submit_button("Efetivar Lançamento"):
                conn.execute("INSERT INTO lancamentos (user_id, data, tipo, categoria, conta, valor, hist) VALUES (?,?,?,?,?,?,?)",
                             (st.session_state.user_id, str(data_l), tipo_l, cat_l, conta_l, valor_l, hist_l))
                conn.commit()
                st.success("Lançamento realizado!")

        st.markdown("---")
        st.subheader("📋 Histórico Recente")
        df_l = pd.read_sql(f"SELECT id, data, tipo, categoria, valor, conta, hist FROM lancamentos WHERE user_id={st.session_state.user_id} ORDER BY id DESC", conn)
        st.dataframe(df_l, use_container_width=True)
        
        id_para_deletar = st.number_input("ID para excluir", step=1, value=0)
        if st.button("🗑️ Excluir Lançamento") and id_para_deletar > 0:
            conn.execute("DELETE FROM lancamentos WHERE id=? AND user_id=?", (id_para_deletar, st.session_state.user_id))
            conn.commit()
            st.rerun()

    # --- TELA 3: DRE ---
    elif menu == "DRE":
        st.markdown("<h1 class='main-header'>📊 Demonstrativo de Resultados</h1>", unsafe_allow_html=True)
        col_i, col_f = st.columns(2)
        d_ini = col_i.date_input("Início", value=date(date.today().year, date.today().month, 1))
        d_fim = col_f.date_input("Fim", value=date.today())
        
        df_dre = pd.read_sql(f"SELECT data, tipo, valor, categoria FROM lancamentos WHERE user_id={st.session_state.user_id}", conn)
        if not df_dre.empty:
            df_dre['data'] = pd.to_datetime(df_dre['data']).dt.date
            df_filtro = df_dre[(df_dre['data'] >= d_ini) & (df_dre['data'] <= d_fim)]
            
            rec_t = df_filtro[df_filtro['tipo'] == 'Receita']['valor'].sum()
            desp_t = df_filtro[df_filtro['tipo'] == 'Despesa']['valor'].sum()
            
            st.metric("Resultado Líquido", f"R$ {rec_t - desp_t:,.2f}", delta=f"Rec: R$ {rec_t:,.2f} | Desp: R$ {desp_t:,.2f}")
            st.dataframe(df_filtro, use_container_width=True)
            
            csv = df_filtro.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Baixar Relatório (CSV)", data=csv, file_name=f"dre_{d_ini}_{d_fim}.csv")

    # --- PAINEL ADMIN ---
    elif menu == "Painel Admin":
        st.markdown("<h1 class='main-header'>👑 Painel Administrativo</h1>", unsafe_allow_html=True)
        usuarios_p = pd.read_sql("SELECT id, nome, email, status FROM usuarios WHERE nivel='cliente'", conn)
        st.table(usuarios_p)
        id_lib = st.number_input("ID do Usuário para Ativar", step=1, value=0)
        if st.button("✅ Ativar Licença"):
            conn.execute("UPDATE usuarios SET status='Ativo' WHERE id=?", (id_lib,))
            conn.commit()
            st.success("Licença Ativada!")
            st.rerun()

    if st.sidebar.button("🚪 Sair"):
        st.session_state.logado = False
        st.rerun()
