// Mapa do Brasil (specs.md, seção 9, passos 1 e 2): UFs em mapa de calor, drill-down
// Brasil > UF > município com zoom animado. Os valores vêm da API (passo 5: dados pré-calculados); a malha é real
// (IBGE 2025) e vem do back-end em TopoJSON, só para quem está logado.

const LARGURA = 900;
const ALTURA = 900;
const ZOOM_MAXIMO = 120; // o município mais detalhado cabe com folga; escolas entram em passo futuro
const CORES_CLASSES = [1, 2, 3, 4, 5].map(function (i) {
    return "var(--mapa-classe-" + i + ")";
});
const COR_SEM_DADO = "var(--mapa-sem-dado)";

// INSE (INEP): Nível I (mais vulnerável) a VII. Os grupos do filtro da lista de escolas.
const GRUPOS_INSE = { baixo: ["I", "II", "III"], medio: ["IV", "V"], alto: ["VI", "VII"] };

function textoINSE(inse) {
    return inse ? "Nível " + inse.nivel + " (" + formatoValor.format(inse.valor) + ")" : "-";
}

const formatoValor = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const formatoInteiro = new Intl.NumberFormat("pt-BR");

const estado = {
    ufSelecionada: null,        // feature da UF
    municipioSelecionado: null, // feature do município
    filtros: null,              // definido depois de carregar o catálogo (mapa-dados.js)
    versaoFiltros: 0,           // descarta respostas antigas quando o usuário troca filtro rápido
    paineis: new Map(),         // detalhe dos municípios já baixados (chave: código|etapa)
    paginaEscolas: 0,
    escolaAberta: null,         // INEP da escola cuja ficha está aberta (nível escola, specs.md 4.1)
    fichas: new Map(),
    favoritos: [],
    listaMedalhistas: null,     // {codigo, dados}: só existe depois de o usuário pedir a lista
    filtroINSE: "todos",        // lista de escolas do município: todos | baixo | medio | alto (nível socioeconômico, INEP)
    alunosIP: null,             // municípios com alunos do Instituto Ponte (filtro de pinos); carregado sob demanda
    dadosUF: new Map(),
    dadosMunicipio: new Map(),
    corUF: null,
    corMunicipio: null,
    municipiosPorUF: new Map(), // cache das malhas já baixadas
    acoes: {},
};

window.addEventListener("load", async function () {
    const usuario = await buscarUsuario();
    if (!usuario) return;

    usuarioNomeHeader.textContent = usuario.nome;
    if (usuario.fotoPerfil) usuarioFotoPerfilHeader.setAttribute("src", usuario.fotoPerfil);
    btnSair.addEventListener("click", sair);

    try {
        await carregarCatalogo();
        estado.filtros = Object.assign({}, FILTROS_PADRAO);
        const [topo, dadosUF] = await Promise.all([buscarJSON("/api/geo/br_uf"), buscarDadosMapa("uf", null, estado.filtros)]);
        iniciarMapa(topojson.feature(topo, topo.objects.ufs), dadosUF);
        iniciarFiltros(estado.filtros, function () { estado.acoes.aplicarFiltros(); });
        iniciarFiltroAlunosIP();
        iniciarFiltroINSE();
        estado.favoritos = await listarFavoritos().catch(function () { return []; });
        iniciarBusca();
    } catch (err) {
        console.error("Falha ao carregar a malha das UFs:", err);
        painelTexto.textContent = "Não foi possível carregar o mapa. Tente recarregar a página.";
    }
});

// ---------- Sessão ----------

async function buscarUsuario() {
    try {
        const resposta = await fetch("/api/me");
        if (resposta.ok) return (await resposta.json()).usuario;
    } catch (err) {
        console.error("Falha ao consultar a sessão:", err);
    }
    window.location.replace("./index.html");
    return null;
}

