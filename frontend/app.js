const API = "";

// ── Health check ────────────────────────────────────────────────────────────
async function checkHealth() {
  try {
    const r = await fetch(`${API}/api/health`);
    const data = await r.json();
    const badge = document.getElementById("status-badge");
    if (data.mode === "live") {
      badge.textContent = "🟢 Modo ao vivo";
      badge.className = "badge badge-live";
    } else {
      badge.textContent = "🟡 Modo demonstração";
      badge.className = "badge badge-demo";
    }
  } catch {
    document.getElementById("status-badge").textContent = "🔴 Offline";
  }
}

// ── Simulator ────────────────────────────────────────────────────────────────
document.getElementById("sim-btn").addEventListener("click", async () => {
  const oddsA = parseFloat(document.getElementById("sim-odds-a").value) || 0;
  const oddsB = parseFloat(document.getElementById("sim-odds-b").value) || 0;
  const oddsC = parseFloat(document.getElementById("sim-odds-c").value) || 0;
  const stake = parseFloat(document.getElementById("sim-stake").value) || 100;
  const resultEl = document.getElementById("sim-result");

  if (oddsA < 1.01 || oddsB < 1.01) {
    resultEl.className = "sim-result no-arb";
    resultEl.innerHTML = "<h3>❌ Odds inválidas. Mínimo 1.01.</h3>";
    resultEl.classList.remove("hidden");
    return;
  }

  try {
    const params = new URLSearchParams({ odds_a: oddsA, odds_b: oddsB, stake });
    if (oddsC > 1.0) params.set("odds_c", oddsC);
    const r = await fetch(`${API}/api/simulate?${params}`);
    const data = await r.json();
    renderSimResult(data, stake, resultEl);
  } catch (e) {
    resultEl.className = "sim-result no-arb";
    resultEl.innerHTML = `<h3>Erro ao conectar com o servidor.</h3><p>${e.message}</p>`;
    resultEl.classList.remove("hidden");
  }
});

function renderSimResult(data, stake, el) {
  el.classList.remove("hidden");
  if (data.is_arbitrage) {
    const betsRows = data.bets
      .map(b => `
        <tr>
          <td>${escHtml(b.outcome)}</td>
          <td>${escHtml(b.bookmaker)}</td>
          <td><strong>${b.odds.toFixed(2)}</strong></td>
          <td>R$ ${b.stake.toFixed(2)}</td>
          <td style="color:var(--profit)">R$ ${b.profit_if_wins.toFixed(2)}</td>
        </tr>`)
      .join("");

    el.className = "sim-result profit";
    el.innerHTML = `
      <h3>✅ Arbitragem encontrada!</h3>
      <div class="result-profit-big">+R$ ${data.guaranteed_profit.toFixed(2)} (${data.profit_percent.toFixed(2)}%)</div>
      <p style="color:var(--text2);font-size:0.9rem">${escHtml(data.explanation)}</p>
      <table class="bets-table" style="margin-top:16px">
        <thead>
          <tr>
            <th>Resultado</th><th>Casa</th><th>Odd</th><th>Apostar</th><th>Se ganhar</th>
          </tr>
        </thead>
        <tbody>${betsRows}</tbody>
      </table>
      <p style="margin-top:12px;font-size:0.8rem;color:var(--text2)">
        Probabilidade implícita total: ${data.arb_percent.toFixed(2)}% (quanto menor, maior o lucro)
      </p>`;
  } else {
    el.className = "sim-result no-arb";
    el.innerHTML = `
      <h3>❌ Sem arbitragem nessas odds</h3>
      <div class="result-no-arb-big">Margem da banca: +${data.margin.toFixed(2)}%</div>
      <p style="color:var(--text2);font-size:0.9rem">${escHtml(data.explanation)}</p>
      <p style="margin-top:10px;font-size:0.85rem;color:var(--text2)">
        Probabilidade implícita total: <strong>${data.implied_probability_sum.toFixed(2)}%</strong>
        (precisa ser &lt; 100% para haver arbitragem)
      </p>`;
  }
}

// ── Scanner ──────────────────────────────────────────────────────────────────
document.getElementById("scan-btn").addEventListener("click", runScan);

