# 保险资管框架 · 详细版（参考）

> **用途**：作为「保险行业 Agent」的领域底图（domain map）。先把业务画清楚，再把每个环节映射成 Agent。
> **对外汇报建议使用 [01-business-overview.md](01-business-overview.md)**；本文件保留完整图集，供拆解 Agent 时查证。
> **口径**：融合中国大陆险资实践（金融监管总局口径、偿二代二期、IFRS 17 / IFRS 9）与香港实践（HKIO 风险为本资本、SFC 第 9 类牌照）。图中的监管数值均为**示意**，落地前须按最新监管文件与公司内部制度校准。
> **渲染**：全部图为 Mermaid 语法，可直接在 GitHub、VS Code、Typora、Obsidian、语雀或 mermaid.live 中渲染。

---

## 0. 一句话主线

**保险资管 = 在三重约束下，把保费与准备金投出去，并在「收益 / 久期匹配 / 偿付能力 / 流动性」之间做权衡。**

三重约束：

| 约束 | 来源 | 对投资的直接含义 |
| --- | --- | --- |
| 负债约束 | 精算：久期、成本刚性、退保与赔付不确定 | 必须做 ALM，久期缺口与再投资风险是硬指标 |
| 监管约束 | 监管比例上限、集中度、偿付能力、关联交易 | 决定了「能投多少、能投什么」，是配置的可行域 |
| 会计约束 | IFRS 17（保险合同）/ IFRS 9（金融工具）分类 | 决定损益波动落在哪张表，直接影响权益与高股息策略偏好 |

五层结构：**治理决策层 → 负债约束层 → 资产配置层 → 中后台闭环层 → 数据与系统底座**。

---

## 1. 图 1：保险资管全景框架图

```mermaid
flowchart TB
  subgraph GOV["① 治理与决策层"]
    direction LR
    BOD["董事会 / 集团投资决策委员会"]
    ALCO["资产负债管理委员会 ALCO"]
    IC["保险资管公司或金控投资部 投委会"]
    RMC["风险管理委员会 / 审计与合规"]
  end

  subgraph LIAB["② 负债端：约束与目标"]
    direction LR
    L1["负债特征<br/>久期长 · 成本刚性 · 现金流不确定"]
    L2["精算模型<br/>现金流预测 · 退保率 · 赔付假设 · 准备金"]
    L3["目标函数<br/>覆盖负债成本 + 偿付能力达标 + 收益稳定"]
  end

  subgraph ASSET["③ 资产端：配置到执行"]
    direction LR
    A1["战略资产配置 SAA"]
    A2["战术资产配置 TAA"]
    A3["组合构建<br/>久期结构 · 行业 · 个券个股 · 权重"]
    A4["交易执行与再平衡"]
  end

  subgraph BACK["④ 中后台与闭环"]
    direction LR
    M1["风险计量<br/>市场 · 信用 · 流动性 · 集中度"]
    M2["估值核算与持仓对账"]
    M3["绩效归因与同业对标"]
    M4["报告披露与监管报送"]
  end

  subgraph EXT["⑤ 外部生态"]
    direction LR
    E1["保险资管公司 · 委外管理人 · 公募 / 私募"]
    E2["托管行 · 券商 · 评级机构 · 数据商 · 审计"]
    E3["监管机构 · 行业协会 · 交易所"]
  end

  subgraph BASE["⑥ 底座：数据与系统"]
    direction LR
    D1["市场数据 / 持仓 / 交易 / 财务"]
    D2["精算负债现金流 / 偿付能力计量"]
    D3["制度库 / 合同 / 研报 / 内部评级报告"]
    D4["投资交易系统 · 风控系统 · 估值系统 · 数据中台"]
  end

  BOD --> ALCO --> IC --> RMC
  L1 --> L2 --> L3
  LIAB --> ASSET
  A1 --> A2 --> A3 --> A4
  A4 --> M1
  A4 --> M2
  M2 --> M3 --> M4
  M3 -.->|配置与选券反馈| A2
  M1 -.->|限额与风险预算| A3
  M4 -.->|考核与资本约束| LIAB
  IC -.->|授权与投资指引| A3
  EXT -.-> ASSET
  BASE -.-> ASSET
  BASE -.-> BACK
  E3 -.-> GOV
```

