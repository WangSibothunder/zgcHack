# 转诊迹 v0.8 验收清单

## P0 功能

- [x] 产品名称展示为“转诊迹｜转院病历证据时间轴”。
- [x] 仓库策略更新为 public synthetic demo。
- [x] v1 fixture 时间轴浏览、筛选、证据弹窗和模拟上传未回退。
- [x] v2 multipart 接口接收合成图片真实字节。
- [x] 未确认 synthetic 上传会被拒绝。
- [x] 不支持格式会被拒绝。
- [x] 模糊样例返回 `retake_required`。
- [x] 清晰样例进入 deterministic OCR fallback 和字段抽取。
- [x] 现场处理样例生成/插入时间轴节点。
- [x] 现场处理证据包含 bbox，并在前端原图上高亮。
- [x] 医生可确认正确、标记需复核、修改字段。
- [x] review 写入 runtime，刷新后仍可读取。
- [x] 接诊前摘要显示节点、现场材料和核验计数。
- [x] 页面持续显示 synthetic 与非诊断边界。
- [x] runtime、密钥、真实数据不进入 Git。

## 自动化验证

- [x] Backend `pytest` 覆盖 v1 fixture 和 v2 ingestion/review/summary。
- [x] Frontend lint/typecheck/unit/build 通过。
- [x] Playwright E2E 覆盖上传清晰合成材料、bbox 高亮、确认正确、摘要计数。

## 外部限制

- OCR 当前为 `deterministic_synthetic` fallback，界面明确展示“预置合成 OCR 演示回放”，未伪称真实 OCR 引擎处理。
- 摄像头采集使用浏览器 `getUserMedia`，权限由用户浏览器控制；权限拒绝时保留文件上传模式。
