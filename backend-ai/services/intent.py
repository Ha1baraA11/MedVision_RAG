# services/intent.py
"""
意图识别路由 (Agentic RAG)
===========================
判断用户提问是针对"当前药品"还是"历史库存药品"。
"""

import json

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from core.logging_config import logger
from core.config import llm

# 意图路由 Prompt 模板：指导 LLM 判断用户提问指向"当前药品"还是"历史药品"
_intent_router_template = """
你是一个医疗意图识别专家。请判断用户的提问是指向"当前正在查看的药品"，还是在询问"历史库存中的某个特定药品"。

用户提问: "{question}"

规则：
1. 如果用户明确提到了药品名称（如"阿莫西林怎么吃"、"找一下布洛芬"、"那个消炎药"），且该名称不是"这个药"、"它"等代词，则判定为【历史查询】。
2. 如果用户说"这个药"、"它"、"刚才拍的"，或者直接问"怎么吃"（省略主语），则判定为【当前查询】。
3. 输出格式必须为 JSON: {{"type": "HISTORY" or "CURRENT", "entity": "提取的药品名称(如果是HISTORY)"}}

例子：
- "阿莫西林怎么吃？" -> {{"type": "HISTORY", "entity": "阿莫西林"}}
- "这个药一次吃几粒？" -> {{"type": "CURRENT", "entity": null}}
- "帮我找找布洛芬" -> {{"type": "HISTORY", "entity": "布洛芬"}}
- "适应症是什么" -> {{"type": "CURRENT", "entity": null}}
"""
_intent_prompt = ChatPromptTemplate.from_template(_intent_router_template)
_intent_chain = _intent_prompt | llm | StrOutputParser()


def analyze_intent(question: str) -> dict:
    """
    意图识别：判断用户提问是指向当前正在查看的药品，还是在询问历史库存中的某个药品。

    通过 LLM 分析用户问题的语义，提取意图类型和实体名称。
    例如："阿莫西林怎么吃" -> HISTORY（历史查询，实体为"阿莫西林"）
          "这个药一次吃几粒" -> CURRENT（当前查询）

    参数:
        question (str): 用户的原始提问文本

    返回:
        dict: {"type": "HISTORY"|"CURRENT", "entity": "药品名称"|null}
    """
    logger.info(f" Analyzing Intent for: {question}")
    try:
        res = _intent_chain.invoke({"question": question})
        # 清洗 LLM 输出：去除可能的 Markdown 代码块标记，提取纯 JSON
        res = res.replace("```json", "").replace("```", "").strip()
        data = json.loads(res)
        logger.info(f" Intent Result: {data}")
        return data
    except Exception as e:
        logger.error(f"Intent Error: {e}")
        return {"type": "CURRENT", "entity": None}
