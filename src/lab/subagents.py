"""GUIDE Phần 1 - Định nghĩa subagent (tác tử con).   >>> SINH VIÊN CÀI ĐẶT <<<

Pseudo-code: guides/pseudocode/02_subagents.md
Kiểm tra:    pytest tests/test_02_agent.py
"""


def get_subagents() -> list[dict]:
    """Trả về danh sách subagent (ít nhất 2, tên khác nhau).

    Mỗi phần tử là một dict có các khóa bắt buộc:
      "name":          tên duy nhất (chữ thường, có thể có dấu gạch ngang)
      "description":   khi nào tác tử chính nên giao việc cho subagent này (viết như một hướng dẫn hành động)
      "system_prompt": chỉ dẫn cho subagent
    Gợi ý vai trò: explorer (đọc và báo cáo), implementer (thực hiện), reviewer (kiểm tra độc lập).
    """
    return [
        {
            "name": "explorer",
            "description": (
                "Call this FIRST for any task before changing anything: it reads the instruction file, "
                "the README/docstrings and sample data under workspace/ and reports the relevant facts "
                "(file layout, existing tests, data quirks) without modifying anything."
            ),
            "system_prompt": (
                "You are an explorer subagent. Read the task instruction, relevant source files, "
                "docstrings and data samples under workspace/. Never write, edit or delete any file. "
                "Reply with a concise factual report: what the task asks for, where the relevant code "
                "or data lives, and any format quirks (duplicates, missing values, mixed date formats, "
                "timezones) you noticed. Quote exact file paths and line numbers where useful."
            ),
        },
        {
            "name": "implementer",
            "description": (
                "Call this to carry out a well-scoped change (fix a function, clean a dataset, write an "
                "output file) once you know what must change. Give it the full task rules and exact file "
                "paths in the delegation message, since it sees nothing else."
            ),
            "system_prompt": (
                "You are an implementer subagent. Make the exact change described in the delegation "
                "message under workspace/, then run any relevant tests or scripts with the shell to check "
                "your work before replying. Reply with a short, factual summary of what you actually "
                "created or changed, and the result of the verification you ran."
            ),
        },
        {
            "name": "reviewer",
            "description": (
                "Call this AFTER an implementer step to independently verify the result against the "
                "original task rules and edge cases, before you report the task as done."
            ),
            "system_prompt": (
                "You are a reviewer subagent. Independently check the current state of workspace/ against "
                "the task rules given in the delegation message, including edge cases (duplicates, missing "
                "values, format differences, timezones). Re-run tests or checks yourself when possible. "
                "Never modify any file. Reply with a verdict (pass or fail) and the specific evidence for it."
            ),
        },
    ]
