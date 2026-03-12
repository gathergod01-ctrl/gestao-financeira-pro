import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime, date, timedelta

# --- CONFIGURAÇÃO DA CONEXÃO (COLE SUA URI AQUI) ---
# Substitua 'SUA_SENHA_AQUI' pela senha que você criou no Supabase
DB_URI = "postgresql://postgres:[@H2obeta77@]@db.xtrgfoiyqppqtocuwbqi.supabase.co:5432/postgres"

# Criamos o "motor" de conexão
engine = create_engine(DB_URI)

def query_db(sql, params=None, commit=False):
    with engine.connect() as conn:
        result = conn.execute(text(sql), params or {})
        if commit:
            conn.commit()
        if result.returns_rows:
            return result.fetchall()
        return None

# A partir daqui, o restante do seu código (DRE, Lançamentos, etc) 
# funcionará usando a função query_db em vez de conn.execute.

conn = init_db()

# --- ESTILIZAÇÃO ---
st.markdown("""
    <style>
    .main-header { color: #1a237e; font-weight: bold; border-bottom: 2px solid #1a237e; padding-bottom: 10px; margin-bottom: 20px; }
    .card-resumo { background-color: #ffffff; padding: 20px; border-radius: 10px; box-shadow: 2px 2px 10px rgba(0,0,0,0.1); border-top: 5px solid #1a237e; }
    .vencimento-alerta { color: #d32f2f; font-weight: bold; background-color: #ffebee; padding: 10px; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- LOGIN / SESSÃO ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.markdown("<h1 style='text-align: center; color: #1a237e;'>📊 Gestão Financeira Gabriel</h1>", unsafe_allow_html=True)
    tab_login, tab_cad = st.tabs(["🔐 Acessar", "📝 Criar Conta"])
    with tab_login:
        e_l, s_l = st.text_input("E-mail", key="l_email"), st.text_input("Senha", type="password", key="l_senha")
        if st.button("Entrar"):
            user = conn.execute("SELECT id, nome, status, nivel FROM usuarios WHERE email=? AND senha=?", (e_l, s_l)).fetchone()
            if user and user[2] == 'Ativo':
                st.session_state.update({"logado": True, "user_id": user[0], "user_nome": user[1], "user_nivel": user[3]})
                st.rerun()
            elif user: st.warning("⚠️ Licença pendente.")
            else: st.error("Login inválido.")
    with tab_cad:
        cn, ct, cd, ce, cs = st.text_input("Nome/Razão"), st.radio("Tipo", ["PF", "PJ"]), st.text_input("Doc"), st.text_input("E-mail"), st.text_input("Senha", type="password")
        if st.button("Solicitar"):
            stus, nvl = ("Ativo", "admin") if ce == "gathergod01@gmail.com" else ("Pendente", "cliente")
            try:
                conn.execute("INSERT INTO usuarios (nome, email, senha, status, nivel, tipo_pessoa, documento) VALUES (?,?,?,?,?,?,?)", (cn, ce, cs, stus, nvl, ct, cd))
                conn.commit(); st.success("Enviado!")
            except: st.error("E-mail já existe.")

else:
    st.sidebar.title(f"Olá, {st.session_state.user_nome}")
    menu = st.sidebar.radio("Navegação", ["Configurações", "Lançamentos", "Despesas Recorrentes", "DRE / Dashboard", "👑 Admin" if st.session_state.user_nivel == 'admin' else None])

    # --- TELA: CONFIGURAÇÕES / LANÇAMENTOS / RECORRENTES (RESUMIDAS PARA FOCO NA DRE) ---
    if menu == "Configurações":
        st.markdown("<h1 class='main-header'>⚙️ Configurações</h1>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            n, t = st.text_input("Nome"), st.selectbox("Tipo", ["Receita", "Despesa", "Banco/Caixa"])
            if st.button("Salvar"):
                conn.execute("INSERT INTO categorias (user_id, nome, tipo) VALUES (?,?,?)", (st.session_state.user_id, n, 'R' if t=="Receita" else 'D' if t=="Despesa" else 'B'))
                conn.commit(); st.rerun()
        with c2:
            df_c = pd.read_sql(f"SELECT id, nome, tipo FROM categorias WHERE user_id={st.session_state.user_id}", conn)
            st.dataframe(df_c, use_container_width=True)
            id_del = st.number_input("ID remover", step=1)
            if st.button("Remover"):
                conn.execute("DELETE FROM categorias WHERE id=? AND user_id=?", (id_del, st.session_state.user_id))
                conn.commit(); st.rerun()

    elif menu == "Despesas Recorrentes":
        st.markdown("<h1 class='main-header'>🔄 Contas Recorrentes</h1>", unsafe_allow_html=True)
        desps = [r[0] for r in conn.execute("SELECT nome FROM categorias WHERE user_id=? AND tipo='D'", (st.session_state.user_id,)).fetchall()]
        with st.form("rec"):
            c1, c2 = st.columns(2)
            desc, dia = c1.text_input("Descrição"), c2.number_input("Dia Vencimento", 1, 31)
            val, cat = c1.number_input("Valor"), c2.selectbox("Categoria", desps)
            if st.form_submit_button("Cadastrar"):
                conn.execute("INSERT INTO recorrencias (user_id, dia_vencimento, categoria, valor, descricao) VALUES (?,?,?,?,?)", (st.session_state.user_id, dia, cat, val, desc))
                conn.commit(); st.rerun()
        st.dataframe(pd.read_sql(f"SELECT * FROM recorrencias WHERE user_id={st.session_state.user_id}", conn))

    elif menu == "Lançamentos":
        st.markdown("<h1 class='main-header'>📝 Lançamentos</h1>", unsafe_allow_html=True)
        # Lógica de inserção (Mesma da v12)
        banks = [r[0] for r in conn.execute("SELECT nome FROM categorias WHERE user_id=? AND tipo='B'", (st.session_state.user_id,)).fetchall()]
        recs = [r[0] for r in conn.execute("SELECT nome FROM categorias WHERE user_id=? AND tipo='R'", (st.session_state.user_id,)).fetchall()]
        desps = [r[0] for r in conn.execute("SELECT nome FROM categorias WHERE user_id=? AND tipo='D'", (st.session_state.user_id,)).fetchall()]
        
        t1, t2 = st.tabs(["Lançar", "Histórico/Excluir"])
        with t1:
            tp = st.radio("Tipo", ["Comum", "Transferência"], horizontal=True)
            if tp == "Comum":
                c1, c2, c3 = st.columns(3)
                dt, tl, bl = c1.date_input("Data"), c2.selectbox("Fluxo", ["Receita", "Despesa"]), c3.selectbox("Banco", banks)
                cl = st.selectbox("Categoria", recs if tl=="Receita" else desps)
                vl, hl = st.number_input("Valor"), st.text_input("Histórico")
                if st.button("Salvar"):
                    conn.execute("INSERT INTO lancamentos (user_id, data, tipo, categoria, conta, valor, hist) VALUES (?,?,?,?,?,?,?)", (st.session_state.user_id, str(dt), tl, cl, bl, vl, hl))
                    conn.commit(); st.rerun()
            else:
                c1, c2, c3 = st.columns(3)
                dt, ori, dest = c1.date_input("Data"), c2.selectbox("De", banks), c3.selectbox("Para", banks)
                vt = st.number_input("Valor Transf.")
                if st.button("Transferir"):
                    conn.execute("INSERT INTO lancamentos (user_id, data, tipo, categoria, conta, valor, hist) VALUES (?,?,'Despesa','Transferência Interna',?,?,?)", (st.session_state.user_id, str(dt), ori, vt, f"Para {dest}"))
                    conn.execute("INSERT INTO lancamentos (user_id, data, tipo, categoria, conta, valor, hist) VALUES (?,?,'Receita','Transferência Interna',?,?,?)", (st.session_state.user_id, str(dt), dest, vt, f"De {ori}"))
                    conn.commit(); st.rerun()
        with t2:
            df_h = pd.read_sql(f"SELECT * FROM lancamentos WHERE user_id={st.session_state.user_id} ORDER BY id DESC", conn)
            st.dataframe(df_h); st.download_button("Exportar CSV", df_h.to_csv(index=False).encode('utf-8'), "financeiro.csv")
            id_del = st.number_input("ID para excluir", step=1)
            if st.button("Confirmar Exclusão"):
                conn.execute("DELETE FROM lancamentos WHERE id=?", (id_del,)); conn.commit(); st.rerun()

    # --- TELA: DRE / DASHBOARD (MELHORADA) ---
    elif menu == "DRE / Dashboard":
        st.markdown("<h1 class='main-header'>📊 Inteligência Financeira</h1>", unsafe_allow_html=True)
        
        # 1. FILTROS E SALDO INICIAL
        col_f1, col_f2, col_f3 = st.columns([2, 2, 2])
        dt_i = col_f1.date_input("Data Início", value=date(date.today().year, date.today().month, 1))
        dt_f = col_f2.date_input("Data Fim", value=date.today())
        
        # Cálculo de Saldo Inicial (Tudo antes de dt_i)
        df_prev = pd.read_sql(f"SELECT tipo, valor, conta FROM lancamentos WHERE user_id={st.session_state.user_id} AND data < '{dt_i}'", conn)
        saldo_inicial_total = df_prev[df_prev['tipo']=='Receita']['valor'].sum() - df_prev[df_prev['tipo']=='Despesa']['valor'].sum()
        col_f3.metric("Saldo Inicial (Até esta data)", f"R$ {saldo_inicial_total:,.2f}")

        # 2. RESULTADO OPERACIONAL (DRE)
        df_periodo = pd.read_sql(f"SELECT * FROM lancamentos WHERE user_id={st.session_state.user_id} AND data >= '{dt_i}' AND data <= '{dt_f}'", conn)
        df_dre = df_periodo[df_periodo['categoria'] != 'Transferência Interna']
        
        rec_real = df_dre[df_dre['tipo'] == 'Receita']['valor'].sum()
        des_real = df_dre[df_dre['tipo'] == 'Despesa']['valor'].sum()
        
        c_m1, c_m2, c_m3 = st.columns(3)
        with c_m1: st.markdown(f"<div class='card-resumo'>🟢 RECEITA REAL<br><h3>R$ {rec_real:,.2f}</h3></div>", unsafe_allow_html=True)
        with c_m2: st.markdown(f"<div class='card-resumo'>🔴 DESPESA REAL<br><h3>R$ {des_real:,.2f}</h3></div>", unsafe_allow_html=True)
        with c_m3: st.markdown(f"<div class='card-resumo'>💎 LUCRO LÍQUIDO<br><h3>R$ {rec_real - des_real:,.2f}</h3></div>", unsafe_allow_html=True)

        st.markdown("### 📈 Análise de Categorias")
        if not df_dre.empty:
            st.bar_chart(df_dre.groupby('categoria')['valor'].sum())

        st.markdown("---")

        # 3. CONTAS A VENCER (NOTIFICAÇÃO)
        st.markdown("### 📅 Contas a Vencer nos Próximos Dias")
        dias_venc = st.slider("Ver vencimentos nos próximos (dias):", 1, 30, 7)
        hoje = date.today()
        futuro = hoje + timedelta(days=dias_venc)
        
        recorrentes = conn.execute("SELECT descricao, valor, dia_vencimento FROM recorrencias WHERE user_id=?", (st.session_state.user_id,)).fetchall()
        venc_list = []
        total_a_vencer = 0
        for r in recorrentes:
            # Lógica para descobrir se o dia cai no intervalo
            if hoje.day <= r[2] <= futuro.day or (futuro.month > hoje.month and r[2] <= futuro.day):
                venc_list.append({"Descrição": r[0], "Valor": r[1], "Dia": r[2]})
                total_a_vencer += r[1]
        
        if venc_list:
            st.warning(f"Montante Total a Vencer: R$ {total_a_vencer:,.2f}")
            st.table(pd.DataFrame(venc_list))
        else: st.success("Nenhuma conta recorrente vencendo no período selecionado.")

        st.markdown("---")

        # 4. FLUXO DE CAIXA DIÁRIO ACUMULADO
        
        st.markdown("### 🌊 Fluxo de Caixa Diário Acumulado")
        banks_list = [r[0] for r in conn.execute("SELECT nome FROM categorias WHERE user_id=? AND tipo='B'", (st.session_state.user_id,)).fetchall()]
        b_caixa = st.selectbox("Selecione a Conta para ver o Fluxo Diário:", banks_list)
        
        if b_caixa:
            # Saldo inicial específico da conta
            saldo_ant_banco = df_prev[df_prev['conta']==b_caixa][df_prev['tipo']=='Receita']['valor'].sum() - \
                              df_prev[df_prev['conta']==b_caixa][df_prev['tipo']=='Despesa']['valor'].sum()
            
            df_b = df_periodo[df_periodo['conta'] == b_caixa].copy()
            df_b['data'] = pd.to_datetime(df_b['data'])
            
            # Agrupar por dia
            diario = df_b.groupby(df_b['data'].dt.date).apply(lambda x: pd.Series({
                'Entradas': x[x['tipo']=='Receita']['valor'].sum(),
                'Saídas': x[x['tipo']=='Despesa']['valor'].sum(),
                'Saldo do Dia': x[x['tipo']=='Receita']['valor'].sum() - x[x['tipo']=='Despesa']['valor'].sum()
            })).reset_index()
            
            diario = diario.sort_values('data')
            diario['Saldo Acumulado'] = diario['Saldo do Dia'].cumsum() + saldo_ant_banco
            
            st.write(f"Saldo Inicial da conta em {dt_i}: **R$ {saldo_ant_banco:,.2f}**")
            st.dataframe(diario, use_container_width=True)
            st.line_chart(diario.set_index('data')['Saldo Acumulado'])

    elif menu == "👑 Admin":
        st.markdown("<h1>Painel Admin</h1>", unsafe_allow_html=True)
        u = pd.read_sql("SELECT id, nome, documento, status FROM usuarios", conn)
        st.table(u)
        id_a = st.number_input("Ativar ID", step=1)
        if st.button("Ativar"): conn.execute("UPDATE usuarios SET status='Ativo' WHERE id=?", (id_a,)); conn.commit(); st.rerun()

    if st.sidebar.button("🚪 Sair"): st.session_state.clear(); st.rerun()
