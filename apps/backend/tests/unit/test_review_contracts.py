from taxmind.modules.reviews.domain import ReviewActionRecord, aggregate_decisions


def test_returned_review_action_keeps_overall_task_open() -> None:
    actions = [
        ReviewActionRecord(
            id="action-1",
            task_id="task-1",
            action_no=1,
            decision="returned",
            comment_safe="请补充业务发生日对应的依据条款",
            actor_user_id="reviewer-1",
            occurred_at=None,
        )
    ]

    assert aggregate_decisions(actions) == "returned"
