# 保险资管框架 · 精简版（一页看懂）

> **用途**：给领导与流程内的人一眼看清「谁做、用什么系统、Agent 将来接哪一段」。
> **读图约定**：**圆角＋小人＝人**；**方块＝系统**；**菱形＝闸门**；**绿色＝Agent**。全部图可直接在 GitHub、VS Code、语雀、mermaid.live 渲染。

---

## 图例

| 视觉 | 含义 | 颜色 | 谁负责 |
| --- | --- | --- | --- |
| 圆角框 / 小人 | 人：决策与执行角色 | 暖黄 | 人，需签批与担责 |
| 直角框 | 系统：已有工具与数据 | 浅蓝 | 系统，自动运行 |
| 菱形 | 闸门：通过 / 降规模 / 升级 / 否决 | 灰 | 人与 Agent 均可初筛 |
| 绿色框 | Agent：AI 可承担的环节 | 浅绿 | 人审后采用 |

---

## 图 1：一页全景 —— 保险资管四步闭环

每一步都是「人在判断 + 系统在支撑」，产出交由下一步。

```mermaid
flowchart TB
  classDef human fill:#FDF3C8,stroke:#C9A227,stroke-width:1.5px,color:#3B2F00
  classDef sys fill:#DCEBFA,stroke:#3E6E9E,stroke-width:1.5px,color:#12324D
  classDef out fill:#EEF1F5,stroke:#8A98A8,stroke-width:1.5px,color:#2B3440
  classDef gate fill:#F3E3E3,stroke:#A96A6A,stroke-width:1.5px,color:#4A1F1F

  subgraph P1["第 1 步 · 定约束"]
    direction LR
    H1(["ALCO 与精算<br/>定负债成本、久期与资本约束"]):::human
    Y1["精算与偿付能力系统"]:::sys
  end
  O1[/"久期目标 · 风险预算 · 可投范围"/]:::out

  subgraph P2["第 2 步 · 定配置"]
    direction LR
    H2(["投委会与投资经理<br/>定大类资产与偏离"]):::human
    Y2["情景与组合优化模型"]:::sys
  end
  O2[/"目标权重 · 偏离区间"/]:::out

  subgraph P3["第 3 步 · 做交易"]
    direction LR
    H3(["投资经理与交易室<br/>下单与调仓"]):::human
    Y3["投资交易系统"]:::sys
  end
  O3[/"成交 · 持仓 · 成本"/]:::out

  subgraph P4["第 4 步 · 控与报"]
    direction LR
    H4(["风控 · 合规 · 财务<br/>否决与披露"]):::human
    Y4["风控 · 估值 · 报表系统"]:::sys
  end
  O4[/"限额报告 · 绩效归因 · 监管报送"/]:::out

  C1{{闸门 · 限额与资本}}:::gate
  C2{{闸门 · 授权与合规}}:::gate

  P1 --> O1 --> C1 --> P2
  P2 --> O2 --> C2 --> P3
  P3 --> O3 --> P4
  P4 --> O4
  O4 -.->|资本与考核反馈| P1
```

**一句话**：定约束 → 定配置 → 做交易 → 控与报，然后回到约束。

---

## 图 2：Agent 目标架构 —— 人只做判断与签批

三层：系统在底、Agent 在中、人在顶。

```mermaid
flowchart BT
  classDef human fill:#FDF3C8,stroke:#C9A227,stroke-width:1.5px,color:#3B2F00
  classDef agent fill:#DDF3E0,stroke:#3F8B54,stroke-width:1.5px,color:#123A1F
  classDef sys fill:#DCEBFA,stroke:#3E6E9E,stroke-width:1.5px,color:#12324D

  subgraph HUMAN["人：判断与签批（责任在这里）"]
    direction LR
    HU1(["投委会：批配置"]):::human
    HU2(["投资经理：批建议"]):::human
    HU3(["风控与合规：批例外"]):::human
  end

  subgraph AGENT_L["Agent 层：新增"]
    direction LR
    AG1["编排 Agent<br/>拆任务与汇总"]:::agent
    AG2["研究 Agent 群<br/>宏观 · 信用 · 权益"]:::agent
    AG3["ALM 与组合 Agent<br/>久期与权重"]:::agent
    AG4["风控与合规 Agent<br/>可初筛可否决"]:::agent
    AG5["报告 Agent<br/>材料与留痕"]:::agent
  end

  subgraph SYS_L["系统与数据层：已有资产"]
    direction LR
    SY1["数据中台"]:::sys
    SY2["精算与偿付能力"]:::sys
    SY3["投资交易系统"]:::sys
    SY4["风控与估值"]:::sys
    SY5["制度与研报知识库"]:::sys
  end

  SYS_L --> AGENT_L --> HUMAN
  AGENT_L -.->|触限或越权则升级给人| HUMAN
```

**保险 Agent 的两块专属增量**：`ALM 与组合 Agent`（把久期与负债成本带进决策）、`风控与合规 Agent`（把监管比例与关联交易变成硬闸门）。通用投资 Agent 都没有这两块。

---

## 图 3：一笔投资的四道闸门

