'use client';

import { useState } from 'react';

import type { RecognitionState, RoiPayload } from '../types/api';

type Props = {
  state: RecognitionState | null;
};

function formatRoi(roi: RecognitionState['player']['debug_roi']) {
  if (!roi) {
    return 'N/A';
  }

  return `x=${roi.x}, y=${roi.y}, w=${roi.w}, h=${roi.h}, confidence=${roi.confidence ?? 'n/a'}`;
}

function renderTeamList(team: string[] | undefined) {
  if (!team || team.length === 0) {
    return <p>N/A</p>;
  }

  return (
    <ul>
      {team.map((member) => (
        <li key={member}>{member}</li>
      ))}
    </ul>
  );
}

function renderRoiPayloadEntries(roiPayloads: RecognitionState['roi_payloads']) {
  if (!roiPayloads || Object.keys(roiPayloads).length === 0) {
    return <p>暂无局部 ROI 结果</p>;
  }

  return (
    <div>
      {Object.entries(roiPayloads).map(([roiName, payload]) => {
        const roiPayload = payload as RoiPayload;
        const recognizedTexts = Array.isArray(roiPayload.recognized_texts) ? roiPayload.recognized_texts : [];
        const isStatusPanel = roiName.endsWith('_status_panel');

        return (
          <div key={roiName} style={{ marginBottom: 16, padding: 8, border: '1px solid #333', borderRadius: 8 }}>
            <p style={{ fontWeight: 'bold' }}>{`${roiName}（${roiPayload.role ?? 'unknown'}）`}</p>

            {isStatusPanel ? (
              <>
                {roiPayload.pokemon_name ? (
                  <p>🎴 宝可梦：{roiPayload.pokemon_name}</p>
                ) : null}
                {roiPayload.hp_text ? (
                  <p>❤️ HP：{roiPayload.hp_text}</p>
                ) : null}
                {roiPayload.hp_percentage ? (
                  <p>📊 HP 百分比：{roiPayload.hp_percentage}</p>
                ) : null}
                {roiPayload.level ? (
                  <p>⭐ 等级：{roiPayload.level}</p>
                ) : null}
                {roiPayload.status_abnormality ? (
                  <p style={{ color: '#ff6b6b' }}>⚠️ 状态异常：{roiPayload.status_abnormality}</p>
                ) : null}
                {roiPayload.matched_by ? <p>{`识别方式：${roiPayload.matched_by}`}</p> : null}
                {Array.isArray(roiPayload.raw_texts) && roiPayload.raw_texts.length > 0 ? (
                  <p style={{ fontSize: '0.85em', color: '#888' }}>{`原始文本：${roiPayload.raw_texts.join(' / ')}`}</p>
                ) : null}
              </>
            ) : (
              <>
                {typeof roiPayload.recognized_count === 'number' ? (
                  <p>{`识别条目（${roiPayload.recognized_count}）：${recognizedTexts.join(' / ') || 'N/A'}`}</p>
                ) : null}
                {roiPayload.matched_by ? <p>{`识别方式：${roiPayload.matched_by}`}</p> : null}
              </>
            )}

            {roiPayload.preview_image_data_url ? (
              <img
                src={roiPayload.preview_image_data_url}
                alt={`${roiName} ROI 预览`}
                style={{ maxWidth: '100%', borderRadius: 8, marginTop: 4 }}
              />
            ) : null}
          </div>
        );
      })}
    </div>
  );
}

export function DebugInfoPanel({ state }: Props) {
  const [expanded, setExpanded] = useState(false);
  const evidence = state?.phase_evidence ?? [];
  const teamPreview = state?.team_preview;

  return (
    <section className="panel">
      <button type="button" onClick={() => setExpanded((current) => !current)}>
        {expanded ? '收起调试面板' : '展开调试面板'}
      </button>

      {expanded ? (
        <>
          <h2>调试信息</h2>
          <p>布局模板：{state?.layout_variant ?? 'unknown'}</p>

          <div>
            <h3>阶段证据</h3>
            {evidence.length > 0 ? (
              <ul>
                {evidence.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : (
              <p>暂无阶段证据</p>
            )}
          </div>

          <div>
            <p>我方原始文本：{state?.player?.debug_raw_text ?? 'N/A'}</p>
            <p>对方原始文本：{state?.opponent?.debug_raw_text ?? 'N/A'}</p>
            <p>我方匹配方式：{state?.player?.matched_by ?? 'N/A'}</p>
            <p>对方匹配方式：{state?.opponent?.matched_by ?? 'N/A'}</p>
            <p>我方 ROI：{formatRoi(state?.player?.debug_roi)}</p>
            <p>对方 ROI：{formatRoi(state?.opponent?.debug_roi)}</p>
          </div>

          <div>
            <h3>抓帧诊断</h3>
            <p>抓帧方式：{state?.capture_method ?? 'N/A'}</p>
            <p>抓帧后端：{state?.capture_backend ?? 'N/A'}</p>
            <p>抓帧错误：{state?.capture_error ?? 'N/A'}</p>
            <p>错误详情：{state?.capture_error_detail ?? 'N/A'}</p>
          </div>

          <div>
            <h3>最近抓取截图</h3>
            {state?.preview_image_data_url ? (
              <img
                src={state.preview_image_data_url}
                alt="最近抓取截图预览"
                style={{ maxWidth: '100%', borderRadius: 8 }}
              />
            ) : (
              <p>暂无截图</p>
            )}
          </div>

          <div>
            <h3>局部 ROI 结果</h3>
            {renderRoiPayloadEntries(state?.roi_payloads)}
          </div>

          <div>
            <h3>队伍预览</h3>
            <p>已选数量：{teamPreview?.selected_count ?? 'N/A'}</p>
            <p>指令文本：{teamPreview?.instruction_text ?? 'N/A'}</p>
            <div>
              <p>我方队伍</p>
              {renderTeamList(teamPreview?.player_team)}
            </div>
            <div>
              <p>对方队伍</p>
              {renderTeamList(teamPreview?.opponent_team)}
            </div>
          </div>
        </>
      ) : null}
    </section>
  );
}
