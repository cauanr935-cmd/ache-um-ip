const test = require("node:test");
const assert = require("node:assert/strict");
const { criarApp } = require("./app");
const { emailAutorizado } = require("./auth");

const config = {
  producao: false,
  googleClientId: "cliente-teste",
  segredoSessao: "segredo-de-teste",
  horasSessao: 1,
  dominiosPermitidos: ["institutoponte.org.br"],
  emailsPermitidos: ["extra@gmail.com"],
  raizFront: require("node:path").resolve(__dirname, "../screens"),
  raizMalha: require("node:path").resolve(__dirname, "../data/malha"),
  raizApi: require("node:path").resolve(__dirname, "../data/api"),
  raizPrivado: require("node:fs").mkdtempSync(require("node:path").join(require("node:os").tmpdir(), "ache-priv-")),
  alunoIdentificado: false,
};

// Verificador falso: o token é o próprio e-mail; "invalido" simula falha de assinatura.
async function verificarFalso(credential) {
  if (credential === "invalido") throw new Error("assinatura");
  return { sub: "1", email: credential, email_verified: !credential.startsWith("naoverificado"), name: "Fulana Teste", given_name: "Fulana" };
}

async function comServidor(fn) {
  const servidor = criarApp({ config, verificarToken: verificarFalso }).listen(0);
  const base = `http://127.0.0.1:${servidor.address().port}`;
  try { await fn(base); } finally { servidor.closeAllConnections(); servidor.close(); }
}

async function login(base, credential) {
  return fetch(base + "/auth/google", {
    method: "POST",
    headers: { "Content-Type": "application/json", Origin: base },
    body: JSON.stringify({ credential }),
    redirect: "manual",
  });
}

const cookieDe = (res) => res.headers.get("set-cookie").split(",").map((c) => c.split(";")[0]).join("; ");

test("emailAutorizado: domínio, subdomínio, lista extra e falsificações", () => {
  assert.ok(emailAutorizado("a@institutoponte.org.br", config));
  assert.ok(emailAutorizado("a@aluno.institutoponte.org.br", config));
  assert.ok(emailAutorizado("EXTRA@gmail.com", config));
  assert.ok(!emailAutorizado("a@gmail.com", config));
  assert.ok(!emailAutorizado("a@evilinstitutoponte.org.br", config));
  assert.ok(!emailAutorizado("a@institutoponte.org.br.evil.com", config));
  assert.ok(!emailAutorizado("", config));
});

test("sem login: login é público, o resto não", () => comServidor(async (base) => {
  assert.equal((await fetch(base + "/html/index.html")).status, 200);
  assert.equal((await fetch(base + "/js/login.js")).status, 200);
  for (const rota of ["/html/mapa.html", "/js/mapa.js", "/js/vendor/d3.min.js"]) {
    const r = await fetch(base + rota, { redirect: "manual" });
    assert.equal(r.status, 302, rota);
    assert.match(r.headers.get("location"), /index\.html$/);
  }
  for (const rota of ["/api/me", "/api/geo/br_uf", "/api/geo/municipios/SP"]) {
    assert.equal((await fetch(base + rota)).status, 401, rota);
  }
}));

test("login com token inválido, e-mail de fora ou não verificado é recusado", () => comServidor(async (base) => {
  assert.equal((await login(base, "invalido")).status, 401);
  assert.equal((await login(base, "a@gmail.com")).status, 403);
  assert.equal((await login(base, "naoverificado@institutoponte.org.br")).status, 403);
}));

test("login só aceita mesma origem e JSON", () => comServidor(async (base) => {
  const outra = await fetch(base + "/auth/google", {
    method: "POST", headers: { "Content-Type": "application/json", Origin: "http://evil.test" }, body: "{}",
  });
  assert.equal(outra.status, 403);
  const texto = await fetch(base + "/auth/google", { method: "POST", headers: { "Content-Type": "text/plain" }, body: "x" });
  assert.equal(texto.status, 415);
}));

