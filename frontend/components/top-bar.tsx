'use client';

import type { VideoSource } from '../types/api';

type Props = {
  sources: VideoSource[];
  selectedSourceId: string;
  debugOpen: boolean;
  onToggleDebug: () => void;
  onSelectSource: (sourceId: string) => void;
};

export function TopBar({ sources, selectedSourceId, debugOpen, onToggleDebug, onSelectSource }: Props) {
  return (
    <div className="top-bar">
      <div className="tb-left">
        <div className="tb-source-select">
          <label htmlFor="video-source-select" className="tb-label">视频输入源</label>
          <select
            id="video-source-select"
            aria-label="视频输入源"
            value={selectedSourceId}
            onChange={(e) => onSelectSource(e.target.value)}
          >
            {sources.length === 0 && <option value="">未检测到输入源</option>}
            {sources.map((source) => (
              <option key={source.id} value={source.id}>
                {source.label}
              </option>
            ))}
          </select>
        </div>

        <button
          type="button"
          className={`tb-debug-btn ${debugOpen ? 'active' : ''}`}
          onClick={onToggleDebug}
        >
          {debugOpen ? '收起调试' : '调试'}
        </button>
      </div>

      <div className="tb-right">
        <span className="tb-brand">Pokémon Champions Assistant</span>
      </div>
    </div>
  );
}
