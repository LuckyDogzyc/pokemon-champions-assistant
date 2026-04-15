'use client';

import { DebugInfoPanel } from '../components/debug-info-panel';
import { PhaseStatusPanel } from '../components/phase-status-panel';
import { PokemonCard } from '../components/pokemon-card';
import { RecognitionStatusPanel } from '../components/recognition-status-panel';
import { TypeMatchupCard } from '../components/type-matchup-card';
import { VideoSourcePanel } from '../components/video-source-panel';
import { useRecognitionPolling, useVideoSources } from '../lib/hooks';

export default function HomePage() {
  const { sources } = useVideoSources();
  const { state } = useRecognitionPolling();

  const playerName = state?.player_active_name ?? state?.player?.name ?? null;
  const opponentName = state?.opponent_active_name ?? state?.opponent?.name ?? null;

  return (
    <main className="dashboard">
      <header className="hero">
        <h1>Pokemon Champions Assistant</h1>
        <p>第二窗口识别仪表盘</p>
      </header>

      <div className="grid two-columns">
        <VideoSourcePanel sources={sources} />
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
