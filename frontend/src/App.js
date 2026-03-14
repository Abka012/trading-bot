// frontend/src/App.js
import React, { useState, useEffect } from "react";
import "./App.css";

function App() {
  const [marketData, setMarketData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMarketData();
    const interval = setInterval(fetchMarketData, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchMarketData = async () => {
    try {
      const response = await fetch("http://localhost:8000/api/market");
      const data = await response.json();
      setMarketData(data);
      setLoading(false);
    } catch (error) {
      console.error("Error fetching market data:", error);
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1 className="app-title">Trading Bot</h1>
        <div className="market-status">
          <span className="status-indicator live">●</span>
          <span>Market Live</span>
        </div>
      </header>

      <main className="dashboard">
        <section className="prediction-results">
          <h2 className="section-title">Prediction Results</h2>

          <div className="cards-grid">
            {/* Trend Forecast Card */}
            <div className="card trend-forecast">
              <h3 className="card-title">Trend Forecast</h3>
              <div className="forecast-content">
                <div className="currency-pair">
                  <span className="pair-name">EUR/USD/JPY</span>
                  <span className="timeframe">1H</span>
                </div>
                {loading ? (
                  <div className="loading">Loading...</div>
                ) : (
                  <div className="forecast-chart">
                    <div className="chart-placeholder">
                      <svg viewBox="0 0 200 100" className="mini-chart">
                        <polyline
                          points="0,80 20,75 40,85 60,60 80,70 100,50 120,55 140,40 160,45 180,30 200,35"
                          fill="none"
                          stroke="#00d4aa"
                          strokeWidth="2"
                        />
                        <polyline
                          points="0,80 20,75 40,85 60,60 80,70 100,50 120,55 140,40 160,45 180,30 200,35"
                          fill="rgba(0,212,170,0.1)"
                          stroke="none"
                        />
                      </svg>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Confidence Level Card */}
            <div className="card confidence-level">
              <h3 className="card-title">Confidence Level</h3>
              <div className="confidence-content">
                <div className="confidence-gauge">
                  <div className="gauge-circle">
                    <svg viewBox="0 0 100 100" className="gauge-svg">
                      <circle
                        cx="50"
                        cy="50"
                        r="40"
                        fill="none"
                        stroke="#1e3a5f"
                        strokeWidth="8"
                      />
                      <circle
                        cx="50"
                        cy="50"
                        r="40"
                        fill="none"
                        stroke="#00d4aa"
                        strokeWidth="8"
                        strokeDasharray="251.2"
                        strokeDashoffset="62.8"
                        strokeLinecap="round"
                        transform="rotate(-90 50 50)"
                      />
                    </svg>
                    <span className="gauge-value">75%</span>
                  </div>
                </div>
                <p className="confidence-text">High Confidence</p>
              </div>
            </div>

            {/* Next Trend Prediction Card */}
            <div className="card next-trend">
              <h3 className="card-title">Next Trend Prediction:</h3>
              <div className="trend-content">
                <div className="trend-direction expected">Expected</div>
                <div className="probability-bars">
                  <div className="probability-item">
                    <div className="probability-label">
                      <span>Rise Probability</span>
                      <span className="probability-value">60%</span>
                    </div>
                    <div className="progress-bar">
                      <div
                        className="progress-fill rise"
                        style={{ width: "60%" }}
                      ></div>
                    </div>
                  </div>
                  <div className="probability-item">
                    <div className="probability-label">
                      <span>Fall Probability</span>
                      <span className="probability-value">40%</span>
                    </div>
                    <div className="progress-bar">
                      <div
                        className="progress-fill fall"
                        style={{ width: "40%" }}
                      ></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Prediction Accuracy Card */}
            <div className="card prediction-accuracy">
              <h3 className="card-title">Prediction Accuracy</h3>
              <div className="accuracy-content">
                <div className="accuracy-percentage">
                  <span className="percent-symbol">%</span>
                  <span className="accuracy-value">87.5</span>
                </div>
                <p className="accuracy-text">Last 100 predictions</p>
              </div>
            </div>

            {/* Backtest Results Card */}
            <div className="card backtest-results">
              <h3 className="card-title">Backtest Results</h3>
              <div className="backtest-content">
                <div className="backtest-metric">
                  <span className="metric-label">Net Profit</span>
                  <span className="metric-value profit">+24.5%</span>
                </div>
                <div className="backtest-metric">
                  <span className="metric-label">Win Rate</span>
                  <span className="metric-value">68%</span>
                </div>
                <div className="backtest-metric">
                  <span className="metric-label">Total Trades</span>
                  <span className="metric-value">156</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Market Data Section */}
        <section className="market-data-section">
          <h2 className="section-title">Live Market Data</h2>
          <div className="market-cards">
            {marketData &&
              Object.entries(marketData).map(([pair, data]) => (
                <div key={pair} className="market-card">
                  <div className="market-pair">{pair}</div>
                  <div className="market-price">
                    ${data.price.toLocaleString()}
                  </div>
                  <div
                    className={`market-change ${data.change >= 0 ? "positive" : "negative"}`}
                  >
                    {data.change >= 0 ? "↑" : "↓"} {Math.abs(data.change)}%
                  </div>
                </div>
              ))}
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;
