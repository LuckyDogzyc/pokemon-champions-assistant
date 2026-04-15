type SideData = {
  title: string;
  name?: string | null;
  confidence: number;
  source: string;
};

export function RecognitionStatusPanel({ title, name, confidence, source }: SideData) {
  return (
    <section className="panel">
      <h2>{title}</h2>
      <p>{name ?? '未识别'}</p>
      <p>置信度：{confidence}</p>
      <p>来源：{source}</p>
    </section>
  );
}
