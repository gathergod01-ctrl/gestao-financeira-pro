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
    conn = sqlite3.connect('financeiro_v9.db', check_same_thread=False)
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
                # CAMPOS FORA DO FORM PARA REATIVIDADE INSTANTÂNEA
                c1, c2, c3 = st.columns(3)
                d_l = c1.date_input("Data")
                t_l = c2.selectbox("Tipo", ["Receita", "Despesa"], key="tipo_lan")
                b_l = c3.selectbox("Conta", banks)
                
                # A categoria agora atualiza na hora baseada no t_l
                lista_filtro = recs if t_l == "Receita" else desps
                cat_l = st.selectbox("Categoria", lista_filtro if lista_filtro else ["Nenhuma cadastrada"])
                
                v_l = st.number_input("Valor R$", min_value=0.0, step=0.01)
                h_l = st.text_input("Histórico / Detalhes")
                
                if st.button("Confirmar Lançamento"):
                    if not banks or not lista_filtro:
                        st.error("Cadastre conta e categoria primeiro!")
                    else:
                        conn.execute("INSERT INTO lancamentos (user_id, data, tipo, categoria, conta, valor, hist) VALUES (?,?,?,?,?,?,?)", 
                                     (st.session_state.user_id, str(d_l), t_l, cat_l, b_l, v_l, h_l))
                        conn.commit()
                        st.success("Lançamento efetuado!")
                        st.rerun()
            else:
                c1, c2, c3 = st.columns(3)
                d_t = c1.date_input("Data")
                origem = c2.selectbox("Saiu de (Origem)", banks)
                destino = c3.selectbox("Entrou em (Destino)", banks)
                v_t = st.number_input("Valor da Transferência", min_value=0.0, step=0.01)
                if st.button("Efetuar Transferência"):
                    if origem == destino: st.error("As contas de origem e destino não podem ser iguais.")
                    else:
                        conn.execute("INSERT INTO lancamentos (user_id, data, tipo, categoria, conta, valor, hist) VALUES (?,?,'Despesa','Transferência Saída',?,?,?)", (st.session_state.user_id, str(d_t), origem, v_t, f"Para {destino}"))
                        conn.execute("INSERT INTO lancamentos (user_id, data, tipo, categoria, conta, valor, hist) VALUES (?,?,'Receita','Transferência Entrada',?,?,?)", (st.session_state.user_id, str(d_t), destino, v_t, f"De {origem}"))
                        conn.commit()
                        st.success("Transferência realizada com sucesso!")
                        st.rerun()

        with tab_edit:
            df_hist = pd.read_sql(f"SELECT * FROM lancamentos WHERE user_id={st.session_state.user_id} ORDER BY id DESC", conn)
            st.dataframe(df_hist, use_container_width=True)
            
            st.markdown("---")
            col_e1, col_e2 = st.columns(2)
            id_acao = col_e1.number_input("ID do Lançamento para Alterar", step=1, value=0)
            acao = col_e2.selectbox("Ação Desejada", ["---", "Excluir Registro", "Editar Informações"])
            
            if acao == "Editar Informações" and id_acao > 0:
                item = conn.execute("SELECT * FROM lancamentos WHERE id=? AND user_id=?", (id_acao, st.session_state.user_id)).fetchone()
                if item:
                    with st.expander("📝 Formulário de Edição", expanded=True):
                        new_val = st.number_input("Novo Valor", value=item[6])
                        new_hist = st.text_input("Novo Histórico", value=item[7])
                        if st.button("Salvar Alterações"):
                            conn.execute("UPDATE lancamentos SET valor=?, hist=? WHERE id=?", (new_val, new_hist, id_acao))
                            conn.commit()
                            st.success("Alterado!")
                            st.rerun()
            elif acao == "Excluir Registro" and id_acao > 0:
                if st.button("⚠️ Confirmar Exclusão Permanente"):
                    conn.execute("DELETE FROM lancamentos WHERE id=? AND user_id=?", (id_acao, st.session_state.user_id))
                    conn.commit()
                    st.warning(f"Lançamento {id_acao} removido.")
                    st.rerun()

    # --- TELA: DRE ---
    elif menu == "DRE/Relatórios":
        st.markdown("<h1 class='main-header'>📊 Filtros e Resultados</h1>", unsafe_allow_html=True)
        banks_f = ["Todos"] + [r[0] for r in conn.execute("SELECT nome FROM categorias WHERE user_id=? AND tipo='B'", (st.session_state.user_id,)).fetchall()]
        
        c1, c2, c3 = st.columns(3)
        dt_ini = c1.date_input("Início", value=date(date.today().year, date.today().month, 1))
        dt_fim = c2.date_input("Fim", value=date.today())
        banco_sel = c3.selectbox("Filtrar por Banco/Conta", banks_f)
        
        df_r = pd.read_sql(f"SELECT * FROM lancamentos WHERE user_id={st.session_state.user_id}", conn)
        if not df_r.empty:
            df_r['data'] = pd.to_datetime(df_r['data']).dt.date
            filtro = (df_r['data'] >= dt_ini) & (df_r['data'] <= dt_fim)
            if banco_sel != "Todos":
                filtro = filtro & (df_r['conta'] == banco_sel)
            
            df_final = df_r[filtro]
            r_t = df_final[df_final['tipo'] == 'Receita']['valor'].sum()
            d_t = df_final[df_final['tipo'] == 'Despesa']['valor'].sum()
            
            st.columns(3)[0].metric("Receitas", f"R$ {r_t:,.2f}")
            st.columns(3)[1].metric("Despesas", f"R$ {d_t:,.2f}")
            st.columns(3)[2].metric("Saldo", f"R$ {r_t - d_t:,.2f}")
            
            st.dataframe(df_final, use_container_width=True)
            st.bar_chart(df_final.groupby('categoria')['valor'].sum())

    elif menu == "👑 Admin":
        st.markdown("<h1 class='main-header'>Painel de Licenças</h1>", unsafe_allow_html=True)
        users = pd.read_sql("SELECT id, nome, documento, email, status FROM usuarios", conn)
        st.table(users)
        id_atv = st.number_input("Ativar Usuário (ID)", step=1)
        if st.button("Liberar Acesso"):
            conn.execute("UPDATE usuarios SET status='Ativo' WHERE id=?", (id_atv,))
            conn.commit()
            st.rerun()

    if st.sidebar.button("🚪 Sair"):
        st.session_state.clear()
        st.rerun()
