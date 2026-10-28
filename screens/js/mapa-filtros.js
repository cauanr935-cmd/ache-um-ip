// Barra de filtros do mapa (specs.md 4.4). Mantém só o estado dos filtros e as regras de
// compatibilidade; quem recolore o mapa é o mapa.js, avisado pelo callback.

function iniciarFiltros(filtros, aoMudar) {
    const campos = {
        prova: document.getElementById("fProva"),
        etapa: document.getElementById("fEtapa"),
        sexo: document.getElementById("fSexo"),
        ano: document.getElementById("fAno"),
    };
    const campoRenda = document.getElementById("fRenda");
    const aviso = document.getElementById("filtrosAviso");
    const motivos = [];

    const nota = document.getElementById("filtrosNota");

    function opcao(valor, texto) {
        const o = document.createElement("option");
        o.value = valor;
        o.textContent = texto;
        return o;
    }

    // Incompatibilidade vira opção desabilitada com explicação, nunca mapa vazio. As regras vêm do
    // catálogo (/api/recortes), que reflete o que existe nos dados.
    function ajustarCompatibilidade() {
        const prova = PROVAS[filtros.prova];
        motivos.length = 0;

        campos.prova.innerHTML = "";
        Object.keys(PROVAS).forEach(function (chave) { campos.prova.appendChild(opcao(chave, PROVAS[chave].nome)); });

        if (prova.etapas.indexOf(filtros.etapa) === -1) {
            filtros.etapa = prova.etapas[0];
            motivos.push(prova.motivo_etapa || ("A etapa foi ajustada: a prova " + prova.nome + " não cobre a etapa anterior."));
        }
        Array.from(campos.etapa.options).forEach(function (o) {
            const permitido = prova.etapas.indexOf(o.value) !== -1;
            o.disabled = !permitido;
            o.title = permitido ? "" : (prova.motivo_etapa || "Indisponível para " + prova.nome + ".");
        });

        if (prova.anos.map(String).indexOf(String(filtros.ano)) === -1) {
            filtros.ano = prova.anos[0]; // edição mais recente da prova
            motivos.push("O ano foi ajustado para " + (filtros.ano === "todos" ? "todos os anos" : filtros.ano) + ", disponível para " + prova.nome + ".");
        }
        campos.ano.innerHTML = "";
        prova.anos.forEach(function (ano) { campos.ano.appendChild(opcao(ano, ano === "todos" ? "Todos (2016 a 2025)" : ano)); });

        if (prova.nota) motivos.push(prova.nota);

        // Todos os alunos de interesse são de escolas públicas: não há filtro de rede, vale sempre a pública.
        // Quando a prova não informa a rede (OBI), usa a única opção dela e avisa.
        filtros.rede = prova.redes.indexOf("publica") !== -1 ? "publica" : prova.redes[0];
        if (filtros.rede !== "publica") motivos.push(prova.motivo_rede || ("Esta prova não separa a rede da escola: o mapa mostra todas as redes."));

        // Sexo e renda não cruzam com as notas e medalhas desta base (specs.md 4.4): ficam desabilitados.
        Array.from(campos.sexo.options).forEach(function (o) {
            o.disabled = CATALOGO.sexo.valores.indexOf(o.value) === -1;
            o.title = o.disabled ? CATALOGO.sexo.motivo : "";
        });
        filtros.sexo = "todos";
        filtros.renda = false;
        campoRenda.disabled = !CATALOGO.renda.disponivel;
        campoRenda.title = CATALOGO.renda.disponivel ? "" : CATALOGO.renda.motivo;
        nota.textContent = [CATALOGO.sexo.motivo, CATALOGO.renda.motivo].join(" ");

        campos.prova.value = filtros.prova;
        campos.etapa.value = filtros.etapa;
        campos.sexo.value = filtros.sexo;
        campos.ano.value = String(filtros.ano);
        campoRenda.checked = filtros.renda;
        aviso.textContent = motivos.join(" ");
        aviso.hidden = motivos.length === 0;
    }

    function aoAlterar(chave, ler) {
        return function () {
            filtros[chave] = ler();
            ajustarCompatibilidade();
            aoMudar();
        };
    }

    campos.prova.addEventListener("change", aoAlterar("prova", function () { return campos.prova.value; }));
    campos.etapa.addEventListener("change", aoAlterar("etapa", function () { return campos.etapa.value; }));
    campos.sexo.addEventListener("change", aoAlterar("sexo", function () { return campos.sexo.value; }));
    campos.ano.addEventListener("change", aoAlterar("ano", function () { return campos.ano.value === "todos" ? "todos" : Number(campos.ano.value); }));
    campoRenda.addEventListener("change", aoAlterar("renda", function () { return campoRenda.checked; }));

    // No mobile os filtros ficam numa gaveta (specs.md 4.4).
    const botao = document.getElementById("btnFiltros");
    botao.addEventListener("click", function () {
        const aberto = document.getElementById("filtros").classList.toggle("aberta");
        botao.setAttribute("aria-expanded", String(aberto));
    });

    ajustarCompatibilidade();
}
