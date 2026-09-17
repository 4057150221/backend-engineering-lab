# Day 8：全局异常处理

## 今日目标

给 API 加上统一的全局异常处理，让错误响应不再"哪里抓到在哪里抛"，而是由集中注册的处理器统一接管：

```text
当前状态：
  HTTPException      -> 每处路由自己 raise，detail 格式手动写
  Pydantic 校验失败  -> FastAPI 默认 422（保留不动）
  未捕获异常         -> FastAPI 默认 500（可能泄露堆栈）
  IntegrityError     -> 没有兜底，直接 500

目标状态：
  HTTPException      -> 保留现有 raise 方式，依然统一 JSON
  未捕获异常         -> 全局兜底 500，不泄露堆栈，带 error_code
  IntegrityError     -> 全局捕获，返回 409 + error_code
  Pydantic 校验失败  -> 保持默认格式不变
```

完成后应当能解释：

- 全局异常处理器（`@app.exception_handler`）和直接在路由里 `raise HTTPException` 各自的职责边界是什么；
- `IntegrityError` 在什么场景下会发生，为什么应用层预查不能完全替代数据库约束兜底；
- 为什么 500 响应绝不能泄露 Python 堆栈和异常详情；
- 为什么 Pydantic 校验错误（默认 422）不加以统一改写——面试官可能反问"你统一了其他所有错误，为什么 422 例外？"

## 今日边界

- 不改写 Pydantic 默认的 422 校验错误格式（FastAPI 默认的 `{"detail": [{"loc": [...], "msg": "...", "type": "..."}]}` 在 OpenAPI/Swagger 中有广泛的工具支持，统一改写反而是画蛇添足）；
- 不改写 `HTTPException` 的默认行为——`detail` 仍是字符串，兼容所有现有测试；
- 不过度精细化——只对 `Exception`（顶层兜底）和 `IntegrityError`（明确知道含义的数据库异常）注册处理器；
- 不覆盖 FastAPI 已有的 `RequestValidationError` 和 `StarletteHTTPException`，除非有明确需求；
- 不改变 401 异常的 `WWW-Authenticate` 响应头——这是 OAuth2 标准行为，不能丢失。

## 检查点A：理解全局异常处理器的机制

阅读 FastAPI 文档或代码实验后再写：

1. `@app.exception_handler(SomeException)` 可以注册一个函数，当 `SomeException` 或其子类被抛出时，该函数接管响应生成。
2. 处理器接收 `Request` 和异常实例，返回 `JSONResponse`（或其他响应）。
3. `HTTPException` 是 FastAPI/Starlette 的内置异常——注册 `@app.exception_handler(Exception)` 会**覆盖**其默认行为吗？想清楚异常处理器的优先级顺序。如果 500 兜底处理器覆盖了 `HTTPException`，需在 500 处理器里先判断是否是 `HTTPException` 并转发。
4. `sqlalchemy.exc.IntegrityError` 是 SQLAlchemy 的数据库约束冲突异常，它继承自 `sqlalchemy.exc.DBAPIError`，需要在 SQLAlchemy 的 engine 层捕获后转为 409。

## 检查点B：设计统一的错误响应结构

在 `app/error_handling.py` 中定义统一的响应 schema：

```python
class ErrorCode(str, Enum):
    DUPLICATE_ENTRY = "DUPLICATE_ENTRY"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"


class ErrorResponse(BaseModel):
    detail: str
    error_code: ErrorCode | None = None
```

要思考的问题：

- `ErrorCode` 枚举加在哪一步——是与 `ErrorResponse` 放在同一个 `error_handling.py`，还是放进 `schemas.py`？你觉得哪个分层更清晰？
- 为什么 `error_code` 是可选字段——哪些场景不需要它（提示：现有 `HTTPException` 继续用 `raise HTTPException(status_code=404, detail="Application not found")`，不需要 error_code 字段，因为 `detail` 已经足够人类理解）？
- 对现有测试的影响：之前很多测试断言 `response.json() == {"detail": "Application not found"}`。加入 `error_code` 字段后，如果 404/401 场景继续用 `raise HTTPException`（不附加 `error_code`），那这个字段在 404 响应中就不存在，新断言不能期待它有。但原来的精确匹配仍然会通过，因为 `HTTPException` 产生的响应仍然只有 `{"detail": "..."}`。

## 检查点C：实现 `IntegrityError` 处理器