test("com login: acessa mapa, malha e /api/me; logout derruba a sessão", () => comServidor(async (base) => {
  const res = await login(base, "fulana@aluno.institutoponte.org.br");
  assert.equal(res.status, 200);
  const cookie = cookieDe(res);
  assert.match(res.headers.get("set-cookie"), /httponly/i);
  const h = { headers: { Cookie: cookie } };

  assert.equal((await fetch(base + "/html/mapa.html", h)).status, 200);
  const me = await (await fetch(base + "/api/me", h)).json();
  assert.equal(me.usuario.email, "fulana@aluno.institutoponte.org.br");
  assert.equal((await fetch(base + "/api/geo/br_uf", h)).status, 200);
  assert.equal((await fetch(base + "/api/geo/municipios/SP", h)).status, 200);
  assert.equal((await fetch(base + "/api/geo/municipios/XX", h)).status, 404);
  assert.equal((await fetch(base + "/api/geo/municipios/..%2Fbr_uf", h)).status, 404);

  const saiu = await fetch(base + "/auth/logout", { method: "POST", headers: { "Content-Type": "application/json", Cookie: cookie } });
  assert.equal(saiu.status, 200);
  const cookieNovo = cookieDe(saiu);
  assert.equal((await fetch(base + "/api/me", { headers: { Cookie: cookieNovo } })).status, 401);
}));

test("API de dados: exige login, valida parâmetros por lista fechada e serve o pré-calculado", async () => {
  const fs = require("node:fs");
  const os = require("node:os");
  const path = require("node:path");
  const raizApi = fs.mkdtempSync(path.join(os.tmpdir(), "ache-api-"));
  const escrever = (rel, obj) => {
    fs.mkdirSync(path.dirname(path.join(raizApi, rel)), { recursive: true });
    fs.writeFileSync(path.join(raizApi, rel), JSON.stringify(obj));
  };
  escrever("recortes.json", {
    provas: { enem: { nome: "ENEM", etapas: ["em"], anos: [2024], redes: ["publica"], motivo_etapa: "Só EM." } },
    sexo: { valores: ["todos"], motivo: "sem sexo" }, renda: { disponivel: false, motivo: "sem renda" },
  });
  escrever("ufs.json", { 35: "SP" });
  escrever("mapa/enem_em_2024_publica/uf.json", [{ codigo: "35", valor: 500, n: 99, suprimido: false }]);
  escrever("municipio/SP.json", { 3550308: { populacao: 1, escolas: { em: { ano: 2023, lista: [] } }, contexto: {}, medalhas: [] } });

  const servidor = criarApp({ config: { ...config, raizApi }, verificarToken: verificarFalso }).listen(0);
  const base = `http://127.0.0.1:${servidor.address().port}`;
  try {
    assert.equal((await fetch(base + "/api/recortes")).status, 401);
    const h = { headers: { Cookie: cookieDe(await login(base, "a@institutoponte.org.br")) } };
    const q = "/api/mapa?nivel=uf&prova=enem&etapa=em&ano=2024";

    assert.equal((await fetch(base + "/api/recortes", h)).status, 200);
    const ok = await fetch(base + q, h);
    assert.equal(ok.status, 200);
    assert.deepEqual(await ok.json(), [{ codigo: "35", valor: 500, n: 99, suprimido: false }]);

    for (const [ruim, status] of [
      ["&prova=../../etc", 400], ["&nivel=x", 400], ["&etapa=ef2", 422], ["&ano=1999", 422],
      ["&sexo=f", 422], ["&renda=true", 422], ["&rede=privada", 422], ["&prova[]=enem", 400],
    ]) {
      const res = await fetch(base + q + ruim, h);
      assert.equal(res.status, status, ruim);
    }
    assert.equal((await fetch(base + "/api/mapa?nivel=municipio&uf=..&prova=enem&etapa=em&ano=2024", h)).status, 400);
    assert.equal((await fetch(base + "/api/mapa?nivel=municipio&uf=SP&prova=enem&etapa=em&ano=2024", h)).status, 404);

    assert.equal((await fetch(base + "/api/municipio/3550308?etapa=em", h)).status, 200);
    assert.equal((await fetch(base + "/api/municipio/3550309", h)).status, 404);
    assert.equal((await fetch(base + "/api/municipio/abc", h)).status, 400);
    assert.equal((await fetch(base + "/api/municipio/3550308?etapa=x", h)).status, 400);
  } finally { servidor.closeAllConnections(); servidor.close(); }
});

