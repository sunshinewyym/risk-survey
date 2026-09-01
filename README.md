# ylaw-survey

独立部署的客户问卷系统，使用 Django 5.2 LTS、PostgreSQL 17 和 Docker Compose。

## 已实现

- 创建多个问卷，配置标题、说明、发布状态及独立 `slug`；
- 配置单行文本、多行文本、单选、多选、下拉题及必填状态；
- 公开地址 `/s/<slug>/`，客户无需注册；
- PostgreSQL 保存提交时间、每一道题及答案快照；
- Django Admin 查看、搜索、按问卷和时间筛选；
- Admin 批量导出 CSV、Excel 和 Markdown；
- 独立活动报名页 `/apply/`，支持一家企业登记多位参会人员；
- 报名后台汇总报名公司、参会人数、来源渠道和热门问题；
- 报名成功后可选发送飞书群机器人提醒，通知失败不影响数据保存；
- 使用项目品牌色的响应式现代后台界面，并保留 Django 原生权限体系；
- Django CSRF、安全 Cookie 和反向代理 HTTPS 识别；
- PostgreSQL Docker Volume、容器自动重启、每日数据库备份；
- 默认导入现有的联营项目风险诊断问卷（44 个可配置问题，不向客户展示评分）。

## 独立性边界

- Compose 项目名：`ylaw-survey`；
- 服务器目录：`/opt/ylaw-survey/`；
- Web 仅发布到 `127.0.0.1:8082`；
- PostgreSQL 没有 `ports` 配置，仅在 `ylaw-survey-internal` 网络内访问；
- 数据卷：`ylaw-survey-postgres-data`；
- 不使用或修改 80、443、8081，不执行 `docker compose down`、`docker rm`、`docker prune`。

## 服务器部署

先将项目上传到 `/opt/ylaw-survey/`，然后只读检查环境：

```bash
cd /opt/ylaw-survey
chmod +x entrypoint.sh scripts/*.sh
./scripts/preflight.sh
```

只有脚本明确显示 `8082` 空闲后才能继续：

```bash
cp .env.example .env
chmod 600 .env
```

编辑 `.env`，至少替换以下三项：

```text
DJANGO_SECRET_KEY
POSTGRES_PASSWORD
DJANGO_SUPERUSER_PASSWORD
```

如需飞书群提醒，请在目标群添加“自定义机器人”，并填写：

```text
FEISHU_WEBHOOK_URL
FEISHU_WEBHOOK_SECRET（机器人未开启签名校验时留空）
```

Webhook 未配置或临时发送失败时，报名仍会正常写入数据库，后台会显示通知状态。

可使用以下命令生成随机值：

```bash
openssl rand -hex 48
```

启动独立 Compose 项目：

```bash
docker compose -p ylaw-survey up -d --build
docker compose -p ylaw-survey ps
curl --fail http://127.0.0.1:8082/healthz
```

本地检查地址：

```text
http://127.0.0.1:8082/
http://127.0.0.1:8082/survey/
http://127.0.0.1:8082/admin/
http://127.0.0.1:8082/apply/
http://127.0.0.1:8082/s/joint-project-risk-diagnosis/
```

## Cloudflare Tunnel

在现有 Tunnel 中新增一条 Published application：

| Public hostname | Service URL |
|---|---|
| `survey.ylawteam.com` | `http://127.0.0.1:8082` |

公开问卷地址为 `https://survey.ylawteam.com/survey/`（原根地址继续可用），活动报名地址为 `https://survey.ylawteam.com/apply/`，管理后台为 `https://survey.ylawteam.com/admin/`，报名统计位于后台“活动报名”。
如使用 Cloudflare Access，只保护 `survey.ylawteam.com/admin/*`，不要保护整个域名，否则客户将无法匿名填写。

## 备份

`backup` 容器启动后立即生成一次 PostgreSQL 自定义格式备份，此后每 24 小时备份一次，默认保留 14 天：

```text
/opt/ylaw-survey/backups/ylaw-survey-YYYYMMDD-HHMMSS.dump
```

手动备份：

```bash
cd /opt/ylaw-survey
./scripts/backup-now.sh
```

备份目录应再同步到服务器外部存储，避免服务器磁盘整体故障时备份一并丢失。

## 本机测试

没有 Docker 时可以使用 SQLite 运行 Django 测试：

```bash
py -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
$env:DJANGO_SECRET_KEY="local-test-secret"
$env:DJANGO_USE_SQLITE="true"
$env:DJANGO_SECURE_COOKIES="false"
.venv/Scripts/python manage.py test
```