async function sair() {
    try {
        await fetch("/auth/logout", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
    } finally {
        window.location.replace("./index.html");
    }
}

async function buscarJSON(url) {
    const resposta = await fetch(url);
    if (resposta.status === 401) {
        window.location.replace("./index.html");
        throw new Error("sessão expirada");
    }
    if (!resposta.ok) throw new Error(url + " respondeu " + resposta.status);
    return resposta.json();
}

// ---------- Mapa ----------

function iniciarMapa(geoUFs, dadosIniciaisUF) {
    const svg = d3.select("#mapa").attr("viewBox", [0, 0, LARGURA, ALTURA]);
    const camada = svg.append("g");
    const camadaUFs = camada.append("g");
    const camadaMunicipios = camada.append("g");
    const camadaRotulos = camada.append("g");
    const camadaPinos = camada.append("g").attr("class", "camada-pinos");
    let zoomAtual = 1;

    const projecao = d3.geoMercator().fitExtent([[10, 10], [LARGURA - 10, ALTURA - 10]], geoUFs);
    const caminho = d3.geoPath(projecao);

    function definirDadosUF(dados) {
        estado.dadosUF = new Map(dados.map(function (d) { return [d.codigo, d]; }));
        estado.corUF = escalaQuantis(dados);
    }
    definirDadosUF(dadosIniciaisUF);

    const ufs = camadaUFs.selectAll("path.uf")
        .data(geoUFs.features)
        .join("path")
        .attr("class", "uf")
        .attr("d", caminho)
        .attr("vector-effect", "non-scaling-stroke")
        .attr("fill", function (f) { return corDe(estado.dadosUF, estado.corUF, f.properties.codigo); })
        .attr("tabindex", 0)
        .attr("role", "button")
        .attr("aria-label", function (f) { return descricao(f.properties, estado.dadosUF); });

    function tituloLegendaUF() {
        return PROVAS[estado.filtros.prova].metrica.titulo + ", por UF";
    }

    function tituloLegendaMunicipios() {
        return PROVAS[estado.filtros.prova].metrica.titulo + ", municípios de " + estado.ufSelecionada.properties.nome;
    }

    const rotulos = camadaRotulos.selectAll("text.rotulo-uf")
        .data(geoUFs.features)
        .join("text")
        .attr("class", "rotulo-uf")
        .attr("transform", function (f) {
            const [x, y] = caminho.centroid(f);
            return "translate(" + x + "," + y + ")";
        })
        .attr("dy", "0.35em")
        .text(function (f) { return f.properties.sigla; });

    const zoom = d3.zoom()
        .scaleExtent([1, ZOOM_MAXIMO])
        .translateExtent([[0, 0], [LARGURA, ALTURA]])
        .on("zoom", function (evento) {
            camada.attr("transform", evento.transform);
            zoomAtual = evento.transform.k;
            camadaPinos.selectAll("g.pino").attr("transform", transformacaoDoPino);
            // Rótulos mantêm o tamanho na tela em qualquer zoom.
            rotulos.style("font-size", (11 / evento.transform.k) + "px")
                .style("stroke-width", (3 / evento.transform.k) + "px");
        });
    svg.call(zoom).on("dblclick.zoom", null);

    function aproximarPara(feature) {
        const [[x0, y0], [x1, y1]] = caminho.bounds(feature);
        const escala = Math.min(ZOOM_MAXIMO, 0.85 / Math.max((x1 - x0) / LARGURA, (y1 - y0) / ALTURA));
        const transformacao = d3.zoomIdentity
            .translate(LARGURA / 2, ALTURA / 2)
            .scale(escala)
            .translate(-(x0 + x1) / 2, -(y0 + y1) / 2);
        svg.transition().duration(duracaoAnimacao()).call(zoom.transform, transformacao);
    }

    // ----- Níveis -----

    function irParaBrasil() {
        limparSelecaoDoPainel();
        estado.ufSelecionada = null;
        estado.municipioSelecionado = null;
        ufs.classed("selecionada", false).style("pointer-events", null);
        camadaMunicipios.selectAll("*").remove();
        rotulos.style("display", null);
        svg.transition().duration(duracaoAnimacao()).call(zoom.transform, d3.zoomIdentity);
        desenharLegenda(estado.corUF, tituloLegendaUF());
        atualizarBreadcrumb();
        atualizarPainel();
    }

    function definirDadosMunicipios(dados) {
        estado.dadosMunicipio = new Map(dados.map(function (d) { return [d.codigo, d]; }));
        estado.corMunicipio = escalaQuantis(dados);
    }

    function recolorirUFs() {
        ufs.attr("fill", function (f) { return corDe(estado.dadosUF, estado.corUF, f.properties.codigo); })
            .attr("aria-label", function (f) { return descricao(f.properties, estado.dadosUF); });
    }

    function recolorirMunicipios() {
        camadaMunicipios.selectAll("path.municipio")
            .attr("fill", function (m) { return corDe(estado.dadosMunicipio, estado.corMunicipio, m.properties.codigo); })
            .attr("aria-label", function (m) { return descricao(m.properties, estado.dadosMunicipio); });
    }

    // Todos os filtros afetam o mapa (specs.md 4.2): rebusca o nível atual e mantém a navegação.
    async function aplicarFiltros() {
        const versao = ++estado.versaoFiltros;
        const ufAtual = estado.ufSelecionada;
        const sigla = ufAtual && estado.municipiosPorUF.has(ufAtual.properties.sigla) ? ufAtual.properties.sigla : null;
        esconderTooltip();
        try {
            const [dadosUF, dadosMun] = await Promise.all([
                buscarDadosMapa("uf", null, estado.filtros),
                sigla ? buscarDadosMapa("municipio", sigla, estado.filtros) : null,
            ]);
            if (versao !== estado.versaoFiltros) return; // chegou outra mudança de filtro depois desta
            definirDadosUF(dadosUF);
            recolorirUFs();
            if (dadosMun && estado.ufSelecionada === ufAtual) {
                definirDadosMunicipios(dadosMun);
                recolorirMunicipios();
                desenharLegenda(estado.corMunicipio, tituloLegendaMunicipios());
            } else {
                desenharLegenda(estado.corUF, tituloLegendaUF());
            }
        } catch (err) {
            if (versao !== estado.versaoFiltros) return;
            console.error("Falha ao carregar os dados do recorte:", err);
            painelTexto.textContent = "Não foi possível carregar os dados deste recorte. Tente novamente.";
            return;
        }
        atualizarPainel();
    }

    async function irParaUF(feature) {
        limparSelecaoDoPainel();
        estado.ufSelecionada = feature;
        estado.municipioSelecionado = null;
        ufs.classed("selecionada", function (f) { return f === feature; });
        aproximarPara(feature);
        atualizarBreadcrumb();
        atualizarPainel();

        const sigla = feature.properties.sigla;
        let municipios, dadosMun;
        try {
            [municipios, dadosMun] = await Promise.all([carregarMunicipios(sigla), buscarDadosMapa("municipio", sigla, estado.filtros)]);
        } catch (err) {
            console.error("Falha ao carregar os municípios de " + sigla + ":", err);
            painelTexto.textContent = "Não foi possível carregar os municípios. Tente novamente.";
            return;
        }
        if (estado.ufSelecionada !== feature) return; // o usuário já foi para outro lugar

        definirDadosMunicipios(dadosMun);

        camadaMunicipios.selectAll("*").remove();
        camadaMunicipios.selectAll("path.municipio")
            .data(municipios.features)
            .join("path")
            .attr("class", "municipio")
            .attr("d", caminho)
            .attr("vector-effect", "non-scaling-stroke")
            .attr("fill", function (m) { return corDe(estado.dadosMunicipio, estado.corMunicipio, m.properties.codigo); })
            .attr("tabindex", 0)
            .attr("role", "button")
            .attr("aria-label", function (m) { return descricao(m.properties, estado.dadosMunicipio); })
            .on("click", function (evento, m) { if (evento.detail > 0) evento.currentTarget.blur(); irParaMunicipio(m); })
            .on("keydown", function (evento, m) { aoTeclar(evento, function () { irParaMunicipio(m); }); })
            .on("mousemove", function (evento, m) { mostrarTooltip(evento, textoTooltip(m.properties, estado.dadosMunicipio)); })
            .on("mouseleave", esconderTooltip)
            .on("focus", function (evento, m) { mostrarTooltipFoco(evento.currentTarget, textoTooltip(m.properties, estado.dadosMunicipio)); })
            .on("blur", esconderTooltip);

        // Os municípios substituem a UF no mapa: ela fica só como pano de fundo e deixa de capturar cliques.
        ufs.filter(function (f) { return f === feature; }).style("pointer-events", "none");
        rotulos.style("display", "none");
        desenharLegenda(estado.corMunicipio, tituloLegendaMunicipios());
        atualizarPainel();
    }

    function irParaMunicipio(feature) {
        limparSelecaoDoPainel();
        estado.municipioSelecionado = feature;
        estado.paginaEscolas = 0;
        camadaMunicipios.selectAll("path.municipio").classed("selecionada", function (m) { return m === feature; });
        aproximarPara(feature);
        atualizarBreadcrumb();
        atualizarPainel();
    }

    function voltar() {
        if (estado.escolaAberta) {
            estado.escolaAberta = null; // do nível escola de volta ao município
            atualizarPainel();
        } else if (estado.municipioSelecionado) {
            limparSelecaoDoPainel();
            estado.municipioSelecionado = null;
            camadaMunicipios.selectAll("path.municipio").classed("selecionada", false);
            aproximarPara(estado.ufSelecionada);
            atualizarBreadcrumb();
            atualizarPainel();
        } else {
            irParaBrasil();
        }
    }

    // Usado pela busca e pelos favoritos: leva ao UF, ao município e, se for o caso, abre a ficha da escola.
    async function irParaLocal(local) {
        const featUF = geoUFs.features.find(function (f) { return f.properties.sigla === local.uf; });
        if (!featUF) return;
        if (estado.ufSelecionada !== featUF || estado.municipioSelecionado) await irParaUF(featUF);
        if (!local.municipio || estado.ufSelecionada !== featUF) return;
        const mun = estado.municipiosPorUF.get(local.uf).features.find(function (m) { return m.properties.codigo === local.municipio; });
        if (!mun) return;
        irParaMunicipio(mun);
        if (local.escola) abrirFichaEscola(local.escola);
    }

    function voltarParaUF() {
        estado.escolaAberta = null;
        if (estado.municipioSelecionado) voltar();
    }

    // O clique do mouse tira o foco da UF (o contorno de foco só serve a quem navega por teclado).
    ufs.on("click", function (evento, f) { if (evento.detail > 0) evento.currentTarget.blur(); irParaUF(f); })
        .on("keydown", function (evento, f) { aoTeclar(evento, function () { irParaUF(f); }); })
        .on("mousemove", function (evento, f) { mostrarTooltip(evento, textoTooltip(f.properties, estado.dadosUF)); })
        .on("mouseleave", esconderTooltip)
        .on("focus", function (evento, f) { mostrarTooltipFoco(evento.currentTarget, textoTooltip(f.properties, estado.dadosUF)); })
        .on("blur", esconderTooltip);

    // ----- Pinos dos alunos do Instituto Ponte (filtro "cidades com alunos do IP") -----

    // O pino mantém o tamanho na tela em qualquer zoom; a ponta fica sobre o centro do município.
    function transformacaoDoPino(m) {
        const [x, y] = projecao([m.lon, m.lat]);
        return "translate(" + x + "," + y + ") scale(" + (1 / zoomAtual) + ")";
    }

    function textoDoPino(m) {
        return m.municipio + " (" + m.uf + "): " + m.alunos.length + (m.alunos.length === 1 ? " aluno" : " alunos") + " do Instituto Ponte";
    }

    function abrirMunicipioDoPino(m) {
        estado.acoes.irParaLocal({ uf: m.uf, municipio: m.codigo });
    }

    function desenharPinos() {
        const dados = estado.mostrarAlunosIP && estado.alunosIP ? estado.alunosIP : [];
        camadaPinos.selectAll("g.pino")
            .data(dados, function (m) { return m.codigo; })
            .join(function (entrada) {
                const pino = entrada.append("g").attr("class", "pino").attr("tabindex", 0).attr("role", "button");
                pino.append("path").attr("d", "M0,0 C-5,-8 -9,-12 -9,-17 A9,9 0 1 1 9,-17 C9,-12 5,-8 0,0 Z");
                pino.append("circle").attr("cy", -17).attr("r", 3.5);
                return pino;
            })
            .attr("transform", transformacaoDoPino)
            .attr("aria-label", textoDoPino)
            .on("click", function (evento, m) { evento.stopPropagation(); if (evento.detail > 0) evento.currentTarget.blur(); abrirMunicipioDoPino(m); })
            .on("keydown", function (evento, m) { aoTeclar(evento, function () { abrirMunicipioDoPino(m); }); })
            .on("mousemove", function (evento, m) { mostrarTooltip(evento, textoDoPino(m)); })
            .on("mouseleave", esconderTooltip)
            .on("focus", function (evento, m) { mostrarTooltipFoco(evento.currentTarget, textoDoPino(m)); })
            .on("blur", esconderTooltip);
    }

    zoomMais.addEventListener("click", function () { svg.transition().duration(250).call(zoom.scaleBy, 1.6); });
    zoomMenos.addEventListener("click", function () { svg.transition().duration(250).call(zoom.scaleBy, 1 / 1.6); });
    zoomReset.addEventListener("click", irParaBrasil);
    btnVoltar.addEventListener("click", voltar);

    estado.acoes = { irParaBrasil: irParaBrasil, voltarParaUF: voltarParaUF, aplicarFiltros: aplicarFiltros, irParaLocal: irParaLocal, desenharPinos: desenharPinos };
    desenharLegenda(estado.corUF, tituloLegendaUF());
    atualizarBreadcrumb();
    atualizarPainel();
}

async function carregarMunicipios(sigla) {
    if (!estado.municipiosPorUF.has(sigla)) {
        const topo = await buscarJSON("/api/geo/municipios/" + sigla);
        estado.municipiosPorUF.set(sigla, topojson.feature(topo, topo.objects.municipios));
    }
    return estado.municipiosPorUF.get(sigla);
}

// ---------- Cor, texto e interação ----------

// Faixas por quantis (5 classes) só sobre os valores válidos; suprimidos ficam fora (specs.md 4.2 e 6.3).
function escalaQuantis(dados) {
    const valores = dados.filter(function (d) { return !d.suprimido; }).map(function (d) { return d.valor; });
    return d3.scaleQuantile().domain(valores).range(CORES_CLASSES);
}

function corDe(dados, escala, codigo) {
    const d = dados.get(codigo);
    return !d || d.suprimido ? COR_SEM_DADO : escala(d.valor);
}

function descricao(props, dados) {
    const d = dados.get(props.codigo);
    if (!d || d.suprimido) return props.nome + ": dados insuficientes";
    return props.nome + ": " + formatoValor.format(d.valor) + " " + PROVAS[estado.filtros.prova].metrica.curta;
}

function textoTooltip(props, dados) {
    const d = dados.get(props.codigo);
    if (!d || d.suprimido) return props.nome + " · dados insuficientes";
    return props.nome + " · " + formatoValor.format(d.valor) + " " + PROVAS[estado.filtros.prova].metrica.curta;
}

function aoTeclar(evento, acao) {
    if (evento.key === "Enter" || evento.key === " ") {
        evento.preventDefault();
        acao();
    }
}

function duracaoAnimacao() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 750;
}

