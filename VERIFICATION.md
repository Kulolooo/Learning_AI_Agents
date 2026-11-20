# 对抗性校验记录

本文件记录 2026-11-20 对 v0.1.1 做的一次刻意挑错，结论是可以发布到 GitHub。远端仓库已建立，首次 CI 在 4 个矩阵组合上全部通过；仍有两类限制待外部环境验证（见末节）。

## 环境

Windows 11，CPython 3.11.5（系统）与 3.12.14（生成插图用的运行时），仓库位于本地工作区，无网络依赖。GitHub 直连在本机被 TLS 证书存储拦截，`git` 需要加 `-c http.sslBackend=openssl` 才能访问远端。

## 检查项与结果

代码边界（20 项，全部通过）。覆盖步数为零、脚本耗尽、工具输出超长、工具返回不可序列化对象、空语料检索、空查询、短文本切分、空计划、空任务图、零轮辩论、空用例集、JSON 数组校验、零预算、缺少 API Key、路由缺处理器、空轨迹、审批门默认放行非副作用工具。探测脚本不进仓库，结论如下：

| 编号 | 探测 | 结果 |
|---|---|---|
| 1 | `max_steps=0` | 正常返回 `max_steps`，不抛异常 |
| 2 | 脚本模型调用次数超限 | 抛 `ScriptExhausted` |
| 3 | 9000 字符工具输出 | 截断并置 `truncated=True` |
| 4 | 返回 `{1: object()}` 的工具 | 以 `default=str` 序列化，不崩 |
| 5 | 空文档集建索引 | 检索返回空列表，作答提示未覆盖 |
| 6 | 空查询串 | 返回列表，不抛异常 |
| 7 | 短于块长的文本 | 切成单块 |
| 8 | 空计划 | 立即返回，`history` 为空 |
| 9 | 空任务图 | `run()` 返回空字典 |
| 10 | `rounds=0` 的辩论 | 直接进入裁决 |
| 11 | 空用例集 | 汇总为 0 例、通过率 0 |
| 12 | JSON 数组字段类型错误 | 抛 `ValueError` |
| 13 | `max_tokens=0` | 首次检查即判定超预算 |
| 14 | 无 API Key 的远端模型 | 抛 `LLMError` |
| 15 | 路由命中但无处理器 | 抛 `KeyError` |
| 16 | 空轨迹汇总 | 事件数为 0 |
| 17 | 审批门遇到非副作用工具 | 放行 |
| 18 | 空 worker 的主管 | 见下文修复项 |
| 19 | 缺失用例的运行结果 | 跳过，不污染汇总 |
| 20 | 空记忆装配上下文 | 返回空串而非崩溃 |

文档与代码一致性（19 项，全部通过）。场景数 10、插图 14、示例 6、编号文档 14、附录 3、单元测试 42，均与 README 和封面声明一致；每张插图都被正文引用，且引用的文件都存在；`book.html` 内联 14 张 SVG，不含外部图片与脚本；LICENSE 为 MIT，附录 C 声明了上游出处与未复用关系。

可重现性。14 张插图重新渲染后与仓库中的 SVG 逐字节一致，且分别用 CPython 3.11 与 3.12 渲染结果相同。全新目录（不含缓存）中 `python -m unittest discover -s tests`、`python -m learning_agents.demo`、6 个示例、`python build.py`、`python tools/check_links.py` 全部通过。

打包。`python -m pip install . --target <tmp>` 离线构建成功，导入版本为 0.1.0。装到用户 site-packages 的操作被本机沙箱拒绝（`WinError 5`），属于环境限制，不是包的问题。

文献。13 条 arXiv 引用逐条核对标题与作者，全部命中，包括 ReAct 2210.03629、RAG 2005.11401、Lost in the Middle 2307.03172、Reflexion 2303.11366、Self-Refine 2303.17651、Self-Consistency 2203.11171、Toolformer 2302.04761、MemGPT 2310.08560、AutoGen 2308.08155、多智能体辩论 2305.14325、Plan-and-Solve 2305.04091、CoT 2201.11903、Codex 2107.03374。

安全与卫生。没有密钥、口令、私钥或内网地址；正文不含本机绝对路径、TODO、FIXME；文件总数 84，`.gitignore` 覆盖 `__pycache__`、`memory/`、`*.jsonl`。

## 发现并修复的问题

主管（`Supervisor`）在 worker 列表为空时，分派逻辑对空列表取模，抛 `ZeroDivisionError`。现在构造时直接抛 `ValueError` 并给出原因，同时补了一条回归测试，测试总数从 41 变为 42，相关文档计数同步更新。

插图 SVG 在标注宽度恰好落在 72.35 这类浮点边界时，逐字符累加的舍入结果依赖累加顺序，导致同一份代码在不同进程里渲染出 72.4 与 72.3 两种宽度。改为按字符计数一次乘出宽度后，两种 Python 版本的输出逐字节一致。

上游 notebook 数量此前写作 64，按仓库文件树实际清点为 65，正文、附录与 README 已统一。

## 远端执行情况

首次推送后 GitHub Actions 跑了一轮，四个矩阵组合（Windows 与 Ubuntu 各配 CPython 3.11、3.12）中 Windows 的两个任务在示例脚本这一步失败。原因是 windows-latest 的默认控制台代码页是 1252，`print` 中文抛 `UnicodeEncodeError`，本机因为设了 `PYTHONIOENCODING` 而没有暴露。修法是在工作流里显式设置 `PYTHONIOENCODING=utf-8` 与 `PYTHONUTF8=1`，重跑后四个组合全部通过。

另有一个只在 API 路径上出现的问题：仓库为空时 `POST /git/blobs` 返回 409，必须先用 Contents API 建首个提交，之后才能写对象。这次上传因此先建了一个 README 提交，再用等价的 root commit 覆盖，最终远端与本地哈希一致（`eeb8e1c`）。

## 未验证项

真实模型接入未在本机跑过，因为需要 API Key 与外部网络；OpenAI 兼容客户端只做了「缺 Key 抛错」与协议解析的单元测试。这是唯一一个既没有本地实测、也没有远端实测的部分。

`github.com` 的 git 端点在本机被网络策略重置（TLS 握手后被 reset，Python 与 git 都一样），因此推送改走 REST API，`git push` 本身没有在本机成功执行过。在能正常访问 GitHub 的机器上，`git push` 应当照常工作。

## 复现

```bash
python -m unittest discover -s tests
python -m learning_agents.demo
python build.py
python tools/check_links.py
python tools/style_audit.py
```
