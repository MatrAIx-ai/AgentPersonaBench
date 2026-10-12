from backend.api.schemas import HarborJobLaunchRequest


def test_harbor_job_launch_request_prefers_chat_application_context():
    request = HarborJobLaunchRequest(
        taskPath="application/tasks/chat_meal-planning-nutrition",
        chatApplicationId="meal_planning_nutrition",
        chatApplicationContext="meal_planning",
    )

    assert request.chatApplicationContext == "meal_planning"
    assert request.chatDomain is None


def test_harbor_job_launch_request_defaults_chat_context():
    request = HarborJobLaunchRequest(
        taskPath="application/tasks/chat_openbb-corporate-action-honesty",
        chatApplicationId="finance_openbb",
    )

    assert request.chatApplicationContext == "financial_research"
    assert request.chatDomain is None