**如何读这张图**：左边（治理 + 负债）决定「目标与可行域」，中间（资产端）是真正的投资动作，右边（中后台）是把结果算清、报准、反馈回配置。绝大多数 Agent 项目的失败原因，是只做了中间一层，缺了负债与合规这两端。

---

## 2. 图 2：投资价值链主流程（含闭环）

```mermaid
flowchart LR
  V0["V0 负债与约束输入<br/>久期 · 成本 · 现金流 · 资本占用"] --> V1["V1 资本市场假设 CMA<br/>长期收益 · 波动 · 相关性 · 情景"]
  V1 --> V2["V2 战略资产配置 SAA<br/>3 到 5 年目标权重"]
  V2 --> V3["V3 战术资产配置 TAA<br/>季度 / 月度偏离"]
  V3 --> V4["V4 组合构建<br/>久期 · 信用 · 行业 · 个券个股"]
  V4 --> V5["V5 决策与授权<br/>投委会 / 授权矩阵"]
  V5 --> V6["V6 交易执行<br/>下单 · 清算 · 交收"]
  V6 --> V7["V7 估值与核算<br/>每日估值 · IFRS 9 分类 · 损益"]
  V7 --> V8["V8 风险与限额监控<br/>VaR · 集中度 · 久期缺口 · 流动性"]
  V8 --> V9["V9 绩效归因与对标<br/>配置 / 久期 / 信用 / 选券 / 择时"]
  V9 --> V10["V10 报告与报送<br/>ALM 报告 · 偿付能力 · IFRS 17 · 监管报送"]

  V8 -.->|触限则降仓| V4
  V9 -.->|归因结论回流| V3
  V10 -.->|资本与考核约束| V2
  V0 -.->|负债假设更新| V2
```

**闭环的三个回馈点**：

1. **风险 → 组合**：触限、久期缺口扩大、流动性不足时，直接约束组合构建。
2. **归因 → TAA**：如果收益主要来自 beta 而非选券，说明应回到配置层决策。
3. **报告 → SAA**：偿付能力与会计结果反过来改写下一轮的风险预算与目标权重。

---

## 3. 图 3：SAA / TAA 配置决策子流程

```mermaid
flowchart TB
  subgraph IN["输入层"]
    direction LR
    I1["负债现金流与久期"]
    I2["负债成本 / 保证利率"]
    I3["监管比例上限与集中度"]
    I4["风险预算与资本约束"]
    I5["会计准则与损益目标"]
    I6["宏观情景与资产估值"]
  end

  subgraph METHOD["方法层"]
    direction LR
    ME1["情景生成<br/>利率 · 通胀 · 信用 · 权益"]
    ME2["随机 ALM 优化<br/>资产与负债联合模拟"]
    ME3["组合优化<br/>均值方差 · Black-Litterman · 风险平价"]
    ME4["压力测试与回撤约束"]
    ME5["流动性匹配"]
  end

  subgraph OUT["输出层"]
    direction LR
    O1["目标权重与偏离区间"]
    O2["久期目标与缺口容忍度"]
    O3["再平衡规则与触发阈值"]
    O4["投委会配置建议与依据"]
  end

  subgraph CHECK["验收层"]
    direction LR
    C1["偿付能力充足率影响"]
    C2["集中度与关联交易"]
    C3["流动性覆盖率"]
    C4["会计损益波动"]
  end

  IN --> METHOD --> OUT --> CHECK
  CHECK -.->|不通过则回到方法层| METHOD
  CHECK -.->|通过则提交投委会| O4
```

---

## 4. 表 1：大类资产地图（保险视角）

