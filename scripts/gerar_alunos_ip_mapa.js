// Junta os alunos do Instituto Ponte (src/coleta_alunos_ip.py) com a posição de cada município, para o mapa.
// Entrada:  data/privado/alunos_ip.json  {ibge: [aluno, ...]}
// Saída:    data/privado/alunos_ip_mapa.json  [{codigo, municipio, uf, lon, lat, alunos: [...]}]
// A posição é o centroide (ponderado pela área) do maior polígono do município, na malha de data/malha.
const fs = require("node:fs");
const path = require("node:path");
const { feature } = require("topojson-client");

const RAIZ = path.resolve(__dirname, "..");
const alunos = JSON.parse(fs.readFileSync(path.join(RAIZ, "data/privado/alunos_ip.json"), "utf8"));
const ufDe = JSON.parse(fs.readFileSync(path.join(RAIZ, "data/api/ufs.json"), "utf8"));

function centroideDoAnel(anel) {
  let area = 0, cx = 0, cy = 0;
  for (let i = 0, n = anel.length - 1; i < n; i++) {
    const [x0, y0] = anel[i], [x1, y1] = anel[i + 1];
    const f = x0 * y1 - x1 * y0;
    area += f; cx += (x0 + x1) * f; cy += (y0 + y1) * f;
  }
  return { area: Math.abs(area / 2), x: cx / (3 * area), y: cy / (3 * area) };
}

function centroide(geometria) {
  const poligonos = geometria.type === "Polygon" ? [geometria.coordinates] : geometria.coordinates;
  return poligonos.map((p) => centroideDoAnel(p[0])).sort((a, b) => b.area - a.area)[0];
}

const porUF = {};
for (const ibge of Object.keys(alunos)) (porUF[ufDe[ibge.slice(0, 2)]] ||= []).push(ibge);

const saida = [];
for (const [uf, codigos] of Object.entries(porUF)) {
  const topo = JSON.parse(fs.readFileSync(path.join(RAIZ, "data/malha/municipios", uf + ".topojson"), "utf8"));
  const municipios = new Map(feature(topo, topo.objects.municipios).features.map((f) => [f.properties.codigo, f]));
  for (const codigo of codigos) {
    const f = municipios.get(codigo);
    if (!f) { console.warn("Sem malha para", codigo); continue; }
    const c = centroide(f.geometry);
    saida.push({ codigo, municipio: f.properties.nome, uf, lon: +c.x.toFixed(5), lat: +c.y.toFixed(5), alunos: alunos[codigo] });
  }
}
saida.sort((a, b) => a.municipio.localeCompare(b.municipio, "pt-BR"));
fs.writeFileSync(path.join(RAIZ, "data/privado/alunos_ip_mapa.json"), JSON.stringify(saida));
console.log(saida.length, "municípios com alunos do IP,", saida.reduce((n, m) => n + m.alunos.length, 0), "alunos.");