function mostrarTooltip(evento, texto) {
    const caixa = document.getElementById("tooltip");
    const moldura = caixa.parentElement.getBoundingClientRect();
    caixa.textContent = texto;
    caixa.hidden = false;
    caixa.style.left = (evento.clientX - moldura.left + 14) + "px";
    caixa.style.top = (evento.clientY - moldura.top + 14) + "px";
}

function mostrarTooltipFoco(elemento, texto) {
    const caixa = document.getElementById("tooltip");
    const moldura = caixa.parentElement.getBoundingClientRect();
    const alvo = elemento.getBoundingClientRect();
    caixa.textContent = texto;
    caixa.hidden = false;
    caixa.style.left = (alvo.left - moldura.left + alvo.width / 2) + "px";
    caixa.style.top = (alvo.top - moldura.top + alvo.height / 2) + "px";
}

function esconderTooltip() {
    document.getElementById("tooltip").hidden = true;
}

function desenharLegenda(escala, titulo) {
    if (!escala.domain().length) {
        d3.select("#legenda").html("").append("div").attr("class", "legenda-titulo").text(titulo + ": sem dados neste recorte");
        return;
    }
    const [min, max] = d3.extent(escala.domain());
    const bordas = [min].concat(escala.quantiles(), [max]);

    const legenda = d3.select("#legenda").html("");
    legenda.append("div").attr("class", "legenda-titulo").text(titulo);
    const lista = legenda.append("ul").attr("class", "legenda-lista");

    CORES_CLASSES.forEach(function (cor, i) {
        const item = lista.append("li");
        item.append("span").attr("class", "legenda-cor").style("background", cor);
        item.append("span").text(formatoValor.format(bordas[i]) + " a " + formatoValor.format(bordas[i + 1]));
    });

    const semDado = lista.append("li");
    semDado.append("span").attr("class", "legenda-cor").style("background", COR_SEM_DADO);
    semDado.append("span").text("Sem dados (dados insuficientes)");
}

