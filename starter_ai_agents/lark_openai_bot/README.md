# Lark OpenAI Bot（第一版）

这是一个可以在 Lark 私聊和群聊中使用的 AI 机器人。

## 已实现功能

- 私聊机器人，直接发送文字即可提问
- 群聊中 `@机器人` 或使用 `/ai 问题` 触发
- 使用 OpenAI Responses API 生成回复
- 每个群成员保留独立的连续对话上下文
- 支持中文、英文和印尼语
- `/reset`、`重置对话` 或 `清空对话` 可清空上下文
- Lark 事件去重，防止同一事件重复回复
- 可通过 `ALLOWED_OPEN_IDS` 限制使用人员
- 提供健康检查和 Docker 部署方式

> 当前第一版只处理文字消息。图片、文件、语音、公司知识库、邮件和 GitHub 操作可以在第二阶段接入。

## 工作结构

```text
Lark 用户发送消息
        ↓
Lark 自建应用机器人
        ↓
POST /lark/events
        ↓
OpenAI Responses API
        ↓
机器人回复原消息
```

Codex 负责帮助开发和维护这个项目；真正在线回复 Lark 消息的是部署后的服务和 OpenAI API。

## 一、准备条件

1. 一个 Lark 工作区管理员或开发者账号
2. 一个 Lark 企业自建应用
3. 一个 OpenAI API Key
4. 一台能公开访问 HTTPS 的服务器，或本地测试隧道
5. Python 3.10 以上

## 二、创建 Lark 自建应用

1. 打开 Lark 开放平台开发者后台。
2. 创建“企业自建应用”。
3. 在“添加应用能力”中开启“机器人”。
4. 在权限管理中添加与以下用途对应的权限：
   - 接收发给机器人的消息
   - 接收群聊中提及机器人的消息
   - 以应用身份发送消息
5. 发布一个应用版本，并让管理员审核通过。

不同语言和后台版本中的权限名称可能略有差异，搜索关键词 `消息`、`机器人`、`群聊` 即可。

## 三、配置环境变量

进入项目目录：

```bash
cd starter_ai_agents/lark_openai_bot
cp .env.example .env
```

编辑 `.env`：

```env
LARK_APP_ID=你的App_ID
LARK_APP_SECRET=你的App_Secret
LARK_VERIFICATION_TOKEN=你的Verification_Token
OPENAI_API_KEY=你的OpenAI_API_Key
OPENAI_MODEL=gpt-5.6
BOT_NAME=Leo AI
REQUIRE_MENTION_IN_GROUP=true
MAX_OUTPUT_TOKENS=1200
ALLOWED_OPEN_IDS=
```

注意：

- 不要把真实 `.env` 文件提交到 GitHub。
- `ALLOWED_OPEN_IDS` 留空代表所有有权接触机器人的成员都可以使用。
- 需要限制人员时，填写逗号分隔的 Lark Open ID。

## 四、本地启动

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

浏览器打开：

```text
http://127.0.0.1:8000/health
```

正常结果：

```json
{"status":"ok","bot":"Leo AI"}
```

## 五、让 Lark 能访问本地服务

Lark 的事件回调必须使用公网 HTTPS 地址。本地测试可以使用 Cloudflare Tunnel：

```bash
brew install cloudflared
cloudflared tunnel --url http://localhost:8000
```

终端会显示一个类似下面的临时 HTTPS 地址：

```text
https://xxxx.trycloudflare.com
```

Lark 事件回调地址填写：

```text
https://xxxx.trycloudflare.com/lark/events
```

临时地址在重启后会变化，只适合测试。正式使用建议部署到云服务器或容器平台。

## 六、配置事件订阅

在 Lark 应用后台：

1. 打开“事件订阅”。
2. 请求地址填写 `https://你的域名/lark/events`。
3. 将后台生成或填写的 Verification Token 同步写入 `.env`。
4. 第一版请先不要设置 Encrypt Key。
5. 添加事件：`im.message.receive_v1`（接收消息）。
6. 保存并重新发布应用版本。

服务已经支持 Lark 的 URL Verification Challenge。

## 七、使用方法

私聊：

```text
帮我把这段中文翻译成印尼语
```

群聊：

```text
@Leo AI 帮我总结今天的销售汇报
```

也可以：

```text
/ai 帮我列一个明天的工作计划
```

清空当前对话：

```text
/reset
```

## 八、Docker 启动

```bash
docker build -t lark-openai-bot .
docker run --rm -p 8000:8000 --env-file .env lark-openai-bot
```

## 九、正式使用前建议

第一版的连续对话和事件去重保存在服务器内存中，服务重启后会清空。正式多人使用时建议增加：

- Redis：保存对话状态和事件去重
- PostgreSQL：保存用户、权限和操作日志
- 消息队列：处理长任务和高并发
- Lark Encrypt Key 解密与完整签名验证
- 管理后台：配置成员权限、提示词和用量上限
- 成本限制：限制单人每日调用次数和最大输出长度

## 十、下一阶段可接入

- Lark 文档和知识库问答
- 邮件自动总结并发到 Lark
- 销售日报收集和汇总
- 中文、英文、印尼语自动翻译
- GitHub Issue、PR 和代码检查
- 合同、报价单、发票信息提取
- Lark 多维表格写入与查询
