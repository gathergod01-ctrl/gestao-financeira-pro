import streamlit as st
import pandas as pd
import sqlite3
import smtplib
from datetime import datetime, date
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Gestão Financeira Pro", layout="wide", page_icon="📊")

# --- BANCO DE DADOS ---
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

# --- FUNÇÕES DE APOIO ---
def enviar_email(nome, email_user):
    # Insira aqui sua Senha de App de 16 dígitos
    remetente = "SEU_EMAIL@gmail.com"
    senha = "SUA_SENHA_16_DIGITOS"
    
    msg = MIMEMultipart()
    msg['Subject'] = f"🚀 Nova Licença Pendente: {nome}"
    msg.attach(MIMEText(f"Usuário {nome} ({email_user}) solicitou acesso.", 'plain'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(remetente, senha)
        server.sendmail(remetente, "gathergod01@gmail.com", msg.as_string())
        server.quit()
    except: pass

# --- INTERFACE DE LOGIN ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    tab1, tab2 = st.tabs(["Login", "Solicitar Acesso"])
    
    with tab1:
        st.title("🔐 Acesso Restrito")
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
                else:
                    st.warning("⚠️ Sua licença ainda está pendente de aprovação pelo Admin.")
            else:
                st.error("E-mail ou senha incorretos.")

    with tab2:
        st.title("📝 Criar Conta")
        novo_nome = st.text_input("Nome Completo")
        novo_email = st.text_input("E-mail de Cadastro")
        nova_senha = st.text_input("Defina uma Senha", type="password")
        if st.button("Solicitar Licença"):
            status = 'Ativo' if novo_email == 'gathergod01@gmail.com' else 'Pendente'
            nivel = 'admin' if novo_email == 'gathergod01@gmail.com' else 'cliente'
            try:
                conn.execute("INSERT INTO usuarios (nome, email, senha, status, nivel) VALUES (?,?,?,?,?)", 
                             (novo_nome, novo_email, nova_senha, status, nivel))
                conn.commit()
                enviar_email(novo_nome, novo_email)
                st.success("Solicitação enviada! Gabriel será notificado.")
            except:
                st.error("Este e-mail já está cadastrado.")

else:
    # --- APP LOGADO ---
    st.sidebar.title(f"Olá, {st.session_state.user_nome}")
    menu = st.sidebar.radio("Navegação", ["Configurações", "Lançamentos", "DRE", "Painel Admin" if st.session_state.user_nivel == 'admin' else None])

    if menu == "Configurações":
        st.header("⚙️ Plano de Contas")
        col1, col2 = st.columns(2)
        with col1:
            nome_cat = st.text_input("Nome da Categoria/Banco")
            tipo_cat = st.selectbox("Tipo", ["Receita", "Despesa", "Banco"])
            if st.button("Adicionar"):
                tipo_cod = 'R' if tipo_cat == 'Receita' else 'D' if tipo_cat == 'Despesa' else 'B'
                conn.execute("INSERT INTO categorias (user_id, nome, tipo) VALUES (?,?,?)", (st.session_state.user_id, nome_cat, tipo_cod))
                conn.commit()
        
        # Exibição das listas
        cats = pd.read_sql(f"SELECT nome, tipo FROM categorias WHERE user_id={st.session_state.user_id}", conn)
        st.table(cats)

    elif menu == "Lançamentos":
        st.header("📝 Novo Lançamento")
        # Lógica de formulário Streamlit aqui...
        st.info("Aqui o usuário fará as entradas e saídas.")

    elif menu == "Painel Admin":
        st.header("👑 Gestão de Licenças")
        users = pd.read_sql("SELECT id, nome, email, status FROM usuarios WHERE nivel='cliente'", conn)
        st.dataframe(users)
        id_liberar = st.number_input("ID do Usuário para Ativar", step=1)
        if st.button("✅ Liberar Acesso"):
            conn.execute("UPDATE usuarios SET status='Ativo' WHERE id=?", (id_liberar,))
            conn.commit()
            st.success("Licença ativada!")

    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.rerun()
