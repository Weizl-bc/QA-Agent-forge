# Backend

QA Agent Forge 的 FastAPI 后端服务。

## 安装依赖

在仓库根目录执行：

```bash
uv sync --dev
```

## 启动开发服务

```bash
uv run uvicorn backend.app.main:app --reload
```

服务启动后可访问：

- API 文档：<http://127.0.0.1:8000/docs>
- 健康检查：<http://127.0.0.1:8000/api/v1/health>

## MySQL 配置

服务从仓库根目录的 `.env` 读取以下配置：

```dotenv
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=your_user
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=qa_agent_forge
MYSQL_CONNECT_TIMEOUT_SECONDS=5
```

数据库表由外部维护，后端不会自动建表或执行迁移。

## 数据目录接口

以下资源均提供新增、详情、分页查询、部分更新和逻辑删除接口：

- `/api/v1/companies`
- `/api/v1/businesses`
- `/api/v1/platforms`
- `/api/v1/systems`
- `/api/v1/pages`

分页接口默认使用 `page_no=1&page_size=20&sort_by=id&sort_order=desc`。完整筛选参数和请求模型可在 `/docs` 中查看。

## 运行测试

```bash
uv run pytest backend/tests
```