function atualizarBreadcrumb() {
    const lista = d3.select("#breadcrumb").html("");
    const uf = estado.ufSelecionada;
    const mun = estado.municipioSelecionado;

    function nivel(texto, atual, acao) {
        const li = lista.append("li");
        if (atual) {
            li.attr("aria-current", "page").text(texto);
        } else {
            li.append("button").attr("type", "button").attr("class", "item-breadcrumb").text(texto).on("click", acao);
        }
    }

    nivel("Brasil", !uf, function () { estado.acoes.irParaBrasil(); });
    const escola = estado.escolaAberta && estado.fichas.get(estado.escolaAberta);
    if (uf) nivel(uf.properties.nome, !mun, function () { estado.acoes.voltarParaUF(); });
    if (mun) nivel(mun.properties.nome, !estado.escolaAberta, function () { estado.escolaAberta = null; atualizarBreadcrumb(); atualizarPainel(); });
    if (mun && estado.escolaAberta) nivel(escola ? escola.nome : "Escola", true);
    btnVoltar.hidden = !uf;
}

function rotuloMetrica() {
    const curta = PROVAS[estado.filtros.prova].metrica.curta;
    return curta.charAt(0).toUpperCase() + curta.slice(1);
}

function textoValor(d) {
    return d && !d.suprimido ? formatoValor.format(d.valor) : "dados insuficientes";
}

