

let usuarioAtual = null;


//localStorage.setItem(Usuario.STORAGE_KEY, JSON.stringify({"id":"67","nome":"Em","sobrenome":"An Uel","nomeCompleto":"Em An Uel","email":"emanuel@aluno.institutoponte.org.br","fotoPerfil":"https://i.imgflip.com/2l2ri4.jpg","emailVerificado":true,"comecoSessao":"2026-10-25T15:53:53.000Z","vencimentoSessao":"2026-10-25T16:53:53.000Z"}));

window.addEventListener("load", function () {

    usuarioAtual = Usuario.carregar();

    renderizarEstadoLogin();

    if (usuarioAtual) {
        console.log("Sessão restaurada:", usuarioAtual);
        monstrarInformacoesUsuario(usuarioAtual);
    }
    else {
        google.accounts.id.initialize({
            client_id: "ID-DO-CLIENTE",
            callback: handleCredentialResponse,
            context: "signin",
            ux_mode: "popup",
            login_uri: "http://localhost",
            auto_prompt: "false"
        });

        google.accounts.id.renderButton(
            document.getElementById("g_id_onload"),
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

        google.accounts.id.prompt();
    }

});

continuarInformacoesUsuario.addEventListener("click", function () {
    if (!usuarioAtual || this.disabled) return;
    this.disabled = true; // evitar clique duplo
    window.location.replace("./dashboard.html");
});

function decodeJWT(token) {
    // JWT = JSON Web Token

    let base64Url = token.split(".")[1];
    let base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    let jsonPayload = decodeURIComponent(
        atob(base64)
        .split("")
        .map(function (c) {
            return "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2);
        })
        .join("")
    );
    return JSON.parse(jsonPayload);
}

function handleCredentialResponse(response) {

    console.log("Encoded JWT ID token: " + response.credential);

    const responsePayload = decodeJWT(response.credential);

    usuarioAtual = Usuario.fromJWTPayload(responsePayload);

    if (!usuarioAtual.salvar()) {
        alert("Login ok, mas não foi possível salvar a sessão localmente.");
        return;
    }

    monstrarInformacoesUsuario(usuarioAtual);
    renderizarEstadoLogin();
}

function monstrarInformacoesUsuario (usuario) {
    // const objeto_full_name = document.getElementById("full-name");
    usuarioID.textContent = usuario.id;
    usuarioNome.textContent = usuario.nome;
    usuarioNomeHeader.textContent = usuario.nome;
    usuarioSobrenome.textContent = usuario.sobrenome;
    usuarioNomeCompleto.textContent = usuario.nomeCompleto;
    usuarioEmail.textContent = usuario.email;
    usuarioEmailVerificado.textContent = usuario.emailVerificado;
    usuarioComecoSessao.textContent = usuario.comecoSessao;
    usuarioVencimentoSessao.textContent = usuario.vencimentoSessao;
    usuarioFotoPerfil.setAttribute("src", usuario.fotoPerfil);
    usuarioFotoPerfilHeader.setAttribute("src", usuario.fotoPerfil);
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
        informeLogin.textContent = "Faça o Longin pelo Google:";
    }
}
