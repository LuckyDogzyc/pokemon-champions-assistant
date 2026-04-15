type Props = {
  title: string;
  name?: string | null;
  subtitle: string;
};

export function PokemonCard({ title, name, subtitle }: Props) {
  return (
    <section className="panel">
      <h2>{title}</h2>
      <p>{name ?? '暂无数据'}</p>
      <p>{subtitle}</p>
    </section>
  );
}
