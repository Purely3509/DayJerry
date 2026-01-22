from tb.summarize import is_blocked_task, is_vague_task


def test_vague_task_detector():
    assert is_vague_task("Plan roadmap")
    assert is_vague_task("figure out budget")
    assert not is_vague_task("Finalize budget for Q1 with finance team")


def test_blocked_task_detector():
    assert is_blocked_task("Waiting for reply from vendor", [])
    assert is_blocked_task("Follow up on invoice", ["finance"])
    assert is_blocked_task("Prepare report", ["blocked"])
    assert not is_blocked_task("Prepare report", [])
