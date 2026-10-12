from backend.service.task_list_summary import read_survey_questionnaire_list_meta


def test_read_survey_questionnaire_list_meta_from_product_feedback(tmp_path):
    task_dir = tmp_path / "example-survey_product-feedback"
    input_dir = task_dir / "input"
    input_dir.mkdir(parents=True)
    (input_dir / "questionnaire.yaml").write_text(
        "\n".join(
            [
                'id: "product_feedback_v1"',
                "title: Survey Product Feedback",
                "questions:",
                "  - id: q0",
                "    type: single",
                "  - id: q1",
                "    type: likert",
            ]
        ),
        encoding="utf-8",
    )

    questionnaire_id, question_count = read_survey_questionnaire_list_meta(task_dir)

    assert questionnaire_id == "product_feedback_v1"
    assert question_count == 2


def test_read_survey_questionnaire_list_meta_missing_yaml(tmp_path):
    task_dir = tmp_path / "survey_missing"
    task_dir.mkdir()

    questionnaire_id, question_count = read_survey_questionnaire_list_meta(task_dir)

    assert questionnaire_id is None
    assert question_count is None