function textoN(d) {
    return d && d.n != null ? formatoInteiro.format(d.n) : "não informado";
}

function atualizarPainel() {
    const uf = estado.ufSelecionada;
    const mun = estado.municipioSelecionado;
    const painel = d3.select("#painel");
    painel.selectAll("dl").remove();
    painel.selectAll("section.secao-painel").remove();
    painel.selectAll(":scope > button").remove(); // favoritar e voltar são recriados a cada desenho

    if (!uf) {
        painelTitulo.textContent = "Brasil";
        painelTexto.textContent = "Clique em um estado para ver seus municípios.";
        return;
    }

    if (mun && estado.escolaAberta) {
        desenharFichaEscola(painel, mun);
        return;
    }

    const campos = [];
    if (mun) {
        const d = estado.dadosMunicipio.get(mun.properties.codigo);
        const detalhe = painelDoMunicipio(mun);
        painelTitulo.textContent = mun.properties.nome + " (" + uf.properties.sigla + ")";
        painelTexto.textContent = !d || d.suprimido
            ? "Dados insuficientes para a métrica deste recorte."
            : (detalhe ? "" : "Carregando detalhes...");
        campos.push(
            ["Código IBGE", mun.properties.codigo],
            ["População (estimada)", detalhe && detalhe.populacao ? formatoInteiro.format(detalhe.populacao) : "-"],
            ["Posição na UF", d && !d.suprimido ? posicaoNaUF(d) : "-"],
            ["Área (km²)", formatoInteiro.format(Math.round(mun.properties.area_km2))],
            [rotuloMetrica(), textoValor(d)],
            ["Participantes (n)", textoN(d)],
        );
    } else {
        const d = estado.dadosUF.get(uf.properties.codigo);
        painelTitulo.textContent = uf.properties.nome + " (" + uf.properties.sigla + ")";
        painelTexto.textContent = estado.dadosMunicipio.size && estado.municipiosPorUF.has(uf.properties.sigla)
            ? "Clique em um município para ver o detalhe."
            : "Carregando municípios...";
        campos.push(
            ["Região", uf.properties.regiao],
            ["Código IBGE", uf.properties.codigo],
            [rotuloMetrica(), textoValor(d)],
            ["Participantes (n)", textoN(d)],
        );
    }

    const lista = painel.append("dl");
    campos.forEach(function (campo) {
        lista.append("dt").text(campo[0]);
        lista.append("dd").text(campo[1]);
    });

    if (mun) {
        botaoFavorito(painel, "municipio", mun.properties.codigo, mun.properties.nome);
        const detalhe = painelDoMunicipio(mun);
        if (detalhe && !detalhe.erro) desenharSecoesMunicipio(painel, detalhe);
        else if (detalhe) painelTexto.textContent = "Não foi possível carregar o detalhe do município.";
    }
}

// Posição entre os municípios da UF com dados válidos (suprimidos ficam fora do ranking, specs.md 6.3).
function posicaoNaUF(d) {
    const validos = Array.from(estado.dadosMunicipio.values()).filter(function (x) { return !x.suprimido; });
    const posicao = validos.filter(function (x) { return x.valor > d.valor; }).length + 1;
    return posicao + "º de " + validos.length;
}

