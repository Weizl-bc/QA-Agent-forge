# QA-Agent-forge

Multi-agent QA platform covering PRD review, test design, execution, bug validation and reporting.

## 代码结构（agent_core）

```
agent_core/
├── __init__.py
├── README.md
│
├── Infrastructure/          # 基础设施层（数据库、缓存、外部服务等）
│   └── __init__.py
│
├── agents/                  # Agent 定义与实现
│   ├── __init__.py
│   └── prd_review/          # PRD 评审 Agent
│       └── agent.py
│
├── common/                  # 公共工具模块
│   ├── __init__.py
│   └── env_config.py        # 环境变量加载（基于 python-dotenv）
│
├── llm/                     # LLM 接入层
│   ├── __init__.py
│   ├── base.py              # 基础模型创建（基于 langchain init_chat_model）
│   └── factory.py           # 模型工厂
│
├── models/                  # 数据模型 / Schema 定义
│   └── __init__.py
│
├── prompts/                 # Prompt 模板管理
│   └── __init__.py
│
├── rag/                     # RAG 检索增强生成
│   ├── __init__.py
│   ├── embeddings/          # 向量嵌入
│   ├── knowledge/           # 知识库管理
│   ├── pipelines/           # RAG 流水线
│   ├── retrievers/          # 检索器
│   └── vectorstores/        # 向量存储
│
├── tools/                   # Agent 可调用的工具
│   └── __init__.py
│
└── workflows/               # 工作流编排（基于 langgraph）
    ├── __init__.py
    └── test_task_workflow.py # 测试任务工作流
```

## 环境变量

项目通过 `agent_core/common/env_config.py` 统一管理环境变量，支持 `.env` 文件自动加载。

核心 LLM 相关变量：

| 变量名 | 说明 |
|---|---|
| `LLM_CHAT_MODEL_NAME` | 聊天模型名称 |
| `LLM_BASE_URL` | LLM API 基础地址 |
| `LLM_API_KEY` | LLM API 密钥 |
