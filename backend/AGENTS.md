# FastAPI 项目开发规范

# 1. 总体原则

FastAPI 项目禁止把所有逻辑写在 `main.py` 或单个 router 文件中。项目必须按照“接口层、业务层、数据访问层、模型层、基础设施层”进行拆分。

核心原则如下：

1. Router / Endpoint 只负责 HTTP 入参、出参、状态码、接口路径定义。
2. Service 只负责业务流程编排和业务规则处理。
3. Repository 只负责数据库访问，不允许包含复杂业务判断。
4. Schema 只负责接口请求和响应的数据结构。
5. Model 只负责数据库表结构映射。
6. Core 只负责配置、安全、日志、异常等基础能力。
7. Utils 只放无业务语义的通用工具函数。
8. 任何文件都不能变成“万能文件”。
9. 新增代码时，优先复用已有模块，不允许重复造相同职责的类或函数。
10. 所有接口、类、函数、变量命名必须能表达真实业务含义，禁止使用模糊命名。

---

# 2. 推荐项目结构

推荐结构如下：

```text
app/
├── main.py                         # FastAPI 应用入口
├── api/                            # API 路由层
│   ├── __init__.py
│   └── v1/
│       ├── __init__.py
│       ├── router.py               # v1 路由聚合
│       └── endpoints/
│           ├── __init__.py
│           ├── user_endpoint.py
│           ├── order_endpoint.py
│           └── task_endpoint.py
├── core/                           # 核心基础设施
│   ├── __init__.py
│   ├── config.py                   # 配置
│   ├── security.py                 # 鉴权、加密、Token
│   ├── logging.py                  # 日志配置
│   ├── exception.py                # 全局异常
│   └── constants.py                # 全局常量
├── db/                             # 数据库相关
│   ├── __init__.py
│   ├── session.py                  # 数据库连接和 Session
│   └── base.py                     # ORM Base
├── models/                         # 数据库模型
│   ├── __init__.py
│   ├── user_model.py
│   ├── order_model.py
│   └── task_model.py
├── schemas/                        # Pydantic 请求/响应模型
│   ├── __init__.py
│   ├── user_schema.py
│   ├── order_schema.py
│   └── task_schema.py
├── services/                       # 业务服务层
│   ├── __init__.py
│   ├── user_service.py
│   ├── order_service.py
│   └── task_service.py
├── repositories/                   # 数据访问层
│   ├── __init__.py
│   ├── user_repository.py
│   ├── order_repository.py
│   └── task_repository.py
├── dependencies/                   # FastAPI Depends 依赖
│   ├── __init__.py
│   ├── auth_dependency.py
│   └── db_dependency.py
├── clients/                        # 外部服务客户端
│   ├── __init__.py
│   ├── sms_client.py
│   ├── payment_client.py
│   └── waybill_client.py
├── enums/                          # 枚举
│   ├── __init__.py
│   ├── user_enum.py
│   └── order_enum.py
├── utils/                          # 通用工具
│   ├── __init__.py
│   ├── datetime_util.py
│   ├── string_util.py
│   └── id_util.py
└── tests/                          # 测试代码
    ├── __init__.py
    ├── test_user_api.py
    ├── test_order_service.py
    └── test_task_repository.py
```

---

# 3. 文件职责要求

## 3.1 `main.py`

`main.py` 只允许做应用启动和全局注册，不允许写业务逻辑。

允许内容：

```python
from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.exception import register_exception_handlers


def create_app() -> FastAPI:
    app = FastAPI(title="Task Platform API")

    app.include_router(api_router, prefix="/api/v1")
    register_exception_handlers(app)

    return app


app = create_app()
```

禁止内容：

```python
@app.get("/users")
def list_users():
    # 禁止在 main.py 里直接写接口和业务逻辑
    pass
```

---

## 3.2 Endpoint 文件

Endpoint 文件只负责接口定义，不处理复杂业务。

正确示例：