// Detalhe do município vindo da API; busca uma vez por município e etapa e redesenha quando chega.
function painelDoMunicipio(mun) {
    const codigo = mun.properties.codigo;
    const etapa = estado.filtros.etapa;
    const chave = codigo + "|" + etapa;
    if (estado.paineis.has(chave)) return estado.paineis.get(chave);
    if (estado.paineis.has(chave + "|buscando")) return null;
    estado.paineis.set(chave + "|buscando", true);
    buscarPainelMunicipio(codigo, etapa)
        .then(function (dados) { estado.paineis.set(chave, dados); })
        .catch(function (err) {
            console.error("Falha ao carregar o município " + codigo + ":", err);
            estado.paineis.set(chave, { erro: true });
        })
        .finally(function () {
            estado.paineis.delete(chave + "|buscando");
            if (estado.municipioSelecionado === mun && estado.filtros.etapa === etapa) atualizarPainel();
        });
    return null;
}

const ESCOLAS_POR_PAGINA = 10;

// Filtro "cidades com alunos do Instituto Ponte": pino nas cidades de origem; o clique leva ao município,
// onde o painel lista os alunos. A lista só é baixada na primeira vez que o filtro é ligado.
function iniciarFiltroAlunosIP() {
    const campo = document.getElementById("fAlunosIP");
    const aviso = document.getElementById("filtrosAviso");
    campo.addEventListener("change", async function () {
        estado.mostrarAlunosIP = campo.checked;
        if (campo.checked && !estado.alunosIP) {
            campo.disabled = true;
            try {
                estado.alunosIP = await buscarAlunosIP();
            } catch (err) {
                console.error("Falha ao carregar os alunos do Instituto Ponte:", err);
                estado.mostrarAlunosIP = false;
                campo.checked = false;
                aviso.textContent = "Não foi possível carregar os alunos do Instituto Ponte.";
                aviso.hidden = false;
            }
            campo.disabled = false;
        } else {
            aviso.hidden = true;
        }
        estado.acoes.desenharPinos();
        atualizarPainel();
    });
}

// Filtro "INSE das escolas": limita a lista de escolas do painel do município a um grupo de nível socioeconômico.
function iniciarFiltroINSE() {
    const campo = document.getElementById("fINSE");
    campo.addEventListener("change", function () {
        estado.filtroINSE = campo.value;
        estado.paginaEscolas = 0;
        atualizarPainel();
    });
}

function desenharSecoesMunicipio(painel, p) {
    function secao(titulo) {
        const s = painel.append("section").attr("class", "secao-painel");
        s.append("h3").text(titulo);
        return s;
    }

    const doIP = estado.mostrarAlunosIP && estado.alunosIP ? estado.alunosIP.find(function (m) { return m.codigo === p.codigo; }) : null;
    if (doIP) {
        const alunosIP = secao("Alunos do Instituto Ponte (" + doIP.alunos.length + ")");
        alunosIP.append("p").attr("class", "nota-painel").text("Alunos cuja cidade de origem é " + doIP.municipio + ". Fonte: página oficial do Instituto Ponte.");
        const ul = alunosIP.append("ul").attr("class", "lista-alunos-ip");
        doIP.alunos.forEach(function (a) {
            const li = ul.append("li");
            li.append("a").attr("href", a.url).attr("target", "_blank").attr("rel", "noopener noreferrer").text(a.nome);
            const detalhes = [a.desde ? "aluno desde " + a.desde : null, a.escola_origem ? "escola de origem: " + a.escola_origem : null].filter(Boolean).join(" · ");
            if (detalhes) li.append("small").text(detalhes);
        });
    }
    function tabela(s, legenda, cabecalho, linhas) {
        const t = s.append("table");
        t.append("caption").attr("class", "so-leitor").text(legenda);
        t.append("thead").append("tr").selectAll("th").data(cabecalho).join("th").attr("scope", "col").text(function (c) { return c; });
        t.append("tbody").selectAll("tr").data(linhas).join("tr")
            .selectAll("td").data(function (l) { return l; }).join("td")
            .each(function (c) {
                if (c && c.acao) {
                    d3.select(this).append("button").attr("type", "button").attr("class", "item-breadcrumb").text(c.texto).on("click", c.acao);
                } else {
                    d3.select(this).text(c);
                }
            });
    }
    const valor = function (v, formato) { return v == null ? "-" : formato.format(v); };

    // Escolas ranqueadas pelo Saeb, com paginação (specs.md 4.3).
    const escolas = secao("Escolas (ranking Saeb" + (p.escolas ? ", " + p.escolas.ano : "") + ")");
    if (p.escolas && p.escolas.lista.length) {
        // A posição é a do ranking completo; o filtro de INSE só esconde linhas.
        const grupo = GRUPOS_INSE[estado.filtroINSE];
        const lista = p.escolas.lista.map(function (e, i) { return { e: e, pos: i + 1 }; })
            .filter(function (x) { return !grupo || (x.e.inse && grupo.indexOf(x.e.inse.nivel) !== -1); });
        const total = lista.length;
        if (grupo) escolas.append("p").attr("class", "nota-painel").text("Filtro de INSE ativo: " + total + " de " + p.escolas.lista.length + " escolas (nível " + grupo[0] + (grupo.length > 1 ? " a " + grupo[grupo.length - 1] : "") + ").");
        const paginas = Math.max(1, Math.ceil(total / ESCOLAS_POR_PAGINA));
        estado.paginaEscolas = Math.min(estado.paginaEscolas, paginas - 1);
        const inicio = estado.paginaEscolas * ESCOLAS_POR_PAGINA;
        if (total) {
            tabela(escolas, "Escolas públicas do município ranqueadas pela nota do Saeb, com o INSE de cada uma",
                ["#", "INEP", "Escola", "Rede / selo", "Nota", "INSE"],
                lista.slice(inicio, inicio + ESCOLAS_POR_PAGINA).map(function (x) {
                    const e = x.e;
                    return [x.pos, e.inep, { texto: e.nome, acao: function () { abrirFichaEscola(e.inep); } },
                        e.destaque ? "Destaque ★" : e.rede, formatoValor.format(e.nota), textoINSE(e.inse)];
                }));
        } else {
            escolas.append("p").text("Nenhuma escola deste município no grupo de INSE escolhido.");
        }
        if (paginas > 1) {
            const nav = escolas.append("div").attr("class", "paginacao");
            nav.append("button").attr("type", "button").attr("class", "botao-secundario").text("Anterior")
                .property("disabled", estado.paginaEscolas === 0)
                .on("click", function () { estado.paginaEscolas--; atualizarPainel(); });
            nav.append("span").text("Página " + (estado.paginaEscolas + 1) + " de " + paginas + " (" + total + " escolas)");
            nav.append("button").attr("type", "button").attr("class", "botao-secundario").text("Próxima")
                .property("disabled", estado.paginaEscolas >= paginas - 1)
                .on("click", function () { estado.paginaEscolas++; atualizarPainel(); });
        }
    } else {
        escolas.append("p").text("Nenhuma escola pública com nota do Saeb divulgada nesta etapa.");
    }

    // Só agregados: a lista nominal depende da política de LGPD (specs.md 7, passo 8).
    const medalhas = secao("Medalhas (2016 a 2025)");
    if (p.medalhas.length) {
        tabela(medalhas, "Total de medalhas por olimpíada e tipo",
            ["Olimpíada", "Medalha", "Total"],
            p.medalhas.map(function (m) { return [m.olimpiada, m.medalha, formatoInteiro.format(m.n)]; }));
    } else {
        medalhas.append("p").text("Nenhuma medalha no período.");
    }
    desenharListaMedalhistas(medalhas, p.codigo);

    const etapa = estado.filtros.etapa;
    const c = p.contexto;
    const ideb = c[etapa];
    const contexto = secao("Contexto");
    const dl = contexto.append("dl");
    [
        ["Ideb" + (ideb ? " (" + ideb.ano + ")" : ""), ideb ? valor(ideb.ideb, formatoValor) : "-"],
        ["Taxa de aprovação (%)", ideb ? valor(ideb.taxa_aprovacao, formatoValor) : "-"],
        ["ENEM, média" + (c.enem ? " (" + c.enem.ano + ")" : ""), c.enem ? valor(c.enem.media, formatoValor) : "-"],
        ["Renda até 1,5 SM, estimado (%)", c.renda ? valor(c.renda.pct_ate_1_5_sm, formatoValor) : "-"],
    ].forEach(function (campo) { dl.append("dt").text(campo[0]); dl.append("dd").text(campo[1]); });

    const ip = secao("Candidatos ao IP");
    ip.append("p").text("Base interna de candidatos ainda não integrada.");
}

