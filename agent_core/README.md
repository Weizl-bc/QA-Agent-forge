# 2026年06月18日10:39:53

## PRD清洗流程

1. 先读取文档（list\[str\]）
2. 标准化文档（standardization_prd_md.py）
   1. 抽象为树模型：把文章分拆分为大段落、小段落，父段落、子段落（md_node）
   2. 把content中的不规则段落，整合为一句话的形式
   3. 图片处理：识别prd中的流程图、业务图等等。最后挂载到node节点中
3. 文档清洗（md_node）
   1. 结构清洗（Structural Cleaning）（md_node）
   2. 语义噪声清洗（Semantic Noise Removal）（PrdSemanticBlock）
      1. 常见噪声：TODO、待补充、见附件、略、xxx占位 等等
   3. 图片语义抽取（Image Semantic Extraction）：将图片转换为PrdSemanticBlock
   4. 结构归一化（Normalization）（md_node）
      1. 标题标准化
         - 去掉编号、去掉括号序号、trim+去特殊符合
      2. 合并重复节点
         - 当PRD出现多个段落说同一件事，则需要合并，例如 1.1 登录说明，1.2
登录流程，这两个段落说的一件事，需要合并。
   5. 语义增强（Enrichment）（md_node）
      1. 为node增加node_type字段
4. 文档切片
5. 转换为纯业务规则
   1. 录入向量库，为后续PRD评审做准备、知识库问答做准备
   2. 转换为面向测试开发的文档


---


1. Read doc → list[str]

2. Parse → MdNode tree
   (STRUCTURE ONLY)

3. MdNode Cleaning
   - 3.1 Structural Cleaning → MdNode
   - 3.2 Normalization → MdNode

4. Semantic Extraction
   MdNode.content → PrdSemanticBlock[]

5. Semantic Cleaning
   PrdSemanticBlock noise filtering

6. Semantic Enrichment
   PrdSemanticBlock + tags + node link

7. Chunking
   PrdSemanticBlock-based slicing

8. Rule Generation
   PrdSemanticBlock → Rule

9. Output Layer
   - Vector DB
   - Test case system
   - QA agent