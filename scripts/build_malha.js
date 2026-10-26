// Gera a malha do mapa em TopoJSON a partir da malha municipal oficial do IBGE
// (data/raw/ibge/BR_Municipios_2025.zip, resolução máxima).
//
// Saídas em data/malha/ (servidas pelo back-end, atrás do login):
//   br_uf.topojson            27 UFs (união dos municípios), simplificado: é o que carrega primeiro
//   municipios/<UF>.topojson  municípios da UF, sem simplificação (só quantização fina)
//
// Uso: npm run malha
const fs = require("node:fs");
const path = require("node:path");
const { execFileSync } = require("node:child_process");
const shapefile = require("shapefile");
const { topology } = require("topojson-server");
const { presimplify, simplify } = require("topojson-simplify");
const { merge, quantize } = require("topojson-client");

const RAIZ = path.resolve(__dirname, "..");
const ZIP = path.join(RAIZ, "data/raw/ibge/BR_Municipios_2025.zip");
const SAIDA = path.join(RAIZ, "data/malha");
const TMP = fs.mkdtempSync(path.join(require("node:os").tmpdir(), "malha-"));

// Quantização por UF: 1e5 passos na maior dimensão da caixa da UF (cerca de 10 m no maior estado).
const QUANT_MUNICIPIO = 1e5;
// Contorno do Brasil para a tela inicial (RN 2: carregar rápido). Mantém só a fração dos
// vértices com maior área de triângulo e regrava quantizado numa grade mais grossa.
const QUANT_BR = 1e4;
const FRACAO_PONTOS_BR = 0.05;

function arredondar(coords, casas) {
  const f = 10 ** casas;
  return coords.map((c) => (Array.isArray(c[0]) ? arredondar(c, casas) : [Math.round(c[0] * f) / f, Math.round(c[1] * f) / f]));
}

async function separarPorUF() {
  execFileSync("unzip", ["-oq", ZIP, "-d", TMP]);
  const origem = await shapefile.open(path.join(TMP, "BR_Municipios_2025.shp"), undefined, { encoding: "utf-8" });
  const fluxos = new Map();
  let total = 0;
  for (let r = await origem.read(); !r.done; r = await origem.read()) {
    const p = r.value.properties;
    if (!fluxos.has(p.SIGLA_UF)) fluxos.set(p.SIGLA_UF, fs.createWriteStream(path.join(TMP, p.SIGLA_UF + ".ndjson")));
    const feature = {
      type: "Feature",
      properties: { codigo: p.CD_MUN, nome: p.NM_MUN, uf: p.SIGLA_UF, area_km2: p.AREA_KM2 },
      geometry: r.value.geometry,
      _uf: { codigo: p.CD_UF, nome: p.NM_UF, regiao: p.NM_REGIAO },
    };
    fluxos.get(p.SIGLA_UF).write(JSON.stringify(feature) + "\n");
    total++;
  }
  await Promise.all([...fluxos.values()].map((s) => new Promise((ok) => s.end(ok))));
  console.log(`${total} municípios em ${fluxos.size} UFs`);
  return [...fluxos.keys()].sort();
}

function tamanho(arquivo) {
  return (fs.statSync(arquivo).size / 1024).toFixed(0) + " KB";
}

async function main() {
  fs.mkdirSync(path.join(SAIDA, "municipios"), { recursive: true });
  const ufs = await separarPorUF();
  const contornos = [];

  for (const sigla of ufs) {
    const features = fs.readFileSync(path.join(TMP, sigla + ".ndjson"), "utf8").trim().split("\n").map((l) => JSON.parse(l));
    const info = features[0]._uf;
    features.forEach((f) => delete f._uf);

    const topo = topology({ municipios: { type: "FeatureCollection", features } }, QUANT_MUNICIPIO);
    const arquivo = path.join(SAIDA, "municipios", sigla + ".topojson");
    fs.writeFileSync(arquivo, JSON.stringify(topo));

    // O contorno da UF vem da união dos municípios, então não sobra fresta entre os dois níveis.
    const uniao = merge(topo, topo.objects.municipios.geometries);
    contornos.push({
      type: "Feature",
      properties: { codigo: info.codigo, sigla, nome: info.nome, regiao: info.regiao },
      geometry: uniao,
    });
    console.log(sigla.padEnd(3), String(features.length).padStart(4), "municípios", tamanho(arquivo));
  }

  let brasil = presimplify(topology({ ufs: { type: "FeatureCollection", features: contornos } }));
  // Vértices colineares têm peso 0 e não contam para o corte.
  const pesos = brasil.arcs.flatMap((arco) => arco.map((p) => p[2])).filter((z) => Number.isFinite(z) && z > 0).sort((a, b) => a - b);
  brasil = quantize(simplify(brasil, pesos[Math.floor(pesos.length * (1 - FRACAO_PONTOS_BR))]), QUANT_BR);
  const arquivoBR = path.join(SAIDA, "br_uf.topojson");
  fs.writeFileSync(arquivoBR, JSON.stringify(brasil));
  console.log("br_uf.topojson", tamanho(arquivoBR));

  fs.rmSync(TMP, { recursive: true, force: true });
}

main().catch((e) => { console.error(e); process.exit(1); });
