export function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export function SummaryList({
  data,
  labels = {},
  empty,
}: {
  data: Record<string, number>;
  labels?: Record<string, string>;
  empty: string;
}) {
  const entries = Object.entries(data).filter(([, count]) => count > 0);
  if (!entries.length) return <div className="empty compact-empty">{empty}</div>;
  return (
    <div className="status-list">
      {entries.map(([key, count]) => (
        <div key={key} className="status-row">
          <span>{labels[key] ?? key}</span>
          <strong>{count}</strong>
        </div>
      ))}
    </div>
  );
}
