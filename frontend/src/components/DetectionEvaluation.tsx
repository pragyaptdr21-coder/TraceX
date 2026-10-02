import { useCallback, useEffect, useState } from 'react';
import {
  ShieldCheck, Download, Loader2, TriangleAlert, FileText
} from 'lucide-react';
import { getPrecisionRecall, downloadEvaluationReport } from '../api';
import type { EvaluationPayload } from '../api';

const formatPercent = (value: number | null | undefined): string => {
  if (value === null || value === undefined) return 'NOT COMPUTABLE';
  return `${(value * 100).toFixed(2)}%`;
};

const formatCount = (value: number | null | undefined): string =>
  value === null || value === undefined ? 'NOT COMPUTABLE' : value.toLocaleString();

export default function DetectionEvaluation() {
  const [data, setData] = useState<EvaluationPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await getPrecisionRecall());
    } catch {
      setError('Evaluation endpoint unavailable.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const handleExport = async () => {
    try {
      const blob = await downloadEvaluationReport();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'TraceX_Precision_Recall_Evaluation_Report.txt';
      document.body.appendChild(link);
      link.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(link);
    } catch {
      setError('Unable to generate the evaluation report.');
    }
  };

  return (
    <section className="reference-panel evaluation-panel">
      <div className="panel-title">
        <ShieldCheck size={16} />
        Detection Evaluation
        <button onClick={handleExport} className="eval-export" title="Download the evaluation report">
          <Download size={13} /> Export Report
        </button>
      </div>

      {loading && (
        <div className="eval-state"><Loader2 size={16} className="eval-spin" /> Loading evaluation status...</div>
      )}

      {!loading && error && (
        <div className="eval-state eval-error"><TriangleAlert size={15} /> {error}</div>
      )}

      {!loading && !error && data && !data.metrics_available && (
        <div className="eval-state">
          <div className="eval-headline">Official ground truth not available</div>
          <div className="eval-sub">Precision/Recall pending official labels</div>
          <p className="eval-body">
            The official 1,500 injected mule account IDs are not present in this
            repository. TraceX does not substitute a proxy label set and never
            treats its own detector output as ground truth, so no precision,
            recall or F1 figure is shown.
          </p>
          <dl className="eval-facts">
            <div><dt>Ground truth source</dt><dd>{data.ground_truth?.path ?? 'n/a'}</dd></div>
            <div><dt>Labels available</dt><dd>{formatCount(data.ground_truth?.ground_truth_accounts)}</dd></div>
            <div><dt>Required population</dt><dd>{formatCount(data.ground_truth?.expected_mule_accounts)} mule / {formatCount(data.ground_truth?.expected_regular_accounts)} regular</dd></div>
            <div><dt>Status</dt><dd>{data.status}</dd></div>
          </dl>
        </div>
      )}

      {!loading && !error && data?.metrics_available && (
        <div className="eval-state">
          <div className="eval-headline eval-ok">Evaluation complete</div>
          <div className={data.population_validated ? 'eval-sub' : 'eval-sub eval-warn'}>
            {data.population_validated
              ? `Population validated: ${formatCount(data.mule_accounts)} mule / ${formatCount(data.regular_accounts)} regular`
              : `Population count mismatch: ${formatCount(data.mule_accounts)} mule / ${formatCount(data.regular_accounts)} regular`}
          </div>

          <div className="eval-grid">
            <Stat label="Precision" value={formatPercent(data.precision)} />
            <Stat label="Recall" value={formatPercent(data.recall)} />
            <Stat label="F1" value={formatPercent(data.f1)} />
            <Stat label="False Positive Rate" value={formatPercent(data.false_positive_rate)} />
          </div>

          <div className="eval-grid eval-grid-cms">
            <Stat label="TP" value={formatCount(data.true_positives)} />
            <Stat label="FP" value={formatCount(data.false_positives)} />
            <Stat label="TN" value={formatCount(data.true_negatives)} />
            <Stat label="FN" value={formatCount(data.false_negatives)} />
          </div>

          <div className="eval-meta">
            <div><span>Risk threshold</span><strong>mule_risk_index &ge; {data.risk_threshold}</strong></div>
            <div><span>Predicted mules</span><strong>{formatCount(data.predicted_mules)}</strong></div>
            <div><span>Ground truth accounts</span><strong>{formatCount(data.ground_truth_accounts)}</strong></div>
          </div>

          {data.false_positive_analysis && (
            <div className="eval-fp">
              <div className="eval-fp-title"><FileText size={13} /> False positives among regular accounts</div>
              <div className="eval-fp-line">
                Regular accounts wrongly flagged: <strong>{formatCount(data.false_positive_analysis.false_positive_count)}</strong>
                {' '}of {formatCount(data.false_positive_analysis.total_regular_accounts)}
              </div>
              {Array.isArray(data.false_positive_analysis.false_positives_by_signal) &&
                data.false_positive_analysis.false_positives_by_signal.length > 0 && (
                  <ul className="eval-fp-list">
                    {data.false_positive_analysis.false_positives_by_signal.map((row: any) => (
                      <li key={row.signal}>
                        <span>{row.detector}</span>
                        <strong>{row.false_positives}</strong>
                      </li>
                    ))}
                  </ul>
                )}
            </div>
          )}

          {data.per_detector && (
            <div className="eval-detectors">
              <div className="eval-fp-title">Per-detector results</div>
              <table>
                <thead>
                  <tr><th>Detector</th><th>TP</th><th>FP</th><th>TN</th><th>FN</th><th>Precision</th><th>Recall</th><th>F1</th></tr>
                </thead>
                <tbody>
                  {Object.entries(data.per_detector).map(([name, metric]) => {
                    const m = metric as any;
                    if (!m) {
                      return <tr key={name}><td>{name}</td><td colSpan={7}>NOT COMPUTED</td></tr>;
                    }
                    return (
                      <tr key={name}>
                        <td>{name}</td>
                        <td>{formatCount(m.true_positives)}</td>
                        <td>{formatCount(m.false_positives)}</td>
                        <td>{formatCount(m.true_negatives)}</td>
                        <td>{formatCount(m.false_negatives)}</td>
                        <td>{formatPercent(m.precision)}</td>
                        <td>{formatPercent(m.recall)}</td>
                        <td>{formatPercent(m.f1)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="eval-stat">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
