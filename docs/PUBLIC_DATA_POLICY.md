# Public Data Policy

`WangSibothunder/zgcHack` 是 public synthetic demo 仓库。

## 允许提交

- 虚构病例 fixtures。
- 合成图片、合成 OCR、sidecar bbox JSON。
- 示例配置、测试代码、演示脚本。
- 明确标注为 `合成演示数据` 的材料。

## 禁止提交

- 真实病历、真实报告截图、真实 OCR 内容。
- 真实患者姓名、就诊号、电话、住址、证件号、条码或二维码。
- API Key、`.env`、token、cookie、credential。
- runtime 上传内容、OCR 缓存、SQLite/数据库运行文件和日志。
- 模型权重、大型本地缓存或私有部署配置。

## 必须忽略

`.gitignore` 必须覆盖：

```text
runtime/
demo-app/backend/runtime/
uploads/
real-data/
private-records/
*.sqlite
*.sqlite3
*.db
*.log
.env
.env.*
```

## 真实材料边界

本仓库不处理真实患者资料。未来真实材料验证必须进入独立合规环境，并先完成授权、脱敏、访问控制、存储加密、审计、删除/保留策略和合规评审。
