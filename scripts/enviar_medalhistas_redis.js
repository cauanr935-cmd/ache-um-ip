// Envia os medalhistas (data/privado/medalhistas/<UF>.json) e os alunos do IP (alunos_ip_mapa.json) para o Redis privado (Upstash / Vercel KV), uma chave por município:
//   medalhistas:<ibge>  ->  JSON da lista. Rode depois de src/api_precompute.py. Precisa de KV_REST_API_URL e
//   KV_REST_API_TOKEN (no .env ou no ambiente). Os nomes nunca vão para o git.
const fs = require("node:fs");
const path = require("node:path");
const { criarRedis } = require("../server/redis");

try {
  process.loadEnvFile(path.resolve(__dirname, "../.env"));
} catch (err) {
  if (err.code !== "ENOENT") throw err;
}

const url = process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL;
const token = process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN;
if (!url || !token) {
  console.error("Defina KV_REST_API_URL e KV_REST_API_TOKEN (veja .env.example).");
  process.exit(1);
}

const redis = criarRedis({ url, token });
const pasta = path.resolve(__dirname, "../data/privado/medalhistas");
const LIMITE_BYTES = 700 * 1024; // as requisições do Upstash têm teto de ~1 MB

async function main() {
  let lote = [];
  let bytes = 0;
  let total = 0;
  const enviar = async () => {
    if (!lote.length) return;
    await redis.pipeline(lote);
    total += lote.length;
    lote = [];
    bytes = 0;
  };
  for (const arquivo of fs.readdirSync(pasta).filter((f) => f.endsWith(".json")).sort()) {
    const porMunicipio = JSON.parse(fs.readFileSync(path.join(pasta, arquivo), "utf8"));
    for (const [ibge, lista] of Object.entries(porMunicipio)) {
      const valor = JSON.stringify(lista);
      if (bytes + valor.length > LIMITE_BYTES) await enviar();
      lote.push(["SET", "medalhistas:" + ibge, valor]);
      bytes += valor.length;
    }
    console.log(arquivo, "ok");
  }
  await enviar();
  console.log("Enviados", total, "municípios.");

  // Alunos do Instituto Ponte para o filtro do mapa (scripts/gerar_alunos_ip_mapa.js), numa única chave.
  const alunosIP = path.resolve(__dirname, "../data/privado/alunos_ip_mapa.json");
  if (fs.existsSync(alunosIP)) {
    await redis.cmd("SET", "alunos_ip", fs.readFileSync(alunosIP, "utf8"));
    console.log("Alunos do IP enviados.");
  }
}

main().catch((err) => { console.error(err); process.exit(1); });
