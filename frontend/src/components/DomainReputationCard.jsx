import React from "react";
import { Globe, AlertTriangle, ShieldCheck, Calendar, ExternalLink } from "lucide-react";

function DomainReputationCard({ domainReputation }) {
  if (!domainReputation || domainReputation.total_domains_found === 0) {
    return null;
  }

  const { domains, has_domain_risk, typosquatting_count, newly_registered_count, suspicious_tld_count } = domainReputation;

  return (
    <div className={`domain-reputation-card ${has_domain_risk ? "risk-detected" : "clean"}`}>
      <div className="domain-card-header">
        <div className="domain-title">
          <Globe size={18} className="domain-icon" />
          <span>Domain & URL Reputation Analysis</span>
        </div>
        {has_domain_risk ? (
          <span className="badge risk-badge">
            <AlertTriangle size={14} /> Domain Risks Flagged ({domains.length})
          </span>
        ) : (
          <span className="badge clean-badge">
            <ShieldCheck size={14} /> All Domains Clean ({domains.length})
          </span>
        )}
      </div>

      {(typosquatting_count > 0 || newly_registered_count > 0 || suspicious_tld_count > 0) && (
        <div className="domain-summary-pills">
          {typosquatting_count > 0 && (
            <span className="pill pill-danger">
              ⚠️ Typosquatting / Impersonation ({typosquatting_count})
            </span>
          )}
          {newly_registered_count > 0 && (
            <span className="pill pill-warning">
              📅 Newly Registered (&lt; 90d) ({newly_registered_count})
            </span>
          )}
          {suspicious_tld_count > 0 && (
            <span className="pill pill-danger">
              🌐 High-Risk TLD ({suspicious_tld_count})
            </span>
          )}
        </div>
      )}

      <div className="domain-list">
        {domains.map((item, index) => {
          const hasRisk = item.is_typosquatted || item.is_newly_registered || item.is_suspicious_tld;

          return (
            <div key={index} className={`domain-item ${hasRisk ? "item-risk" : "item-safe"}`}>
              <div className="domain-item-top">
                <span className="domain-name">
                  <ExternalLink size={14} style={{ marginRight: 6 }} />
                  {item.domain}
                </span>

                {item.registration_age_days !== null && (
                  <span className="domain-age">
                    <Calendar size={13} style={{ marginRight: 4 }} />
                    Age: {item.registration_age_days} days ({item.registration_date})
                  </span>
                )}
              </div>

              {item.flags && item.flags.length > 0 && (
                <ul className="domain-flags">
                  {item.flags.map((flag, fIdx) => (
                    <li key={fIdx}>⚠️ {flag}</li>
                  ))}
                </ul>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default DomainReputationCard;