```python
from fastapi import APIRouter, Depends

from app.schemas.user_schema import UserCreateRequest, UserResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["用户管理"])


@router.post("", response_model=UserResponse)
def create_user(
    request: UserCreateRequest,
    user_service: UserService = Depends(),
):
    return user_service.create_user(request)
```

Endpoint 中禁止：

1. 直接写 SQL。
2. 直接操作 ORM Model。
3. 编写复杂 `if/else` 业务规则。
4. 拼接复杂返回结构。
5. 直接访问 Redis、MQ、第三方接口。
6. 直接处理事务。

---

## 3.3 Service 文件

Service 负责业务规则、业务流程编排、事务边界和跨模块协调。

正确示例：

```python
from app.repositories.user_repository import UserRepository
from app.schemas.user_schema import UserCreateRequest


class UserService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def create_user(self, request: UserCreateRequest):
        existing_user = self.user_repository.get_by_mobile(request.mobile)
        if existing_user:
            raise ValueError("手机号已存在")

        return self.user_repository.create_user(request)
```

Service 中允许：

1. 参数业务校验。
2. 业务状态流转。
3. 调用多个 Repository。
4. 调用外部服务 Client。
5. 组装业务结果。
6. 控制事务边界。

Service 中禁止：

1. 写原生 SQL。
2. 直接拼 HTTP Response。
3. 直接读取 FastAPI Request 对象。
4. 写无业务语义的工具方法。
5. 直接创建数据库连接。

---

## 3.4 Repository 文件

Repository 只负责数据库读写。

正确示例：

```python
from sqlalchemy.orm import Session

from app.models.user_model import UserModel


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_mobile(self, mobile: str) -> UserModel | None:
        return self.db.query(UserModel).filter(UserModel.mobile == mobile).first()

    def create_user(self, user: UserModel) -> UserModel:
        self.db.add(user)
        self.db.flush()
        return user
```

Repository 中允许：

1. 查询数据库。
2. 新增、修改、删除数据库记录。
3. 简单查询条件组装。
4. 分页查询。

Repository 中禁止：

1. 写业务状态判断。
2. 调用其他 Service。
3. 调用 HTTP 接口。
4. 处理接口响应结构。
5. 写复杂业务流程。

---

## 3.5 Schema 文件

Schema 用于定义接口入参和出参。

命名必须体现用途：

```python
from pydantic import BaseModel, Field


class UserCreateRequest(BaseModel):
    mobile: str = Field(..., description="手机号")
    username: str = Field(..., description="用户名")


class UserUpdateRequest(BaseModel):
    username: str | None = Field(None, description="用户名")


class UserResponse(BaseModel):
    id: int = Field(..., description="用户ID")
    mobile: str = Field(..., description="手机号")
    username: str = Field(..., description="用户名")
```

不推荐使用模糊 Schema 命名：

```python
class UserDto(BaseModel):
    pass


class UserData(BaseModel):
    pass


class UserInfo(BaseModel):
    pass
```

除非项目已有明确约定，否则不推荐使用 `Dto`、`Vo`、`Bo` 这类 Java 风格后缀。FastAPI 项目中建议统一使用：

```text
CreateRequest
UpdateRequest
QueryRequest
Response
DetailResponse
ListResponse
PageResponse
```

---

## 3.6 Model 文件

Model 只表示数据库表结构。

正确示例：

```python
from sqlalchemy import Column, Integer, String

from app.db.base import Base


class UserModel(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True, comment="用户ID")
    mobile = Column(String(20), nullable=False, unique=True, comment="手机号")
    username = Column(String(64), nullable=False, comment="用户名")
```

Model 中禁止：

1. 写业务方法。
2. 写接口响应逻辑。
3. 写第三方服务调用。
4. 写复杂数据转换。

---

## 3.7 Dependency 文件

Dependency 只负责 FastAPI 依赖注入。

正确示例：

