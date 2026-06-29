function SummaryStats({ recap }) {
  const stats = [
    { label: "Hypotheses", value: recap.hypotheses },
    { label: "Runs", value: recap.runs },
    { label: "Steps", value: recap.steps },
  ];

  return (
    <div className="row g-4 mb-3">
      {stats.map((stat) => (
        <div key={stat.label} className="col-12 col-sm-4">
          <div className="card shadow-sm h-100 border-start border-1 rounded-3">
            <div className="card-body d-flex align-items-center justify-content-between gap-3 px-3 py-2">
              <div className="fs-6 fw-semibold text-secondary">
                {stat.label}
              </div>
              <div className="fs-4 fw-semibold lh-sm">
                {stat.value.toLocaleString()}
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export default SummaryStats;
