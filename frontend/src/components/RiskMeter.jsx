

const RISK_COLOR = {
  Low: "var(--risk-low)",
  Medium: "var(--risk-medium)",
  High: "var(--risk-high)",
  "Very High": "var(--risk-critical)",
  Critical: "var(--risk-critical)",
};

function RiskMeter({ probability, riskLevel }) {
  const r = 80;
  const arcLength = Math.PI * r;
  const offset = arcLength * (1 - probability / 100);
  const color = RISK_COLOR[riskLevel] || "var(--muted)";

  return (
    <div className="gauge">
      <svg viewBox="0 0 200 118" className="gauge-svg">
        <path
          d="M20,100 A80,80 0 0 1 180,100"
          fill="none"
          stroke="var(--line)"
          strokeWidth="10"
          strokeLinecap="round"
        />
        <path
          d="M20,100 A80,80 0 0 1 180,100"
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={`${arcLength} ${arcLength}`}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 700ms ease, stroke 300ms ease" }}
        />
        <text x="100" y="88" textAnchor="middle" className="gauge-number" fill="var(--ink)">
          {probability}%
        </text>
      </svg>
      <div className="gauge-caption" style={{ color }}>
        {riskLevel} risk
      </div>
    </div>
  );
}

export default RiskMeter;