```python
from collections.abc import Generator

from app.db.session import SessionLocal


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

常见依赖文件：

```text
auth_dependency.py       # 登录态、Token、权限
db_dependency.py         # 数据库 Session
pagination_dependency.py # 分页参数
trace_dependency.py      # trace_id、request_id
```

---

## 3.8 Client 文件

第三方 HTTP、RPC、MQ、Redis 调用必须封装到 client 或 infrastructure 层。

推荐结构：

```text
app/clients/
├── payment_client.py
├── sms_client.py
└── waybill_client.py
```

正确示例：

```python
class SmsClient:
    def send_verify_code(self, mobile: str, code: str) -> None:
        pass
```

Service 调用：

```python
self.sms_client.send_verify_code(request.mobile, verify_code)
```

禁止在 Service 中散落 HTTP 请求：

```python
requests.post("https://sms.example.com/send", json={...})
```

---

## 3.9 Utils 文件

Utils 只放纯工具方法，不允许包含业务语义。

正确示例：

```python
from datetime import datetime


def format_datetime(value: datetime, pattern: str = "%Y-%m-%d %H:%M:%S") -> str:
    return value.strftime(pattern)
```

错误示例：

```python
def check_order_can_cancel(order):
    # 这是业务规则，不应该放 utils
    pass
```

---

# 4. 文件命名规则

Python 文件统一使用小写字母 + 下划线。

正确：

```text
user_service.py
order_repository.py
task_endpoint.py
user_schema.py
order_model.py
auth_dependency.py
datetime_util.py
```

错误：

```text
UserService.py
userService.py
userservice.py
user-service.py
user.service.py
```

不同职责文件使用固定后缀：

```text
接口层：xxx_endpoint.py
业务层：xxx_service.py
数据访问层：xxx_repository.py
数据库模型：xxx_model.py
接口模型：xxx_schema.py
枚举：xxx_enum.py
依赖注入：xxx_dependency.py
工具类：xxx_util.py
配置：config.py
常量：constants.py
异常：exception.py
```

如果业务模块名是多个单词，使用下划线连接：

```text
delivery_order_service.py
delivery_order_repository.py
delivery_order_endpoint.py
delivery_order_schema.py
```

禁止缩写业务名：

```text
do_service.py
usr_service.py
ord_repo.py
```

除非缩写是公司内部强约定，例如 `oms`、`wms`、`crm`、`erp`。

---

# 5. 类命名规则

类名使用 PascalCase。

正确：

```python
class UserService:
    pass


class OrderRepository:
    pass


class TaskCreateRequest:
    pass


class DeliveryOrderModel:
    pass
```

错误：

```python
class userService:
    pass


class user_service:
    pass


class USERSERVICE:
    pass
```

不同类型类使用固定后缀：

```text
业务服务类：UserService
数据访问类：UserRepository
数据库模型类：UserModel
请求参数类：UserCreateRequest
响应结果类：UserResponse
枚举类：UserStatusEnum
异常类：UserNotFoundException
第三方客户端类：PaymentClient
配置类：AppConfig
```

---

# 6. 函数命名规则

函数和方法使用小写字母 + 下划线。

函数命名必须以动词开头，表达动作。

正确：

```python
def create_user():
    pass


def update_order_status():
    pass


def get_user_by_mobile():
    pass


def list_task_by_page():
    pass


def delete_expired_token():
    pass
```

错误：

```python
def user():
    pass


def data():
    pass


def handle():
    pass


def process():
    pass


def doSomething():
    pass
```

常用动词规范：

```text
create_xxx     创建
update_xxx     更新
delete_xxx     删除
remove_xxx     移除
get_xxx        查询单个对象
list_xxx       查询列表
page_xxx       分页查询
count_xxx      统计数量
check_xxx      校验，返回 bool 或抛异常
validate_xxx   参数或业务规则校验
build_xxx      构建对象
convert_xxx    对象转换
sync_xxx       同步
send_xxx       发送消息
parse_xxx      解析
format_xxx     格式化
```

查询函数命名要求：

```python
def get_user_by_id(user_id: int):
    pass


def get_user_by_mobile(mobile: str):
    pass


def list_users_by_status(status: str):
    pass


