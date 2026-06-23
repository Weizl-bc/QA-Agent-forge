PARSER_MD_TO_NORMAL_TEXT_PROMPT = """
请将以下Markdown PRD内容转换为结构化PRD说明文本：

背景：
- 原始文本是唯一事实来源。
- 标准化文本仅用于帮助理解结构。

内容要求：
1. 不得加入原始文本不存在的信息。
2. 不得因标准化文本遗漏而忽略原始信息。
3. raw_text 必须能在原始文本中定位。
4. 标准化文本与原始文本冲突时，以原始文本为准。

输出格式要求：
- 第一行：页面/模块名称
- 后续按“模块 → 子模块 → 功能描述”扁平展开
- 字段用“，”分隔
- 操作用一句话描述
- 不要保留层级缩进
- 不要保留Markdown符号

请对同类信息进行归并，例如：
- 查询条件统一输出一行
- 表格字段统一输出一行
- 枚举值归到字段括号中
- 不要拆成单独条目
"""


PARSER_MD_IMG_TO_NORMAL_TEXT_PROMPT = """
你是一个 PRD 图片语义解析器，专门分析产品需求文档中的流程图、泳道图、状态流转图、页面原型图、表格截图。

请只基于图片中可见的信息进行分析，不要补充图片中没有出现的业务规则。
如果文字模糊、箭头方向不清楚、节点无法识别，请在 uncertain_items 中说明，不要猜测。

上下文信息：
- 当前章节标题：{source_title}
- 当前章节路径：{source_node_path}
- 图片 alt 文本：{alt_text}
- 图片前文：{before_text}
- 图片后文：{after_text}

请完成以下任务：
1. 判断图片类型。
2. 提取图片中的所有文字。
3. 识别图片中的角色/泳道/系统参与方。
4. 识别流程节点、节点顺序、箭头方向。
5. 识别条件分支，例如“是/否”“成功/失败”“通过/驳回”。
6. 识别异常流程、终止节点、回退节点。
7. 提取可转化为业务规则的信息。
8. 输出严格 JSON，不要输出 markdown，不要输出解释性文字。

输出 JSON 格式如下：
{{
  "image_type": "flow_chart | swimlane | state_machine | ui_prototype | table_screenshot | field_screenshot | error_screenshot | architecture | decoration | unknown",
  "is_business_relevant": true,
  "ocr_texts": [
    {{
      "text": "",
      "confidence": "high | medium | low"
    }}
  ],
  "participants": [
    {{
      "name": "",
      "type": "user | role | system | external_system | unknown"
    }}
  ],
  "nodes": [
    {{
      "node_id": "n1",
      "name": "",
      "node_type": "start | action | decision | state | end | data | page | unknown",
      "owner": "",
      "description": ""
    }}
  ],
  "edges": [
    {{
      "from": "n1",
      "to": "n2",
      "condition": "",
      "action": "",
      "direction_confidence": "high | medium | low"
    }}
  ],
  "branches": [
    {{
      "condition": "",
      "true_path": "",
      "false_path": "",
      "description": ""
    }}
  ],
  "business_summary": "",
  "uncertain_items": [
    ""
  ]
}}

注意：
1. business_summary不要使用md格式返回，要求以普通文本返回，方便后续llm解析
"""

PARSER_IMG_TO_SEMANTIC_BLOCK_PROMPT = """
你是一个 PRD 业务规则抽取器。现在给你一份从 PRD 图片中识别出来的结构化结果，请把它转换为 PrdSemanticBlock 列表。

要求：
1. 每个 PrdSemanticBlock 只表达一个相对独立的业务规则。
2. 不要把多个无关规则塞进同一个 block。
3. conditions 只放触发条件、前置条件、判断条件。
4. actions 只放系统动作、用户动作、状态变化、页面跳转。
5. constraints 只放限制、拦截、必填、唯一性、金额范围、次数限制、状态约束。
6. entities 只放业务实体，例如用户、订单、支付单、退款单、审批人、网点、角色、状态、按钮、字段。
7. 如果图片信息不足，不要猜测，标记 uncertain_items。
8. 如果图片只是装饰图，is_noise = true。
9. 输出严格 JSON，不要输出 markdown，不要输出解释。

上下文信息：
- source_node_path: {source_node_path}
- source_title: {source_title}
- source_image_id: {source_image_id}

图片结构化结果：
{image_analysis_json}

请输出：
{{
  "semantic_blocks": [
    {{
      "raw_text": "",
      "block_type": "flow_rule | state_rule | ui_requirement | data_rule | exception_rule | permission_rule | api_rule | unknown",
      "source_type": "image",
      "source_image_id": "{source_image_id}",
      "conditions": [],
      "actions": [],
      "constraints": [],
      "entities": [],
      "is_noise": false,
      "source_node_path": "{source_node_path}",
      "source_title": "{source_title}"
    }}
  ],
  "test_points": [
    {{
      "title": "",
      "preconditions": [],
      "steps": [],
      "expected_result": "",
      "priority": "P0 | P1 | P2 | P3"
    }}
  ],
  "uncertain_items": []
}}
"""