async function runScan() {
  const btn = document.getElementById("scan-btn");
  const btnText = document.getElementById("scan-btn-text");
  const sport = document.getElementById("sport-select").value;
  const stake = parseFloat(document.getElementById("scan-stake").value) || 100;
  const minProfit = parseFloat(document.getElementById("min-profit").value) || 0;

  btn.disabled = true;
  btnText.innerHTML = `<span class="spinner"></span> Varrendo...`;

  const resultsList = document.getElementById("results-list");
  const emptyState = document.getElementById("results-empty");
  const scanInfo = document.getElementById("scan-info");
  resultsList.classList.add("hidden");
  emptyState.classList.remove("hidden");

  try {
    const params = new URLSearchParams({ sport, stake, min_profit: minProfit });
    const r = await fetch(`${API}/api/arbitrage?${params}`);
    const opportunities = await r.json();

    if (!Array.isArray(opportunities)) throw new Error("Resposta inválida do servidor.");

    scanInfo.classList.remove("hidden");
    scanInfo.textContent = `Encontradas ${opportunities.length} oportunidade(s) de arbitragem${opportunities.length > 0 ? " — clique para ver os detalhes de cada aposta." : "."}`;

    if (opportunities.length === 0) {
      emptyState.querySelector("p").textContent =
        "Nenhuma oportunidade de arbitragem encontrada no momento. Tente novamente mais tarde ou ajuste os filtros.";
      emptyState.classList.remove("hidden");
      resultsList.classList.add("hidden");
    } else {
      emptyState.classList.add("hidden");
      resultsList.classList.remove("hidden");
      resultsList.innerHTML = opportunities.map(renderArbCard).join("");
      // Bind expand/collapse
      resultsList.querySelectorAll(".arb-card-header").forEach(h => {
        h.addEventListener("click", () => {
          const body = h.nextElementSibling;
          const chevron = h.querySelector(".chevron");
          body.classList.toggle("expanded");
          chevron.classList.toggle("expanded-chevron");
        });
      });
    }
  } catch (e) {
    scanInfo.classList.remove("hidden");
    scanInfo.style.borderColor = "var(--loss)";
    scanInfo.textContent = `Erro: ${e.message}`;
  } finally {
    btn.disabled = false;
    btnText.textContent = "Varrer Agora";
  }
}

function renderArbCard(opp) {
  const time = opp.commence_time
    ? new Date(opp.commence_time).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })
    : "";

  const betsRows = opp.bets
    .map(b => `
      <tr>
        <td>${escHtml(b.outcome)}</td>
        <td style="color:var(--accent)">${escHtml(b.bookmaker)}</td>
        <td><strong>${b.odds.toFixed(2)}</strong></td>
        <td>R$ ${b.stake.toFixed(2)}</td>
        <td style="color:var(--profit)">R$ ${b.profit_if_wins.toFixed(2)}</td>
      </tr>`)
    .join("");

  return `
    <div class="arb-card">
      <div class="arb-card-header">
        <div class="arb-event">
          <span class="arb-sport">${escHtml(opp.sport)}</span>
          <span class="arb-teams">${escHtml(opp.home_team)} vs ${escHtml(opp.away_team)}</span>
          ${time ? `<span class="arb-time">📅 ${time}</span>` : ""}
        </div>
        <div class="arb-profit-badge">
          <span class="profit-pct">+${opp.profit_percent.toFixed(2)}%</span>
          <span class="profit-label">lucro garantido</span>
        </div>
        <span class="chevron">▼</span>
      </div>
      <div class="arb-card-body">
        <div class="arb-summary">
          <div class="summary-item">
            <span class="summary-label">Stake total</span>
            <span class="summary-value">R$ ${opp.total_stake.toFixed(2)}</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">Lucro garantido</span>
            <span class="summary-value green">R$ ${opp.guaranteed_profit.toFixed(2)}</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">Prob. implícita total</span>
            <span class="summary-value">${opp.arb_percent.toFixed(2)}%</span>
          </div>
        </div>
        <table class="bets-table">
          <thead>
            <tr><th>Resultado</th><th>Casa</th><th>Odd</th><th>Apostar</th><th>Retorno</th></tr>
          </thead>
          <tbody>${betsRows}</tbody>
        </table>
        <p style="margin-top:12px;font-size:0.8rem;color:var(--text2)">
          ⚠️ Verifique as odds diretamente nas casas antes de apostar — elas mudam constantemente.
          Confirme os limites de apostas e regras de cada casa.
        </p>
      </div>
    </div>`;
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ── Init ─────────────────────────────────────────────────────────────────────
checkHealth();
