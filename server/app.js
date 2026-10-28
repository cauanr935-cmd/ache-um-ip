const path = require("node:path");
const express = require("express");
const compression = require("compression");
const cookieSession = require("cookie-session");
const { emailAutorizado, sessaoDoPayload, usuarioPublico } = require("./auth");

// Páginas e arquivos que o visitante ainda não logado precisa para ver a tela de login.
const PUBLICOS = new Set([
  "/html/index.html",
  "/html/sobre.html",
  "/css/style.css",
  "/js/login.js",
  "/assets/placeholder_usuario.png",
  "/assets/logo-instituto-ponte.png",
]);

const { UFS } = require("./ufs");
const { criarDados } = require("./dados");

function criarApp({ config, verificarToken }) {
  const app = express();
  app.disable("x-powered-by");
  app.set("trust proxy", 1);

  app.use((req, res, next) => {
    res.set({
      "X-Content-Type-Options": "nosniff",
      "Referrer-Policy": "same-origin",
      "X-Frame-Options": "DENY",
      // Google Identity Services (login) precisa de script, frame e estilo do Google.
      "Content-Security-Policy": [
        "default-src 'self'",
        "script-src 'self' https://accounts.google.com/gsi/client",
        "frame-src https://accounts.google.com/gsi/",
        "style-src 'self' 'unsafe-inline' https://accounts.google.com/gsi/style https://fonts.googleapis.com",
        "font-src https://fonts.gstatic.com",
        "img-src 'self' data: https:",
        "connect-src 'self' https://accounts.google.com/gsi/",
      ].join("; "),
    });
    next();
  });

  app.use(compression());
  app.use(cookieSession({
    name: "ache_sessao",
    keys: [config.segredoSessao],
    httpOnly: true,
    sameSite: "lax",
    secure: config.producao,
    maxAge: config.horasSessao * 3600 * 1000,
  }));

  // Sessão expirada no servidor vale como não logado, mesmo com o cookie ainda no navegador.
  const sessaoValida = (req) => Boolean(req.session && req.session.expira > Date.now());

  function exigirLogin(req, res, next) {
    if (sessaoValida(req)) return next();
    req.session = null;
    if (req.path.startsWith("/api/") || req.method !== "GET") return res.status(401).json({ erro: "nao_autenticado" });
    return res.redirect("/html/index.html");
  }

  // Requisições que mudam estado só valem se vierem da própria origem e como JSON.
  function exigirMesmaOrigem(req, res, next) {
    const origem = req.get("origin");
    if (origem && new URL(origem).host !== req.get("host")) return res.status(403).json({ erro: "origem_invalida" });
    if (!req.is("application/json")) return res.status(415).json({ erro: "use_json" });
    next();
  }

  app.use(express.json({ limit: "10kb" }));

  // ---- Autenticação ----
  app.get("/auth/config", (req, res) => res.json({ clientId: config.googleClientId }));

  app.post("/auth/google", exigirMesmaOrigem, async (req, res) => {
    const credential = req.body && req.body.credential;
    if (typeof credential !== "string" || credential.length > 4096) return res.status(400).json({ erro: "credencial_invalida" });

    let payload;
    try {
      payload = await verificarToken(credential);
    } catch {
      return res.status(401).json({ erro: "token_invalido" });
    }
    if (!payload || payload.email_verified !== true || !emailAutorizado(payload.email, config)) {
      return res.status(403).json({ erro: "email_nao_autorizado" });
    }
    req.session = sessaoDoPayload(payload, config);
    res.json({ usuario: usuarioPublico(req.session) });
  });

  app.post("/auth/logout", exigirMesmaOrigem, (req, res) => {
    req.session = null;
    res.json({ ok: true });
  });

  app.get("/api/me", exigirLogin, (req, res) => res.json({ usuario: usuarioPublico(req.session) }));

  // ---- Malha (TopoJSON), só para logados. A UF vem de uma lista fechada. ----
  app.get("/api/geo/br_uf", exigirLogin, (req, res) => {
    res.type("application/json").set("Cache-Control", "private, max-age=86400");
    res.sendFile(path.join(config.raizMalha, "br_uf.topojson"));
  });

  app.get("/api/geo/municipios/:uf", exigirLogin, (req, res) => {
    const uf = String(req.params.uf).toUpperCase();
    if (!UFS.has(uf)) return res.status(404).json({ erro: "uf_desconhecida" });
    res.type("application/json").set("Cache-Control", "private, max-age=86400");
    res.sendFile(path.join(config.raizMalha, "municipios", uf + ".topojson"));
  });

  // ---- Dados do mapa (pré-computados, specs.md 6.2) ----
  criarDados(config).registrar(app, { exigirLogin, exigirMesmaOrigem });

  // ---- Páginas ----
  app.get("/", (req, res) => res.redirect(sessaoValida(req) ? "/html/mapa.html" : "/html/index.html"));

  // Arquivos públicos primeiro, o resto do front só depois do login.
  const estatico = express.static(config.raizFront, { index: false, dotfiles: "ignore" });
  app.use((req, res, next) => (PUBLICOS.has(req.path) ? estatico(req, res, next) : next()));
  app.use("/api", exigirLogin);
  app.use(exigirLogin, estatico);

  app.use((req, res) => res.status(404).json({ erro: "nao_encontrado" }));
  return app;
}

module.exports = { criarApp, UFS };
