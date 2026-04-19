import type { VideoSource } from '../types/api';

type Props = {
  sources: VideoSource[];
  onSelectSource?: (sourceId: string) => void | Promise<void>;
};

function deviceKindLabel(kind: VideoSource['device_kind']): string | null {
  if (kind === 'virtual') {
    return '虚拟设备';
  }
  if (kind === 'physical') {
    return '实体设备';
  }
  return null;
}

function buildSourceMeta(source: VideoSource): string {
  const parts = [source.backend ? `设备来源：${source.backend}` : '设备来源：unknown'];
  const kindLabel = deviceKindLabel(source.device_kind);
  if (kindLabel) {
    parts.push(kindLabel);
  }
  if (source.device_index !== undefined && source.device_index !== null) {
    parts.push(`索引 ${source.device_index}`);
  }
  if (source.is_selected) {
    parts.push('当前已选');
  }
  return parts.join(' · ');
}

function usesGenericDeviceLabel(label: string | undefined): boolean {
  if (!label) {
    return false;
  }
  return /^Video Device \d+$/i.test(label.trim());
}

function findRecommendedSource(sources: VideoSource[]): VideoSource | undefined {
  return (
    sources.find((source) => source.label.toLowerCase().includes('obs virtual camera')) ??
    sources.find((source) => source.device_kind === 'virtual') ??
    sources[0]
  );
}

function buildRecommendedSourceText(source: VideoSource | undefined): string | null {
  if (!source) {
    return null;
  }
  const backend = source.backend
    ? source.backend.toLowerCase() === 'opencv'
      ? 'OpenCV'
      : source.backend.toUpperCase()
    : 'UNKNOWN';
  return `当前推荐输入：${source.label}（${backend} / ${deviceKindLabel(source.device_kind)}）`;
}

export function VideoSourcePanel({ sources, onSelectSource }: Props) {
  const selected = sources.find((item) => item.is_selected) ?? sources[0];
  const recommended = findRecommendedSource(sources);
  const recommendedText = buildRecommendedSourceText(recommended);
  const showGenericLabelHint = usesGenericDeviceLabel(selected?.label);

  return (
    <section className="panel">
      <h2>输入源选择</h2>
      <label htmlFor="video-source-select" className="label">
        视频输入源
      </label>
      <select
        id="video-source-select"
        aria-label="视频输入源"
        value={selected?.id ?? ''}
        onChange={(event) => void onSelectSource?.(event.target.value)}
      >
        {sources.map((source) => (
          <option key={source.id} value={source.id}>
            {source.label}
          </option>
        ))}
      </select>
      {selected ? <p>{buildSourceMeta(selected)}</p> : null}
      {recommendedText ? <p>{recommendedText}</p> : null}
      <p>建议优先在 OBS 中开启 Virtual Camera，再回到这里确认最近抓取截图是否正确。</p>
      {selected?.device_kind === 'physical' ? (
        <p>当前选中的是实体采集设备；正式使用时建议切换到 OBS Virtual Camera，避免和 OBS/其他程序争用物理采集卡。</p>
      ) : null}
      <p>可展开页面下方调试面板，查看最近抓取截图预览来确认当前输入源是否正确。</p>
      {showGenericLabelHint ? (
        <p>当前名称仍是系统索引占位名（如 {selected?.label}），可结合下方截图预览确认它对应的是哪一路画面。</p>
      ) : null}
    </section>
  );
}
