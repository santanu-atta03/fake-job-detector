import { Check, AlertTriangle, AlertCircle, Info, ShieldAlert } from "lucide-react";

const SEVERITY_CONFIG = {
  CRITICAL: {
    label: "CRITICAL",
    color: "#dc2626",
    bg: "#fef2f2",
    border: "#fca5a5",
    icon: ShieldAlert
  },
  HIGH: {
    label: "HIGH RISK",
    color: "#ea580c",
    bg: "#fff7ed",
    border: "#fdba74",
    icon: AlertTriangle
  },
  MEDIUM: {
    label: "MEDIUM RISK",
    color: "#d97706",
    bg: "#fffbeb",
    border: "#fcd34d",
    icon: AlertCircle
  },
  LOW: {
    label: "LOW RISK",
    color: "#4b5563",
    bg: "#f9fafb",
    border: "#e5e7eb",
    icon: Info
  }
};

function ReasonList({ findings, reasons }) {
  const hasFindings = Array.isArray(findings) && findings.length > 0;
  const hasReasons = Array.isArray(reasons) && reasons.length > 0;

  if (!hasFindings && !hasReasons) {
    return (
      <div className="findings-section">
        <div className="findings-heading">Risk Findings & Analysis</div>
        <div className="finding-clear">
          <Check size={16} strokeWidth={2} />
          No notable risk signals were detected in this listing.
        </div>
      </div>
    );
  }

  return (
    <div className="findings-section">
      <div className="findings-heading">Risk Findings & Analysis</div>

      {hasFindings ? (
        <div className="findings-container" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {findings.map((finding, index) => {
            const sev = (finding.severity || "MEDIUM").toUpperCase();
            const config = SEVERITY_CONFIG[sev] || SEVERITY_CONFIG.MEDIUM;
            const IconComp = config.icon;

            return (
              <div
                key={index}
                className="finding-card"
                style={{
                  border: `1px solid ${config.border}`,
                  backgroundColor: config.bg,
                  borderRadius: '8px',
                  padding: '14px 16px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '6px'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <IconComp size={16} color={config.color} strokeWidth={2} />
                    <strong style={{ fontSize: '0.95rem', color: '#111827' }}>
                      {finding.title}
                    </strong>
                  </div>
                  <span
                    style={{
                      fontSize: '0.72rem',
                      fontWeight: 700,
                      letterSpacing: '0.05em',
                      color: config.color,
                      backgroundColor: 'rgba(255, 255, 255, 0.85)',
                      padding: '2px 8px',
                      borderRadius: '4px',
                      border: `1px solid ${config.border}`
                    }}
                  >
                    {config.label}
                  </span>
                </div>

                <p style={{ margin: 0, fontSize: '0.88rem', color: '#374151', lineHeight: '1.45' }}>
                  {finding.description}
                </p>

                {finding.evidence && (
                  <div
                    style={{
                      marginTop: '4px',
                      padding: '6px 10px',
                      backgroundColor: 'rgba(255, 255, 255, 0.7)',
                      borderLeft: `3px solid ${config.color}`,
                      borderRadius: '0 4px 4px 0',
                      fontSize: '0.82rem',
                      fontFamily: 'monospace',
                      color: '#1f2937'
                    }}
                  >
                    <strong>Evidence snippet:</strong> "{finding.evidence}"
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <ol className="findings-list">
          {reasons.map((reason, index) => (
            <li className="finding-item" key={index}>
              <span className="finding-index">{String(index + 1).padStart(2, "0")}</span>
              <span>{reason}</span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

export default ReasonList;