test("busca, favoritos, ficha da escola e medalhistas com auditoria e pseudonimização", async () => {
  const fs = require("node:fs");
  const os = require("node:os");
  const path = require("node:path");
  const raizApi = fs.mkdtempSync(path.join(os.tmpdir(), "ache-api-"));
  const raizPrivado = fs.mkdtempSync(path.join(os.tmpdir(), "ache-priv-"));
  const escrever = (raiz, rel, obj) => {
    fs.mkdirSync(path.dirname(path.join(raiz, rel)), { recursive: true });
    fs.writeFileSync(path.join(raiz, rel), JSON.stringify(obj));
  };
  escrever(raizApi, "ufs.json", { 35: "SP" });
  escrever(raizApi, "recortes.json", { provas: {}, sexo: {}, renda: {} });
  escrever(raizApi, "busca.json", {
    municipios: [["3550308", "São Paulo", "SP"], ["3509502", "Campinas", "SP"]],
    escolas: [["35910818", "ETEC DE SAO PAULO", "3550308", "SP"]],
  });
  escrever(raizApi, "escola/SP.json", { 35910818: { nome: "ETEC DE SAO PAULO", rede: "Estadual", municipio: "3550308", uf: "SP", series: { em: [] }, tem_medalhista: true, n_medalhistas: 1 } });
  escrever(raizPrivado, "medalhistas/SP.json", {
    3550308: [{ pseudonimo: "A.B. #ABC123", nome: "ANA BELA", medalha: "Ouro", olimpiada: "OBMEP", ano: 2024, escola: "ETEC", escola_inep: "35910818", fonte: "http://premiacao.obmep.org.br/19obmep/mapa.htm" }],
  });

  const abrir = (alunoIdentificado) => criarApp({ config: { ...config, raizApi, raizPrivado, alunoIdentificado }, verificarToken: verificarFalso }).listen(0);
  const servidor = abrir(false);
  const base = `http://127.0.0.1:${servidor.address().port}`;
  try {
    assert.equal((await fetch(base + "/api/busca?q=sao")).status, 401);
    assert.equal((await fetch(base + "/api/municipio/3550308/medalhistas")).status, 401);
    const cookie = cookieDe(await login(base, "ana@institutoponte.org.br"));
    const h = { headers: { Cookie: cookie } };
    const json = { "Content-Type": "application/json", Cookie: cookie, Origin: base };

    // Busca: sem acento, por UF, município e escola (nome ou INEP).
    const achados = await (await fetch(base + "/api/busca?q=sao%20pa", h)).json();
    assert.deepEqual(achados.map((a) => a.tipo), ["uf", "municipio", "escola"]);
    assert.equal((await (await fetch(base + "/api/busca?q=3591", h)).json())[0].id, "35910818");
    assert.equal((await (await fetch(base + "/api/busca?q=sp", h)).json())[0].tipo, "uf");
    assert.deepEqual(await (await fetch(base + "/api/busca?q=a", h)).json(), []);
    assert.equal((await fetch(base + "/api/busca?q=" + "x".repeat(81), h)).status, 400);

    // Ficha da escola.
    assert.equal((await (await fetch(base + "/api/escola/35910818", h)).json()).municipio_nome, "São Paulo");
    assert.equal((await fetch(base + "/api/escola/12345678", h)).status, 404);
    assert.equal((await fetch(base + "/api/escola/abc", h)).status, 400);

    // Medalhistas: pseudonimizado por padrão e cada abertura é auditada.
    const lista = await (await fetch(base + "/api/municipio/3550308/medalhistas", h)).json();
    assert.equal(lista.identificado, false);
    assert.equal(lista.lista[0].pseudonimo, "A.B. #ABC123");
    assert.equal("nome" in lista.lista[0], false);
    assert.equal(lista.lista[0].fonte, "http://premiacao.obmep.org.br/19obmep/mapa.htm");
    await fetch(base + "/api/municipio/3550308/medalhistas", h);
    const linhas = fs.readFileSync(path.join(raizPrivado, "auditoria.jsonl"), "utf8").trim().split("\n").map(JSON.parse);
    assert.equal(linhas.length, 2);
    assert.equal(linhas[0].email, "ana@institutoponte.org.br");
    assert.equal(linhas[0].municipio, "3550308");

    // Favoritos: só itens que existem, por usuário, só mesma origem.
    const post = (corpo, extra = {}) => fetch(base + "/api/favoritos", { method: "POST", headers: { ...json, ...extra }, body: JSON.stringify(corpo) });
    assert.equal((await post({ tipo: "municipio", id: "3550308" })).status, 201);
    assert.equal((await post({ tipo: "municipio", id: "3550308" })).status, 201); // repetido não duplica
    assert.equal((await post({ tipo: "escola", id: "35910818" })).status, 201);
    assert.equal((await post({ tipo: "escola", id: "00000000" })).status, 400);
    assert.equal((await post({ tipo: "aluno", id: "x" })).status, 400);
    assert.equal((await post({ tipo: "municipio", id: "3550308" }, { Origin: "http://evil.test" })).status, 403);
    assert.equal((await (await fetch(base + "/api/favoritos", h)).json()).length, 2);

    const outra = { headers: { Cookie: cookieDe(await login(base, "bia@institutoponte.org.br")) } };
    assert.deepEqual(await (await fetch(base + "/api/favoritos", outra)).json(), []);

    const apagado = await fetch(base + "/api/favoritos/municipio/3550308", { method: "DELETE", headers: json, body: "{}" });
    assert.equal((await apagado.json()).length, 1);
  } finally { servidor.closeAllConnections(); servidor.close(); }

  // Com o flag ligado o nome sai, e a auditoria registra que foi identificado.
  const ligado = abrir(true);
  try {
    const b = `http://127.0.0.1:${ligado.address().port}`;
    const h = { headers: { Cookie: cookieDe(await login(b, "ana@institutoponte.org.br")) } };
    const lista = await (await fetch(b + "/api/municipio/3550308/medalhistas", h)).json();
    assert.equal(lista.lista[0].nome, "ANA BELA");
    const ultima = fs.readFileSync(path.join(raizPrivado, "auditoria.jsonl"), "utf8").trim().split("\n").map(JSON.parse).pop();
    assert.equal(ultima.identificado, true);
  } finally { ligado.closeAllConnections(); ligado.close(); }
});

