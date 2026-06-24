# Augur 本次更新说明

> 面向用户的功能说明（非技术变更日志，技术细节见 [CHANGELOG.md](../CHANGELOG.md)）。

## 这次更新解决了什么问题

之前 `augur_workflow`（无论是你在终端跑 CLI、还是 Agent 通过 MCP 调用）默认永远是固定的三步 `fetch → analyze → consensus`，跟你在 `/settings` 里选的终端布局预设完全没关系。换句话说，"定制化"（你选的布局）和"agentic"（Agent 帮你跑分析流水线）这两件事是脱钩的——你切换到"交易员"布局只是改了页面展示，Agent 替你跑 workflow 时该干的事一点没变。

## 新增功能

### `augur_workflow` 默认步骤跟随你的终端布局预设

不再硬编码 `fetch,analyze,consensus`。CLI 的 `--steps`、MCP 工具 `augur_workflow` 的 `steps` 参数、Dashboard `/api/workflow` 接口的 `steps` 字段，留空时现在会去看你当前激活的 Profile 用的是哪个布局预设，按预设选不同的默认步骤组合：

- **分析师（analyst）**：`fetch,analyze,consensus`——和之前一样，深度调研流程不变。
- **交易员 / 极简（trader / minimal）**：`fetch,consensus`——跳过逐个大师的详细打分展开，更快拿到一个信号。
- **委员会（committee）**：`fetch,analyze,consensus,committee`——直接带上委员会投票结果。

如果你显式传了 `--steps`（或 MCP 调用里指定了 steps），还是以你传的为准，这个联动只在你没指定的时候生效。

这意味着你在 `/settings` 选好的布局，现在不只是改 Dashboard 怎么显示，也会改变 Agent（Claude Desktop / Hermes / OpenClaw 等）替你跑分析时默认做哪几步——定制化的选择真正影响到了 agentic 的行为。

## 测试情况

完整测试套件 **2075 个测试全部通过**（含需要网络访问的 5 个测试），没有失败项。

## 接下来还会做什么

P1 backlog 里只剩 P1-9（dashboard 的路由文件拆分，纯内部代码组织调整），暂不安排。P2 backlog 里有一项被标记为"地基类风险"：**regime 检测（P2-3）目前没有任何平滑/滞后机制，也没有历史回测验证**——这次顺手核实过，确实还是开放风险，在它落地前不建议把共识结果当作风险输入来用。其余 P2 项（懒加载 persona、workflow 进度实时推送等）按需排期。

详细的技术变更记录见 [CHANGELOG.md](../CHANGELOG.md)。
