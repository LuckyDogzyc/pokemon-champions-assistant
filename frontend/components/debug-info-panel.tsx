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

function renderFrameVariants(frameVariantsDebug: RecognitionState['frame_variants_debug']) {
  if (!frameVariantsDebug || Object.keys(frameVariantsDebug).length === 0) {
    return <p>暂无 FrameVariants 调试信息</p>;
  }

  return (
    <div>
      {Object.entries(frameVariantsDebug).map(([name, payload]) => (
        <div key={name} style={{ marginBottom: 16, padding: 8, border: '1px solid #333', borderRadius: 8 }}>
          <p style={{ fontWeight: 'bold' }}>{name}</p>
          <p>{`${name} 来源：${payload?.source ?? 'unknown'}`}</p>
          <p>{`${name} 尺寸：${payload?.width ?? 'N/A'} × ${payload?.height ?? 'N/A'}`}</p>
          {payload?.preview_image_data_url ? (
            <img
              src={payload.preview_image_data_url}
              alt={`${name} 预览`}
              style={{ maxWidth: '100%', borderRadius: 8, marginTop: 4 }}
            />
          ) : null}
        </div>
      ))}
    </div>
  );
}

function renderRoiPayloads(roiPayloads: Record<string, RoiPayload> | undefined) {
  if (!roiPayloads || Object.keys(roiPayloads).length === 0) {
    return <p>暂无 ROI 数据</p>;
  }

  // Sort by name for stable display
  const entries = Object.entries(roiPayloads).sort(([a], [b]) => a.localeCompare(b));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {entries.map(([name, payload]) => {
        const hasCrop = !!payload.preview_image_data_url;
        const hasOcrText = !!payload.recognized_texts || !!payload.pokemon_name ||
          (payload.raw_texts && payload.raw_texts.length > 0);

        return (
          <div key={name} style={{ padding: 8, border: '1px solid #555', borderRadius: 8, background: '#1a1a1a' }}>
            <p style={{ fontWeight: 'bold', color: '#89B4FA' }}>{name}</p>
            <p style={{ fontSize: '0.85em', color: '#aaa' }}>
              角色: {payload.role ?? 'N/A'} | 来源: {payload.source ?? 'N/A'}
            </p>

            {/* Crop preview */}
            {hasCrop && (
              <div style={{ margin: '8px 0' }}>
                <img
                  src={payload.preview_image_data_url!}
                  alt={`${name} crop`}
                  style={{ maxWidth: 280, maxHeight: 120, borderRadius: 4, border: '1px solid #444' }}
                />
                {payload.crop_width && payload.crop_height && (
                  <p style={{ fontSize: '0.8em', color: '#888' }}>
                    {payload.crop_width} × {payload.crop_height}
                  </p>
                )}
              </div>
            )}

            {/* OCR text results */}
            <div style={{ fontSize: '0.9em' }}>
              {/* Status panel fields */}
              {payload.pokemon_name && (
                <p>宝可梦: <strong style={{ color: '#A6E3A1' }}>{payload.pokemon_name}</strong></p>
              )}
              {payload.hp_text && <p>HP: {payload.hp_text}</p>}
              {payload.hp_percentage && <p>HP%: {payload.hp_percentage}</p>}
              {payload.level && <p>等级: {payload.level}</p>}
              {payload.status_abnormality && <p style={{ color: '#F38BA8' }}>异常状态: {payload.status_abnormality}</p>}

              {/* Move list */}
              {payload.recognized_texts && payload.recognized_texts.length > 0 && (
                <div>
                  <p>技能识别 ({payload.recognized_count ?? payload.recognized_texts.length}):</p>
                  <ul style={{ margin: 0, paddingLeft: 20 }}>
                    {payload.recognized_texts.map((t, i) => (
                      <li key={i}>{t}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Raw texts (status panel) */}
              {payload.raw_texts && payload.raw_texts.length > 0 && (
                <div>
                  <p>原始 OCR 文本:</p>
                  <pre style={{ fontSize: '0.8em', color: '#CDD6F4', background: '#111', padding: 4, borderRadius: 4 }}>
                    {JSON.stringify(payload.raw_texts, null, 2)}
                  </pre>
                </div>
              )}

              {payload.matched_by && (
                <p>匹配方式: {payload.matched_by}</p>
              )}
            </div>

            {/* Pixel box info */}
            {payload.pixel_box && (
              <p style={{ fontSize: '0.8em', color: '#666' }}>
                box: l={payload.pixel_box.left} t={payload.pixel_box.top} w={payload.pixel_box.width} h={payload.pixel_box.height}
              </p>
            )}
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
          <p>当前 OCR provider：{state?.ocr_provider ?? 'unknown'}</p>
          {state?.ocr_warning ? (
            <p style={{ color: '#ffb347' }}>{state.ocr_warning}</p>
          ) : null}

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
            <h3>ROI 分区 OCR 识别结果</h3>
            {renderRoiPayloads(state?.roi_payloads)}
          </div>

          <div>
            <h3>抓帧诊断</h3>
            <p>抓帧方式：{state?.capture_method ?? 'N/A'}</p>
            <p>抓帧后端：{state?.capture_backend ?? 'N/A'}</p>
            <p>抓帧错误：{state?.capture_error ?? 'N/A'}</p>
            <p>错误详情：{state?.capture_error_detail ?? 'N/A'}</p>
            <p>识别错误：{state?.recognition_error ?? 'N/A'}</p>
            <p>识别错误详情：{state?.recognition_error_detail ?? 'N/A'}</p>
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
            <h3>FrameVariants</h3>
            {renderFrameVariants(state?.frame_variants_debug)}
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
