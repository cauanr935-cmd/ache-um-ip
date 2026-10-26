const config = require("./config");
const { criarApp } = require("./app");
const { criarVerificadorGoogle } = require("./auth");

if (!config.googleClientId) {
  console.warn("Aviso: GOOGLE_CLIENT_ID não definido. O login com Google não vai funcionar (veja .env.example).");
}

const app = criarApp({ config, verificarToken: criarVerificadorGoogle(config) });

// Na Vercel o app é exportado como função; localmente sobe o servidor.
if (require.main === module) {
  app.listen(config.porta, () => console.log(`Ache um IP em http://localhost:${config.porta}`));
}

module.exports = app;
