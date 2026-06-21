class PrdImageType:
    """
    flow_chart:
    - block_type = flow_rule
    - 重点提取流程节点、条件分支、动作

    state_machine:
    - block_type = state_rule
    - 重点提取状态、状态流转、触发条件

    ui_prototype:
    - block_type = ui_requirement
    - 重点提取页面元素、按钮、输入框、校验规则

    table_screenshot:
    - block_type = data_rule
    - 重点提取字段、枚举、取值范围、必填规则

    error_screenshot:
    - block_type = exception_rule
    - 重点提取异常场景、错误提示、拦截条件

    decoration:
    - is_noise = True
    - 不进入向量库
    """
    UI_PROTOTYPE = "ui_prototype"  # 页面原型图
    FLOW_CHART = "flow_chart"  # 流程图
    STATE_MACHINE = "state_machine"  # 状态流转图
    TABLE_SCREENSHOT = "table_screenshot"  # 表格截图
    FIELD_SCREENSHOT = "field_screenshot"  # 字段截图
    ERROR_SCREENSHOT = "error_screenshot"  # 错误提示截图
    ARCHITECTURE = "architecture"  # 架构图
    DECORATION = "decoration"  # 装饰图
    UNKNOWN = "unknown"