// ---------- Nível escola, favoritos e medalhistas ----------

function limparSelecaoDoPainel() {
    estado.escolaAberta = null;
    estado.listaMedalhistas = null;
}

function abrirFichaEscola(inep) {
    estado.escolaAberta = inep;
    atualizarBreadcrumb();
    atualizarPainel();
    if (!estado.fichas.has(inep)) {
        buscarFichaEscola(inep)
            .then(function (ficha) { estado.fichas.set(inep, ficha); })
            .catch(function (err) {
                console.error("Falha ao carregar a escola " + inep + ":", err);
                estado.fichas.set(inep, { erro: true });
            })
            .finally(function () {
                if (estado.escolaAberta === inep) { atualizarBreadcrumb(); atualizarPainel(); }
            });
    }
}

function ehFavorito(tipo, id) {
    return estado.favoritos.some(function (f) { return f.tipo === tipo && f.id === id; });
}

function botaoFavorito(painel, tipo, id, nome) {
    const ativo = ehFavorito(tipo, id);
    painel.append("button")
        .attr("type", "button")
        .attr("class", "botao-secundario botao-favorito")
        .attr("aria-pressed", String(ativo))
        .text(ativo ? "★ Favorito" : "☆ Favoritar")
        .attr("aria-label", (ativo ? "Remover dos favoritos: " : "Adicionar aos favoritos: ") + nome)
        .on("click", async function () {
            try {
                estado.favoritos = ativo ? await removerFavorito(tipo, id) : await adicionarFavorito(tipo, id);
            } catch (err) {
                console.error("Falha ao atualizar os favoritos:", err);
            }
            atualizarPainel();
            if (typeof atualizarMenuFavoritos === "function") atualizarMenuFavoritos();
        });
}

