# Lark OpenAI Bot（长连接版）

这是一个可在 Lark 私聊和群聊中使用的 AI 机器人。默认采用 Lark 官方 SDK 的 WebSocket 长连接方式，不需要公网域名，也不需要配置 HTTP 回调地址。

## 已实现功能

- 私聊机器人，直接发送文字即可提问
- 群聊中 `@机器人` 或发送 `/ai 问题` 触发
- 使用 OpenAI Responses API 生成回复
- 每个群成员保留独立的连续对话上下文
- 支持中文、英文和印尼语
- `/reset`、`重置对话` 或 `清空对话` 可清空上下文
- 事件去重，防止同一消息重复回复
- 可通过 `ALLOWED_OPEN_IDS` 限制使用人员
- 长连接断开后由 Lark SDK自动重连

> 第一版只处理文字消息。图片、文件、语音、公司知识库、邮件、GitHub 和多维表格可以在后续阶段接入。

## 一、Lark 开放平台配置

### 1. 创建企业自建应用

在 Lark Developer Console 创建企业自建应用，并添加“机器人”能力。

### 2. 开通权限

至少开通：

- `im:message`：获取与发送单聊、群组消息
- 接收群组中用户 `@机器人` 消息所需权限

不需要开通“读取群内全部消息”。

### 3. 配置事件

在“事件与回调”中：

1. 订阅方式选择“使用长连接接收事件”
2. 添加事件 `im.message.receive_v1`
3. 保存配置

### 4. 获取应用凭证

进入“凭证与基础信息”，复制：

- App ID
- App Secret

不要把 App Secret、OpenAI API Key 上传到 GitHub，也不要发到群聊或聊天截图里。

### 5. 创建并发布版本

点击“创建版本”，填写版本号和更新说明，选择可用范围，然后提交发布。应用发布后，权限和事件配置才会对组织成员正式生效。

## 二、Mac 本地运行

### 1. 打开项目目录

```bash
cd ~/awesome-llm-apps/starter_ai_agents/lark_openai_bot
```

实际克隆位置不同，请把前面的路径替换成你的真实目录。

### 2. 创建虚拟环境

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. 安装依赖

```bash
python3 -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. 创建环境变量文件

```bash
cp .env.example .env
```

用文本编辑器打开 `.env`：

```bash
open -e .env
```

填写：

```dotenv
LARK_APP_ID=你的App_ID
LARK_APP_SECRET=你的App_Secret

LARK_VERIFICATION_TOKEN=
LARK_ENCRYPT_KEY=

OPENAI_API_KEY=你的OpenAI_API_Key
OPENAI_MODEL=gpt-5.6-terra

BOT_NAME=Leo AI
REQUIRE_MENTION_IN_GROUP=true
MAX_OUTPUT_TOKENS=1200
ALLOWED_OPEN_IDS=
```

长连接模式下，如果你没有在 Lark 中配置加密策略，`LARK_VERIFICATION_TOKEN` 和 `LARK_ENCRYPT_KEY` 可以保持为空。

### 5. 启动机器人

```bash
python3 -m app.ws_main
```

终端出现已连接日志后，程序需要保持运行。关闭终端或电脑休眠，机器人就会暂时离线。

## 三、测试

### 私聊

在 Lark 中找到机器人，发送：

```text
你好，请介绍一下你能做什么。
```

### 群聊

把机器人加入群聊，然后发送：

```text
@Leo AI 助手 帮我总结今天的工作重点
```

也可以发送：

```text
/ai 把这句话翻译成印尼语：明天下午三点开会
```

清除连续对话：

```text
/reset
```

## 四、Docker 运行

```bash
docker build -t lark-openai-bot .
docker run --rm --env-file .env lark-openai-bot
```

Docker 默认执行：

```bash
python -m app.ws_main
```

## 五、安全要求

- `.env` 已被 `.gitignore` 排除，不要强制提交
- App Secret 泄露后应立即在 Lark 开放平台重置
- OpenAI API Key 泄露后应立即撤销并重新创建
- 正式给员工使用前，建议配置 `ALLOWED_OPEN_IDS`
- 公司敏感信息接入前，需要增加权限分级、审计日志和数据保留策略

## 六、备用 HTTP 回调模式

项目仍保留 `app/main.py`，用于以后部署到具有公网 HTTPS 地址的服务器：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

当前本地测试优先使用长连接版：

```bash
python3 -m app.ws_main
```