| 资产类别 | 典型工具 | 在保险组合中的角色 | 关键风险 | 监管 / 资本 / 会计要点 |
| --- | --- | --- | --- | --- |
| 利率债与存款 | 国债、政金债、协议存款、大额存单 | 久期匹配的压舱石，稳定票息 | 利率风险、再投资风险 | 资本占用低；多计入 AC / FVOCI |
| 信用债与非标 | 信用债、债权投资计划、ABS | 票息增强，拉长久期 | 信用与流动性风险 | 需内部评级；非标集中度受限 |
| 权益 | 蓝筹、高股息、长期股权投资、举牌 | 收益弹性与抗通胀 | 波动与减值 | 权益类比例上限与偿付能力挂钩；高股息常走 FVOCI 以平滑损益 |
| 基金与委外 | 公募、私募、MOM / FOF | 能力外延，快速调仓 | 管理人风险、风格漂移 | 需委外准入与业绩评价机制 |
| 另类 | 不动产、基础设施、股权、REITs | 长期现金流，匹配长久期负债 | 估值不透明、退出难 | 比例与集中度受限；需穿透与估值审查 |
| 海外资产 | QDII、港股通、境外债 | 分散与币种配置 | 汇率与政策风险 | 额度管理、汇率对冲要求 |
| 衍生品 | 利率互换、国债期货、期权 | 对冲而非投机 | 基差与操作风险 | 严格限于套期保值，需授权与留痕 |
| 流动性资产 | 货币基金、活期与短期存款 | 应对赔付与退保高峰 | 机会成本 | 流动性覆盖率要求 |

---

## 5. 图 4：限额与合规校验链（下单前的层层闸门）

```mermaid
flowchart TB
  START["拟投项目 / 拟下单指令"] --> G1{"① 监管硬约束<br/>大类比例 · 单一主体 · 关联交易"}
  G1 -->|超限| REJ1["否决：不可投"]
  G1 -->|通过| G2{"② 投资指引与授权<br/>mandate · 久期区间 · 信用下限"}
  G2 -->|超授权| ESC["升级审批：投委会 / 授权人"]
  G2 -->|通过| G3{"③ 组合级限额<br/>集中度 · 行业 · 评级 · DV01"}
  G3 -->|触限| TRIM["降规模 / 调结构 / 置换"]
  G3 -->|通过| G4{"④ 流动性约束<br/>现金流与变现能力"}
  G4 -->|不足| TRIM
  G4 -->|通过| G5{"⑤ 资本与偿付能力影响<br/>最低资本占用变化"}
  G5 -->|不达标| ESC
  G5 -->|通过| G6{"⑥ 会计与损益影响<br/>分类 · 波动 · 减值"}
  G6 -->|不可接受| ESC
  G6 -->|通过| PASS["通过：进入下单与留痕"]
  ESC --> G1
  TRIM --> G1
```

---

## 6. 时序图 A：季度 SAA + 月度 TAA 决策

```mermaid
sequenceDiagram
  autonumber
  participant DK as 数据与系统
  participant RS as 研究与量化
  participant PM as 投资经理
  participant AL as 精算与财务
  participant RK as 风控与合规
  participant CC as 投委会 / ALCO
  participant TR as 交易室
  participant OP as 运营与估值

  Note over DK,OP: 每月 / 每季循环，季度定战略，月度做战术
  DK->>RS: 输出市场数据包与持仓快照
  AL->>RS: 输出负债现金流与久期缺口
  RS->>RS: 更新资本市场假设与宏观情景
  RS->>RS: 运行 ALM 与组合优化，形成配置初稿
  RS->>PM: 提交配置方案与偏离建议
  PM->>PM: 复核逻辑，形成投资建议
  PM->>RK: 提交限额与资本影响测算
  RK->>RK: 校验监管比例、集中度、偿付能力、流动性
  alt 校验通过
    RK->>CC: 出具风控与合规意见，材料上会
    CC->>PM: 批准目标权重与偏离区间
    PM->>TR: 下达执行指令
    TR->>OP: 成交回报与交收确认
    OP->>DK: 更新持仓与估值
  else 校验不通过
    RK-->>PM: 退回并附限制条件
    PM->>RS: 调整方案后重新测算
  end
  OP->>RS: 提供绩效归因与执行偏差
  RS->>CC: 下期回顾与配置调整建议
```

