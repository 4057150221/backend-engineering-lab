# Day 1：HTTP 最小闭环与请求数据校验

## 今日目标

今天不追求“学会 FastAPI”，完成两个连续的小闭环：

```text
浏览器或测试客户端
        ↓ HTTP GET /health
FastAPI 路由函数
        ↓
JSON 响应与状态码
        ↓
pytest 自动验证

客户端
        ↓ HTTP POST /items + JSON 请求体
Pydantic 数据模型
        ↓ 类型转换与字段校验
FastAPI 路由函数
        ↓
JSON 响应、201 与 422
```

完成后，你应当能解释：

- Python解释器、虚拟环境、第三方包、模块分别是什么；
- `import` 大致在做什么；
- HTTP方法、路径、状态码和JSON响应分别是什么；
- 请求体与响应体有什么区别；
- Pydantic模型、Python类型标注和字段校验分别起什么作用；
- 为什么创建资源通常使用POST和201；
- 为什么自动化测试比“浏览器点一下能用”更可靠。

## 环境任务

1. 在 VS Code 中打开本仓库。
2. 选择仓库内 `.venv/Scripts/python.exe` 作为解释器。
3. 在仓库终端确认当前解释器来自 `.venv`。
4. 安装并记录今天需要的最小依赖：FastAPI、Uvicorn、pytest、HTTPX。

在本仓库打开 PowerShell 终端后依次运行：

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -c "import sys; print(sys.executable)"
.\.venv\Scripts\python.exe -m pip install -r requirements-day1.txt
```

前两条命令应显示 Python 3.12，并且解释器路径位于当前仓库的 `.venv` 中。第三条命令需要正常访问 Python 包下载服务；Codex沙箱无法代替你完成该网络下载，因此由你在本机 VS Code 终端执行。

不要安装数据库、认证或前端依赖；它们不属于今天的任务。

## 第一部分：健康检查（已完成）

不得让 AI 生成实现代码。可以查官方文档和错误信息。

1. 创建 `app` Python 包。
2. 在 `app/main.py` 中创建 FastAPI 应用。
3. 实现 `GET /health`：
   - 成功状态码为 `200`；
   - JSON响应严格为 `{"status": "ok"}`。
4. 创建 `tests/test_health.py`，至少验证：
   - `/health` 返回 `200`；
   - 响应JSON完全匹配预期；
   - 一个不存在的路径返回 `404`。
5. 分别通过开发服务器和pytest验证结果。

本机的Windows保留端口范围包含 `8000`，开发服务器统一使用 `9000`：

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 9000
```

启动后访问 `http://127.0.0.1:9000` 和 `http://127.0.0.1:9000/docs`。

如果看到 `WinError 10013`，先区分是代码执行错误还是服务器绑定IP/端口失败。本机已验证 `7998–8097` 属于Windows TCP排除端口范围，不修改系统保留规则，直接使用9000。

## 第二部分：请求体、Pydantic校验与Item接口

### 先读什么

只阅读官方文档的以下三个小节，不继续向后扩展：

1. [Request Body](https://fastapi.tiangolo.com/tutorial/body/)
2. [Body - Fields](https://fastapi.tiangolo.com/tutorial/body-fields/)
3. [Response Status Code](https://fastapi.tiangolo.com/tutorial/response-status-code/)

带着下面四个问题阅读：

- 为什么函数参数标注为Pydantic模型后，FastAPI会把它当作请求体？
- `str | None = None` 中，类型标注和默认值分别表达什么？
- `Field(...)` 在哪里执行长度等业务约束？
- 为什么校验失败时路由函数还没有真正开始执行？

### 最小概念

- `GET`主要用于读取资源；`POST`常用于提交数据并创建资源。
- 请求体是客户端发给服务器的数据；响应体是服务器返回给客户端的数据。
- Pydantic模型是一份数据契约：它声明允许哪些字段、字段类型以及约束。
- FastAPI会读取JSON请求体，交给Pydantic验证；合法时构造模型对象，不合法时直接返回`422`。
- `201 Created`表示服务器成功创建了资源。本阶段不连接数据库，只模拟创建结果。

### 独立编码任务

保留现有`GET /health`，在`app/main.py`中新增请求模型和`POST /items`。

请求体契约：

| 字段 | 类型 | 必填 | 约束 |
|---|---|---:|---|
| `title` | 字符串 | 是 | 长度1～100，不能是空字符串 |
| `description` | 字符串或空值 | 否 | 默认值为`None`，最大长度300 |

接口契约：

- 方法和路径：`POST /items`
- 成功状态码：`201`
- 暂不生成ID、不保存到列表或数据库。
- 对合法请求，将校验后的Item数据作为JSON响应返回。
- 缺少`title`、`title`为空字符串或字段长度超限时，应由FastAPI自动返回`422`。

不要直接复制官方示例中的`name/price/tax`。阅读后关闭文档，根据上面的契约自己写。

### 手动验证

启动服务后打开`http://127.0.0.1:9000/docs`，依次尝试：

1. 合法：`title`和`description`都有值。
2. 合法：只有`title`。
3. 非法：缺少`title`。
4. 非法：`title`是空字符串。

观察Swagger UI展示的请求模型、实际状态码和响应JSON。

### 自动化测试

新建`tests/test_items.py`，至少覆盖：

1. 合法完整请求返回`201`，响应JSON与输入一致。
2. 只提交必填字段仍返回`201`，响应中`description`为`null`。
3. 缺少`title`返回`422`。
4. 空字符串`title`返回`422`。

测试客户端提交JSON时，查清`client.post()`的`json`参数，而不是手工拼接JSON字符串。

## 禁止项

- 不增加数据库。
- 不拆分router/service/model层。
- 不复制成熟模板目录。
- 不让AI生成核心实现或测试。
- 不增加内存列表、ID、查询、修改或删除接口。
- 不自定义422异常响应；先观察框架默认行为。

## 验收问题

完成代码后，先不看资料，用自己的话回答：

1. 为什么要创建虚拟环境？
2. `app` 为什么需要成为一个Python包？
3. 请求 `/health` 时，哪一段代码决定了路径和HTTP方法？
4. Python字典为什么能变成JSON响应？
5. 为什么访问不存在的路径会得到404，而不是程序崩溃？
6. 测试客户端为什么可以在不手动打开浏览器的情况下请求应用？
7. 请求体和响应体分别是谁发给谁？
8. Pydantic模型为什么既能用于类型提示，又能在运行时验证数据？
9. 为什么缺少必填字段得到422，而不是进入函数后再由你写`if`判断？
10. `None`在Python响应中为什么会变成JSON的`null`？

## Git验收

健康检查的第一条提交已经完成：

```text
39f18f7 feat: add health endpoint and test
```

第二部分测试全部通过后，查看变更，再由你本人创建第二条提交。建议提交信息：

```text
feat: validate item creation requests
```

提交前必须能够逐行解释自己新增的每段代码。
