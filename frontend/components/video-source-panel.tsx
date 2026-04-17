import type { VideoSource } from '../types/api';

type Props = {
  sources: VideoSource[];
};

function buildSourceMeta(source: VideoSource): string {
  const parts = [source.backend ? `设备来源：${source.backend}` : '设备来源：unknown'];
  if (source.device_index !== undefined && source.device_index !== null) {
    parts.push(`索引 ${source.device_index}`);
  }
  if (source.is_selected) {
    parts.push('当前已选');
  }
  return parts.join(' · ');
}

export function VideoSourcePanel({ sources }: Props) {
  const selected = sources.find((item) => item.is_selected) ?? sources[0];

  return (
    <section className="panel">
      <h2>输入源选择</h2>
      <label htmlFor="video-source-select" className="label">
        视频输入源
      </label>
      <select id="video-source-select" aria-label="视频输入源" defaultValue={selected?.id}>
        {sources.map((source) => (
          <option key={source.id} value={source.id}>
            {source.label}
          </option>
        ))}
      </select>
      {selected ? <p>{buildSourceMeta(selected)}</p> : null}
    </section>
  );
}
