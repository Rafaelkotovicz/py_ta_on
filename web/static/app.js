// SmartGate - JS leve, sem frameworks.
// Estrategia: polling periodico via fetch (sem WebSocket, para poupar
// RAM do ESP32). Cada pagina ativa apenas o loop de que precisa.

const POLL_MS = 4000;

function el(id) { return document.getElementById(id); }

function badge(resultado) {
  const r = (resultado || "").toUpperCase();
  if (r === "LIBERADO" || r === "APROVADA") return '<span class="badge ok">' + r + "</span>";
  if (r === "NEGADO" || r === "NEGADA") return '<span class="badge bad">' + r + "</span>";
  return '<span class="badge warn">' + r + "</span>";
}

async function getJSON(url) {
  const res = await fetch(url);
  return res.json();
}

// ---------------- Dashboard ----------------
async function loadStats() {
  try {
    const s = await getJSON("/api/stats");
    el("stat-usuarios").textContent = s.usuarios;
    el("stat-acessos").textContent = s.acessos;
    el("stat-negados").textContent = s.negados;
    el("stat-pendentes").textContent = s.pendentes;
  } catch (e) {}
}

// ---------------- Logs ----------------
async function loadLogs() {
  try {
    const logs = await getJSON("/api/logs");
    const body = el("logs-body");
    if (!logs.length) {
      body.innerHTML = '<tr><td colspan="5" class="empty">Nenhum log ainda</td></tr>';
      return;
    }
    body.innerHTML = logs.map(function (l) {
      return "<tr><td>" + (l.uid || "-") + "</td><td>" + (l.data_hora || "-") +
        "</td><td>" + (l.metodo || "-") + "</td><td>" + (l.nivel_acesso || "-") +
        "</td><td>" + badge(l.resultado) + "</td></tr>";
    }).join("");
  } catch (e) {}
}

// ---------------- Solicitacoes ----------------
async function loadSolicitacoes() {
  try {
    const items = await getJSON("/api/solicitacoes");
    const body = el("sol-body");
    if (!items.length) {
      body.innerHTML = '<tr><td colspan="5" class="empty">Nenhuma solicitacao pendente</td></tr>';
      return;
    }
    body.innerHTML = items.map(function (s) {
      return "<tr><td>" + s.id + "</td><td>" + (s.uid || "-") + "</td><td>" +
        (s.data_hora || "-") + "</td><td>" + badge(s.status) +
        '</td><td><button class="btn ok" onclick="decidir(' + s.id +
        ',true)">Aprovar</button> <button class="btn bad" onclick="decidir(' +
        s.id + ',false)">Negar</button></td></tr>";
    }).join("");
  } catch (e) {}
}

async function decidir(id, aprovar) {
  const url = aprovar ? "/api/solicitacoes/aprovar" : "/api/solicitacoes/negar";
  try {
    await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: "id=" + id,
    });
  } catch (e) {}
  loadSolicitacoes();
}

// ---------------- Bootstrap por pagina ----------------
function startPolling(fn) {
  fn();
  setInterval(fn, POLL_MS);
}

window.addEventListener("load", function () {
  if (el("stat-usuarios")) startPolling(loadStats);
  if (el("logs-body")) startPolling(loadLogs);
  if (el("sol-body")) startPolling(loadSolicitacoes);
});
