"""
LLM Service for Q&A generation from news.

Uses LangChain with OpenRouter to generate question-answer pairs
from Google News headlines.
"""

import os
import re
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from news_service import fetch_google_news, format_news_for_llm

load_dotenv()

# Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3-nano-30b-a3b:free")


@dataclass
class GeneratedQA:
    """A generated question-answer pair."""
    question: str
    answer: str
    topic: str
    source: str = "llm_generated"


@dataclass
class GenerationResult:
    """Result from Q&A generation."""
    success: bool
    qa_pairs: list[GeneratedQA]
    topic: str
    news_count: int
    error: str = ""


# System prompt for Q&A generation
QA_GENERATION_PROMPT = """You are an expert news analyst and educational content creator. 
Your task is to analyze news headlines and create high-quality question and answer pairs.

Given the following news headlines about "{topic}":

{news_content}

Generate exactly {num_pairs} question-answer pairs based on this news content.

**Guidelines:**
- Create diverse question types: factual, analytical, and inferential
- Questions should be clear, specific, and directly tied to the news content
- Answers should be comprehensive and cite the relevant headline/source when appropriate
- Focus on key facts, implications, and broader context

**Output Format (STRICTLY follow this format):**
For each Q&A pair, use EXACTLY this format:

Q1: [Question text here]
A1: [Detailed answer here]

Q2: [Question text here]
A2: [Detailed answer here]

... and so on.

Generate the Q&A pairs now:"""


def get_llm(temperature: float = 0.3) -> ChatOpenAI:
    """
    Get a configured LLM instance.

    Args:
        temperature: Sampling temperature (0-1)

    Returns:
        Configured ChatOpenAI instance
    """
    return ChatOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
        model=OPENROUTER_MODEL,
        temperature=temperature
    )


def parse_qa_pairs(text: str, topic: str) -> list[GeneratedQA]:
    """
    Parse Q&A pairs from LLM output text.

    Args:
        text: Raw LLM output containing Q&A pairs
        topic: The topic these Q&As are about

    Returns:
        List of GeneratedQA objects
    """
    qa_pairs = []

    # Pattern to match Q1:/A1: format
    pattern = r'Q(\d+):\s*(.+?)\s*A\1:\s*(.+?)(?=Q\d+:|$)'
    matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)

    for _, question, answer in matches:
        question = question.strip()
        answer = answer.strip()

        if question and answer:
            qa_pairs.append(GeneratedQA(
                question=question,
                answer=answer,
                topic=topic,
                source="llm_generated"
            ))

    # Fallback: try alternate patterns if primary didn't work
    if not qa_pairs:
        # Try **Q1:** format
        pattern = r'\*\*Q(\d+):\*\*\s*(.+?)\s*\*\*A\1:\*\*\s*(.+?)(?=\*\*Q\d+:\*\*|$)'
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)

        for _, question, answer in matches:
            question = question.strip()
            answer = answer.strip()

            if question and answer:
                qa_pairs.append(GeneratedQA(
                    question=question,
                    answer=answer,
                    topic=topic,
                    source="llm_generated"
                ))

    return qa_pairs


async def generate_qa_from_news(
    topic: str,
    days: int = 7,
    num_pairs: int = 5
) -> GenerationResult:
    """
    Generate Q&A pairs from news about a topic.

    Args:
        topic: The news topic to search for
        days: Number of days to look back
        num_pairs: Number of Q&A pairs to generate

    Returns:
        GenerationResult with Q&A pairs or error
    """
    try:
        # Fetch news
        news_result = fetch_google_news(topic, days=days, max_results=10)

        if not news_result.success:
            return GenerationResult(
                success=False,
                qa_pairs=[],
                topic=topic,
                news_count=0,
                error=news_result.error
            )

        if not news_result.articles:
            return GenerationResult(
                success=False,
                qa_pairs=[],
                topic=topic,
                news_count=0,
                error=f"No news found for '{topic}' in the last {days} days."
            )

        # Format news for LLM
        news_content = format_news_for_llm(news_result)

        # Create prompt
        prompt = QA_GENERATION_PROMPT.format(
            topic=topic,
            news_content=news_content,
            num_pairs=num_pairs
        )

        # Generate Q&A pairs
        llm = get_llm(temperature=0.3)
        response = await llm.ainvoke(prompt)

        # Parse the response
        qa_pairs = parse_qa_pairs(response.content, topic)

        if not qa_pairs:
            return GenerationResult(
                success=False,
                qa_pairs=[],
                topic=topic,
                news_count=len(news_result.articles),
                error="Failed to parse Q&A pairs from LLM response."
            )

        return GenerationResult(
            success=True,
            qa_pairs=qa_pairs,
            topic=topic,
            news_count=len(news_result.articles)
        )

    except Exception as e:
        return GenerationResult(
            success=False,
            qa_pairs=[],
            topic=topic,
            news_count=0,
            error=f"Generation error: {str(e)}"
        )