def page_orders_by_user_id(user_id: int, page_no: int, page_size: int):
    pass
```

禁止使用无意义方法名：

```python
def handle_user():
    pass


def process_order():
    pass


def execute():
    pass


def run():
    pass
```

只有在抽象接口、Agent、任务执行器等统一入口中，才允许使用 `run`、`execute`。

---

# 7. 变量命名规则

变量使用小写字母 + 下划线。

正确：

```python
user_id = 1001
order_status = "PAID"
created_at = datetime.now()
task_list = []
user_repository = UserRepository()
```

错误：

```python
userId = 1001
orderstatus = "PAID"
CreatedAt = datetime.now()
lst = []
repo = UserRepository()
```

变量命名必须表达业务含义。

正确：

```python
pending_order_list = []
current_user = None
delivery_order_id = "DN202606280001"
receiver_mobile = "13100000000"
```

错误：

```python
list1 = []
data = None
obj = {}
temp = "DN202606280001"
phone = "13100000000"
```

允许的短变量：

```text
i, j      只允许在简单循环中使用
db        数据库 Session
e         只允许在异常捕获中使用
```

不推荐单独使用 `id`，优先使用 `user_id`、`order_id`、`task_id`。

布尔变量必须使用明确前缀：

```python
is_deleted = False
has_permission = True
can_cancel = True
should_retry = False
enable_cache = True
```

禁止：

```python
deleted = False
permission = True
cancel = True
retry = False
```

集合变量必须体现复数或集合语义：

```python
user_list = []
order_ids = []
task_map = {}
status_set = set()
```

禁止：

```python
user = []
order = []
task = {}
status = set()
```

---

# 8. 常量命名规则

常量使用全大写 + 下划线。

正确：

```python
MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 20
TOKEN_EXPIRE_SECONDS = 7200
ORDER_STATUS_PAID = "PAID"
```

错误：

```python
maxPageSize = 100
default_page_size = 20
tokenExpireSeconds = 7200
```

常量应集中放在：

```text
app/core/constants.py
```

或者业务模块自己的常量文件：

```text
app/constants/order_constant.py
```

如果常量只在一个文件内部使用，可以放在当前文件顶部。

---

# 9. 枚举命名规则

枚举类使用 PascalCase + Enum 后缀。

正确：

```python
from enum import Enum


class OrderStatusEnum(str, Enum):
    CREATED = "CREATED"
    PAID = "PAID"
    CANCELLED = "CANCELLED"
```

枚举值使用全大写 + 下划线。

正确：

```python
class TaskStatusEnum(str, Enum):
    WAITING_EXECUTE = "WAITING_EXECUTE"
    EXECUTING = "EXECUTING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
```

禁止魔法字符串散落在代码中：

```python
if order.status == "PAID":
    pass
```

推荐：

```python
if order.status == OrderStatusEnum.PAID:
    pass
```

---

# 10. 接口路径命名规则

接口路径统一使用小写字母 + 中划线。

正确：

```text
GET    /api/v1/users
GET    /api/v1/users/{user_id}
POST   /api/v1/orders
PUT    /api/v1/orders/{order_id}
DELETE /api/v1/orders/{order_id}
POST   /api/v1/orders/{order_id}/cancel
```

错误：

```text
/api/v1/getUser
/api/v1/user_list
/api/v1/order/cancelOrder
/api/v1/OrderDetail
```

REST 风格要求：

```text
查询列表：GET /resources
查询详情：GET /resources/{resource_id}
创建资源：POST /resources
全量更新：PUT /resources/{resource_id}
局部更新：PATCH /resources/{resource_id}
删除资源：DELETE /resources/{resource_id}
业务动作：POST /resources/{resource_id}/actions
```

业务动作示例：

```text
POST /orders/{order_id}/cancel
POST /orders/{order_id}/pay
POST /tasks/{task_id}/execute
POST /users/{user_id}/disable
```

---

# 11. Pydantic Schema 命名规则

请求类：

```text
UserCreateRequest
UserUpdateRequest
UserQueryRequest
UserLoginRequest
OrderCreateRequest
OrderCancelRequest
```

响应类：

```text
UserResponse
UserDetailResponse
UserListResponse
OrderResponse
OrderDetailResponse
PageResponse
```

分页响应推荐统一结构：

```python
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PageResponse(BaseModel, Generic[T]):
    total: int
    page_no: int
    page_size: int
    records: list[T]
