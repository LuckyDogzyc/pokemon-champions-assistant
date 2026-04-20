# Phase Detector Sample Fixtures

这个目录存放 phase-first / phase detector 的真实样本索引与标注 JSON。

当前约定：

- `index.json` 是回归入口；新增样本后，测试会自动参数化加载。
- 每个样本 JSON 至少包含：
  - `sample_id`
  - `image.width` / `image.height`
  - `phase.expected_phase`
  - `layout_variant`
  - `anchors.required_texts`
- battle / OCR 样本可额外包含 `roi_expectations`，用于定义逐区块验收标准：
  - `strong`：当前要求稳定精确命中的字段
  - `weak`：允许软匹配或人工核对的字段
  - `forbidden_hard_asserts`：禁止写成硬性回归断言的字段
  - 若某字段需要“值锁定但顺序可忽略”，可显式写出类似 `move_order_sensitive: false`
- `source_image_path` 当前允许指向本地临时缓存，仅作采样来源记录；
  回归测试**不依赖**该图片文件必须存在。
- 后续如果引入真实截图固化文件，优先放到本目录或其子目录，并继续通过 `index.json` 暴露。

建议新增样本时同时补齐：

1. `index.json` 条目
2. 对应样本 JSON
3. 该样本能覆盖的 phase / substate / ROI 说明
4. 如有 OCR 易混淆点，写入 `notes` / `ocr_hard_negatives`
