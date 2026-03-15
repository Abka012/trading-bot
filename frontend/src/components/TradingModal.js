/**
 * Trading Modal Component
 * Enhanced UI for Analyze and Trade
 */

import React, { useState } from "react";
import PnLChart from "./PnLChart";

const TradingModal = ({ isOpen, onClose, symbol, data, analysis }) => {
  const [activeTab, setActiveTab] = useState("analysis"); // 'analysis' or 'trade'
  const [tradeType, setTradeType] = useState("buy");
  const [quantity, setQuantity] = useState(10);
  const [orderType, setOrderType] = useState("market");

  if (!isOpen || !symbol) return null;

  const tech = analysis?.technicals || {};
  const prediction = analysis?.prediction || {};
  const market = analysis?.market || {};
  const pnlHistory = analysis?.pnlHistory?.data || [];
  const accountPnlHistory = analysis?.accountPnlHistory?.data || [];

  const handleTrade = () => {
    alert(
      `Order ${tradeType.toUpperCase()} ${quantity} shares of ${symbol}\nType: ${orderType}`,
    );
    onClose();
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        {/* Modal Header */}
        <div className="modal-header">
          <div className="modal-title-section">
            <div className="modal-symbol-icon">
              <img
                src={`https://logo.clearbit.com/${symbol.toLowerCase()}.com`}
                alt={symbol}
                onError={(e) => {
                  e.target.style.display = "none";
                  e.target.nextSibling.style.display = "flex";
                }}
              />
              <span className="symbol-fallback" style={{ display: "none" }}>
                {symbol[0]}
              </span>
            </div>
            <div>
              <h2>{symbol}</h2>
              <p className="modal-subtitle">ML Trading Model</p>
            </div>
          </div>
          <button className="modal-close" onClick={onClose}>
            ✕
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="modal-tabs">
          <button
            className={`modal-tab ${activeTab === "analysis" ? "active" : ""}`}
            onClick={() => setActiveTab("analysis")}
          >
            📊 Analysis
          </button>
          <button
            className={`modal-tab ${activeTab === "trade" ? "active" : ""}`}
            onClick={() => setActiveTab("trade")}
          >
            💰 Trade
          </button>
        </div>

        <div className="modal-body">
          {activeTab === "analysis" ? (
            /* ANALYSIS TAB */
            <div className="analysis-tab">
              {/* AI Recommendation */}
              <div className="analysis-section">
                <h3>AI Recommendation</h3>
                <div className="recommendation-card">
                  <div
                    className={`rec-badge-large ${tech.recommendation?.includes("BUY") ? "positive" : tech.recommendation?.includes("SELL") ? "negative" : ""}`}
                  >
                    {tech.recommendation || "HOLD"}
                  </div>
                  <p className="rec-description">
                    {getRecommendationDescription(
                      tech.recommendation,
                      tech.confidence,
                    )}
                  </p>
                  <div className="confidence-bar">
                    <div className="confidence-label">Confidence</div>
                    <div className="confidence-track">
                      <div
                        className="confidence-fill"
                        style={{ width: `${tech.confidence || 50}%` }}
                      ></div>
                    </div>
                    <div className="confidence-value">
                      {tech.confidence?.toFixed(0) || 50}%
                    </div>
                  </div>
                </div>
              </div>

              {/* Model Prediction */}
              <div className="analysis-section">
                <h3>Model Prediction</h3>
                <div className="prediction-cards">
                  <div className="prediction-card">
                    <span className="pred-label">Direction</span>
                    <span
                      className={`pred-value ${prediction.direction === "UP" ? "positive" : prediction.direction === "DOWN" ? "negative" : ""}`}
                    >
                      {prediction.direction || "NEUTRAL"}
                    </span>
                  </div>
                  <div className="prediction-card">
                    <span className="pred-label">Signal</span>
                    <span className="pred-value">
                      {(prediction.signal * 100)?.toFixed(1) || 0}%
                    </span>
                  </div>
                  <div className="prediction-card">
                    <span className="pred-label">Confidence</span>
                    <span className="pred-value">
                      {prediction.confidence?.toFixed(1) || 50}%
                    </span>
                  </div>
                  <div className="prediction-card">
                    <span className="pred-label">Raw Value</span>
                    <span className="pred-value">
                      {prediction.prediction?.toFixed(6) || "0.000000"}
                    </span>
                  </div>
                </div>

                {/* Signal Meter */}
                <div className="signal-meter">
                  <div className="meter-bar">
                    <div className="meter-gradient"></div>
                    <div
                      className="meter-indicator"
                      style={{ left: `${50 + (prediction.signal || 0) * 50}%` }}
                    ></div>
                  </div>
                  <div className="meter-labels">
                    <span>Strong Sell</span>
                    <span>Neutral</span>
                    <span>Strong Buy</span>
                  </div>
                </div>
              </div>

              {/* Technical Indicators */}
              <div className="analysis-section">
                <h3>Technical Indicators</h3>
                <div className="technicals-grid">
                  <div className="tech-card">
                    <span className="tech-name">Trend</span>
                    <span
                      className={`tech-value ${tech.trend === "BULLISH" ? "positive" : tech.trend === "BEARISH" ? "negative" : ""}`}
                    >
                      {tech.trend || "NEUTRAL"}
                    </span>
                  </div>
                  <div className="tech-card">
                    <span className="tech-name">Strength</span>
                    <span className="tech-value">
                      {tech.strength || "MODERATE"}
                    </span>
                  </div>
                  <div className="tech-card">
                    <span className="tech-name">RSI (14)</span>
                    <span
                      className={`tech-value ${tech.rsi > 70 ? "negative" : tech.rsi < 30 ? "positive" : ""}`}
                    >
                      {tech.rsi || "50.0"}
                    </span>
                  </div>
                  <div className="tech-card">
                    <span className="tech-name">MACD</span>
                    <span
                      className={`tech-value ${(prediction.signal || 0) > 0 ? "positive" : "negative"}`}
                    >
                      {(prediction.signal || 0) > 0 ? "Bullish ↗" : "Bearish ↘"}
                    </span>
                  </div>
                </div>
              </div>

              {/* P&L Performance */}
              {accountPnlHistory.length > 0 && (
                <div className="analysis-section">
                  <h3>Paper Trading P&L (Alpaca)</h3>
                  <div className="pnl-chart-box">
                    <PnLChart
                      symbol="PAPER"
                      data={accountPnlHistory}
                      height={180}
                      showYAxis={true}
                      showLabels={true}
                    />
                  </div>
                </div>
              )}

              {/* Model P&L Performance */}
              {pnlHistory.length > 0 && (
                <div className="analysis-section">
                  <h3>Model P&L Performance</h3>
                  <div className="pnl-chart-box">
                    <PnLChart
                      symbol={symbol}
                      data={pnlHistory}
                      height={180}
                      showYAxis={true}
                      showLabels={true}
                    />
                  </div>
                </div>
              )}

              {/* Market Data */}
              {market && (
                <div className="analysis-section">
                  <h3>Market Data</h3>
                  <div className="market-data-grid">
                    <div className="market-item">
                      <span className="market-label">Price</span>
                      <span className="market-value">
                        ${market.price?.toFixed(2) || "N/A"}
                      </span>
                    </div>
                    <div className="market-item">
                      <span className="market-label">Change</span>
                      <span
                        className={`market-value ${market.change >= 0 ? "positive" : "negative"}`}
                      >
                        {market.change >= 0 ? "+" : ""}
                        {market.change?.toFixed(2) || "0.00"}%
                      </span>
                    </div>
                    <div className="market-item">
                      <span className="market-label">Volume</span>
                      <span className="market-value">
                        {market.volume?.toLocaleString() || "N/A"}
                      </span>
                    </div>
                    <div className="market-item">
                      <span className="market-label">Range</span>
                      <span className="market-value">
                        ${market.low?.toFixed(2) || "N/A"} - $
                        {market.high?.toFixed(2) || "N/A"}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* Summary */}
              <div className="analysis-section">
                <h3>Analysis Summary</h3>
                <div className="summary-card">
                  <p>
                    The AI model indicates a{" "}
                    <strong
                      className={
                        tech.trend === "BULLISH"
                          ? "positive"
                          : tech.trend === "BEARISH"
                            ? "negative"
                            : ""
                      }
                    >
                      {tech.trend?.toLowerCase() || "neutral"}
                    </strong>{" "}
                    outlook for {symbol} with{" "}
                    <strong>
                      {tech.confidence?.toFixed(0) || 50}% confidence
                    </strong>
                    .
                    {tech.trend === "BULLISH" &&
                      " Technical indicators suggest upward momentum."}
                    {tech.trend === "BEARISH" &&
                      " Technical indicators suggest downward pressure."}
                    {tech.trend === "NEUTRAL" &&
                      " No clear directional bias at this time."}
                  </p>
                </div>
              </div>
            </div>
          ) : (
            /* TRADE TAB */
            <div className="trade-tab">
              {/* Current Position */}
              {data?.position && (
                <div className="position-info-card">
                  <div className="position-header">
                    <span className="position-label">Current Position</span>
                    <span
                      className={`position-badge ${data.position.unrealized_pl >= 0 ? "positive" : "negative"}`}
                    >
                      {data.position.unrealized_pl >= 0 ? "+" : ""}$
                      {data.position.unrealized_pl?.toFixed(2)}
                    </span>
                  </div>
                  <div className="position-details">
                    <div className="position-detail">
                      <span className="detail-label">Shares</span>
                      <span className="detail-value">{data.position.qty}</span>
                    </div>
                    <div className="position-detail">
                      <span className="detail-label">Entry Price</span>
                      <span className="detail-value">
                        ${data.position.entry_price?.toFixed(2)}
                      </span>
                    </div>
                    <div className="position-detail">
                      <span className="detail-label">Current Price</span>
                      <span className="detail-value">
                        ${data.position.current_price?.toFixed(2)}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* Trade Form */}
              <div className="trade-form">
                <div className="form-group">
                  <label>Action</label>
                  <div className="action-selector">
                    <button
                      className={`action-btn buy ${tradeType === "buy" ? "active" : ""}`}
                      onClick={() => setTradeType("buy")}
                    >
                      Buy
                    </button>
                    <button
                      className={`action-btn sell ${tradeType === "sell" ? "active" : ""}`}
                      onClick={() => setTradeType("sell")}
                    >
                      Sell
                    </button>
                  </div>
                </div>

                <div className="form-group">
                  <label>Order Type</label>
                  <select
                    value={orderType}
                    onChange={(e) => setOrderType(e.target.value)}
                  >
                    <option value="market">Market Order</option>
                    <option value="limit">Limit Order</option>
                    <option value="stop">Stop Order</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>Quantity</label>
                  <div className="quantity-selector">
                    <button
                      onClick={() => setQuantity(Math.max(1, quantity - 1))}
                    >
                      -
                    </button>
                    <input
                      type="number"
                      value={quantity}
                      onChange={(e) =>
                        setQuantity(parseInt(e.target.value) || 1)
                      }
                      min="1"
                    />
                    <button onClick={() => setQuantity(quantity + 1)}>+</button>
                  </div>
                  <div className="quantity-presets">
                    <button onClick={() => setQuantity(10)}>10</button>
                    <button onClick={() => setQuantity(50)}>50</button>
                    <button onClick={() => setQuantity(100)}>100</button>
                    <button
                      onClick={() =>
                        setQuantity(
                          Math.floor(10000 / (data?.currentPrice || 100)),
                        )
                      }
                    >
                      Max
                    </button>
                  </div>
                </div>

                {/* Order Summary */}
                <div className="order-summary">
                  <div className="summary-row">
                    <span>Estimated Total</span>
                    <span className="summary-value">
                      ${(quantity * (data?.currentPrice || 0)).toFixed(2)}
                    </span>
                  </div>
                  <div className="summary-row">
                    <span>Buying Power</span>
                    <span className="summary-value">$100,000.00</span>
                  </div>
                  <div className="summary-row">
                    <span>Est. Commission</span>
                    <span className="summary-value">$0.00</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="modal-footer">
          {activeTab === "trade" ? (
            <>
              <button className="btn-secondary" onClick={onClose}>
                Cancel
              </button>
              <button
                className={`btn-primary ${tradeType === "sell" ? "sell" : "buy"}`}
                onClick={handleTrade}
              >
                {tradeType === "buy" ? "🟢 Buy" : "🔴 Sell"} {quantity} Shares
              </button>
            </>
          ) : (
            <>
              <button className="btn-secondary" onClick={onClose}>
                Close
              </button>
              {data?.position && (
                <button
                  className="btn-danger"
                  onClick={() => {
                    /* Close position logic */
                  }}
                >
                  Close Position
                </button>
              )}
              <button
                className="btn-primary"
                onClick={() => setActiveTab("trade")}
              >
                Trade {symbol}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

// Helper function
function getRecommendationDescription(recommendation, confidence) {
  const descriptions = {
    "STRONG BUY": `Strong buy signal with ${confidence}% confidence. Model indicates significant upward momentum based on technical analysis.`,
    BUY: `Buy signal detected. Model suggests potential upward movement with ${confidence}% confidence.`,
    HOLD: `No clear trading signal. Model recommends holding current positions and monitoring market conditions.`,
    SELL: `Sell signal detected. Model suggests potential downward movement with ${confidence}% confidence.`,
    "STRONG SELL": `Strong sell signal with ${confidence}% confidence. Model indicates significant downward pressure.`,
  };
  return descriptions[recommendation] || descriptions["HOLD"];
}

export default TradingModal;
