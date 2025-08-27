"""Calendar agent DSPy signature definition."""

import dspy


class CalendarAgentSignature(dspy.Signature):
    """
    You are a Calendar agent that can handle the user's calendar-related requests.
    You are given Calendar-specific tools and must decide which to use to fulfill the request.
    """

    user_query: str = dspy.InputField(desc="The user's Calendar-related query")
    request_context: dict = dspy.InputField(desc="Context passed from the orchestrator")

    tools_used: list[str] = dspy.OutputField(
        desc="The Calendar tools used to fulfill the request"
    )
    reasoning: str = dspy.OutputField(
        desc="The reasoning process of the Calendar agent"
    )
    response: str = dspy.OutputField(desc="The Calendar-related response to the query")


class CalendarBackgroundAgentSignature(dspy.Signature):
    """
    You are a Calendar agent capable of going through the details of the current event. And can decide to take some actions and give an update to the user.

    You are triggered automatically when the user gets a new event, modification or cancellation of a calendar event.
    You are supposed to read throught the details of the event and decide if you need to take some actions and give an update to the user.

    Remember the user is away and busy with other things. So you should be concise and to the point and give a quick personalized notification.
    The user will read the notification when they come back to the app.
    """

    event_details: dict = dspy.InputField(desc="The details of the event")
    user_context: dict = dspy.InputField(desc="Context passed from the orchestrator")

    action_taken: bool = dspy.OutputField(
        desc="Whether an action was taken by the agent"
    )
    personalized_notification: str = dspy.OutputField(
        desc="The personalized notification to the user"
    )
    reasoning: str = dspy.OutputField(
        desc="The reasoning process of the Calendar agent"
    )