---

## 7. 时序图 B：单笔固收 / 非标投资端到端

```mermaid
sequenceDiagram
  autonumber
  participant PM as 投资经理
  participant CR as 信用研究员
  participant RK as 风控
  participant CO as 合规
  participant AU as 授权人 / 投委会
  participant TR as 交易室
  participant CP as 托管行 / 对手方
  participant OP as 运营与估值

  PM->>CR: 提出标的与投资逻辑
  CR->>CR: 内部评级、财务与舆情分析
  CR-->>PM: 出具信用意见与评级建议
  PM->>RK: 提交限额与资本占用测算
  RK->>RK: 校验集中度、久期、流动性与偿付能力
  RK-->>PM: 风控意见
  PM->>CO: 提交关联交易与合规审查
  CO->>CO: 核查对手方、关联方名单与披露要求
  CO-->>PM: 合规意见
  PM->>AU: 提交投资审批材料
  alt 授权范围内
    AU-->>PM: 授权内批准
  else 超授权
    AU->>AU: 召开投委会审议
    AU-->>PM: 投委会决议
  end
  PM->>TR: 下达交易指令
  TR->>CP: 询价、成交、清算交收
  CP-->>TR: 成交与交收确认
  TR->>OP: 交易数据落地
  OP->>OP: 估值入账、持仓对账、损益确认
  OP->>RK: 存续期风险监测与评级跟踪
  RK-->>PM: 预警、评级下调或触发退出条件
```

---

## 8. 时序图 C：月末估值—归因—报告—报送闭环

```mermaid
sequenceDiagram
  autonumber
  participant OP as 运营与估值
  participant DK as 数据中台
  participant RK as 风控
  participant RS as 研究与量化
  participant AL as 精算与财务
  participant CC as 管理层 / 投委会
  participant RG as 监管报送

  Note over OP,RG: 月末与季末闭环，报表口径需双人复核
  OP->>OP: 完成估值与持仓对账，锁账
  OP->>DK: 推送锁账后持仓、成交与损益数据
  DK->>RK: 计算风险指标与限额使用率
  DK->>RS: 提供组合收益与基准数据
  RS->>RS: 做配置 / 久期 / 信用 / 选券 / 择时归因
  RS->>AL: 提交投资收益与资本影响
  AL->>AL: 更新偿付能力计量与 IFRS 17 口径结果
  RK-->>CC: 风险与限额报告
  RS-->>CC: 绩效归因与同业对标
  AL-->>CC: ALM 与偿付能力报告
  CC-->>RS: 下期配置与考核反馈
  AL->>RG: 生成监管报送底稿与披露材料
  RG->>RG: 复核、签批、报送与归档
```

---

## 9. 状态图：一笔投资的存续生命周期

```mermaid
stateDiagram-v2
  [*] --> S1
  state "投前立项" as S1
  state "尽职调查与内部评级" as S2
  state "风控与合规审查" as S3
  state "审批与授权" as S4
  state "下单执行与交收" as S5
  state "存续期管理" as S6
  state "调整或减持" as S7
  state "退出与清算" as S8

  S1 --> S2 : 通过初筛
  S2 --> S3 : 评级达标
  S3 --> S4 : 无限额冲突
  S4 --> S5 : 获得授权
  S5 --> S6 : 交收成功
  S6 --> S7 : 触限、评级下调或配置调整
  S7 --> S6 : 结构调整完成
  S6 --> S8 : 到期、回售或主动退出
  S8 --> [*]

  S3 --> S9 : 否决
  S4 --> S9 : 未获授权
  state "终止" as S9
  S9 --> [*]

  note right of S6
    存续期动作：付息与派息、
    评级跟踪、估值复核、
    风险预警、减值判断
  end note
```

