interface EmptyStateProps {
  title: string;
  path: string;
  message: string;
}

export function EmptyState({ title, path, message }: EmptyStateProps) {
  return (
    <section className="empty-state">
      <h2>{title}</h2>
      <p>{message}</p>
      <dl>
        <div>
          <dt>Attempted report</dt>
          <dd><code>{path}</code></dd>
        </div>
        <div>
          <dt>Generate it</dt>
          <dd>
            <code>
              python -m pipeline.main --source csv --period month --start 2026-04-01 --end 2026-04-30
            </code>
          </dd>
        </div>
      </dl>
    </section>
  );
}
