// Login com Google. O navegador só recebe o ID token e o entrega ao servidor, que valida
// assinatura, validade e e-mail institucional e cria a sessão em cookie httpOnly.
// Nada de sessão ou token fica no localStorage.

let usuarioAtual = null;

window.addEventListener("load", async function () {
    usuarioAtual = await buscarUsuarioDaSessao();
    renderizarEstadoLogin();

    if (usuarioAtual) {
        monstrarInformacoesUsuario(usuarioAtual);
    } else {
        iniciarGoogle();
    }
});

continuarInformacoesUsuario.addEventListener("click", function () {
    if (!usuarioAtual || this.disabled) return;
    this.disabled = true; // evitar clique duplo
    window.location.replace("./mapa.html");
});

async function buscarUsuarioDaSessao() {
    try {
        const resposta = await fetch("/api/me");
        if (!resposta.ok) return null;
        return (await resposta.json()).usuario;
    } catch (err) {
        console.error("Falha ao consultar a sessão:", err);
        return null;
    }
}

async function iniciarGoogle() {
    let clientId = "";
    try {
        clientId = (await (await fetch("/auth/config")).json()).clientId;
    } catch (err) {
        console.error("Falha ao ler a configuração de login:", err);
    }
    if (!clientId) {
        informeLogin.textContent = "Login indisponível: o servidor está sem GOOGLE_CLIENT_ID configurado.";
        return;
    }

    google.accounts.id.initialize({
        client_id: clientId,
        callback: handleCredentialResponse,
        context: "signin",
        ux_mode: "popup",
        auto_select: false,
    });

    google.accounts.id.renderButton(
        document.getElementById("botao-google"),
        {
            type: "standard",
            shape: "pill",
            theme: "filled_blue",
            text: "signin_with",
            size: "large",
            locale: "pt-BR",
            logo_alignment: "left",
            width: "300px"
        }
    );
}

async function handleCredentialResponse(response) {
    let resposta;
    try {
        resposta = await fetch("/auth/google", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ credential: response.credential }),
        });
    } catch (err) {
        informeLogin.textContent = "Sem conexão com o servidor. Tente novamente.";
        return;
    }

    if (resposta.status === 403) {
        informeLogin.textContent = "Esse e-mail não tem acesso. Use o e-mail institucional do Instituto Ponte.";
        return;
    }
    if (!resposta.ok) {
        informeLogin.textContent = "Não foi possível entrar. Tente novamente.";
        return;
    }

    usuarioAtual = (await resposta.json()).usuario;
    monstrarInformacoesUsuario(usuarioAtual);
    renderizarEstadoLogin();
}

function monstrarInformacoesUsuario(usuario) {
    usuarioID.textContent = usuario.id;
    usuarioNome.textContent = usuario.nome;
    usuarioNomeHeader.textContent = usuario.nome;
    usuarioSobrenome.textContent = usuario.sobrenome;
    usuarioNomeCompleto.textContent = usuario.nomeCompleto;
    usuarioEmail.textContent = usuario.email;
    usuarioEmailVerificado.textContent = "sim"; // o servidor só cria sessão com e-mail verificado
    usuarioComecoSessao.textContent = new Date(usuario.inicio).toLocaleString("pt-BR");
    usuarioVencimentoSessao.textContent = new Date(usuario.expira).toLocaleString("pt-BR");
    if (usuario.fotoPerfil) {
        usuarioFotoPerfil.setAttribute("src", usuario.fotoPerfil);
        usuarioFotoPerfilHeader.setAttribute("src", usuario.fotoPerfil);
    }
}

function renderizarEstadoLogin() {
    if (usuarioAtual) {
        opcaoFazerLogin.hidden = true;
        opcaoContinuar.hidden = false;
        informeLogin.textContent = "Encontramos seu login, clique continuar se estiver correto.";
    }
    else {
        opcaoFazerLogin.hidden = false;
        opcaoContinuar.hidden = true;
        informeLogin.textContent = "Faça o login pelo Google:";
    }
}