---

## 10. 图 5：保险行业 Agent 目标架构

```mermaid
flowchart TB
  subgraph L0["L0 交互层"]
    direction LR
    U1["投研问答与数据查询"]
    U2["配置建议与情景推演"]
    U3["报表与会议材料生成"]
    U4["制度与合同问答"]
  end

  subgraph L1["L1 编排层（Orchestrator）"]
    direction LR
    O1["任务规划与路由"]
    O2["工具与数据选择"]
    O3["记忆与上下文管理"]
    O4["权限与成本闸门"]
    O5["人工签核点"]
  end

  subgraph L2["L2 专业 Agent 群"]
    direction LR
    AG1["数据接入 Agent<br/>取数与质量校验"]
    AG2["宏观与利率 Agent"]
    AG3["信用与发行人 Agent"]
    AG4["权益与行业 Agent"]
    AG5["另类与私募 Agent"]
    AG6["负债与 ALM Agent<br/>久期缺口 · 现金流匹配"]
    AG7["组合优化 Agent<br/>SAA · TAA · 风险预算"]
    AG8["风控 Agent<br/>限额 · 压力测试 · 可否决"]
    AG9["合规 Agent<br/>监管比例 · 关联交易"]
    AG10["运营与对账 Agent"]
    AG11["报告与叙事 Agent"]
    AG12["评估与审计 Agent<br/>打分 · 留痕 · 复现"]
  end

  subgraph L3["L3 工具与数据层（MCP / API）"]
    direction LR
    T1["市场数据源"]
    T2["内部数仓与持仓交易"]
    T3["精算与 ALM 引擎"]
    T4["优化器与回测引擎"]
    T5["风控与估值系统"]
    T6["制度 / 合同 / 研报知识库"]
    T7["监管规则库"]
  end

  subgraph L4["L4 底座与治理"]
    direction LR
    G1["数据治理与字段字典"]
    G2["权限与脱敏"]
    G3["审计日志与版本"]
    G4["模型评估与上线审批"]
    G5["成本与调用监控"]
  end

  L0 --> L1 --> L2 --> L3 --> L4
  L2 -.->|风控与合规可否决| L1
  L4 -.->|约束与复核要求| L1
```

**保险行业相比通用投资 Agent 的两个关键增量**：`负债与 ALM Agent`（把久期、成本、退保假设带进决策）与 `合规 Agent`（把监管比例、关联交易、披露口径变成硬闸门）。通用开源项目基本都没有这两块，这正是保险 Agent 的差异化所在。

---

## 11. 时序图 D：Agent 编排一次「本月配置建议」

```mermaid
sequenceDiagram
  autonumber
  participant PM as 投资经理
  participant OR as 编排器
  participant DA as 数据接入 Agent
  participant AL as 负债与 ALM Agent
  participant RE as 研究 Agent 群
  participant PO as 组合优化 Agent
  participant RK as 风控 Agent
  participant CO as 合规 Agent
  participant RW as 报告 Agent
  participant AU as 人工签核
  participant LOG as 审计与评估

  PM->>OR: 请生成本月配置建议与偏离说明
  OR->>DA: 拉取持仓、市场、负债与限额数据
  DA->>DA: 校验完整性、口径一致性与数据时点
  DA-->>OR: 标准化数据包与质量报告
  OR->>AL: 测算久期缺口与现金流匹配
  AL-->>OR: 负债约束与久期目标
  par 并行研究
    OR->>RE: 宏观与利率情景
    OR->>RE: 信用与利差机会
    OR->>RE: 权益与行业观点
    OR->>RE: 另类与流动性资产
  end
  RE-->>OR: 各领域结论与证据链
  loop 多空辩论，最多 3 轮
    OR->>RE: 交叉质证与假设挑战
    RE-->>OR: 修订后结论与置信度
  end
  OR->>PO: 在负债与风险预算约束下优化权重
  PO-->>OR: 目标权重、偏离区间与换手成本
  OR->>RK: 提交限额、压力测试与资本占用核验
  alt 风控通过
    RK-->>OR: 通过，附风险提示
  else 风控否决
    RK-->>OR: 否决或降规模，附触发条款
    OR->>PO: 在收紧约束下重新优化
  end
  OR->>CO: 校验监管比例、关联交易与披露口径
  CO-->>OR: 合规意见
  OR->>RW: 生成配置建议书与会议材料
  RW-->>PM: 建议书初稿，含数据来源与计算过程
  PM->>AU: 复核与签批
  AU-->>OR: 批准、修改或退回
  OR->>LOG: 记录输入、版本、工具调用与结论
  LOG-->>PM: 可复现审计报告
  Note over OR,LOG: 数字由确定性代码计算，语言由模型组织；任何投资结论必须有人签核
```