```

禁止混用：

```python
class UserReq:
    pass


class UserDTO:
    pass


class UserVO:
    pass


class UserInfo:
    pass
```

除非项目已有历史规范，否则不要混用 Java 后端命名体系。

---

# 12. 注释规则

注释不是越多越好。注释必须解释“为什么这样做”，而不是重复“代码做了什么”。

## 12.1 必须写注释的场景

以下场景必须写注释：

1. 复杂业务规则。
2. 非直观的边界条件。
3. 临时兼容历史数据。
4. 外部系统特殊约定。
5. 金额、时间、状态流转等高风险逻辑。
6. 性能优化相关代码。
7. 安全、权限、加密、签名逻辑。

正确示例：

```python
# 历史订单缺少 receiver_city 字段，这里保留兼容逻辑，避免老数据查询失败。
if not order.receiver_city:
    order.receiver_city = infer_city_from_address(order.receiver_address)
```

错误示例：

```python
# 判断 receiver_city 是否为空
if not order.receiver_city:
    order.receiver_city = infer_city_from_address(order.receiver_address)
```

---

## 12.2 函数 Docstring 规则

公共函数、复杂业务函数、Service 方法必须写 Docstring。

推荐格式：

```python
def cancel_order(order_id: str, operator_id: int) -> None:
    """取消订单。

    当订单处于 CREATED 或 PAID 状态时允许取消。
    已发货、已签收、已关闭订单不允许取消。

    Args:
        order_id: 订单ID。
        operator_id: 操作人ID。

    Raises:
        OrderNotFoundException: 订单不存在。
        OrderStatusException: 当前状态不允许取消。
    """
```

简单私有函数可以不写 Docstring，但命名必须清楚。

---

## 12.3 类 Docstring 规则

复杂 Service、Client、Repository 建议写类注释。

```python
class OrderService:
    """订单业务服务。

    负责订单创建、取消、支付、状态流转等业务流程编排。
    不直接处理 HTTP 请求，也不直接拼接数据库 SQL。
    """
```

---

## 12.4 禁止无效注释

禁止写：

```python
# 创建用户
def create_user():
    pass


# 循环用户列表
for user in user_list:
    pass


# 返回结果
return result
```

这种注释没有信息增量，应该删除。

---

# 13. 设计范式

## 13.1 分层架构

推荐调用链路：

```text
endpoint -> service -> repository -> model -> database
```

示例：

```text
user_endpoint.py
    ↓
user_service.py
    ↓
user_repository.py
    ↓
user_model.py
```

禁止跨层调用：

```text
endpoint -> repository       # 不推荐
endpoint -> model            # 禁止
repository -> service        # 禁止
model -> service             # 禁止
utils -> service             # 禁止
```

---

## 13.2 依赖倒置

Service 不应该直接 new Repository。推荐通过依赖注入或工厂函数获取依赖。

推荐：

```python
class UserService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository
```

不推荐：

```python
class UserService:
    def __init__(self):
        self.user_repository = UserRepository()
```

---

## 13.3 单一职责

一个类只做一类事情。

正确：

```text
UserService：用户业务
UserRepository：用户数据访问
UserModel：用户表结构
UserCreateRequest：创建用户请求
```

错误：

```text
UserManager：既写接口、又写业务、又写数据库、又调第三方接口
CommonService：什么业务都放
BaseUtil：什么工具都放
```

---

## 13.4 面向业务建模

命名以业务领域为中心，而不是以技术动作命名。

正确：

```python
class DeliveryOrderService:
    pass


class WaybillService:
    pass


class PaymentService:
    pass
```

错误：

```python
class DataService:
    pass


