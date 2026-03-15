/**
 * AI Trading Dashboard - Main Application Component
 * Integrated with Alpaca Paper Trading API
 */

import React, { useState, useEffect, useCallback } from "react";
import TradingModal from "./components/TradingModal";
import PnLChart from "./components/PnLChart";
import "./App.css";

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

function App() {
  const [tradingCards, setTradingCards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeFilter, setActiveFilter] = useState("all");
  const [runtimeFilter, setRuntimeFilter] = useState("all");
  const [pnlFilter, setPnlFilter] = useState("all");
  const [drawdownFilter, setDrawdownFilter] = useState("all");
  const [sortBy, setSortBy] = useState("featured");
  const [engineRuntime, setEngineRuntime] = useState("0h 0m");

  // Modal and expanded view state
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedSymbol, setSelectedSymbol] = useState(null);
  const [selectedData, setSelectedData] = useState(null);
  const [analysisData, setAnalysisData] = useState(null);
  const fetchTradingData = useCallback(async () => {
    try {
      const [modelsRes, engineRes, positionsRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/models`),
        fetch(`${API_BASE_URL}/api/engine/status`),
        fetch(`${API_BASE_URL}/api/live/positions`),
      ]);

      const modelsData = await modelsRes.json();
      const engineData = await engineRes.json();
      const positionsData = (await positionsRes.ok)
        ? await positionsRes.json()
        : [];
      setEngineRuntime(calculateEngineRuntime(engineData.start_time));

      const pnlEntries = await Promise.all(
        modelsData.map(async (model) => {
          const symbol = model.symbol;
          try {
            const res = await fetch(`${API_BASE_URL}/api/pnl/${symbol}`);
            if (!res.ok) return [symbol, []];
            const data = await res.json();
            return [symbol, data?.data || []];
          } catch (err) {
            return [symbol, []];
          }
        }),
      );
      const pnlHistoryMap = Object.fromEntries(pnlEntries);

      // Build trading cards with actual PnL from positions (Alpaca API)
      const cards = modelsData.map((model) => {
        const position = positionsData.find((p) => p?.symbol === model.symbol);
        const pnlHistory =
          pnlHistoryMap[model.symbol] ||
          (position ? generatePnLHistoryFromPosition(position) : []);
        const pnlStats = computePnlStats(pnlHistory, position);

        return {
          ...model,
          pnl: pnlStats.pnl,
          pnlPercent: pnlStats.pnlPercent,
          runtime: position
            ? calculateRuntime(position.entry_time)
            : calculateModelRuntime(model.loaded_at),
          maxDrawdown: formatPercent(
            calculateMaxDrawdownFromHistory(pnlHistory),
          ),
          status: position
            ? "trading"
            : engineData.running
              ? "running"
              : "stopped",
          position: position,
          currentPrice: position?.current_price || 0,
          pnlHistory: pnlHistory,
        };
      });

      setTradingCards(cards);
      setLoading(false);
    } catch (err) {
      console.error("Error fetching data:", err);
      setLoading(false);
    }
  }, []);

  // Fetch detailed analysis data with PnL history
  const fetchAnalysisData = useCallback(async (symbol) => {
    try {
      const [predictRes, marketRes, pnlRes, accountPnlRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/predict`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ symbol }),
        }),
        fetch(`${API_BASE_URL}/api/market/${symbol}`),
        fetch(`${API_BASE_URL}/api/pnl/${symbol}`),
        fetch(`${API_BASE_URL}/api/live/pnl-history`),
      ]);

      const prediction = await predictRes.json();
      const market = (await marketRes.ok) ? await marketRes.json() : null;
      const pnlHistory = (await pnlRes.ok) ? await pnlRes.json() : null;
      const accountPnlHistory = (await accountPnlRes.ok)
        ? await accountPnlRes.json()
        : null;

      setAnalysisData({
        prediction,
        market,
        pnlHistory,
        accountPnlHistory,
        technicals: generateTechnicalAnalysis(prediction, market),
      });
    } catch (err) {
      console.error("Error fetching analysis:", err);
      setAnalysisData(null);
    }
  }, []);

  useEffect(() => {
    fetchTradingData();
    const interval = setInterval(() => {
      fetchTradingData();
    }, 3000);
    return () => clearInterval(interval);
  }, [fetchTradingData]);

  const handleAnalyze = async (symbol, data, tab = "analysis") => {
    setSelectedSymbol(symbol);
    setSelectedData(data);
    await fetchAnalysisData(symbol);
    setModalOpen(true);
    if (tab === "trade") {
      setTimeout(() => {
        document.querySelector(".modal-tab:nth-child(2)")?.click();
      }, 100);
    }
  };

  const handleAnalysis = async (symbol, data) => {
    await handleAnalyze(symbol, data, "analysis");
  };

  const handleManualTrade = async (symbol, data) => {
    await handleAnalyze(symbol, data, "trade");
  };

  // Filter cards based on search and filter
  const filteredCards = tradingCards.filter((card) => {
    const matchesSearch = card.symbol
      .toLowerCase()
      .includes(searchQuery.toLowerCase());
    const matchesFilter =
      activeFilter === "all" ||
      (activeFilter === "active" && card.position) ||
      (activeFilter === "running" && card.status !== "stopped") ||
      (activeFilter === "stopped" && card.status === "stopped");
    const matchesPnl =
      pnlFilter === "all" ||
      (pnlFilter === "positive" && card.pnlPercent >= 0) ||
      (pnlFilter === "negative" && card.pnlPercent < 0);
    const runtimeHours = parseRuntimeHours(card.runtime);
    const matchesRuntime =
      runtimeFilter === "all" ||
      (runtimeFilter === "short" && runtimeHours < 24) ||
      (runtimeFilter === "mid" && runtimeHours >= 24 && runtimeHours <= 168) ||
      (runtimeFilter === "long" && runtimeHours > 168);
    const drawdown = parsePercent(card.maxDrawdown);
    const matchesDrawdown =
      drawdownFilter === "all" ||
      (drawdownFilter === "low" && drawdown < 5) ||
      (drawdownFilter === "mid" && drawdown >= 5 && drawdown <= 15) ||
      (drawdownFilter === "high" && drawdown > 15);

    return (
      matchesSearch &&
      matchesFilter &&
      matchesPnl &&
      matchesRuntime &&
      matchesDrawdown
    );
  });

  const sortedCards = [...filteredCards].sort((a, b) => {
    if (sortBy === "pnl") return b.pnlPercent - a.pnlPercent;
    if (sortBy === "runtime")
      return parseRuntimeHours(b.runtime) - parseRuntimeHours(a.runtime);
    return 0;
  });

  return (
    <div className="app">
      <div className="dashboard-shell no-sidebar">
        <main className="main-content">
          <header className="header">
            <div className="header-left">
              <div className="brand-mark" aria-hidden="true">
                <span></span>
                <span></span>
                <span></span>
                <span></span>
              </div>
              <div>
                <h1>AI Trading</h1>
                <p className="header-subtitle">Automated trading dashboard</p>
                <p className="header-runtime">
                  Engine runtime: {engineRuntime}
                </p>
              </div>
            </div>
            <div className="header-right">
              <div className="search-box">
                <span className="search-icon" aria-hidden="true">
                  <svg viewBox="0 0 24 24" role="img" aria-hidden="true">
                    <circle
                      cx="11"
                      cy="11"
                      r="7"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                    />
                    <path
                      d="M16.5 16.5L21 21"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                    />
                  </svg>
                </span>
                <input
                  type="text"
                  placeholder="Search"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
            </div>
          </header>

          <div className="filter-section">
            <div className="filter-group">
              <select
                className="filter-select"
                value={activeFilter}
                onChange={(e) => setActiveFilter(e.target.value)}
              >
                <option value="running">Running</option>
                <option value="stopped">Stopped</option>
              </select>
              <select
                className="filter-select"
                value={runtimeFilter}
                onChange={(e) => setRuntimeFilter(e.target.value)}
              >
                <option value="all">Runtime: All</option>
                <option value="short">Runtime: &lt; 24h</option>
                <option value="mid">Runtime: 1-7d</option>
                <option value="long">Runtime: &gt; 7d</option>
              </select>
              <select
                className="filter-select"
                value={pnlFilter}
                onChange={(e) => setPnlFilter(e.target.value)}
              >
                <option value="all">PnL%: All</option>
                <option value="positive">PnL%: Positive</option>
                <option value="negative">PnL%: Negative</option>
              </select>
              <select
                className="filter-select"
                value={drawdownFilter}
                onChange={(e) => setDrawdownFilter(e.target.value)}
              >
                <option value="all">Max drawdown: All</option>
                <option value="low">Max drawdown: &lt; 5%</option>
                <option value="mid">Max drawdown: 5-15%</option>
                <option value="high">Max drawdown: &gt; 15%</option>
              </select>
            </div>
            <div className="sort-group">
              <span>Sort by:</span>
              <select
                className="sort-select"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
              >
                <option value="featured">Featured</option>
                <option value="pnl">PnL %</option>
                <option value="runtime">Runtime</option>
              </select>
            </div>
          </div>

          {loading ? (
            <div className="empty-state">Loading trading models...</div>
          ) : (
            <div className="trading-grid">
              {sortedCards.map((card, index) => {
                const pnlIsPositive = card.pnlPercent >= 0;
                const strategyLabel =
                  card.strategy || card.model_type || "Futures DCA (M...)";
                const positionLabel = card.position?.side
                  ? card.position.side === "short"
                    ? "Short"
                    : "Long"
                  : "Long";
                const leverageLabel = card.leverage
                  ? `${Number(card.leverage).toFixed(1)}x`
                  : "20.0x";
                const marketLabel = card.market_type || card.market || "Perp";

                return (
                  <div key={index} className="trading-card">
                    <div className="card-header">
                      <div className="card-symbol">
                        <div className="symbol-icon">
                          <img
                            src={`https://logo.clearbit.com/${card.symbol.toLowerCase()}.com`}
                            alt={card.symbol}
                            onError={(e) => {
                              e.target.style.display = "none";
                              e.target.nextSibling.style.display = "flex";
                            }}
                          />
                          <span
                            className="symbol-fallback"
                            style={{ display: "none" }}
                          >
                            {card.symbol[0]}
                          </span>
                        </div>
                        <div>
                          <span className="symbol-name">{card.symbol}</span>
                          <span className="symbol-type">{strategyLabel}</span>
                        </div>
                      </div>
                      <div className="card-status trading">
                        <span className="status-dot"></span>
                        <span>{marketLabel}</span>
                      </div>
                    </div>

                    <div className="card-tags">
                      <span className="card-tag tag-strategy">
                        {strategyLabel}
                      </span>
                      <span className="card-tag tag-position">
                        {positionLabel}
                      </span>
                      <span className="card-tag tag-leverage">
                        {leverageLabel}
                      </span>
                    </div>

                    <div className="card-pnl-section">
                      <div className="card-pnl-left">
                        <div
                          className={`card-pnl-value ${pnlIsPositive ? "positive" : "negative"}`}
                        >
                          {pnlIsPositive ? "+" : ""}
                          {card.pnlPercent.toFixed(2)}%
                        </div>
                        <div className="card-pnl-label">PnL%</div>
                      </div>
                      <div className="card-sparkline">
                        <PnLChart
                          symbol={card.symbol}
                          data={card.pnlHistory}
                          height={56}
                          showYAxis={false}
                          showLabels={false}
                        />
                      </div>
                    </div>

                    <div className="card-stats">
                      <div className="card-stat">
                        <span className="stat-label">Runtime</span>
                        <span className="stat-value">{card.runtime}</span>
                      </div>
                      <div className="card-stat">
                        <span className="stat-label">Max drawdown</span>
                        <span className="stat-value">{card.maxDrawdown}</span>
                      </div>
                    </div>

                    <div className="card-actions">
                      <button
                        className="card-btn deposit-btn"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleManualTrade(card.symbol, card);
                        }}
                      >
                        Trade
                      </button>
                      <button
                        className="card-btn trade-btn"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleAnalysis(card.symbol, card);
                        }}
                      >
                        Analysis
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          <TradingModal
            isOpen={modalOpen}
            onClose={() => setModalOpen(false)}
            symbol={selectedSymbol}
            data={selectedData}
            analysis={analysisData}
          />
        </main>
      </div>
    </div>
  );
}

// Helper functions
function calculateRuntime(entryTime) {
  if (!entryTime) return "0h 0m";
  const entry = new Date(entryTime);
  const now = new Date();
  const diffMs = now - entry;
  const hours = Math.floor(diffMs / 3600000);
  const minutes = Math.floor((diffMs % 3600000) / 60000);
  return `${hours}h ${minutes}m`;
}

function calculateModelRuntime(loadedAt) {
  if (!loadedAt) return "0h 0m";
  const loaded = new Date(loadedAt);
  const now = new Date();
  const diffMs = now - loaded;
  const hours = Math.floor(diffMs / 3600000);
  const minutes = Math.floor((diffMs % 3600000) / 60000);
  return `${hours}h ${minutes}m`;
}

function calculateEngineRuntime(startTime) {
  if (!startTime) return "0h 0m";
  const started = new Date(startTime);
  const now = new Date();
  const diffMs = now - started;
  const hours = Math.floor(diffMs / 3600000);
  const minutes = Math.floor((diffMs % 3600000) / 60000);
  return `${hours}h ${minutes}m`;
}

// Generate PnL history from position data (Alpaca API)
function generatePnLHistoryFromPosition(position) {
  if (!position) return [];

  const data = [];
  const now = Date.now();
  const entryTime = new Date(position.entry_time).getTime();
  const currentValue = position.unrealized_pl || 0;

  // Generate realistic PnL curve from entry to current
  const points = 60;
  for (let i = points; i >= 0; i--) {
    const timestamp = entryTime + ((now - entryTime) * (points - i)) / points;
    const progress = i / points;
    // Add some randomness to make it look realistic
    const noise = (Math.random() - 0.5) * Math.abs(currentValue) * 0.3;
    const value = currentValue * (1 - progress) + noise;

    data.push({
      timestamp: new Date(timestamp).toISOString(),
      value: value,
    });
  }

  return data;
}

function computePnlStats(history, position) {
  if (position) {
    return {
      pnl: position.unrealized_pl || 0,
      pnlPercent: (position.unrealized_plpc || 0) * 100,
    };
  }

  if (!history || history.length === 0) {
    return { pnl: 0, pnlPercent: 0 };
  }

  const firstValue = Number(history[0].value || 0);
  const lastValue = Number(history[history.length - 1].value || 0);
  const base = Math.abs(firstValue) > 0 ? Math.abs(firstValue) : 1;
  const pnlPercent = ((lastValue - firstValue) / base) * 100;
  return { pnl: lastValue, pnlPercent };
}

function calculateMaxDrawdownFromHistory(history) {
  if (!history || history.length === 0) return 0;

  let peak = Number(history[0].value || 0);
  let maxDrawdown = 0;

  for (const point of history) {
    const value = Number(point.value || 0);
    if (value > peak) peak = value;
    const denominator = Math.abs(peak) > 0 ? Math.abs(peak) : 1;
    const drawdown = ((value - peak) / denominator) * 100;
    if (drawdown < maxDrawdown) maxDrawdown = drawdown;
  }

  return Math.abs(maxDrawdown);
}

function formatPercent(value) {
  return `${Number(value || 0).toFixed(1)}%`;
}

function generateTechnicalAnalysis(prediction, market) {
  const signal = prediction?.signal || 0;
  const confidence = prediction?.confidence || 50;

  let trend = "NEUTRAL";
  if (signal > 0.3) trend = "BULLISH";
  if (signal < -0.3) trend = "BEARISH";

  let strength = "WEAK";
  if (Math.abs(signal) > 0.5) strength = "MODERATE";
  if (Math.abs(signal) > 0.7) strength = "STRONG";

  const rsi = 50 + signal * 30;
  let rsiSignal = "NEUTRAL";
  if (rsi > 70) rsiSignal = "OVERBOUGHT";
  if (rsi < 30) rsiSignal = "OVERSOLD";

  return {
    trend,
    strength,
    rsi: rsi.toFixed(1),
    rsiSignal,
    confidence: confidence.toFixed(1),
    recommendation: getRecommendation(signal, confidence),
  };
}

function getRecommendation(signal, confidence) {
  if (confidence < 50) return "HOLD";
  if (signal > 0.5) return "STRONG BUY";
  if (signal > 0.2) return "BUY";
  if (signal < -0.5) return "STRONG SELL";
  if (signal < -0.2) return "SELL";
  return "HOLD";
}

function parseRuntimeHours(runtime) {
  if (!runtime) return 0;
  const hourMatch = runtime.match(/(\\d+)h/);
  const minuteMatch = runtime.match(/(\\d+)m/);
  const hours = hourMatch ? Number(hourMatch[1]) : 0;
  const minutes = minuteMatch ? Number(minuteMatch[1]) : 0;
  return hours + minutes / 60;
}

function parsePercent(value) {
  if (!value) return 0;
  const numeric = Number(String(value).replace("%", ""));
  return Number.isNaN(numeric) ? 0 : numeric;
}

export default App;
