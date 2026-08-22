# Day 1：让第一个后端请求真正跑起来

## 今日目标

今天不追求“学会 FastAPI”，只完成一个最小闭环：

```text
浏览器或测试客户端
        ↓ HTTP GET /health
FastAPI 路由函数
        ↓
JSON 响应与状态码
        ↓
pytest 自动验证
```

完成后，你应当能解释：

- Python解释器、虚拟环境、第三方包、模块分别是什么；
- `import` 大致在做什么；
- HTTP方法、路径、状态码和JSON响应分别是什么；
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

## 独立编码任务

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

## 禁止项

- 不增加数据库。
- 不拆分router/service/model层。
- 不复制成熟模板目录。
- 不让AI生成核心实现或测试。
- 不因为代码少而增加第二个接口。

## 验收问题

完成代码后，先不看资料，用自己的话回答：

1. 为什么要创建虚拟环境？
2. `app` 为什么需要成为一个Python包？
3. 请求 `/health` 时，哪一段代码决定了路径和HTTP方法？
4. Python字典为什么能变成JSON响应？
5. 为什么访问不存在的路径会得到404，而不是程序崩溃？
6. 测试客户端为什么可以在不手动打开浏览器的情况下请求应用？

## Git验收

确认测试通过后，查看变更，再由你本人创建第一条提交。建议提交信息：

```text
feat: add health check endpoint and tests
```

提交前必须能够逐行解释自己新增的每段代码。
