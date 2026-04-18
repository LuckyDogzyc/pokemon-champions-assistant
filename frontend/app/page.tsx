'use client';

import { DebugInfoPanel } from '../components/debug-info-panel';
import { PhaseStatusPanel } from '../components/phase-status-panel';
import { PokemonCard } from '../components/pokemon-card';
import { RecognitionStatusPanel } from '../components/recognition-status-panel';
import { TypeMatchupCard } from '../components/type-matchup-card';
import { VideoSourcePanel } from '../components/video-source-panel';
import { useRecognitionPolling, useVideoSources } from '../lib/hooks';

function CapturePreviewPanel({
  previewImageDataUrl,
  captureError,
}: {
  previewImageDataUrl?: string | null;
  captureError?: string | null;
}) {
  return (
    <section className="panel">
      <h2>最近抓取截图</h2>
      {previewImageDataUrl ? (
        <img
          src={previewImageDataUrl}
          alt="最近抓取截图预览"
          style={{ maxWidth: '100%', borderRadius: 8, width: '100%' }}
        />
      ) : (
        <p>暂无截图</p>
      )}
      {captureError ? <p>最近一次抓帧失败：{captureError}</p> : null}
    </section>
  );
}

export default function HomePage() {
  const { sources, selectSource } = useVideoSources();
  const { state, restartSession } = useRecognitionPolling();

  const playerName = state?.player_active_name ?? state?.player?.name ?? null;
  const opponentName = state?.opponent_active_name ?? state?.opponent?.name ?? null;

  const handleSelectSource = async (sourceId: string) => {
    await selectSource(sourceId);
    await restartSession();
  };

  return (
    <main className="dashboard">
      <header className="hero">
        <h1>Pokemon Champions Assistant</h1>
        <p>第二窗口识别仪表盘</p>
      </header>

      <div className="grid two-columns">
        <div>
          <VideoSourcePanel sources={sources} onSelectSource={handleSelectSource} />
          <CapturePreviewPanel
            previewImageDataUrl={state?.preview_image_data_url}
            captureError={state?.capture_error}
          />
        </div>
        <PhaseStatusPanel phase={state?.current_phase ?? 'unknown'} />
      </div>

      <div className="grid two-columns">
        <RecognitionStatusPanel
          title="我方识别"
          name={playerName}
          confidence={state?.player?.confidence ?? 0}
          source={state?.player?.source ?? 'mock'}
        />
        <RecognitionStatusPanel
          title="对方识别"
          name={opponentName}
          confidence={state?.opponent?.confidence ?? 0}
          source={state?.opponent?.source ?? 'mock'}
        />
      </div>

      <div className="grid two-columns">
        <PokemonCard title="宝可梦资料" name={playerName} subtitle="我方当前场上宝可梦" />
        <PokemonCard title="宝可梦资料" name={opponentName} subtitle="对方当前场上宝可梦" />
      </div>

      <TypeMatchupCard summary="根据当前识别结果展示属性克制摘要。" />
      <DebugInfoPanel state={state ?? null} />
    </main>
  );
}
