"""Gmail agent DSPy signature definition."""

import dspy


class GmailAgentSignature(dspy.Signature):
    """
    You are a Gmail agent that can handle the user's Gmail-related requests.
    You are given Gmail-specific tools and must decide which to use to fulfill the request.
    """

    user_query: str = dspy.InputField(desc="The user's Gmail-related query")
    request_context: dict = dspy.InputField(desc="Context passed from the orchestrator")

    tools_used: list[str] = dspy.OutputField(
        desc="The Gmail tools used to fulfill the request"
    )
    reasoning: str = dspy.OutputField(desc="The reasoning process of the Gmail agent")
    response: str = dspy.OutputField(desc="The response to the user's query")


class GmailBackgroundAgentSignature(dspy.Signature):
    """
    You are a Gmail agent capable of going through the details of the current email. And can decide to take some appropriate actions and give an update to the user.

    You are triggered automatically when the user gets a new email. You are supposed to read throught the details of the email and decide if you need to take some actions and give an update to the user.

    Remember the user could be away and busy with other things. So you should be concise and to the point and give a quick personalized notification.
    The user will read the notification when they come back to the app.

    You have access to many tools so use different tools to fulfill the request and dont get stuck on a single tool.

    If you are unable to take any action, you should just give a quick personalized notification and include a to-do for the user.
    """

    event_details: dict = dspy.InputField(desc="The details of the event")
    user_context: dict = dspy.InputField(desc="Context passed from the orchestrator")

    action_taken: list[str] = dspy.OutputField(
        desc="The actions taken by the agent during the processing of the email"
    )
    personalized_notification: str = dspy.OutputField(
        desc="The personalized notification to the user"
    )
    reasoning: str = dspy.OutputField(
        desc="The reasoning process of the Calendar agent"
    )