class CommonService:
    pass


class ProcessService:
    pass
```

---

## 13.5 业务异常显式化

禁止直接抛出模糊异常：

```python
raise Exception("失败")
raise ValueError("错误")
```

推荐定义业务异常：

```python
class BusinessException(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message


class OrderStatusException(BusinessException):
    pass
```

使用：

```python
raise OrderStatusException(
    code="ORDER_STATUS_INVALID",
    message="当前订单状态不允许取消",
)
```

---

## 13.6 返回结构统一

接口返回结构必须统一，不允许每个接口随意返回。

推荐：

```python
from pydantic import BaseModel


class ApiResponse(BaseModel):
    success: bool
    code: str
    message: str
    data: object | None = None
```

示例：

```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "操作成功",
  "data": {}
}
```

错误：

```json
{
  "ok": true,
  "result": {}
}
```

另一个接口又返回：

```json
{
  "success": 1,
  "data": {},
  "msg": "ok"
}
```

---

## 13.7 参数校验前置

基础格式校验放在 Schema。

```python
from pydantic import BaseModel, Field


class UserCreateRequest(BaseModel):
    mobile: str = Field(..., min_length=11, max_length=11, description="手机号")
```

业务规则校验放在 Service。

```python
def create_user(self, request: UserCreateRequest):
    if self.user_repository.exists_by_mobile(request.mobile):
        raise BusinessException("USER_EXISTS", "手机号已存在")
```

禁止把业务校验全部塞进 endpoint。

---

## 13.8 外部服务调用隔离

第三方 HTTP、RPC、MQ、Redis 调用必须封装到 client 或 infrastructure 层。

推荐结构：

```text
app/clients/
├── payment_client.py
├── sms_client.py
└── waybill_client.py
```

正确：

```python
class SmsClient:
    def send_verify_code(self, mobile: str, code: str) -> None:
        pass
```

Service 调用：

```python
self.sms_client.send_verify_code(request.mobile, verify_code)
```

禁止在 Service 中散落 HTTP 请求：

```python
requests.post("https://sms.example.com/send", json={...})
```

---

## 13.9 事务边界清晰

事务应放在 Service 层控制，因为 Service 才知道完整业务流程。

示例：

```python
def create_order(self, request: OrderCreateRequest):
    with self.transaction_manager.begin():
        order = self.order_repository.create_order(request)
        self.order_log_repository.create_order_log(order.id)
        return order
```

禁止每个 Repository 自己随意提交事务，避免半成功半失败。

---

## 13.10 可测试性优先

Service 必须可以被单元测试直接调用。

好的 Service：

```python
def test_create_user_success():
    user_repository = FakeUserRepository()
    user_service = UserService(user_repository)

    result = user_service.create_user(request)

    assert result.mobile == request.mobile
```

差的 Service：

```python
class UserService:
    def create_user(self, request):
        db = SessionLocal()
        redis = Redis()
        requests.post(...)
```

这种代码强依赖数据库、Redis、外部接口，难以测试。

---

# 14. Agent 写代码时必须遵守的规则

如果 Codex、Claude Code 或其他 Agent 修改本项目代码，必须遵守以下约束：

1. 新增接口时，必须新增或复用对应的 endpoint、schema、service、repository。
2. 不允许把业务逻辑直接写在 endpoint 中。
3. 不允许把数据库查询写在 service 之外的任意位置。
4. 新增文件必须符合文件命名规则。
5. 新增类必须符合类命名规则。
6. 新增函数必须使用动词 + 业务对象命名。
7. 新增变量必须表达真实业务含义。
8. 不允许使用 `data`、`obj`、`temp`、`result` 作为长期变量名。
9. 不允许新增 `common.py`、`helper.py`、`manager.py` 这类模糊职责文件，除非已有明确目录规范。
10. 修改老代码时，优先保持当前模块风格一致。
11. 如果发现现有代码和本规范冲突，不要大范围重构，只修改本次任务相关范围。
12. 如果必须违反规范，需要在提交说明中写明原因。

---

# 15. 正例：新增用户接口

目录：

```text
app/api/v1/endpoints/user_endpoint.py
app/schemas/user_schema.py
app/services/user_service.py
app/repositories/user_repository.py
app/models/user_model.py
```

Endpoint：

```python
from fastapi import APIRouter, Depends

