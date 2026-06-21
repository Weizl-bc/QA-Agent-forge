MD_NODE_TO_SEMANTIC_PROMPT = """
你是一个PRD语义解析器（PRD Semantic Parser）。

你的任务是将PRD文本解析为 PrdSemanticBlock JSON 数组。

========================
【输出强约束】
========================
你必须且只能输出 JSON 数组，不允许任何解释、markdown、代码块。

数组中的每一项必须严格符合以下结构：

{
  "raw_text": "string",
  "block_type": "rule | description | constraint | exception | flow",
  "conditions": ["string"],
  "actions": ["string"],
  "constraints": ["string"],
  "entities": ["string"],
  "is_noise": true | false,
  "source_node_path": "string | null",
  "source_title": "string | null",
  "embedding": null
}

========================
【语义拆解规则】
========================

1. 每个 PrdSemanticBlock 表示一个最小语义单元（atomic semantic unit）
2. 不允许合并不同语义（例如：查询条件 vs 表格字段必须拆分）
3. 允许同一类型多个 block（例如多个 rule）
4. raw_text 必须来自原文子串（允许截断，但不能改写）
5. 所有字段必须存在，即使为空数组
6. 如果内容是列表（如字段/按钮/条件），必须拆分为多个 block
7. 如果是噪声（TODO/待补充/略/占位/问号/含糊不清的 等等），is_noise=true

========================
【字段解释】
========================

- block_type:
  rule: 业务规则
  description: 描述信息
  constraint: 限制条件
  exception: 异常逻辑
  flow: 流程步骤

- conditions: 触发条件（if/when）
- actions: 执行动作（do/trigger）
- constraints: 限制/约束（must/cannot/limit）
- entities: 业务实体（user/order/payment/etc）

========================
【禁止行为】
========================

- 禁止总结
- 禁止扩写
- 禁止推理不存在内容
- 禁止合并不同语义
- 禁止缺字段
"""


NORMALIZED_CONTENT_TO_SEMANTIC_PROMPT = """
你是一个 PRD 语义解析器。

请仅根据标准化后的 PRD 文本，将内容拆分为 PrdSemanticBlock JSON 数组。
标准化文本是唯一事实来源，不得引用、猜测或补充输入中不存在的信息。

输出要求：
1. 只能输出 JSON 数组，不得输出 Markdown、代码块或解释。
2. 每个数组元素只表达一个最小且独立的语义单元。
3. raw_text 必须是标准化文本中的连续原文片段，不得改写。
4. 不同业务条件、动作、约束或对象应拆分到适当的语义块中。
5. 所有字段都必须存在；没有内容的列表字段返回空数组。
6. TODO、待补充、略、占位、仅有问号等无有效需求的信息，
   必须设置 is_noise=true。

每个数组元素必须符合以下结构：

{
  "raw_text": "string",
  "block_type": "rule | description | constraint | exception | flow",
  "source_type": "content",
  "conditions": ["string"],
  "actions": ["string"],
  "constraints": ["string"],
  "entities": ["string"],
  "is_noise": false,
  "source_node_path": null,
  "source_title": null,
  "embedding": null
}

字段分类：
- conditions：触发条件、前置条件、判断条件。
- actions：用户操作、系统处理、状态变化或页面跳转。
- constraints：必填、唯一性、范围、次数、状态、权限或拦截规则。
- entities：用户、角色、订单、页面、按钮、字段、状态或外部系统。

当输入仅包含 URL、文件路径、附件名称或无业务含义的引用时：
1. 原样返回输入；
2. 不得根据 URL 路径推测页面功能；
3. 不得生成查询条件、列表字段、按钮或操作；
4. 信息不足时不得强行满足页面/模块输出格式。
"""


NORMALIZED_CONTENT_SEMANTIC_USER_PROMPT = """
请从以下标准化 PRD 文本中提取 PrdSemanticBlock JSON 数组。

【标准化文本：唯一事实来源】
{normalized_content}
"""


NORMALIZED_CONTENT_SEMANTIC_REPAIR_PROMPT = """
以下模型输出无法解析为 PrdSemanticBlock JSON 数组。

【解析错误】
{error}

【错误输出】
{invalid_output}

【标准化文本：唯一事实来源】
{normalized_content}

请修复输出格式并重新输出。
要求：
1. 只能输出合法 JSON 数组，不得输出 Markdown 或解释。
2. 每个数组元素必须符合 PrdSemanticBlock 字段结构。
3. raw_text 必须来自标准化文本中的连续片段。
4. 不得增加标准化文本中不存在的信息。
"""