---

## 12. 附录：与开源投资 Agent 的对应关系

| 参考项目 | 热度（星标，2026-09） | 可借鉴的机制 | 对应本框架环节 |
| --- | --- | --- | --- |
| TradingAgents（TauricResearch） | 约 10.5 万 | 分析师团队 → 多空辩论 → 交易 → 风控审批的分层编排 | 图 5 的 L1 / L2，时序图 D 的辩论循环 |
| ai-hedge-fund（virattt） | 约 6.3 万 | 角色化人格 Agent + 风控 + 组合经理，可回测原型 | 研究 Agent 群与组合优化 Agent |
| FinRobot（AI4Finance） | 约 8 千 | 分层金融 Agent 平台，工具与模型解耦 | 图 5 的 L2 / L3 分层 |
| Qlib + RD-Agent（微软） | 约 4.9 万 / 1.5 万 | 研究自动化循环：假设 → 实现 → 回测 → 反思 | 研究流水线、因子与模型治理 |
| OpenBB | 约 7.3 万 | 统一数据接口层，供 Agent 调用 | 图 5 的 L3 工具层 |
| ai-berkshire（中文，Codex / Claude Code） | 约 1.6 万 | 多大师方法论 + 并行研究，基于 Skill 与 MCP 落地 | 中文语境的研究 Agent 编排 |
| Vibe-Trading（HKUDS） | 约 3.3 万 | MCP 工具化 + 多 Agent + 回测闭环 | 工具层与回测治理 |
| FinGPT | 约 2.1 万 | 金融文本模型与情绪因子管道 | 信用舆情与另类数据 Agent |
| QuantsPlaybook | 约 6 千 | 中文券商金工研报复现知识库 | 知识库与策略素材 |
| ALM / 偿付能力类小众项目（Stochastic-ALM-Model、ALMSystem-PublicDemo） | 个位数到数十 | 随机 ALM、IFRS 17 + Solvency II 现金流预测 | 负债与 ALM Agent（保险专有） |

> 说明：截至 2026-09，开源生态在「投资 / 交易 / 研究」侧非常丰富，但**保险资管专属的 Agent 项目几乎空白**（保险侧多为核保、理赔、合同问答等小项目）。因此合理路线是：**用投资 Agent 的骨架，补上负债与监管合规两层**。

---

## 13. 使用与维护建议

1. **作图与改图**：直接在 mermaid.live 粘贴单张图代码即可编辑；公司内部文档建议用 VS Code 或语雀预览。
2. **口径校准**：表 1 与图 4 的监管比例必须替换为公司内部制度与最新监管文件的实际数值，并标注生效日期。
3. **与 Agent 的衔接**：每个图节点都应能回答三个问题——输入是什么、输出是什么、谁负责签核。不能回答的节点，暂时不适合 Agent 化。
4. **落地顺序**：先做数据接入与报告（低风险），再做研究与配置建议（中风险），交易执行永远保留人工。

> 配套文件：`保险资管Agent_映射与路线图.md`（环节 × Agent 化机会矩阵、数据契约、合规红线、分阶段路线图）。
