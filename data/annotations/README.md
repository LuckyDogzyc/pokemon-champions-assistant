# Battle Screenshot Annotation Format

这份目录用于存放 Pokémon Champions Assistant 的训练/回归样本标注。

当前目标不是直接训练端到端模型，而是优先支持：
- 阶段识别（team_select / battle / switching / move_resolution）
- 布局模板与 ROI 锚点校准
- OCR 后处理回归测试
- 名称归一化与噪声文本过滤

## 目录结构
- `schema.json`：样本标注 schema（JSON Schema 草案）
- `samples/*.json`：具体样本标注

## 字段设计原则
1. **先支持规则与模板校准**，所以重点是 phase、layout_variant、anchors、noise_texts、roi_candidates。
2. **允许 ROI 先粗标**，后续可随着样本增加逐步精细化。
3. **保留 source_image_path**，让同一份标注既能用于开发期回放，也能用于回归测试。
4. **所有坐标使用归一化比例**，范围 `[0, 1]`，避免分辨率变动时失效。

## 推荐使用方式
### 1. 阶段识别回归
读取 `phase.expected_phase`、`anchors.required_texts`、`noise_texts`，用于验证 phase detector 是否能从真实截图判定阶段。

### 2. ROI 模板校准
读取 `roi_candidates` 中的：
- `player_name`
- `opponent_name`
- `team_list_left`
- `team_list_right`
- `instruction_banner`
- `command_panel`

用于迭代 `layout_anchors.py`。

### 3. OCR 后处理回归
读取：
- `targets.player_active_name`
- `targets.opponent_active_name`
- `noise_texts`
- `ocr_hard_negatives`

用于验证 OCR 候选清洗、黑名单过滤、alias/fuzzy matcher。

## ROI 约定
每个 ROI 使用：
```json
{
  "x": 0.08,
  "y": 0.80,
  "w": 0.22,
  "h": 0.07,
  "confidence": "approx"
}
```

其中：
- `x`, `y`：左上角归一化坐标
- `w`, `h`：归一化宽高
- `confidence`：`approx` / `verified`

## 当前样本覆盖
- `battle_default_garchomp_vs_froslass.json`：标准战斗视图
- `battle_move_menu_meganium_vs_froslass.json`：招式菜单展开的战斗视图
- `team_select_hippowdon_preview.json`：选人阶段视图

## 下一步建议
1. 补 10-20 张 battle 样本，覆盖天气、特效、不同镜头。
2. 补 switching / move_resolution 样本。
3. 将样本接入 pytest，做真实截图回归测试。
4. 后续可加入 `cropped_text_expectations` 字段，保存 ROI 内应识别出的原始文本。
