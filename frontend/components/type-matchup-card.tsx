type Props = {
  summary: string;
};

export function TypeMatchupCard({ summary }: Props) {
  return (
    <section className="panel">
      <h2>属性克制摘要</h2>
      <p>{summary}</p>
    </section>
  );
}
