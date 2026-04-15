import type { VideoSource } from '../types/api';

type Props = {
  sources: VideoSource[];
};

export function VideoSourcePanel({ sources }: Props) {
  return (
    <section className="panel">
      <h2>输入源选择</h2>
      <label htmlFor="video-source-select" className="label">
        视频输入源
      </label>
      <select id="video-source-select" aria-label="视频输入源" defaultValue={sources.find((item) => item.is_selected)?.id}>
        {sources.map((source) => (
          <option key={source.id} value={source.id}>
            {source.label}
          </option>
        ))}
      </select>
    </section>
  );
}
