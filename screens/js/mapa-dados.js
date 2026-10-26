// Acesso aos dados do mapa pela API (specs.md 6.2). Formato dos valores: [{codigo, valor, n, suprimido}].

let PROVAS = {};    // catálogo de provas, preenchido por carregarCatalogo()
let CATALOGO = null;

const FILTROS_PADRAO = { prova: "saeb", etapa: "em", sexo: "todos", renda: false, ano: null, rede: "publica" };

async function carregarCatalogo() {
    CATALOGO = await buscarJSON("/api/recortes");
    PROVAS = CATALOGO.provas;
    FILTROS_PADRAO.ano = PROVAS[FILTROS_PADRAO.prova].anos[0]; // edição mais recente
    return CATALOGO;
}

function parametrosDoRecorte(f) {
    return new URLSearchParams({
        prova: f.prova, etapa: f.etapa, ano: String(f.ano), rede: f.rede, sexo: f.sexo, renda: String(f.renda),
    });
}

// nivel "uf" traz as 27 UFs; nivel "municipio" traz os municípios da UF (sigla).
function buscarDadosMapa(nivel, sigla, filtros) {
    const params = parametrosDoRecorte(filtros);
    params.set("nivel", nivel);
    if (sigla) params.set("uf", sigla);
    return buscarJSON("/api/mapa?" + params);
}

function buscarPainelMunicipio(codigo, etapa) {
    return buscarJSON("/api/municipio/" + encodeURIComponent(codigo) + "?etapa=" + encodeURIComponent(etapa));
}

function buscarFichaEscola(inep) {
    return buscarJSON("/api/escola/" + encodeURIComponent(inep));
}

// Cada chamada abre a lista e gera registro de auditoria no servidor (specs.md 7): não guardar em cache.
function buscarMedalhistas(codigo) {
    return buscarJSON("/api/municipio/" + encodeURIComponent(codigo) + "/medalhistas");
}

function buscarSugestoes(consulta) {
    return buscarJSON("/api/busca?q=" + encodeURIComponent(consulta));
}

async function enviarJSON(metodo, url, corpo) {
    const resposta = await fetch(url, { method: metodo, headers: { "Content-Type": "application/json" }, body: JSON.stringify(corpo || {}) });
    if (resposta.status === 401) {
        window.location.replace("./index.html");
        throw new Error("sessão expirada");
    }
    if (!resposta.ok) throw new Error(url + " respondeu " + resposta.status);
    return resposta.json();
}

function listarFavoritos() {
    return buscarJSON("/api/favoritos");
}

function adicionarFavorito(tipo, id) {
    return enviarJSON("POST", "/api/favoritos", { tipo: tipo, id: id });
}

function removerFavorito(tipo, id) {
    return enviarJSON("DELETE", "/api/favoritos/" + encodeURIComponent(tipo) + "/" + encodeURIComponent(id));
}
