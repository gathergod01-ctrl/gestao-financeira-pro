import streamlit as st
import pandas as pd
from supabase import create_client, Client

# --- CONFIGURAÇÕES ---
st.set_page_config(page_title="Gestão Financeira Gabriel", layout="wide")

# --- CONEXÃO API SUPABASE ---
# Lembre-se de manter sua URL e colocar a Key Anon Public correta aqui
URL_SVP = "https://xtrgfoiyqppqtocuwbqi.supabase.co"
KEY_SVP = "COLE_AQUI_SUA_CHAVE_ANON_PUBLIC"
supabase: Client = create_client(URL_SVP, KEY_SVP)

if 'logado' not in st.session_state:
    st.session_state.logado = False

# --- FLUXO DE ACESSO ---
if not st.session_state.logado:
    st.markdown("<h1 style='text-align: center; color: #1a237e;'>📊 Financeiro Pro</h1>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["🔐 Entrar", "📝 Solicitar Acesso"])
    
    with t1:
        e = st.text_input("E-mail")
        s = st.text_input("Senha", type="password")
        if st.button("Acessar Sistema"):
            try:
                # Busca usuário
                res = supabase.table("usuarios").select("*").eq("email", e).eq("senha", s).execute()
                if res.data:
                    u = res.data[0]
                    # O admin gathergod01 sempre entra, outros dependem do status
                    if u.get('status') == 'Ativo' or e == "gathergod01@gmail.com":
                        st.session_state.update({
                            "logado": True, 
                            "user_id": u['id'], 
                            "user_nome": u['nome'], 
                            "user_nivel": u.get('nivel', 'cliente')
                        })
                        st.rerun()
                    else:
                        st.warning("Aguarde a ativação da sua conta pelo administrador.")
                else:
                    st.error("Login ou senha incorretos.")
            except Exception as ex:
                st.error(f"Erro técnico: {ex}")

    with t2:
        st.subheader("Cadastro de Novo Usuário")
        cn = st.text_input("Nome Completo")
        ce = st.text_input("E-mail Comercial")
        cs = st.text_input("Senha de Acesso", type="password")
        if st.button("Cadastrar"):
            # Se for seu e-mail, já entra como Ativo e Admin
            stus = "Ativo" if ce == "gathergod01@gmail.com" else "Pendente"
            nvl = "admin" if ce == "gathergod01@gmail.com" else "cliente"
            novo_u = {"nome": cn, "email": ce, "senha": cs, "status": stus, "nivel": nvl}
            try:
                supabase.table("usuarios").insert(novo_u).execute()
                st.success("Cadastro realizado! Se você é o admin, já pode logar.")
            except:
                st.error("Erro: E-mail já cadastrado ou falha na rede.")

else:
    # --- INTERFACE LOGADA ---
    st.sidebar.title(f"Olá, {st.session_state.user_nome}")
    
    # Menu lateral
    menu = st.sidebar.radio("Navegação", ["Dashboard", "Lançamentos", "👑 Admin" if st.session_state.user_nivel == 'admin' else "Sair"])

    if menu == "Dashboard":
        st.header("📊 Resumo Financeiro")
        try:
            # Puxa lançamentos do usuário logado
            res_l = supabase.table("lancamentos").select("*").eq("user_id", st.session_state.user_id).execute()
            if res_l.data:
                df = pd.DataFrame(res_l.data)
                df['valor'] = df['valor'].astype(float)
                rec = df[df['tipo'] == 'Receita']['valor'].sum()
                des = df[df['tipo'] == 'Despesa']['valor'].sum()
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Receitas", f"R$ {rec:,.2f}")
                c2.metric("Despesas", f"R$ {des:,.2f}")
                c3.metric("Saldo", f"R$ {rec-des:,.2f}")
                st.divider()
                st.subheader("Histórico Recente")
                st.dataframe(df[['data', 'tipo', 'categoria', 'valor']].sort_values(by='data', ascending=False))
            else:
                st.info("Você ainda não possui lançamentos cadastrados.")
        except:
            st.error("Erro ao carregar dados. Verifique se a tabela 'lancamentos' tem a coluna 'valor'.")

    if st.sidebar.button("🚪 Sair"):
        st.session_state.logado = False
        st.rerun()