```mermaid
flowchart LR
  classDef gate fill:#F3E3E3,stroke:#A96A6A,stroke-width:1.5px,color:#4A1F1F
  classDef human fill:#FDF3C8,stroke:#C9A227,stroke-width:1.5px,color:#3B2F00
  classDef ok fill:#DDF3E0,stroke:#3F8B54,stroke-width:1.5px,color:#123A1F
  classDef stop fill:#F6D9D9,stroke:#A33A3A,stroke-width:1.5px,color:#4A1010

  S0(["立项"]):::human --> G1{"① 监管比例<br/>合规 Agent 初筛"}:::gate
  G1 -->|超限| X1["否决"]:::stop
  G1 -->|通过| G2{"② 内部授权<br/>投资经理与授权人"}:::gate
  G2 -->|超授权| UP["升级投委会"]:::human
  G2 -->|通过| G3{"③ 风险限额<br/>风控 Agent 初筛"}:::gate
  G3 -->|触限| TR["降规模或置换"]:::human
  G3 -->|通过| G4{"④ 会计与披露<br/>财务与合规"}:::gate
  G4 -->|不可接受| X2["否决"]:::stop
  G4 -->|通过| OK(["通过：下单并留痕"]):::ok
  UP --> OK
  TR --> G1
```

---

## 时序图 1：现在的配置决策（人和系统分工）

**小人＝人，方块＝系统**。

```mermaid
sequenceDiagram
  autonumber
  box rgba(253,243,200,0.6) 人：决策与审核
    actor PM as 投资经理
    actor RK as 风控与合规
    actor CC as 投委会
  end
  box rgba(220,235,250,0.6) 系统：数据与工具
    participant DW as 数据中台
    participant MO as 模型与优化
    participant TS as 投资交易系统
    participant RP as 估值与报表
  end

  DW->>PM: 提供持仓、市场与负债数据
  PM->>MO: 设定约束与情景假设
  MO-->>PM: 输出配置建议与偏离区间
  PM->>RK: 提交限额、资本与合规核验
  RK-->>PM: 风控与合规意见
  PM->>CC: 上会审议
  CC-->>PM: 批准目标权重
  PM->>TS: 下达交易指令
  TS->>RP: 更新成交与持仓
  RP-->>PM: 估值、归因与限额报告
```

---

## 时序图 2：Agent 接入后的目标态（人只签批）

与上一张对比即可看出：**Agent 承担中间环节，人在三处签批**。

```mermaid
sequenceDiagram
  autonumber
  box rgba(253,243,200,0.6) 人：只做判断与签批
    actor PM as 投资经理
    actor RK as 风控与合规
    actor CC as 投委会
  end
  box rgba(221,243,224,0.6) Agent：新增
    participant OR as 编排 Agent
    participant RS as 研究 Agent 群
    participant AL as ALM 与组合 Agent
  end
  box rgba(220,235,250,0.6) 系统：已有
    participant DW as 数据中台
    participant TS as 投资交易系统
    participant RP as 估值与报表
  end

  PM->>OR: 要求本月配置建议
  OR->>DW: 取持仓、市场与负债数据
  DW-->>OR: 标准化数据包
  OR->>AL: 测算久期缺口与目标权重
  par 并行研究
    OR->>RS: 宏观与利率
    OR->>RS: 信用与利差
    OR->>RS: 权益与行业
  end
  RS-->>OR: 观点与证据
  AL-->>OR: 配置建议与偏离原因
  OR->>RK: 提交初筛结论与例外项
  RK-->>OR: 签批或退回
  OR-->>PM: 建议书与会议材料
  PM->>CC: 上会审议
  CC-->>PM: 批准
  PM->>TS: 人工下单
  TS->>RP: 成交与持仓更新
  RP-->>OR: 归因结果，供下期复盘
```

---

## 现状 → Agent：谁做这一段的对照表

| 环节 | 现在谁做 | Agent 后 | 人保留什么 |
| --- | --- | --- | --- |
| 取数与校验 | 人工拼数 | 数据 Agent 自动完成 | 抽查口径 |
| 研究观点 | 研究员各自完成 | 研究 Agent 群并行 | 采纳与否 |
| 久期与配置测算 | 人工与模型混合 | ALM 与组合 Agent | 定约束与拍板 |
| 限额与合规核验 | 人工逐条核对 | 风控与合规 Agent 初筛 | 批例外 |
| 报告与材料 | 手工拼接 | 报告 Agent 生成初稿 | 复核签发 |
| 下单与交收 | 投资经理与交易室 | 不变，人工执行 | 全程人工 |
| 投资决议 | 投委会 | 不变 | 全程人工 |

**两条底线**：Agent 不接触下单接口；所有结论必须有人签批，且全程留痕。

---

> 详细图集（价值链、SAA/TAA 子流程、四类时序图与状态图）：[02-full-diagrams.md](02-full-diagrams.md)
> Agent 怎么搭、做几个、A/B/C/D 四层怎么分：[03-agent-architecture.md](03-agent-architecture.md)
> Agent 化机会矩阵、数据契约、合规红线与落地路线：[04-roadmap.md](04-roadmap.md)
> 可运行代码与示例输出：[返回项目首页](../README.md)
