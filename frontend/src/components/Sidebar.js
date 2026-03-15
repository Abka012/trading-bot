/**
 * Sidebar Navigation Component
 * Left sidebar with navigation icons matching the Ai Trading design
 */

import React, { useState } from "react";
import "./Sidebar.css";

const Sidebar = () => {
  const [activeItem, setActiveItem] = useState("dashboard");

  const menuItems = [
    { id: "dashboard", icon: "📊", label: "Dashboard" },
    { id: "bots", icon: "🤖", label: "Trading Bots" },
    { id: "portfolio", icon: "💼", label: "Portfolio" },
    { id: "analytics", icon: "📈", label: "Analytics" },
    { id: "transactions", icon: "💳", label: "Transactions" },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="logo">
          <div className="logo-icon">
            <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="20" cy="20" r="18" stroke="currentColor" strokeWidth="2" />
              <path d="M20 8L26 14L20 20L14 14L20 8Z" fill="currentColor" />
              <path d="M20 20L26 26L20 32L14 26L20 20Z" fill="currentColor" opacity="0.6" />
              <circle cx="20" cy="20" r="4" fill="currentColor" />
            </svg>
          </div>
        </div>
      </div>

      <nav className="sidebar-nav">
        <ul className="nav-list">
          {menuItems.map((item) => (
            <li key={item.id} className="nav-item">
              <button
                className={`nav-link ${activeItem === item.id ? "active" : ""}`}
                onClick={() => setActiveItem(item.id)}
                title={item.label}
              >
                <span className="nav-icon">{item.icon}</span>
              </button>
            </li>
          ))}
        </ul>
      </nav>

      <div className="sidebar-footer">
        <button className="nav-link" title="Settings">
          <span className="nav-icon">⚙️</span>
        </button>
        <div className="user-avatar">
          <img
            src="https://ui-avatars.com/api/?name=User&background=374151&color=fff"
            alt="User"
          />
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
