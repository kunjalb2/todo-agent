"""Guardrails for the AI agent."""
from agents import InputGuardrail, OutputGuardrail, GuardrailFunctionOutput

# Allowed topics for the TodoAgent (not code review - that's separate)
ALLOWED_TOPICS = [
    "IT and technology",
    "coding and programming",
    "software development",
    "task and todo management",
    "productivity",
    "technical questions",
    "debugging",
    "system design",
    "APIs and integrations",
    "database queries",
    "algorithms and data structures",
]


async def topic_guardrail(ctx, agent, input_data):
    """Guardrail function to ensure user queries are about allowed topics.

    Args:
        ctx: RunContextWrapper containing context and user info
        agent: The agent instance
        input_data: The input messages (string or list of messages)

    Returns:
        GuardrailFunctionOutput with tripwire_triggered if off-topic
    """
    # Extract user message from input_data
    if isinstance(input_data, str):
        user_message = input_data.lower()
    elif isinstance(input_data, list) and len(input_data) > 0:
        # Handle list of message items
        msg = input_data[-1]
        if hasattr(msg, "content"):
            user_message = str(msg.content).lower()
        elif isinstance(msg, str):
            user_message = msg.lower()
        elif isinstance(msg, dict):
            user_message = str(msg.get("content", "")).lower()
        else:
            user_message = str(msg).lower()
    else:
        user_message = str(input_data).lower()

    # Check for off-topic keywords
    off_topic_patterns = [
        # Politics
        ["politics", "election", "government", "president", "political"],
        # Entertainment
        ["movie", "celebrity", "entertainment", "tv show", "series", "actor", "actress"],
        # Sports
        ["sport", "football", "basketball", "soccer", "tennis", "game", "match"],
        # Finance (investment advice)
        ["stock tip", "investment advice", "buy stock", "sell stock", "financial advice"],
        # Medical
        ["medical diagnosis", "what disease do i have", "prescribe", "treatment for"],
        # Personal relationships
        ["dating advice", "relationship advice", "love life"],
        # General gossip
        ["gossip", "rumor about"],
    ]

    for patterns in off_topic_patterns:
        if any(pattern in user_message for pattern in patterns):
            return GuardrailFunctionOutput(
                output_info=(
                    f"I can only help with IT, coding, and task management questions. "
                    f"Your message seems to be about a different topic. "
                    f"I can assist with: {', '.join(ALLOWED_TOPICS[:5])}, and more."
                ),
                tripwire_triggered=True,
            )

    # Check if message is empty or too short
    if len(user_message.strip()) < 3:
        return GuardrailFunctionOutput(
            output_info="Please provide a more detailed question or request.",
            tripwire_triggered=True,
        )

    # Check for code review requests and redirect to ReviewAgent
    code_review_patterns = [
        "review this code", "review my code", "code review",
        "review this file", "review this snippet", "review this function",
        "check this code", "audit this code", "code analysis",
        "review git diff", "review my changes", "review my pull request",
    ]
    if any(pattern in user_message for pattern in code_review_patterns):
        return GuardrailFunctionOutput(
            output_info=(
                "For code review requests, please use the dedicated Code Review Agent at the `/review` endpoint. "
                "The Todo Agent handles todo management and general IT/coding questions only."
            ),
            tripwire_triggered=True,
        )

    return GuardrailFunctionOutput(
        output_info=None,
        tripwire_triggered=False,
    )


def create_topic_guardrail() -> InputGuardrail:
    """Create an input guardrail for topic filtering."""
    return InputGuardrail(
        guardrail_function=topic_guardrail,
        name="TopicGuardrail",
    )


# Output guardrail (permissive - mainly for potential future use)
async def output_guardrail(ctx, agent, output):
    """Guardrail function to ensure agent responses stay on topic.

    Args:
        ctx: RunContextWrapper containing context and user info
        agent: The agent instance
        output: The agent's output

    Returns:
        GuardrailFunctionOutput with tripwire_triggered if validation fails
    """
    # This is a permissive output guardrail
    # We always pass validation
    return GuardrailFunctionOutput(
        output_info=None,
        tripwire_triggered=False,
    )


def create_output_guardrail() -> OutputGuardrail:
    """Create an output guardrail for response validation."""
    return OutputGuardrail(
        guardrail_function=output_guardrail,
        name="OutputGuardrail",
    )
