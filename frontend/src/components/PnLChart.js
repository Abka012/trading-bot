/**
 * PnL Chart Component
 * Professional profit/loss chart with Y-axis, grid lines, and gradient fill
 *
 * Features:
 * - Y-axis with dollar values
 * - Horizontal grid lines
 * - Zero line (dashed) when in range
 * - Gradient fill (green for profit, red for loss)
 * - Smooth bezier curve
 * - Current value indicator (dot + label)
 * - Responsive sizing (main card: 150px, modal: 180px)
 */

import React, { useEffect, useRef } from "react";

const PnLChart = ({
  data,
  symbol,
  height = 150,
  showYAxis = true,
  showLabels = true,
}) => {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    const dpr = window.devicePixelRatio || 1;

    // Set canvas size with high DPI support
    canvas.width = canvas.offsetWidth * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);

    const width = canvas.offsetWidth;
    const chartHeight = height;
    const padding = {
      top: showLabels ? 25 : 15,
      right: showLabels ? 60 : 15,
      bottom: showLabels ? 25 : 15,
      left: showYAxis ? (showLabels ? 55 : 45) : 15,
    };

    // Clear canvas
    ctx.clearRect(0, 0, width, chartHeight);

    // Generate or use provided PnL data
    const pnlData = data && data.length > 0 ? data : generateSamplePnLData();

    // Calculate min/max for scaling with padding
    const values = pnlData.map((d) => d.value);
    let maxValue = Math.max(...values, 0);
    let minValue = Math.min(...values, 0);

    // Add 10% padding to min/max for better visualization
    const range = maxValue - minValue || 1;
    maxValue += range * 0.1;
    minValue -= range * 0.1;
    const adjustedRange = maxValue - minValue;

    const chartWidth = width - padding.left - padding.right;
    const chartAreaHeight = chartHeight - padding.top - padding.bottom;

    // Draw Y-axis labels and grid lines
    if (showYAxis) {
      const ySteps = 5;

      for (let i = 0; i <= ySteps; i++) {
        const value = maxValue - (adjustedRange * i) / ySteps;
        const y = padding.top + (chartAreaHeight * i) / ySteps;

        // Format value as currency
        ctx.fillStyle = "#6b7280";
        ctx.font =
          '11px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
        ctx.textAlign = "right";
        ctx.textBaseline = "middle";

        const label = formatCurrency(value);
        ctx.fillText(label, padding.left - 8, y);

        // Draw grid line
        ctx.strokeStyle = "rgba(107, 114, 128, 0.15)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(padding.left, y);
        ctx.lineTo(width - padding.right, y);
        ctx.stroke();
      }

      // Draw Y-axis line
      ctx.strokeStyle = "rgba(107, 114, 128, 0.3)";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(padding.left, padding.top);
      ctx.lineTo(padding.left, chartHeight - padding.bottom);
      ctx.stroke();
    }

    const showAxes = showLabels || showYAxis;

    // Draw X-axis line
    if (showAxes) {
      ctx.strokeStyle = "rgba(107, 114, 128, 0.3)";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(padding.left, chartHeight - padding.bottom);
      ctx.lineTo(width - padding.right, chartHeight - padding.bottom);
      ctx.stroke();
    }

    // Draw zero line (dashed) if within range
    const zeroY =
      padding.top + chartAreaHeight * (1 - (0 - minValue) / adjustedRange);
    if (
      showAxes &&
      zeroY >= padding.top &&
      zeroY <= chartHeight - padding.bottom
    ) {
      ctx.strokeStyle = "rgba(107, 114, 128, 0.4)";
      ctx.lineWidth = 1;
      ctx.setLineDash([5, 5]);
      ctx.beginPath();
      ctx.moveTo(padding.left, zeroY);
      ctx.lineTo(width - padding.right, zeroY);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // Generate points for the line
    const points = pnlData.map((point, index) => {
      const x = padding.left + (chartWidth * index) / (pnlData.length - 1);
      const y =
        padding.top +
        chartAreaHeight * (1 - (point.value - minValue) / adjustedRange);
      return { x, y, value: point.value };
    });

    // Determine if positive or negative based on last value
    const isPositive = points[points.length - 1].value >= 0;
    const lineColor = isPositive ? "#10b981" : "#ef4444";

    // Draw gradient fill
    const gradient = ctx.createLinearGradient(
      0,
      padding.top,
      0,
      chartHeight - padding.bottom,
    );

    if (isPositive) {
      gradient.addColorStop(0, "rgba(16, 185, 129, 0.4)");
      gradient.addColorStop(0.5, "rgba(16, 185, 129, 0.15)");
      gradient.addColorStop(1, "rgba(16, 185, 129, 0.02)");
    } else {
      gradient.addColorStop(0, "rgba(239, 68, 68, 0.4)");
      gradient.addColorStop(0.5, "rgba(239, 68, 68, 0.15)");
      gradient.addColorStop(1, "rgba(239, 68, 68, 0.02)");
    }

    // Create filled area
    ctx.beginPath();
    ctx.moveTo(points[0].x, chartHeight - padding.bottom);

    // Draw line to first point
    ctx.lineTo(points[0].x, points[0].y);

    // Draw smooth bezier curve through all points
    for (let i = 1; i < points.length - 1; i++) {
      const prev = points[i - 1];
      const curr = points[i];
      const next = points[i + 1];

      // Calculate control points for smooth curve
      const cp1x = prev.x + (curr.x - prev.x) * 0.5;
      const cp1y = prev.y + (curr.y - prev.y) * 0.5;
      const cp2x = curr.x + (next.x - curr.x) * 0.5;
      const cp2y = curr.y + (next.y - curr.y) * 0.5;

      ctx.bezierCurveTo(cp1x, cp1y, cp2x, cp2y, curr.x, curr.y);
    }

    // Connect to last point
    const lastPoint = points[points.length - 1];
    ctx.lineTo(lastPoint.x, lastPoint.y);

    // Close the path at the bottom
    ctx.lineTo(lastPoint.x, chartHeight - padding.bottom);
    ctx.closePath();
    ctx.fillStyle = gradient;
    ctx.fill();

    // Draw the line with smooth bezier curves
    ctx.beginPath();
    ctx.moveTo(points[0].x, points[0].y);

    for (let i = 1; i < points.length - 1; i++) {
      const prev = points[i - 1];
      const curr = points[i];
      const next = points[i + 1];

      const cp1x = prev.x + (curr.x - prev.x) * 0.5;
      const cp1y = prev.y + (curr.y - prev.y) * 0.5;
      const cp2x = curr.x + (next.x - curr.x) * 0.5;
      const cp2y = curr.y + (next.y - curr.y) * 0.5;

      ctx.bezierCurveTo(cp1x, cp1y, cp2x, cp2y, curr.x, curr.y);
    }

    ctx.lineTo(lastPoint.x, lastPoint.y);

    ctx.strokeStyle = lineColor;
    ctx.lineWidth = 2.5;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.stroke();

    // Draw current value indicator (glowing dot at the end)
    // Outer glow
    const glowGradient = ctx.createRadialGradient(
      lastPoint.x,
      lastPoint.y,
      0,
      lastPoint.x,
      lastPoint.y,
      12,
    );
    glowGradient.addColorStop(
      0,
      isPositive ? "rgba(16, 185, 129, 0.4)" : "rgba(239, 68, 68, 0.4)",
    );
    glowGradient.addColorStop(1, "rgba(0, 0, 0, 0)");

    ctx.beginPath();
    ctx.arc(lastPoint.x, lastPoint.y, 12, 0, Math.PI * 2);
    ctx.fillStyle = glowGradient;
    ctx.fill();

    // Inner dot
    ctx.beginPath();
    ctx.fillStyle = lineColor;
    ctx.arc(lastPoint.x, lastPoint.y, 5, 0, Math.PI * 2);
    ctx.fill();

    // White center dot
    ctx.beginPath();
    ctx.fillStyle = "#ffffff";
    ctx.arc(lastPoint.x, lastPoint.y, 2.5, 0, Math.PI * 2);
    ctx.fill();

    // Draw current value label with background
    const valueLabel = formatCurrency(lastPoint.value, true);
    ctx.font =
      'bold 13px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
    const labelWidth = ctx.measureText(valueLabel).width + 12;
    const labelHeight = 24;
    const labelX = lastPoint.x - 10 - labelWidth;
    const labelY = lastPoint.y - labelHeight / 2;

    // Label background
    ctx.fillStyle = isPositive
      ? "rgba(16, 185, 129, 0.9)"
      : "rgba(239, 68, 68, 0.9)";
    ctx.beginPath();
    ctx.roundRect(labelX, labelY, labelWidth, labelHeight, 6);
    ctx.fill();

    // Label text
    ctx.fillStyle = "#ffffff";
    ctx.textAlign = "left";
    ctx.fillText(valueLabel, labelX + 6, labelY + labelHeight / 2 + 4);
  }, [data, height, showYAxis, showLabels]);

  // Format currency value
  function formatCurrency(value, showSign = false) {
    const sign = showSign && value >= 0 ? "+" : "";
    const absValue = Math.abs(value);

    if (absValue >= 1000) {
      return `${sign}$${absValue.toFixed(0)}`;
    } else if (absValue >= 1) {
      return `${sign}$${absValue.toFixed(2)}`;
    } else {
      return `${sign}$${absValue.toFixed(3)}`;
    }
  }

  // Generate sample PnL data for demonstration
  function generateSamplePnLData() {
    const data = [];
    let value = (Math.random() - 0.5) * 50;
    const now = Date.now();

    for (let i = 60; i >= 0; i--) {
      // Generate realistic PnL movements with trend
      const trend = Math.sin(i / 10) * 20; // Slight wave pattern
      const noise = (Math.random() - 0.48) * 15;
      value = trend + noise;

      data.push({
        timestamp: new Date(now - i * 60000).toISOString(),
        value: value,
      });
    }

    return data;
  }

  return (
    <div
      className="pnl-chart-container"
      style={{ height: `${height}px`, width: "100%" }}
    >
      <canvas ref={canvasRef} style={{ width: "100%", height: "100%" }} />
    </div>
  );
};

export default PnLChart;