```python
@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content=ErrorResponse(
            detail="A resource with the given data already exists.",
            error_code=ErrorCode.DUPLICATE_ENTRY,
        ).model_dump(),
    )
```

- `IntegrityError` 是在什么具体业务场景中会被触发？当前哪个接口有竞态窗口？（提示：`POST /users`）
- 默认的 409 响应已经在 `create_user` 里手动 `raise HTTPException(409)` 了——新加的 `IntegrityError` 处理器是为了覆盖竞态窗口，而不是替代已有手动检查。
- 思考业务含义：409 不一定是"邮箱重复"——数据库约束有 UNIQUE、NOT NULL、FOREIGN KEY 等多种。这里的统一消息 "A resource with the given data already exists." 是否在所有场景下都准确？或者你想为不同类型的 `IntegrityError` 写更具体的判断逻辑？

## 检查点D：实现 500 兜底处理器

```python
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # 不要吞掉 HTTPException —— 让 Starlette 的默认行为继续生效
    if isinstance(exc, HTTPException):
        raise exc

    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            detail="An internal server error occurred.",
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
        ).model_dump(),
    )
```

- 为什么处理器里要先判断 `isinstance(exc, HTTPException)` 再重新抛出？如果不加这个判断，会发生什么？（提示：`HTTPException` 也是 `Exception` 的子类，500 处理器会覆盖默认的行为。）
- 为什么不应该在 500 响应中返回 `str(exc)`——Python 异常可能包含路径、变量值、SQL 语句等敏感信息。

## 检查点E：测试

在 `tests/test_applications.py` 中：

1. 修改已有的测试断言——不再精确匹配 `response.json() == {"detail": "..."}`（因为 `IntegrityError` 和 `Exception` 兜底的响应会新增 `error_code` 字段，但 `HTTPException` 产生的 404/401 等响应不变）。

   改法：将 `assert response.json() == {"detail": "..."}` 改为：
   ```python
   assert response.status_code == XXX
   assert response.json()["detail"] == "..."
   ```
   或保持原样不修改（因为这个精确断言只出现在 `HTTPException` 对应场景，不会多出 `error_code` 字段）。

   思考：`HTTPException` 返回的 `{"detail": "..."}` 和 `ErrorResponse` 返回的 `{"detail": "...", "error_code": "..."}` 在序列化上的区别决定了哪些测试需要改哪些不改。逐一确认以下精确断言测试是否受影响：

   - `test_read_missing_application_returns_404` — 由 `_get_application_or_404` 的 `HTTPException(404)` 产生，没有 `ErrorResponse`，不受影响
   - `test_read_other_users_application_returns_404` — 同上
   - `test_create_user_rejects_duplicate_email` — 由手动 `HTTPException(409)` 产生，没有 `ErrorResponse`，不受影响
   - ... 同理，所有现有的 `HTTPException` 响应都不受影响

2. 新增 `IntegrityError` 测试（可选，如果不能直接触发，也可以提一个"手动用 `psql` 验证"的检查点）：

   ```python
   def test_concurrent_duplicate_email_returns_409():
       """验证 IntegrityError 被正确转为 409。"""
       import sqlalchemy.exc
       from unittest.mock import patch
       from app.main import app
       ...
   ```
   但更好的做法是让用户自己判断是否值得 mock 测试。

3. 新增 500 兜底测试：

   可以写一个测试 helper 路由或 mock 一个 CRUD 函数，确认 500 响应体包含 `error_code` 且没有泄露异常消息。

## 今日完成标准

- `IntegrityError` 被统一捕获并返回 409 + `error_code`；
- 未捕获的异常返回 500 + `error_code`，堆栈不进入响应 JSON；
- `HTTPException` 继续正常工作，404/401 等不受影响；
- Pydantic 校验错误保持默认格式不变；
- 所有原有测试不受影响，全部通过（`56 passed`）。

## 扩展思考（面试向）

- 为什么不在全局处理器中统一日志记录？当前项目最小化，日志可以作为一个独立的工程化阶段（不晚于 Day9/10）加入。
- 如果一个接口希望返回自定义 `error_code`（比如"邮箱未验证"），是扩展 `ErrorCode` 枚举好，还是直接 `raise HTTPException` 并自定义响应好？
- `IntegrityError` 和 `HTTPException` 的捕获顺序哪个优先？为什么？
- 如果要在 500 处理器里加入异步日志（记堆栈到文件），需要注意什么？

## 建议提交

全部检查通过后：

```text
feat: add global exception handling with unified error responses
```