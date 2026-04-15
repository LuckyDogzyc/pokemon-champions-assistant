type Props = {
  phase: string;
};

export function PhaseStatusPanel({ phase }: Props) {
  return (
    <section className="panel">
      <h2>当前阶段</h2>
      <p>{phase}</p>
      <p>默认抓帧频率：每 3 秒 1 帧</p>
    </section>
  );
}