from app.schemas.user_schema import UserCreateRequest, UserResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["用户管理"])


@router.post("", response_model=UserResponse)
def create_user(
    request: UserCreateRequest,
    user_service: UserService = Depends(),
):
    return user_service.create_user(request)
```

Schema：

```python
from pydantic import BaseModel, Field


class UserCreateRequest(BaseModel):
    mobile: str = Field(..., min_length=11, max_length=11, description="手机号")
    username: str = Field(..., min_length=1, max_length=64, description="用户名")


class UserResponse(BaseModel):
    id: int = Field(..., description="用户ID")
    mobile: str = Field(..., description="手机号")
    username: str = Field(..., description="用户名")
```

Service：

```python
from app.repositories.user_repository import UserRepository
from app.schemas.user_schema import UserCreateRequest


class UserService:
    """用户业务服务。"""

    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def create_user(self, request: UserCreateRequest):
        """创建用户。

        Args:
            request: 创建用户请求。

        Raises:
            BusinessException: 手机号已存在。
        """
        existing_user = self.user_repository.get_by_mobile(request.mobile)
        if existing_user:
            raise BusinessException("USER_EXISTS", "手机号已存在")

        return self.user_repository.create_user(request)
```

Repository：

```python
from sqlalchemy.orm import Session

from app.models.user_model import UserModel
from app.schemas.user_schema import UserCreateRequest


class UserRepository:
    """用户数据访问层。"""

    def __init__(self, db: Session):
        self.db = db

    def get_by_mobile(self, mobile: str) -> UserModel | None:
        return self.db.query(UserModel).filter(UserModel.mobile == mobile).first()

    def create_user(self, request: UserCreateRequest) -> UserModel:
        user = UserModel(
            mobile=request.mobile,
            username=request.username,
        )
        self.db.add(user)
        self.db.flush()
        return user
```

---

# 16. 反例：禁止写法

禁止把所有逻辑写在 endpoint：

```python
@router.post("/users")
def create_user(request: UserCreateRequest, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.mobile == request.mobile).first()
    if user:
        return {"msg": "手机号已存在"}

    new_user = UserModel(mobile=request.mobile, username=request.username)
    db.add(new_user)
    db.commit()

    requests.post("https://sms.example.com/send", json={"mobile": request.mobile})

    return {"data": new_user}
```

问题：

1. endpoint 直接访问数据库。
2. endpoint 写业务规则。
3. endpoint 调用第三方接口。
4. 返回结构不统一。
5. 异常不规范。
6. 不利于单元测试。
7. 后续维护成本高。

---

# 17. 最终要求

FastAPI 项目必须做到：

```text
看文件名，就知道职责。
看类名，就知道处理哪个业务对象。
看函数名，就知道执行什么动作。
看变量名，就知道保存什么数据。
看目录结构，就知道代码应该放在哪里。
看调用链路，就知道业务从入口到数据库如何流转。
```

所有新增代码必须优先满足：

```text
清晰 > 灵活
稳定 > 炫技
可维护 > 少写几行
业务语义 > 技术缩写
分层明确 > 快速堆代码
```

---

# 18. 建议放置位置

如果用于 Codex 和 Claude Code，建议这样放：

```text
项目根目录
├── AGENTS.md
├── CLAUDE.md
└── docs/
    └── agent-rules/
        └── fastapi_agent_rules.md
```

`AGENTS.md` / `CLAUDE.md` 中引用：

```md
# Agent 必须遵守

在修改 FastAPI 后端代码前，必须阅读并遵守：

- `docs/agent-rules/fastapi_agent_rules.md`

如果现有代码和规范冲突，以当前模块已有模式为准，不允许大范围重构。
```
