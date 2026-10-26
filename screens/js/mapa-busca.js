// Busca única com autocomplete e menu de favoritos (specs.md 4.5). Escolher um resultado faz zoom e abre o painel.

const ROTULO_TIPO = { uf: "UF", municipio: "Município", escola: "Escola" };

function localDe(item) {
    if (item.tipo === "uf") return { uf: item.id };
    if (item.tipo === "municipio") return { uf: item.uf, municipio: item.id };
    return { uf: item.uf, municipio: item.codigo_municipio, escola: item.id };
}

function iniciarBusca() {
    const campo = document.getElementById("busca");
    const lista = document.getElementById("sugestoes");
    const status = document.getElementById("buscaStatus");
    let sugestoes = [];
    let ativa = -1;
    let versao = 0;
    let adiar = null;

    function fechar() {
        lista.hidden = true;
        campo.setAttribute("aria-expanded", "false");
        campo.removeAttribute("aria-activedescendant");
        ativa = -1;
    }

    function marcarAtiva(i) {
        ativa = i;
        Array.from(lista.children).forEach(function (li, j) { li.setAttribute("aria-selected", String(j === i)); });
        if (i >= 0) campo.setAttribute("aria-activedescendant", "sugestao-" + i);
        else campo.removeAttribute("aria-activedescendant");
    }

    function escolher(item) {
        campo.value = "";
        fechar();
        estado.acoes.irParaLocal(localDe(item));
    }

    function desenhar() {
        lista.innerHTML = "";
        sugestoes.forEach(function (item, i) {
            const li = document.createElement("li");
            li.id = "sugestao-" + i;
            li.setAttribute("role", "option");
            li.setAttribute("aria-selected", "false");
            const nome = document.createElement("span");
            nome.textContent = item.nome;
            const detalhe = document.createElement("small");
            detalhe.textContent = ROTULO_TIPO[item.tipo] + (item.tipo === "escola" && item.municipio ? " · " + item.municipio : "") + " · " + item.uf;
            li.append(nome, detalhe);
            li.addEventListener("mousedown", function (e) { e.preventDefault(); escolher(item); });
            lista.appendChild(li);
        });
        lista.hidden = sugestoes.length === 0;
        campo.setAttribute("aria-expanded", String(sugestoes.length > 0));
        status.textContent = campo.value.trim().length >= 2 ? (sugestoes.length ? sugestoes.length + " resultados" : "Nenhum resultado") : "";
        ativa = -1;
    }

    campo.addEventListener("input", function () {
        clearTimeout(adiar);
        const consulta = campo.value.trim();
        if (consulta.length < 2) { sugestoes = []; desenhar(); return; }
        adiar = setTimeout(async function () {
            const minha = ++versao;
            try {
                const achados = await buscarSugestoes(consulta);
                if (minha !== versao) return; // resposta de uma digitação anterior
                sugestoes = achados;
                desenhar();
            } catch (err) {
                console.error("Falha na busca:", err);
            }
        }, 200);
    });

    campo.addEventListener("keydown", function (e) {
        if (e.key === "ArrowDown" && sugestoes.length) { e.preventDefault(); lista.hidden = false; marcarAtiva((ativa + 1) % sugestoes.length); }
        else if (e.key === "ArrowUp" && sugestoes.length) { e.preventDefault(); marcarAtiva((ativa - 1 + sugestoes.length) % sugestoes.length); }
        else if (e.key === "Enter" && ativa >= 0) { e.preventDefault(); escolher(sugestoes[ativa]); }
        else if (e.key === "Escape") fechar();
    });
    campo.addEventListener("blur", fechar);

    iniciarMenuFavoritos();
}

function iniciarMenuFavoritos() {
    const botao = document.getElementById("btnFavoritos");
    const menu = document.getElementById("menuFavoritos");

    function alternar(abrir) {
        menu.hidden = !abrir;
        botao.setAttribute("aria-expanded", String(abrir));
    }

    botao.addEventListener("click", function () { alternar(menu.hidden); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape" && !menu.hidden) { alternar(false); botao.focus(); } });
    document.addEventListener("click", function (e) { if (!menu.hidden && !menu.parentElement.contains(e.target)) alternar(false); });

    window.atualizarMenuFavoritos = function () {
        menu.innerHTML = "";
        if (!estado.favoritos.length) {
            const vazio = document.createElement("li");
            vazio.textContent = "Nenhum favorito ainda.";
            menu.appendChild(vazio);
            return;
        }
        estado.favoritos.forEach(function (item) {
            const li = document.createElement("li");
            const b = document.createElement("button");
            b.type = "button";
            b.textContent = item.nome + " (" + ROTULO_TIPO[item.tipo] + ", " + item.uf + ")";
            b.addEventListener("click", function () { alternar(false); estado.acoes.irParaLocal(localDe(item)); });
            li.appendChild(b);
            menu.appendChild(li);
        });
    };
    window.atualizarMenuFavoritos();
}
