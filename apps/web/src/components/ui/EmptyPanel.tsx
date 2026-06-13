export function EmptyPanel({ title, text }: { title: string; text: string }) {
  return (
    <section className="panel empty-panel">
      <h2>{title}</h2>
      <p>{text}</p>
    </section>
  );
}