// Vercel: disco somente leitura, mas com Redis a lista de medalhistas funciona e a auditoria vai para o Redis.
test("medalhistas e auditoria via Redis quando o disco é somente leitura", async () => {
  const fs = require("node:fs");
  const os = require("node:os");
  const path = require("node:path");
  const guardado = new Map([["medalhistas:3550308", JSON.stringify([{ pseudonimo: "A.B. #1", nome: "ANA BELA", medalha: "Ouro", olimpiada: "OBMEP", ano: 2024, escola: "ETEC", fonte: "http://f" }])]]);
  const auditoria = [];
  const redisFalso = require("node:http").createServer((req, res) => {
    let corpo = "";
    req.on("data", (c) => (corpo += c));
    req.on("end", () => {
      const [cmd, chave, valor] = JSON.parse(corpo);
      if (req.headers.authorization !== "Bearer tok") { res.statusCode = 401; return res.end("{}"); }
      if (cmd === "GET") return res.end(JSON.stringify({ result: guardado.get(chave) ?? null }));
      if (cmd === "RPUSH") { auditoria.push(JSON.parse(valor)); return res.end(JSON.stringify({ result: auditoria.length })); }
      res.end(JSON.stringify({ result: null }));
    });
  }).listen(0);
  const redis = { url: `http://127.0.0.1:${redisFalso.address().port}`, token: "tok" };
  const raizApi = fs.mkdtempSync(path.join(os.tmpdir(), "ache-api-"));
  fs.writeFileSync(path.join(raizApi, "recortes.json"), "{}");
  fs.writeFileSync(path.join(raizApi, "ufs.json"), JSON.stringify({ 35: "SP" }));
  const abrir = (cfg) => criarApp({ config: { ...config, raizApi, somenteLeitura: true, alunoIdentificado: true, ...cfg }, verificarToken: verificarFalso }).listen(0);
  const sem = abrir({});
  const com = abrir({ redis });
  try {
    const baseSem = `http://127.0.0.1:${sem.address().port}`;
    const hSem = { headers: { Cookie: cookieDe(await login(baseSem, "ana@institutoponte.org.br")) } };
    assert.equal((await fetch(baseSem + "/api/municipio/3550308/medalhistas", hSem)).status, 503);

    const base = `http://127.0.0.1:${com.address().port}`;
    const h = { headers: { Cookie: cookieDe(await login(base, "ana@institutoponte.org.br")) } };
    const lista = await (await fetch(base + "/api/municipio/3550308/medalhistas", h)).json();
    assert.equal(lista.lista[0].nome, "ANA BELA");
    assert.equal(lista.lista[0].fonte, "http://f");
    assert.equal(auditoria.length, 1);
    assert.equal(auditoria[0].email, "ana@institutoponte.org.br");
    assert.equal(auditoria[0].identificado, true);
  } finally {
    for (const x of [sem, com, redisFalso]) { x.closeAllConnections(); x.close(); }
  }
});
