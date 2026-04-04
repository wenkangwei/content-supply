"""LLM content rewriter — paraphrase, summarize, expand."""

import logging
from datetime import datetime
from typing import Optional

from openai import AsyncOpenAI

from content_supply.config import load_app_config

logger = logging.getLogger(__name__)

# Prompt templates per rewrite type
PROMPTS = {
    "paraphrase": (
        "你是一个专业的内容编辑。请用不同的表达方式改写以下文章，保持核心意思不变，"
        "但使用不同的措辞、句式和段落结构。确保改写后的文章：\n"
        "1. 读起来自然流畅，像是原创内容\n"
        "2. 保留所有关键信息和数据\n"
        "3. 长度与原文相近\n\n"
        "原文：\n{content}"
    ),
    "summarize": (
        "你是一个专业的内容编辑。请将以下文章总结为一段精炼的摘要（200-400字），"
        "突出核心观点和关键信息。\n\n"
        "原文：\n{content}"
    ),
    "expand": (
        "你是一个专业的内容编辑。请在保持原文核心内容的基础上，扩展以下文章：\n"
        "1. 添加更多背景信息和上下文\n"
        "2. 补充相关案例或数据支撑\n"
        "3. 深化分析和观点\n"
        "4. 扩展到原文 1.5-2 倍长度\n\n"
        "原文：\n{content}"
    ),
}


class ContentRewriter:
    """Rewrite content using LLM (OpenAI-compatible API)."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        config = load_app_config()
        self.client = AsyncOpenAI(
            base_url=base_url or config.llm.base_url,
            api_key=api_key or config.llm.api_key,
        )
        self.model = model or config.llm.model
        self.max_tokens = config.llm.max_tokens
        self.temperature = config.llm.temperature

    async def rewrite(
        self,
        content: str,
        rewrite_type: str = "paraphrase",
        custom_prompt: Optional[str] = None,
    ) -> dict:
        """Rewrite content using LLM.

        Returns:
            {
                "rewritten": str,      # 改写后的内容
                "model": str,          # 使用的模型
                "prompt_used": str,    # 实际使用的 prompt
                "tokens_used": int,    # token 消耗
            }
        Raises RuntimeError on failure.
        """
        if rewrite_type not in PROMPTS and not custom_prompt:
            raise ValueError(f"Unknown rewrite type: {rewrite_type}. Choose from: {list(PROMPTS.keys())}")

        prompt = custom_prompt or PROMPTS[rewrite_type].format(content=content[:8000])

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的内容编辑助手。"},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
            rewritten = response.choices[0].message.content or ""
            tokens_used = response.usage.total_tokens if response.usage else 0

            return {
                "rewritten": rewritten,
                "model": self.model,
                "prompt_used": prompt[:500],
                "tokens_used": tokens_used,
            }
        except Exception as e:
            logger.error(f"LLM rewrite failed: {e}")
            raise RuntimeError(f"LLM rewrite failed: {e}") from e

    async def rewrite_batch(
        self,
        items: list[dict],
        rewrite_type: str = "paraphrase",
        content_key: str = "content",
    ) -> list[dict]:
        """Rewrite multiple items sequentially (to avoid rate limits).

        Args:
            items: list of dicts with content to rewrite
            rewrite_type: paraphrase / summarize / expand
            content_key: key in dict that holds the content

        Returns:
            list of dicts with added "rewritten" field
        """
        import asyncio

        results = []
        for item in items:
            content = item.get(content_key, "")
            if not content:
                results.append({**item, "rewritten": "", "error": "empty content"})
                continue
            try:
                result = await self.rewrite(content, rewrite_type)
                results.append({**item, "rewritten": result["rewritten"]})
            except Exception as e:
                logger.warning(f"Batch rewrite failed for item: {e}")
                results.append({**item, "rewritten": "", "error": str(e)})
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.5)
        return results
