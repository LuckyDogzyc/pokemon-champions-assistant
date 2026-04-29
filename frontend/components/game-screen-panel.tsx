'use client';

type Props = {
  previewImageDataUrl: string | null;
  phase?: string | null;
};

export function GameScreenPanel({ previewImageDataUrl, phase }: Props) {
  return (
    <div className="game-screen-panel">
      {phase && (
        <div className="gsp-phase-badge">{phase}</div>
      )}
      {previewImageDataUrl ? (
        <img
          src={previewImageDataUrl}
          alt="实时游戏画面"
          className="gsp-image"
        />
      ) : (
        <div className="gsp-placeholder">
          <span>🎮</span>
          <p>暂无画面</p>
          <p className="gsp-hint">请先选择视频输入源</p>
        </div>
      )}
    </div>
  );
}
