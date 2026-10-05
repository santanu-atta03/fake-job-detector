import { ShieldCheck, ShieldAlert } from "lucide-react";
import RiskMeter from "./RiskMeter";
import ReasonList from "./ReasonList";
import DomainReputationCard from "./DomainReputationCard";


const TAB_COLOR = {
  Low: "var(--risk-low)",
  Medium: "var(--risk-medium)",
  High: "var(--risk-high)",
  "Very High": "var(--risk-critical)",
  Critical: "var(--risk-critical)",
};

function ResultCard({ result }) {
  if (!result) {
    return null;
  }

  const isFraudulent = result.prediction === "fraudulent";
  const color = TAB_COLOR[result.risk_level] || "var(--muted)";
  const score = result.risk_score !== undefined ? result.risk_score : Math.round(result.fraud_probability);

  return (
    <div className="result-card">
      <div className="result-tab" style={{ background: color }} />

      <div className="result-header">
        <div className="verdict">
          {isFraudulent ? (
            <ShieldAlert size={20} color={color} strokeWidth={1.8} />
          ) : (
            <ShieldCheck size={20} color={color} strokeWidth={1.8} />
          )}
          <span style={{ color }}>
            {isFraudulent ? "Potentially fraudulent" : "Likely legitimate"}
          </span>
        </div>
      </div>

      <RiskMeter probability={score} riskLevel={result.risk_level} />

      {result.domain_reputation && (
        <DomainReputationCard domainReputation={result.domain_reputation} />
      )}

      <ReasonList findings={result.findings} reasons={result.reasons} />

      <div className="disclaimer">
        <strong>Important: </strong>
        This tool provides an automated risk assessment and does not
        guarantee that a job posting is fraudulent or legitimate.
      </div>
    </div>
  );
}

export default ResultCard;