function desenharFichaEscola(painel, mun) {
    const inep = estado.escolaAberta;
    const ficha = estado.fichas.get(inep);
    painel.append("button").attr("type", "button").attr("class", "botao-secundario")
        .text("← " + mun.properties.nome)
        .on("click", function () { estado.escolaAberta = null; atualizarBreadcrumb(); atualizarPainel(); });

    if (!ficha || ficha.erro) {
        painelTitulo.textContent = "Escola " + inep;
        painelTexto.textContent = ficha ? "Não foi possível carregar a escola." : "Carregando a escola...";
        return;
    }
    painelTitulo.textContent = ficha.nome;
    painelTexto.textContent = "";

    const dl = painel.append("dl");
    [["Código INEP", ficha.inep], ["Rede", ficha.rede], ["Município", ficha.municipio_nome + " (" + ficha.uf + ")"],
        ["INSE" + (ficha.inse ? " (" + ficha.inse.ano + ")" : ""), textoINSE(ficha.inse)],
        ["Medalhistas", ficha.n_medalhistas ? formatoInteiro.format(ficha.n_medalhistas) + " aluno(s) vinculados" : "nenhum vinculado"]]
        .forEach(function (campo) { dl.append("dt").text(campo[0]); dl.append("dd").text(campo[1]); });
    botaoFavorito(painel, "escola", ficha.inep, ficha.nome);

    const nomesEtapa = { ef2: "Ensino Fundamental 2", em: "Ensino Médio" };
    const num = function (v) { return v == null ? "-" : formatoValor.format(v); };
    Object.keys(ficha.series).forEach(function (etapa) {
        const sec = painel.append("section").attr("class", "secao-painel");
        sec.append("h3").text("Evolução, " + (nomesEtapa[etapa] || etapa));
        const t = sec.append("table");
        t.append("caption").attr("class", "so-leitor").text("Notas do Saeb, Ideb e aprovação por edição");
        t.append("thead").append("tr").selectAll("th").data(["Ano", "LP", "MT", "Ideb", "Aprov. (%)"]).join("th").attr("scope", "col").text(function (c) { return c; });
        t.append("tbody").selectAll("tr").data(ficha.series[etapa]).join("tr")
            .selectAll("td").data(function (r) { return [r.ano, num(r.lp), num(r.mt), num(r.ideb), num(r.aprovacao)]; }).join("td").text(function (c) { return c; });
    });
}

// A lista nominal é dado pessoal: só abre por clique e cada abertura é registrada no servidor (specs.md 7).
function desenharListaMedalhistas(secao, codigo) {
    const aberta = estado.listaMedalhistas && estado.listaMedalhistas.codigo === codigo ? estado.listaMedalhistas : null;
    if (!aberta) {
        secao.append("button").attr("type", "button").attr("class", "botao-secundario").text("Ver lista de medalhistas")
            .on("click", async function () {
                d3.select(this).property("disabled", true);
                try {
                    estado.listaMedalhistas = { codigo: codigo, dados: await buscarMedalhistas(codigo) };
                } catch (err) {
                    console.error("Falha ao carregar os medalhistas:", err);
                    estado.listaMedalhistas = { codigo: codigo, dados: { erro: true } };
                }
                atualizarPainel();
            });
        secao.append("p").attr("class", "nota-painel").text("A abertura da lista fica registrada para auditoria.");
        return;
    }
    const dados = aberta.dados;
    if (dados.erro) {
        secao.append("p").text("Não foi possível carregar a lista de medalhistas.");
        return;
    }
    secao.append("p").attr("class", "nota-painel").text(
        dados.identificado ? "Lista com nomes completos. Acesso restrito à coordenação do IP; abertura registrada."
            : "Alunos pseudonimizados (iniciais e código). Abertura registrada para auditoria.");
    if (dados.fora_do_criterio) {
        secao.append("p").attr("class", "nota-painel").text(
            formatoInteiro.format(dados.fora_do_criterio) + " medalhista(s) do ensino médio fora do critério de elegibilidade (medalha anterior ao ano passado) não aparecem.");
    }
    if (!dados.lista.length) {
        secao.append("p").text("Nenhum medalhista elegível vinculado a este município.");
        return;
    }
    const t = secao.append("div").attr("class", "rolagem-tabela").append("table");
    t.append("caption").attr("class", "so-leitor").text("Medalhistas do município");
    t.append("thead").append("tr").selectAll("th").data(["Aluno", "Medalha", "Olimpíada", "Ano", "Escola", "Fonte oficial"]).join("th").attr("scope", "col").text(function (c) { return c; });
    t.append("tbody").selectAll("tr").data(dados.lista.slice(0, 200)).join("tr")
        .selectAll("td").data(function (m) { return [m.nome || m.pseudonimo, m.medalha, m, m.ano, m.escola, m.fonte]; }).join("td")
        .each(function (c, i) {
            const celula = d3.select(this);
            if (i === 2) {
                // Olimpíada; na OCMAT o nível aparece sempre, e os níveis 1 e 4 (séries misturadas) vêm com aviso.
                celula.text(c.nivel && c.olimpiada === "OCMAT" ? "OCMAT, nível " + c.nivel : c.olimpiada);
                if (c.aviso) celula.append("small").attr("class", "aviso-nivel").text("⚠ " + c.aviso);
                return;
            }
            if (i < 5) return celula.text(c);
            // Link para a página oficial da olimpíada de onde a lista foi tirada.
            if (c) celula.append("a").attr("href", c).attr("target", "_blank").attr("rel", "noopener noreferrer").text("Abrir página");
            else celula.text("-");
        });
    if (dados.total > 200) secao.append("p").attr("class", "nota-painel").text("Mostrando 200 de " + formatoInteiro.format(dados.total) + ".");
    secao.append("button").attr("type", "button").attr("class", "botao-secundario").text("Ocultar lista")
        .on("click", function () { estado.listaMedalhistas = null; atualizarPainel(); });
}
