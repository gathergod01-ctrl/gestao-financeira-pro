if not st.session_state.logado:
    tab1, tab2 = st.tabs(["🔐 Login", "📝 Solicitar Acesso"])
    with tab1:
        # Adicionado key="login_email" e key="login_senha"
        email = st.text_input("E-mail", key="login_email")
        senha = st.text_input("Senha", type="password", key="login_senha")
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
        # Adicionado key="cad_nome", key="cad_email" e key="cad_senha"
        novo_nome = st.text_input("Nome Completo", key="cad_nome")
        novo_email = st.text_input("E-mail", key="cad_email")
        nova_senha = st.text_input("Senha", type="password", key="cad_senha")
        if st.button("Solicitar Licença"):
            status = 'Ativo' if novo_email == 'gathergod01@gmail.com' else 'Pendente'
            nivel = 'admin' if novo_email == 'gathergod01@gmail.com' else 'cliente'
            try:
                conn.execute("INSERT INTO usuarios (nome, email, senha, status, nivel) VALUES (?,?,?,?,?)", (novo_nome, novo_email, nova_senha, status, nivel))
                conn.commit()
                st.success("Solicitação enviada!")
            except: st.error("Este e-mail já está cadastrado.")
