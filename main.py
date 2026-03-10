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
    conn = sqlite3.connect('financeiro_v7.db', check_same_thread=False)
    cursor = conn.cursor()
    # Tabela de usuários com campos de documento e nível
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

# --- FUNÇÃO DE NOTIFICAÇÃO AUTOMÁTICA ---
def enviar_notificacao_admin(nome, email_user, documento):
    email_remetente = "gathergod01@gmail.com"
    senha_app = "epfvedqblmbxecyb" # Sua senha de 16 dígitos configurada
    
    msg = MIMEMultipart()
    msg['From'] = email_remetente
    msg['To'] = email_remetente
    msg['Subject'] = f"🔔 Nova Solicitação de Licença: {nome}"
    
    corpo = f"""
    Olá Gabriel,
    
    Um novo usuário solicitou acesso ao seu sistema:
    
    👤 Nome: {nome}
    📧 E-mail: {email_user}
    🆔 Documento: {documento}
    
    Acesse o Painel Admin com sua senha para liberar a licença.
    """
    msg.attach(MIMEText(corpo, 'plain'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(email_remetente, senha_app)
        server.sendmail(email_remetente, email_remetente, msg.as_string())
        server.quit()
        return True
    except:
        return False

# --- ESTILIZAÇÃO ---
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; background-color: #1a237e; color: white; height: 3em; font-weight: bold; }
    .main-header { color: #1a237e; font-weight: bold; border-bottom: 2px solid #1a237e; padding-bottom: 10px; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- FLUXO DE ACESSO ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.markdown("<h1 style='text-align: center; color: #1a237e;'>📊 Gestão Financeira Gabriel</h1>", unsafe_allow_html=True)
    tab_login, tab_cad = st.tabs(["🔐 Acessar Minha Conta", "📝 Criar Nova Conta"])
    
    with tab_login:
        email_l = st.text_input("E-mail", key="l_email")
        senha_l = st.text_input("Senha", type="password", key="l_senha")
        if st.button("Entrar no Sistema", key="btn_l"):
            user = conn.execute("SELECT id, nome, status, nivel FROM usuarios WHERE email=? AND senha=?", (email_l, senha_l)).fetchone()
            if user:
                if user[2] == 'Ativo':
                    st.session_state.logado = True
                    st.session_state.user_id = user[0]
                    st.session_state.user_nome = user[1]
                    st.session_state.user_nivel = user[3]
                    st.rerun()
                else: st.warning("⚠️ Sua licença está pendente. Gabriel já foi notificado para sua liberação.")
            else: st.error("E-mail ou senha incorretos.")

    with tab_cad:
        c_nome = st.text_input("Nome Completo / Razão Social", key="c_nome")
        c_tipo = st.radio("Tipo de Cadastro", ["Pessoa Física (CPF)", "Pessoa Jurídica (CNPJ)"], horizontal=True, key="c_tipo")
        c_doc = st.text_input("CPF ou CNPJ", key="c_doc")
        c_email = st.text_input("E-mail para Acesso", key="c_email")
        c_senha = st.text_input("Crie uma Senha", type="password", key="c_senha")
        
        if st.button("Enviar Solicitação de Acesso", key="btn_c"):
            if not c_nome or not c_doc or not c_email:
                st.error("Preencha todos os campos obrigatórios.")
            else:
                # Se for o e-mail do Gabriel, já nasce Ativo e Admin
                is_admin = (c_email == "gathergod01@gmail.com")
                status = 'Ativo' if is_admin else 'Pendente'
                nivel = 'admin' if is_admin else 'cliente'
                
                try:
                    conn.execute("INSERT INTO usuarios (nome, email, senha, status, nivel, tipo_pessoa, documento) VALUES (?,?,?,?,?,?,?)", 
                                 (c_nome, c_email, c_senha, status, nivel, c_tipo, c_doc))
                    conn.commit()
                    if not is_admin:
                        enviar_notificacao_admin(c_nome, c_email, c_doc)
                    st.success("✅ Solicitação enviada! Aguarde a liberação do seu acesso.")
                except: st.error("Este e-mail já possui um cadastro pendente ou ativo.")

else:
    # --- INTERFACE LOGADA ---
    st.sidebar.markdown(f"### Olá, **{st.session_state.user_nome}**")
    st.sidebar.write(f"Nível: {st.session_state.user_nivel.upper()}")
    
    menu_options = ["Configurações", "Lançamentos", "Relatórios (DRE)"]
    if st.session_state.user_nivel == 'admin':
        menu_options.append("👑 Painel Administrativo")
    
    menu = st.sidebar.radio("Selecione a tela:", menu_options)

    # --- TELA: CONFIGURAÇÕES ---
    if menu == "Configurações":
        st.markdown("<h1 class='main-header'>⚙️ Configurações de Conta</h1>", unsafe_allow_html=True)
        col_cad, col_ger = st.columns(2)
        with col_cad:
            st.subheader("➕ Nova Categoria ou Banco")
            n_cat = st.text_input("Nome (Ex: Bradesco, Vendas, Energia)")
            t_cat = st.selectbox("Tipo", ["Receita", "Despesa", "Banco/Caixa"])
            if st.button("Salvar Item"):
                code = 'R' if t_cat == "Receita" else 'D' if t_cat == "Despesa" else 'B'
                conn.execute("INSERT INTO categorias (user_id, nome, tipo) VALUES (?,?,?)", (st.session_state.user_id, n_cat, code))
                conn.commit()
                st.success(f"{n_cat} adicionado!")
        with col_ger:
            st.subheader("🗑️ Excluir Itens")
            items = [r[0] for r in conn.execute("SELECT nome FROM categorias WHERE user_id=?", (st.session_state.user_id,)).fetchall()]
            item_del = st.selectbox("Selecione para remover", [""] + items)
            if st.button("Excluir Permanente") and item_del != "":
                conn.execute("DELETE FROM categorias WHERE user_id=? AND nome=?", (st.session_state.user_id, item_del))
                conn.commit()
                st.rerun()

    # --- TELA: LANÇAMENTOS ---
    elif menu == "Lançamentos":
        st.markdown("<h1 class='main-header'>📝 Livro Diário de Lançamentos</h1>", unsafe_allow_html=True)
        recs = [r[0] for r in conn.execute("SELECT nome FROM categorias WHERE user_id=? AND tipo='R'", (st.session_state.user_id,)).fetchall()]
        desps = [r[0] for r in conn.execute("SELECT nome FROM categorias WHERE user_id=? AND tipo='D'", (st.session_state.user_id,)).fetchall()]
        banks = [r[0] for r in conn.execute("SELECT nome FROM categorias WHERE user_id=? AND tipo='B'", (st.session_state.user_id,)).fetchall()]

        if not banks:
            st.warning("⚠️ Cadastre uma conta (Banco/Caixa) em 'Configurações' antes de lançar.")
        else:
            with st.form("form_novo"):
                c1, c2, c3 = st.columns(3)
                data_l = c1.date_input("Data", value=date.today())
                tipo_l = c2.selectbox("Tipo Movimentação", ["Receita", "Despesa"])
                banco_l = c3.selectbox("Origem/Destino", banks)
                cat_l = st.selectbox("Categoria", recs if tipo_l == "Receita" else desps)
                valor_l = st.number_input("Valor R$", min_value=0.0, step=0.01)
                hist_l = st.text_input("Descrição")
                if st.form_submit_button("Confirmar Registro"):
                    conn.execute("INSERT INTO lancamentos (user_id, data, tipo, categoria, conta, valor, hist) VALUES (?,?,?,?,?,?,?)",
                                 (st.session_state.user_id, str(data_l), tipo_l, cat_l, banco_l, valor_l, hist_l))
                    conn.commit()
                    st.success("Registrado com sucesso!")
            
            st.markdown("---")
            df_hist = pd.read_sql(f"SELECT id, data, tipo, categoria, valor, conta, hist FROM lancamentos WHERE user_id={st.session_state.user_id} ORDER BY id DESC", conn)
            st.dataframe(df_hist, use_container_width=True)

    # --- TELA: DRE ---
    elif menu == "Relatórios (DRE)":
        st.markdown("<h1 class='main-header'>📊 Demonstrativo de Resultados</h1>", unsafe_allow_html=True)
        df_dre = pd.read_sql(f"SELECT data, tipo, valor FROM lancamentos WHERE user_id={st.session_state.user_id}", conn)
        if not df_dre.empty:
            r_t = df_dre[df_dre['tipo'] == 'Receita']['valor'].sum()
            d_t = df_dre[df_dre['tipo'] == 'Despesa']['valor'].sum()
            st.metric("Resultado Final", f"R$ {r_t - d_t:,.2f}", delta=f"Total Receitas: R$ {r_t:,.2f}")
            st.bar_chart(df_dre.groupby('tipo')['valor'].sum())

    # --- TELA: ADMIN ---
    elif menu == "👑 Painel Administrativo":
        st.markdown("<h1 class='main-header'>👑 Gestão de Clientes</h1>", unsafe_allow_html=True)
        clis = pd.read_sql("SELECT id, nome, documento, email, status FROM usuarios WHERE nivel='cliente'", conn)
        st.dataframe(clis, use_container_width=True)
        id_atv = st.number_input("ID do Cliente para Liberar", step=1, value=0)
        if st.button("✅ Ativar Licença Agora"):
            conn.execute("UPDATE usuarios SET status='Ativo' WHERE id=?", (id_atv,))
            conn.commit()
            st.success(f"Cliente {id_atv} liberado com sucesso!")
            st.rerun()

    if st.sidebar.button("🚪 Sair com Segurança"):
        st.session_state.clear()
        st.rerun()
