import { Check } from "lucide-react";


function ReasonList({ reasons }) {
  return (
    <div className="findings-section">
      <div className="findings-heading">Findings</div>

      {!reasons || reasons.length === 0 ? (
        <div className="finding-clear">
          <Check size={16} strokeWidth={2} />
          No notable risk signals were found in the listing as written.
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