// Rotas de dados do mapa (specs.md 6.2). Servem JSON pré-computado por src/api_precompute.py.
// Todo parâmetro é validado contra o catálogo (lista fechada) antes de virar nome de arquivo.
const fs = require("node:fs");
const path = require("node:path");
const { UFS } = require("./ufs");
const { criarIndice, buscar } = require("./busca");
const { criarFavoritos } = require("./favoritos");
const { criarRedis, redisConfigurado } = require("./redis");
const { elegivel } = require("./medalhistas");

function criarDados(config) {
  const raiz = config.raizApi;
  const lerJSON = (...partes) => JSON.parse(fs.readFileSync(path.join(raiz, ...partes), "utf8"));

  let catalogo = null;
  let ufsPorCodigo = null;
  const paineis = new Map(); // UF -> painéis dos municípios (cada arquivo tem ~1 MB)
  const fichas = new Map();  // UF -> fichas das escolas
  let indice = null;
  const favoritos = criarFavoritos(path.join(config.raizPrivado, "favoritos.json"), config.redis);
  const arquivoAuditoria = path.join(config.raizPrivado, "auditoria.jsonl");
  // Na Vercel (disco somente leitura) os medalhistas e a auditoria ficam no Redis privado, nunca no git.
  const redis = redisConfigurado(config.redis) ? criarRedis(config.redis) : null;

  function carregarBase() {
    if (!catalogo) {
      catalogo = lerJSON("recortes.json");
      ufsPorCodigo = lerJSON("ufs.json");
    }
  }

  function carregarIndice() {
    if (!indice) indice = criarIndice(lerJSON("busca.json"));
    return indice;
  }

  // Rótulo de um favorito vem sempre do índice do servidor, nunca do que o cliente enviou.
  function descreverItem(tipo, id) {
    const ind = carregarIndice();
    if (tipo === "municipio") {
      const m = ind.municipios.get(id);
      return m && { tipo, id, nome: m.nome, uf: m.uf };
    }
    if (tipo === "escola") {
      const e = ind.escolas.get(id);
      return e && { tipo, id, nome: e.nome, uf: e.uf, codigo_municipio: e.municipio };
    }
    return null;
  }

  // Registro de auditoria: sem conseguir gravar, a lista de medalhistas não é entregue (specs.md 7).
  async function auditar(registro) {
    const linha = JSON.stringify({ quando: new Date().toISOString(), ...registro });
    if (redis) return redis.cmd("RPUSH", "auditoria:medalhistas", linha);
    fs.mkdirSync(path.dirname(arquivoAuditoria), { recursive: true });
    fs.appendFileSync(arquivoAuditoria, linha + "\n");
  }

  async function lerMedalhistas(uf, ibge) {
    if (redis) return JSON.parse((await redis.cmd("GET", "medalhistas:" + ibge)) || "[]");
    try {
      return JSON.parse(fs.readFileSync(path.join(config.raizPrivado, "medalhistas", uf + ".json"), "utf8"))[ibge] || [];
    } catch (err) {
      if (err.code !== "ENOENT") throw err;
      return [];
    }
  }

  const texto = (v) => (typeof v === "string" ? v : undefined);

  // Devolve { arquivo } ou { status, erro, motivo }.
  function resolverMapa(q) {
    carregarBase();
    const nivel = texto(q.nivel);
    const uf = (texto(q.uf) || "").toUpperCase();
    if (nivel !== "uf" && nivel !== "municipio") return { status: 400, erro: "nivel_invalido" };
    if (nivel === "municipio" && !UFS.has(uf)) return { status: 400, erro: "uf_invalida" };

    const prova = texto(q.prova);
    const def = prova && Object.hasOwn(catalogo.provas, prova) ? catalogo.provas[prova] : null;
    if (!def) return { status: 400, erro: "prova_invalida" };
    const etapa = texto(q.etapa);
    if (!def.etapas.includes(etapa)) return { status: 422, erro: "recorte_indisponivel", motivo: def.motivo_etapa || "Etapa indisponível para " + def.nome + "." };
    const ano = texto(q.ano);
    if (!def.anos.map(String).includes(ano)) return { status: 422, erro: "recorte_indisponivel", motivo: "Ano indisponível para " + def.nome + "." };
    const rede = texto(q.rede) || def.redes[0];
    if (!def.redes.includes(rede)) return { status: 422, erro: "recorte_indisponivel", motivo: def.motivo_rede || "Rede indisponível para " + def.nome + "." };
    if ((texto(q.sexo) || "todos") !== "todos") return { status: 422, erro: "recorte_indisponivel", motivo: catalogo.sexo.motivo };
    if ((texto(q.renda) || "false") !== "false") return { status: 422, erro: "recorte_indisponivel", motivo: catalogo.renda.motivo };

    const pasta = `${prova}_${etapa}_${ano}_${rede}`;
    return { arquivo: path.join(raiz, "mapa", pasta, (nivel === "uf" ? "uf" : uf) + ".json") };
  }

  function painelDoMunicipio(ibge, etapa) {
    carregarBase();
    const uf = ufsPorCodigo[ibge.slice(0, 2)];
    if (!uf || !UFS.has(uf)) return null;
    if (!paineis.has(uf)) paineis.set(uf, lerJSON("municipio", uf + ".json"));
    const m = paineis.get(uf)[ibge];
    if (!m) return null;
    return { codigo: ibge, uf, populacao: m.populacao, escolas: m.escolas[etapa] || null, contexto: m.contexto, medalhas: m.medalhas };
  }

  function fichaDaEscola(inep) {
    const escola = carregarIndice().escolas.get(inep);
    if (!escola) return null;
    if (!fichas.has(escola.uf)) fichas.set(escola.uf, lerJSON("escola", escola.uf + ".json"));
    const ficha = fichas.get(escola.uf)[inep];
    if (!ficha) return null;
    return { inep, ...ficha, municipio_nome: carregarIndice().municipios.get(ficha.municipio)?.nome || null };
  }

  function registrar(app, { exigirLogin, exigirMesmaOrigem }) {
    // Falta de arquivo pré-computado é erro de operação, não do usuário.
    const protegido = (fn) => async (req, res, next) => {
      try {
        await fn(req, res);
      } catch (err) {
        if (err.code === "ENOENT") return res.status(503).json({ erro: "dados_nao_gerados" });
        next(err);
      }
    };

    app.get("/api/recortes", exigirLogin, protegido((req, res) => {
      carregarBase();
      res.set("Cache-Control", "private, max-age=3600").json(catalogo);
    }));

    app.get("/api/mapa", exigirLogin, protegido((req, res) => {
      const r = resolverMapa(req.query);
      if (r.erro) return res.status(r.status).json({ erro: r.erro, motivo: r.motivo });
      if (!fs.existsSync(r.arquivo)) return res.status(404).json({ erro: "recorte_sem_dados" });
      res.type("application/json").set("Cache-Control", "private, max-age=3600").sendFile(r.arquivo);
    }));

    app.get("/api/municipio/:ibge", exigirLogin, protegido((req, res) => {
      const etapa = texto(req.query.etapa) || "em";
      if (!/^\d{7}$/.test(req.params.ibge)) return res.status(400).json({ erro: "codigo_invalido" });
      if (etapa !== "ef2" && etapa !== "em") return res.status(400).json({ erro: "etapa_invalida" });
      const painel = painelDoMunicipio(req.params.ibge, etapa);
      if (!painel) return res.status(404).json({ erro: "municipio_desconhecido" });
      res.set("Cache-Control", "private, max-age=3600").json(painel);
    }));

    app.get("/api/escola/:inep", exigirLogin, protegido((req, res) => {
      if (!/^\d{8}$/.test(req.params.inep)) return res.status(400).json({ erro: "codigo_invalido" });
      const ficha = fichaDaEscola(req.params.inep);
      if (!ficha) return res.status(404).json({ erro: "escola_desconhecida" });
      res.set("Cache-Control", "private, max-age=3600").json(ficha);
    }));

    app.get("/api/busca", exigirLogin, protegido((req, res) => {
      const q = texto(req.query.q);
      if (q === undefined || q.length > 80) return res.status(400).json({ erro: "consulta_invalida" });
      res.set("Cache-Control", "private, max-age=60").json(buscar(carregarIndice(), q));
    }));

    // Lista de medalhistas: dado pessoal. Cada abertura gera registro de auditoria; o nome só sai com o flag ligado.
    app.get("/api/municipio/:ibge/medalhistas", exigirLogin, protegido(async (req, res) => {
      // Sem disco gravável nem Redis não há como auditar nem guardar dado pessoal: a lista fica indisponível.
      if (config.somenteLeitura && !redis) return res.status(503).json({ erro: "indisponivel_neste_ambiente" });
      const ibge = req.params.ibge;
      if (!/^\d{7}$/.test(ibge)) return res.status(400).json({ erro: "codigo_invalido" });
      carregarBase();
      const uf = ufsPorCodigo[ibge.slice(0, 2)];
      if (!uf || !UFS.has(uf)) return res.status(404).json({ erro: "municipio_desconhecido" });
      const todos = await lerMedalhistas(uf, ibge);
      const lista = todos.filter((m) => elegivel(m));
      try {
        await auditar({ email: req.session.email, acao: "abrir_lista_medalhistas", municipio: ibge, uf, identificado: config.alunoIdentificado, n: lista.length, fora_do_criterio: todos.length - lista.length });
      } catch (err) {
        console.error("Falha ao gravar a auditoria:", err);
        return res.status(500).json({ erro: "auditoria_indisponivel" });
      }
      const saida = lista.map(({ nome, ensino_medio, ...resto }) => (config.alunoIdentificado ? { ...resto, nome } : resto));
      res.set("Cache-Control", "no-store").json({ identificado: config.alunoIdentificado, total: saida.length, fora_do_criterio: todos.length - lista.length, lista: saida });
    }));

    // ---- Favoritos (por usuário) ----
    app.get("/api/favoritos", exigirLogin, protegido(async (req, res) => {
      res.set("Cache-Control", "no-store").json(await favoritos.listar(req.session.email));
    }));

    app.post("/api/favoritos", exigirLogin, exigirMesmaOrigem, protegido(async (req, res) => {
      const { tipo, id } = req.body || {};
      const item = typeof tipo === "string" && typeof id === "string" ? descreverItem(tipo, id) : null;
      if (!item) return res.status(400).json({ erro: "favorito_invalido" });
      if (!(await favoritos.adicionar(req.session.email, item))) return res.status(409).json({ erro: "limite_de_favoritos" });
      res.status(201).json(await favoritos.listar(req.session.email));
    }));

    app.delete("/api/favoritos/:tipo/:id", exigirLogin, exigirMesmaOrigem, protegido(async (req, res) => {
      await favoritos.remover(req.session.email, req.params.tipo, req.params.id);
      res.json(await favoritos.listar(req.session.email));
    }));
  }

  return { registrar };
}

module.exports = { criarDados };
