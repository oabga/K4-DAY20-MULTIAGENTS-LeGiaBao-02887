---
name: validate-file-existence
description: Use this skill to ensure all required files are present before executing tasks.
---
- Check if all input files specified in the task are available.
- Verify the file paths are correct and accessible.
- If a file is missing, log an error message indicating which file is not found.
- Before running any processing commands, confirm the existence of output files as well.
- Use exception handling to manage file-related errors gracefully.
- Document the expected file structure and naming conventions in the project README.
- Create a checklist of required files for each task to ensure completeness.
- Implement automated tests to verify file presence before task execution.