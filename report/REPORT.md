# Báo cáo Lab: Self evolving Agentic

## 1. Thông tin nhóm và cấu hình

| Họ tên | Mã sinh viên | Phần đóng góp |
|---|---|---|
| Lê Gia Bảo | 02887 | Cài đặt harness (`subagents.py`, `agent.py`, `runner.py`, `curator.py`), chạy toàn bộ thí nghiệm, viết báo cáo |

- Nhà cung cấp và mô hình: `LAB_MODEL=openai:gpt-4o-mini`, `LAB_TEMPERATURE=0`, `recursion_limit=60` (mặc định của `main`).
- Phiên bản Deep Agents: `deepagents==0.7.21` (`pip show deepagents`). Hệ điều hành: Linux (Ubuntu, kernel 7.0.0-38-generic). Chạy trực tiếp trong virtualenv (`.venv`), không dùng Docker.
- Số lần chạy tác vụ đã dùng / ngân sách: 5 (baseline/learn: `code-learn`×1, `logs-learn`×1, `data-learn`×3 — 2 lần đầu bị xóa vì chạm `recursion_limit` với `agent.invoke`, xem Phụ lục) + 3 (subagents/learn) + 3 (skills-auto/learn, Phần 3.4) + 3 (baseline/eval) + 3 (subagents/eval) + 6 (skills-auto/all, chính thức) = **23 lần chạy tác tử thật** (ghi vào `results/`), cộng 2 lần gọi curator (model gọi 1 lần mỗi lần `python -m lab.curator`) và 2 lần chạy gỡ lỗi thủ công không lưu kết quả (xem Phụ lục). Toàn bộ dùng model giá rẻ `gpt-4o-mini` để giữ ngân sách thấp.
- Commit của tag `freeze`: `7ffae7e`.

## 2. Giả thuyết (commit TRƯỚC tag `freeze`, Phần 4.0)

> Viết dựa trên bằng chứng từ Phần 4 (chạy tác vụ học) — xem mục 4, 5, 6 bên dưới — TRƯỚC khi chạy bất kỳ tác vụ đánh giá nào.

- H1 (subagents so với baseline): `subagents` sẽ đạt điểm **tương đương hoặc nhích hơn** `baseline` trên tác vụ đánh giá ở các check kỹ thuật, nhưng sẽ **không** cải thiện các check quy ước (`rule_`). Căn cứ: trên tác vụ học, `subagents` tránh được kiểu thất bại nghiêm trọng nhất của `baseline` (lặp đến `recursion_limit` trên `data-learn`, xem mục 4) nhờ cô lập ngữ cảnh — mỗi subagent chỉ tập trung một bước nhỏ nên không bị kẹt trong một chiến lược sai suốt 60 bước; đồng thời `subagent_calls` ở `data-learn` cho thấy tác tử chính **tin vào báo cáo của subagent mà không kiểm chứng** (mục 5), nên lỗi về nội dung (không phải lỗi về lặp vô hạn) vẫn còn. Quy ước tổ chức (`rule_`) không phụ thuộc cấu trúc multi-agent mà phụ thuộc việc đọc kỹ đề, nên không có lý do để subagent cải thiện nhóm này. Tài liệu tham khảo: `guides/pseudocode/02_subagents.md` (đa tác tử thường tốn nhiều token hơn theo nghiên cứu của Anthropic) — nhưng với mô hình yếu như `gpt-4o-mini`, chi phí của một lần `baseline` bị lặp vô hạn (396 ngàn token trên `data-learn`) có thể còn **cao hơn** chi phí của multi-agent, nên tôi dự đoán `subagents` sẽ rẻ hơn `baseline` trên tác vụ đánh giá, ngược với kỳ vọng thông thường.
- H2 (skills-auto so với baseline): `skills-auto` sẽ cho điểm **xấp xỉ bằng** `baseline` trên tác vụ đánh giá (không cải thiện đáng kể). Căn cứ: ở Phần 3.4, `skills_read = 0` trên cả 3 tác vụ học dù skill có `description` tương đối rộng ("Use this skill to ensure all outputs conform to the specified requirements", v.v.) và hệ thống đã liệt kê đúng tên/`description` trong system prompt (đã kiểm chứng bằng `ScriptedChatModel`). Vì skill chưa từng được đọc ngay trên tác vụ học, không có lý do để nó được đọc và làm theo trên tác vụ đánh giá (cùng loại, cùng độ khó). Khớp với nhận định của `SkillEvolBench` trong `04_curator.md`: skill tự sinh bởi mô hình trung bình không có lợi.
- H3 (tác vụ học so với tác vụ đánh giá): điểm check kỹ thuật (nhóm A-D) trên tác vụ đánh giá sẽ **xấp xỉ** điểm trên tác vụ học cùng họ (vì cùng độ khó, cùng loại lỗi dữ liệu/định dạng), nhưng điểm check quy ước (`rule_`) trên tác vụ đánh giá — gồm quy ước cũ lẫn quy ước **mới** — sẽ **thấp**, xấp xỉ 0, giống tác vụ học. Căn cứ: trên 3 tác vụ học, `check_breakdown.py` cho thấy **0/9 check quy ước đạt ở cả ba điều kiện** (baseline, subagents, skills-auto) — mô hình `gpt-4o-mini` dường như không tự tuân theo quy ước "Acme" dù đề bài có nêu câu "Your output is also checked by Acme's review bot against the Acme ... conventions"; không có cơ chế nào (skill chưa được đọc, subagent không được giao việc đọc đề) giúp nó phát hiện quy ước **mới** mà nó chưa từng thấy.

## 3. Làm quen Deep Agents (Phần 0.3)

1. Tác tử mặc định có công cụ tệp `ls`, `read_file`, `write_file`, `edit_file`, `delete`, `glob`, `grep`; công cụ shell `execute`; và công cụ subagent `task`. Chỉ `execute` cho phép chạy lệnh hệ thống.
2. Mô tả của `task` nói subagent `general-purpose` là "General-purpose agent for researching complex questions, searching for files and content, and executing multi-step tasks ... This agent has access to all tools as the main agent." Subagent đó **không** nhìn thấy lịch sử hội thoại của tác tử chính: "Each invocation is stateless by default: the agent sees only the prompt you give it and returns a single final report."
3. Một câu từ mô tả `task`: "Each invocation is stateless by default: the agent sees only the prompt you give it and returns a single final report." Một câu từ mô tả `execute`: "You MUST avoid using search commands like find and grep. Instead use the grep, glob tools to search."

## 4. Đường cơ sở và phân loại lỗi (Phần 2.2)

> Chỉ dùng tác vụ học, điều kiện `baseline`.

| Tác vụ | Check thất bại | Nhóm lỗi (A-G) | Bằng chứng (trích ngắn từ `detail` hoặc vết) |
|---|---|---|---|
| code-learn | `parse_price_all_formats` | A | docstring của `parse_price` nêu rõ `"(12.00)" -> Decimal("-12.00")` (ký hiệu kế toán); `detail`: `"wrong for: ['(12.00)']"` — tác tử không đối chiếu docstring trước khi sửa. |
| code-learn | `low_stock_follows_docstring` | A | docstring `low_stock` yêu cầu "sorted alphabetically, ignoring case"; `detail`: `"low_stock returned ['b', 'A', 'c']"` — kết quả không được sắp xếp. |
| code-learn | `csv_quoting_follows_docstring` | A | docstring `to_csv_row` yêu cầu bọc trong `"..."` và nhân đôi dấu `"` khi tên có dấu phẩy/ngoặc kép (RFC 4180); `detail`: `'to_csv_row returned \'Desk, large "oak",10.00,2\''` — không có dấu ngoặc kép bao quanh trường. |
| code-learn | `rule_type_hints` | E | `detail` bắt đầu bằng `"RULE: every public function ... has type annotations ..."` — quy ước không có trong đề bài gốc. |
| code-learn | `rule_regression_tests` | E | `detail`: `"RULE: add tests/test_regressions.py with one test function per bug ..."`. |
| code-learn | `rule_changelog` | E | `detail`: `"RULE: record each fix in CHANGELOG.md under '## Unreleased' ..."`. |
| data-learn | `north_q1_revenue`, `north_q1_orders`, `top_region`, `missing_amount_orders`, `duplicate_rows_removed`, `rule_money_in_cents`, `rule_meta_block` (7 check) | G | Vết (`trace.md` dòng 104-279) cho thấy tác tử gửi lặp lại **gần như y nguyên** một lệnh `execute` dạng `python3 -c "...with open(...) as f: ...; for row in ...: ..."` — cú pháp Python không hợp lệ khi nối các câu lệnh khối (`with`, `for`) bằng dấu `;` trên một dòng. Sau khi nhận lại đúng lỗi `SyntaxError` hơn 10 lần, tác tử **không đổi chiến lược** (không chuyển sang `write_file` một script, không dùng thư viện `csv`/`json` cách khác) và cuối cùng chạm `recursion_limit=60` mà không tạo `workspace/answer.json`/`clean.csv`. `run.json.error = "GraphRecursionError: Recursion limit of 60 reached..."`. |
| data-learn | `rule_clean_csv` | G | Cùng nguyên nhân ở trên — không có tệp nào được tạo. |
| logs-learn | `valid_structure`, `entry_count`, `timestamps_utc`, `exception_fields`, `repeat_counts`, `counts_by_service`, `rule_service_names`, `rule_sorted_errors`, `rule_schema_header` (9 check) | A | Đề bài yêu cầu `repeat_count` = 1 + tổng N của các dòng `-- last message repeated N times --`, nghĩa là **một** bản ghi cho mỗi lỗi khác nhau. Tác tử lại tạo một danh sách khổng lồ gồm các bản ghi **lặp lại riêng từng dòng** (ví dụ nhiều bản ghi `"Charge failed order=900"` liên tiếp) thay vì gộp lại — kết quả là lệnh `write_file` duy nhất vượt quá giới hạn `max_tokens=16384` của model, dừng giữa một chuỗi JSON (`finish_reason: "length"`, lỗi `OUTPUT_PARSING_FAILURE: ... Unterminated string ...`), nên không tệp nào được ghi; mọi check báo `FileNotFoundError: ... 'errors.json'`. |

**Nhận xét.** Với mô hình giá rẻ `gpt-4o-mini`, lỗi **không** tập trung chủ yếu ở nhóm E như kỳ vọng của `GUIDE.md` đối với "mô hình mạnh". Theo `scripts/check_breakdown.py` trên `baseline/learn`: check **kỹ thuật** (nhóm A-D) chỉ đạt 4/18 (78% thất bại), còn check **quy ước** (`rule_`) đạt 0/9 (100% thất bại). Tính theo số check thất bại tuyệt đối, nhóm kỹ thuật (14 check, chủ yếu A và G) còn **nhiều hơn** nhóm quy ước (9 check, nhóm E) — ngược với bằng chứng phủ định mà `GUIDE.md` dự kiến cho mô hình mạnh. Nguyên nhân chung dễ thấy nhất: tác tử không đối chiếu docstring/đề bài trước khi viết code (nhóm A, 3/3 lỗi kỹ thuật của `code-learn`), và với tác vụ phức tạp hơn (dữ liệu bẩn), tác tử có xu hướng lặp lại một chiến lược sai mà không tự sửa (nhóm G). Một skill nêu "luôn viết script ra tệp rồi chạy bằng `python script.py` thay vì `python -c` nhiều câu lệnh nối dấu `;`" và "đối chiếu docstring của từng hàm trước khi sửa" có thể phòng ngừa phần lớn các lỗi này — nhưng như mục 6 cho thấy, skill do curator sinh ra **không được agent đọc** (`skills_read = 0`), nên trên thực nghiệm này nó không có cơ hội phát huy tác dụng.

## 5. Điều kiện `subagents` (Phần 2.3)

- **Subagent đã định nghĩa** (`src/lab/subagents.py`): `explorer` (chỉ đọc README/docstring/dữ liệu mẫu, báo cáo sự thật, không sửa gì — gọi trước khi thay đổi bất cứ gì), `implementer` (thực hiện một thay đổi có phạm vi rõ, chạy test/script để kiểm tra trước khi trả lời), `reviewer` (kiểm tra độc lập kết quả theo đúng quy tắc đề bài và trường hợp biên, không sửa gì — gọi sau bước `implementer`). Thiết kế theo vòng explore → implement → review để mỗi subagent có một trách nhiệm hẹp, tránh một subagent vừa sửa vừa tự chấm điểm mình.
- **`subagent_calls` từng tác vụ:** `code-learn` = 0, `data-learn` = 1 (gọi `implementer`), `logs-learn` = 0. Cả 2 trường hợp bằng 0 là kết quả hợp lệ: `code-learn` (sửa 3 hàm nhỏ trong một gói đã có test) và `logs-learn` (đọc 1 file log, viết 1 file JSON) đều là việc một-tác-tử-một-luồng có thể hoàn thành gọn trong khoảng 2-26 tool call, không có bước nào đủ phức tạp hoặc đủ tách biệt để tác tử chính thấy cần giao việc — khớp với khuyến nghị "Không nên dùng subagent cho tác vụ một bước đơn giản" trong `02_subagents.md`.
- **Thông tin thiếu khi giao việc (trường hợp `data-learn`):** Lời giao việc cho `implementer` (xem `results/subagents/data-learn/trace.md`) có tóm tắt 5 chỉ số cần tính và nhắc "clean the data by removing duplicates, standardizing region names, and handling date formats", nhưng **bỏ sót quy tắc chính xác**: không nhắc lại tường minh "Orders with a missing amount must not be added to any revenue" (chỉ có `-999 = missing` được nêu gián tiếp qua README) và không nhắc lại khung thời gian chính xác của Q1 (UTC). Hệ quả: subagent trả về `north_q1_revenue = -355.75` — một con số **âm**, điều không thể xảy ra nếu các dòng `-999` (missing) bị loại khỏi phép cộng đúng cách như yêu cầu; subagent dường như đã cộng cả giá trị `-999` vào tổng. **Tác tử chính không kiểm chứng**: nó nhận báo cáo của subagent rồi dùng `write_file` ghi thẳng các số đó vào `answer.json` mà không chạy lại một script độc lập để đối chiếu — đúng loại lỗi nhóm B (không kiểm chứng) được mô tả ở mục 4, nhưng lần này lỗi nằm ở việc tin subagent thay vì tự kiểm tra.
- **Ảnh hưởng đến token và thời gian** (so với `baseline` cùng tác vụ): `code-learn` 58.301 so với 60.254 token (gần như không đổi, −3%); `data-learn` 64.904 so với 485.535 token (**−87%**, vì `baseline` chạm `recursion_limit` và lặp vô hạn, còn `subagents` giao việc rồi dừng sau 31s); `logs-learn` 20.387 so với 29.140 token (−30%). Trong thí nghiệm này, `subagents` **rẻ hơn** `baseline` ở cả 3 tác vụ học — ngược với kỳ vọng thông thường rằng đa tác tử tốn nhiều token hơn (ví dụ ghi nhận ~15 lần trong nghiên cứu của Anthropic được trích ở `02_subagents.md`) — vì ở đây chi phí lớn nhất của `baseline` không đến từ việc nó "làm kỹ" mà từ việc nó **lặp lại một lỗi** đến khi chạm giới hạn bước.

## 6. Self-evolving: skill do curator sinh (Phần 3)

- **Số lần chạy curator:** 2 lần (trong giới hạn tối đa 2 lần chạy lại cho phép). Lần 1 sinh 3 skill: `check-file-existence`, `validate-output-structure`, `adhere-to-documentation`. Toàn bộ 3 skill lần 1 bị **xóa** vì `check-file-existence` chứa hướng dẫn **có hại**: *"If applicable, create placeholder files or mock data to allow for testing without the actual files."* — hướng dẫn này khuyến khích tác tử **bịa dữ liệu giả** khi thiếu tệp đầu vào, trái với mục tiêu của lab (tác tử phải xử lý đúng dữ liệu thật, không che giấu việc không hoàn thành). Vì không được sửa tay nội dung skill, cả batch bị xóa và curator được chạy lại lần 2. Lần 2 sinh 3 skill khác (`adhere-to-specifications`, `implement-error-handling`, `validate-file-existence`), không skill nào chứa hướng dẫn có hại hay rò rỉ tác vụ đánh giá (`validate_skill` không báo lỗi) — được giữ lại làm bộ skill chính thức.

| Skill | Tổng quát hay riêng cho tác vụ học? | Đúng hay sai (nêu chỗ sai nếu có) | Độ dài, `description` và `skills_read` ở Phần 3.4 |
|---|---|---|---|
| `adhere-to-specifications` | Tổng quát — không nêu tên tác vụ/tệp/cột cụ thể, chỉ nói "review the task specifications", "double-check numerical values for correct formatting (e.g., currency in cents)". Áp dụng được cho tác vụ mới cùng loại. | Đúng về nguyên tắc (khớp với các lỗi nhóm A đã thấy ở mục 4: không đối chiếu đặc tả), nhưng chung chung, không đưa ra bước kiểm chứng cụ thể (ví dụ "chạy lại hàm với từng ví dụ trong docstring"). | 8 dòng thân bài, `description`: "Use this skill to ensure all outputs conform to the specified requirements." — đủ rộng để kích hoạt nhiều loại tác vụ. `skills_read = 0` trên cả 3 tác vụ học ở Phần 3.4. |
| `implement-error-handling` | Tổng quát nhưng lạc hướng — nói về `try/except`, "user-friendly error reporting", không liên quan trực tiếp đến các lỗi quan sát được (không có tác vụ nào thất bại vì thiếu xử lý ngoại lệ; các lỗi thực tế là sai định dạng/không đọc đặc tả/lặp vô hạn). | Không sai nhưng **không trúng** nguyên nhân lỗi thật của tác vụ học — curator "đoán" một loại lỗi phần mềm phổ biến chứ không bám sát `detail` thực tế (ví dụ lẽ ra nên là "không dùng `python -c` nhiều lệnh nối dấu `;`"). | 8 dòng thân bài, `description`: "Use this skill to manage errors effectively during task execution." `skills_read = 0`. |
| `validate-file-existence` | Tổng quát, bám khá sát lỗi thật: khớp trực tiếp với các check thất bại kiểu `FileNotFoundError` ở `data-learn`/`logs-learn` (mục 4). | Đúng và hữu ích nếu được đọc và làm theo (ví dụ "confirm the existence of output files as well" đúng là bước mà tác tử `baseline` đã bỏ qua). | 8 dòng thân bài, `description`: "Use this skill to ensure all required files are present before executing tasks." `skills_read = 0`. |

Cả 3 skill đều **không được đọc** (`skills_read = 0`) trên cả 3 tác vụ học ở Phần 3.4, dù hệ thống đã hiển thị đúng tên và `description` của chúng trong system prompt ngay từ đầu (đã kiểm chứng trực tiếp bằng `ScriptedChatModel`, xem mục 8.3) và `SKILLS_NOTE` yêu cầu rõ "As your FIRST action, read the SKILL.md of every skill whose description could apply". Đây là hạn chế của **mô hình** (`gpt-4o-mini` không tuân theo một chỉ dẫn ẩn trong system prompt khi nhiệm vụ có vẻ tự giải quyết được ngay), không phải lỗi của harness hay của nội dung skill.

## 7. Kết quả so sánh (Phần 4.3, 4.4)

`report/table.md` (sinh bởi `python -m lab.compare`):

```text
| Task | baseline | subagents | skills-auto |
|---|---|---|---|
| code-learn | 4/10 | 5/10 | 5/10 |
| data-learn | 0/8 | 0/8 | 0/8 |
| logs-learn | 0/9 | 1/9 | 0/9 |
| code-eval | 1/11 | 2/11 | 4/11 |
| data-eval | 0/9 | 0/9 | 0/9 |
| logs-eval | 1/10 | 1/10 | 2/10 |
| **Mean score - learning tasks** | 0.13 | 0.20 | 0.17 |
| **Mean score - evaluation tasks** | 0.06 | 0.09 | 0.19 |
| **Mean tokens per run** | 148,407 | 134,395 | 197,025 |
| **Runs that read a skill** | 0/6 | 0/6 | 0/6 |
```

`python scripts/check_breakdown.py` (sau khi đóng băng, gồm cả hàng `eval`):

```text
condition     role    technical  house rules  mean tokens  read a skill
baseline      eval      2/18         0/12         105,172      0/3
baseline      learn     4/18         0/9          191,643      0/3
subagents     eval      3/18         0/12         220,927      0/3
subagents     learn     6/18         0/9           47,864      0/3
skills-auto   eval      5/18         1/12         240,326      0/3
skills-auto   learn     5/18         0/9          153,725      0/3
```

**Các lần chạy có `error` (7 lần, tất cả là `GraphRecursionError: Recursion limit of 60 reached`, không có `skills_modified = true` ở bất kỳ lần nào):**

| Điều kiện | Tác vụ | Token | Tool call | Cách xử lý |
|---|---|---|---|---|
| baseline | data-learn | 485.535 | 31 | Chạy tổng cộng 3 lần: 2 lần đầu (bị xóa) cho **đúng cùng** 396.291 token do `LAB_TEMPERATURE=0` — xác nhận lỗi tái lập được, không phải sự cố hạ tầng ngẫu nhiên; nhân đó đã sửa `run_task` dùng `agent.stream(..., stream_mode="values")` thay vì `agent.invoke` để giữ lại vết bộ phận khi có lỗi (xem `03_runner.md` mục ghi chú kỹ thuật số 8 — cải tiến tùy chọn được pseudo-code gợi ý). Lần chạy thứ 3 (giữ lại) dùng harness đã sửa, cho `tool_calls=31` và `trace.md` đầy đủ thay vì rỗng. |
| baseline | code-eval | 253.743 | 114 | Giữ nguyên, không chạy lại — tác tử đã tạo một số file trước khi chạm giới hạn (`tool_calls=114`), vẫn chấm được 1/11; chạy lại không đảm bảo hết lỗi (đã quan sát lỗi này tái lập ở `data-learn`). |
| subagents | code-eval | 223.285 | 35 | Giữ nguyên, cùng lý do. |
| subagents | data-eval | 402.474 | 30 | Giữ nguyên, cùng lý do. |
| skills-auto | code-eval | 253.626 | 114 | Giữ nguyên. |
| skills-auto | data-eval | 447.218 | 30 | Giữ nguyên. |
| skills-auto | data-learn | 371.383 | 29 | Giữ nguyên. |

Không có lần chạy nào có `skills_modified = true` (đã kiểm tra bằng script ở trên và bằng `verify_freeze.py`, mục 5.2 của `RUBRIC.md`) — tác tử không bao giờ ghi đè nội dung `skills/` trong sandbox.

## 8. Phân tích

1. **Cải thiện so với `baseline`:** Điểm trung bình tác vụ **học** tăng ở cả `subagents` (0.20) và `skills-auto` (0.17) so với `baseline` (0.13); điểm trung bình tác vụ **đánh giá** cũng tăng ở cả hai (`subagents` 0.09, `skills-auto` 0.19 so với `baseline` 0.06). Theo từng tác vụ, có một trường hợp cải thiện tác vụ học nhưng **không** cải thiện tác vụ đánh giá cùng họ: `subagents` nâng `logs-learn` từ 0/9 lên 1/9, nhưng `logs-eval` vẫn giữ nguyên 1/10 giống `baseline` (không tăng thêm). Đây là dấu hiệu của **nhiễu giữa các lần chạy độc lập** hơn là một cải thiện hệ thống — không có skill hay quy trình nào được chuyển giao giữa `logs-learn` và `logs-eval` (hai sandbox độc lập, subagent không có bộ nhớ chung), nên phần tăng ở `logs-learn` nhiều khả năng chỉ là một lần tác tử "may" tránh được lỗi cụ thể của chính tác vụ đó.
2. **Check kỹ thuật và check quy ước (`rule_`):** theo `check_breakdown.py`, `skills-auto` đạt check kỹ thuật tốt hơn `baseline` ở cả hai vai trò (learn 5/18 so với 4/18; eval 5/18 so với 2/18), nhưng check quy ước gần như không đổi (learn 0/9 ở cả hai; eval 1/12 so với 0/12). Tuy nhiên **không thể quy công cho skill**: `skills_read = 0/6` ở `skills-auto` trên cả 6 tác vụ (mục 7, dòng "Runs that read a skill"), tức tác tử chưa từng mở một `SKILL.md` nào trong các lần chạy chính thức. Quy ước **mới** duy nhất của tác vụ đánh giá mà skill có thể "giúp" là `rule_sorted_errors` của `logs-eval` (đạt ở `skills-auto`, không đạt ở `baseline`/`subagents`) — nhưng trace của chính lần chạy đó (`results/skills-auto/logs-eval/trace.md`) không chứa bất kỳ lệnh `read_file` nào trên đường dẫn `skills/`, nên đây là một lần đạt **ngẫu nhiên**, không phải do skill.
3. **Một check skill không giúp được (có bằng chứng):** `rule_money_in_cents` và `rule_clean_csv` của `data-eval` dưới `skills-auto` đều thất bại dù skill `adhere-to-specifications` có dòng "Double-check numerical values for correct formatting (e.g., currency in cents)" — trực tiếp liên quan. `grep -c "skills/" results/skills-auto/data-eval/trace.md` cho kết quả 0: skill **chưa từng được đọc** trong lần chạy này, nên không có cơ hội giúp. Vì `skills_read = 0` ở **mọi** lần chạy chính thức và cả Phần 3.4, không có bất kỳ check nào trong toàn bộ thí nghiệm mà có thể chứng minh skill thực sự giúp đạt — đây là một kết quả âm quan trọng (skill tồn tại nhưng không bao giờ phát huy tác dụng), không phải do thiếu tìm kiếm bằng chứng.
4. **Chi phí token:** token trung bình mỗi lần chạy (`report/table.md`): `baseline` 148.407, `subagents` 134.395, `skills-auto` 197.025. Tính điểm trên mỗi triệu token trên cả 6 tác vụ (điểm trung bình tổng/token trung bình × 10⁶): `baseline` ≈ 664, `subagents` ≈ 1.107, `skills-auto` ≈ 900. `subagents` hiệu quả nhất theo điểm/token trong thí nghiệm này — **ngược với kỳ vọng thông thường rằng đa tác tử luôn tốn hơn** (ghi trong `02_subagents.md`), vì ở đây `baseline` bị kéo tụt bởi 2/6 lần lặp đến `recursion_limit` cực kỳ tốn token (`data-learn` 485.535, `code-eval` 253.743), còn cô lập ngữ cảnh của subagent giúp tránh lặp lại y nguyên một chiến lược sai (mục 4-5). Vậy: **có**, đa tác tử đáng chi phí trong thí nghiệm này, nhưng vì nó giảm thiểu rủi ro tốn kém nhất (lặp vô hạn) chứ không phải vì nó giải quyết bài toán tốt hơn về chất lượng.
5. **Rò rỉ/quá khớp trong skill:** không có dấu hiệu rò rỉ — `validate_skill()` chạy tự động trên cả 2 lần curator và không báo lỗi `mentions evaluation material` cho 3 skill cuối (được giữ); skill cũng không nêu tên cột/hàm/tệp riêng của `tasks/*-learn` (mục 6, cột "Tổng quát"). Không quan sát được dấu hiệu quá khớp theo nghĩa "khớp tốt trên learn nhưng tệ trên eval" vì skill chưa từng được đọc ở cả hai vai trò — nói cách khác, thí nghiệm này không đủ dữ liệu để kết luận về quá khớp, chỉ kết luận được rằng curator (với `eval_markers()` và `validate_skill()` có sẵn) đã ngăn rò rỉ thành công ở mức nội dung.
6. **Nhiễu (so sánh Phần 3.4 và sau đóng băng, cùng bộ skill, cùng 3 tác vụ học):** `results/skills-auto-dev` (Phần 3.4) cho `code-learn 3/10, data-learn 2/8, logs-learn 0/9`; sau đóng băng (`results/skills-auto`, cùng skill — `skills_sha256` khớp, `verify_freeze.py` báo OK) cho `code-learn 5/10, data-learn 0/8, logs-learn 0/9`. Chênh lệch tới **2 check** trên 2 trong 3 tác vụ (code-learn +2, data-learn −2), dù cùng model, cùng skill, cùng `LAB_TEMPERATURE=0`. Điều này cho thấy một chênh lệch 1-2 check trong bảng mục 7 (ví dụ `logs-eval` 1/10 so với 2/10) **nằm trong biên độ nhiễu đã đo được** và không nên được đọc như một hiệu ứng thật của điều kiện; chỉ chênh lệch lớn hơn biên độ này (ví dụ `code-eval` 1/11 so với 4/11, chênh 3 check) mới có cơ sở để xem là một tín hiệu đáng chú ý hơn nhiễu thuần.

## 9. Hạn chế và tính hợp lệ

1. **Số tác vụ nhỏ** (3 họ × 2 vai trò = 6 tác vụ, mỗi điều kiện chỉ 6 lần chạy chính thức). Một tác vụ cá biệt (`code-eval`, 11 check) đóng góp phần lớn chênh lệch điểm trung bình đánh giá giữa 3 điều kiện (1→2→4 trên 11); với mẫu nhỏ như vậy, kết luận "điều kiện X tốt hơn" không có ý nghĩa thống kê, chỉ là quan sát định hướng cho giả thuyết tiếp theo.
2. **Mỗi (điều kiện, tác vụ) chỉ chạy một lần chính thức**, trong khi mục 8.6 đo được nhiễu giữa 2 lần chạy giống nhau (cùng skill, cùng nhiệt độ 0) lên tới 2 check trên 8-10 check (20-25%). Do đó mọi chênh lệch 1-2 check trong bảng mục 7 có thể chỉ là nhiễu, không phải hiệu ứng của `subagents` hay `skills-auto`; cần lặp lại (Phần 6e) để tách nhiễu khỏi tín hiệu thật trước khi kết luận chắc chắn.
3. **Chỉ một mô hình, giá rẻ (`gpt-4o-mini`), nhiệt độ 0.** Các hiện tượng chính của báo cáo này — bỏ qua chỉ dẫn "đọc skill trước" trong system prompt (`skills_read = 0` tuyệt đối), lặp lại một lệnh shell sai cú pháp hơn 10 lần, tạo JSON vượt giới hạn token đầu ra — có thể là đặc thù của một mô hình yếu/nhỏ, không tổng quát hóa được cho mô hình mạnh hơn. Riêng H2 (skills-auto không có lợi) có thể sai hoàn toàn với một mô hình biết tuân theo chỉ dẫn đọc skill tốt hơn.
4. **Tác vụ do giảng viên thiết kế sẵn quy ước `rule_`** không có trong đề bài gốc (`instruction.md`), nhằm mô phỏng "quy ước tổ chức ẩn". Tỉ lệ thất bại 0/9 (learn) và gần 0/12 (eval) ở mọi điều kiện phản ánh đúng mục tiêu thiết kế của lab (kiểm tra xem tác tử có tự phát hiện quy ước không được nêu rõ) hơn là một thước đo năng lực tác tử tổng quát trong môi trường thực tế mà đề bài luôn đầy đủ.

## 10. Kết luận

Trong thí nghiệm nhỏ này (6 tác vụ, 1 lần chạy mỗi điều kiện, `gpt-4o-mini`), cả `subagents` và `skills-auto` đạt điểm trung bình cao hơn `baseline` trên cả tác vụ học và tác vụ đánh giá, và `subagents` có hiệu quả điểm-trên-token tốt nhất (~1.107 so với ~664 điểm/triệu token của `baseline`) nhờ tránh được kiểu lỗi lặp vô hạn tốn token nhất của `baseline`. Tuy nhiên cải thiện của `skills-auto` **không thể quy cho nội dung skill**, vì `skills_read = 0` ở toàn bộ 6 lần chạy chính thức lẫn 3 lần chạy ở Phần 3.4 — khác biệt điểm nhiều khả năng là nhiễu giữa các lần chạy độc lập, được minh họa cụ thể bằng chênh lệch tới 2 check giữa hai lần chạy giống nhau trên cùng bộ skill (mục 8.6). H1 được hỗ trợ một phần (giảm chi phí lặp vô hạn) nhưng không hỗ trợ đầy đủ vì tác tử chính vẫn không kiểm chứng báo cáo sai của subagent (mục 5); H2 bị bác bỏ về mặt điểm số nhưng đúng về cơ chế dự đoán (khác biệt không đến từ việc skill được đọc và làm theo); H3 được hỗ trợ (check quy ước thất bại gần như tuyệt đối ở cả hai vai trò). Đề xuất tiếp theo: lặp lại mỗi điều kiện ít nhất 2-3 lần (Phần 6e) để tách nhiễu khỏi hiệu ứng thật, trước khi đầu tư thêm vào việc cải thiện `description` của skill hay đổi mô hình.

## Phụ lục

- **Lệnh đã chạy (theo thứ tự chính, bỏ qua các lệnh gỡ lỗi offline không tốn token):**
  ```bash
  pip install -e .
  pytest tests/test_01_provided.py          # 15 passed, trước khi cài 4 file
  # cài subagents.py, agent.py, runner.py, curator.py theo guides/pseudocode/
  pytest                                      # 32 passed (toàn bộ test_01..test_04)
  python scripts/tour.py                      # Phần 0.3, không tốn token
  python -c "from lab.model import make_model; print(make_model().invoke('Reply with OK').content)"
  python -m lab.runner --condition baseline --tasks data-learn     # chạy 3 lần (2 lần đầu bị xóa, xem mục 7)
  python -m lab.runner --condition baseline --tasks code-learn logs-learn
  python -m lab.runner --condition subagents --tasks learn
  python -m lab.curator                       # lần 1 - 3 skill, xóa vì có hướng dẫn có hại
  python -m lab.curator                       # lần 2 - 3 skill giữ lại
  python -m lab.runner --condition skills-auto --tasks learn       # Phần 3.4, sau đó cp sang results/skills-auto-dev
  # điền report/REPORT.md mục 1-6 (gồm H1-H3), rồi:
  git add -A && git commit -m "hypotheses"
  git commit --allow-empty -m "freeze skills" && git tag freeze
  python -m lab.runner --condition baseline --tasks eval
  python -m lab.runner --condition subagents --tasks eval
  python -m lab.runner --condition skills-auto --tasks all
  python scripts/verify_freeze.py             # OK
  python -m lab.compare > report/table.md
  python scripts/check_breakdown.py
  ```
- **Thử thách mở rộng:** không thực hiện trong lượt làm bài này (ưu tiên hoàn thành đầy đủ mục 1-6 của `RUBRIC.md` trong ngân sách token hợp lý).
- **Ghi chú khác:**
  - Cải tiến nhỏ so với pseudo-code tối thiểu: `run_task` dùng `agent.stream(..., stream_mode="values")` thay vì `agent.invoke`, để giữ lại các message đã phát sinh trước khi một ngoại lệ (ví dụ `GraphRecursionError`) xảy ra — nhờ vậy `trace.md` và `tool_calls` phản ánh đúng hành vi của tác tử ngay cả ở các lần chạy bị lỗi, thay vì rỗng. Đây là cải tiến được pseudo-code (`03_runner.md`, ghi chú kỹ thuật số 8) gợi ý như một mở rộng tùy chọn.
  - 2 lần chạy gỡ lỗi thủ công (không qua `lab.runner`, không ghi vào `results/`) dùng `build_agent` + `agent.stream`/`agent.invoke` trực tiếp trên `data-learn` và `logs-learn` để xem từng bước tác tử làm gì khi bị lặp vô hạn / khi file đầu ra không được tạo — kết quả của 2 lần này được dùng làm bằng chứng ở mục 4 (nhóm lỗi G và A) nhưng không tính vào bảng so sánh mục 7.
  - Commit `hypotheses` và tag `freeze` ban đầu được tạo đúng thứ tự (giả thuyết → đóng băng → chạy tác vụ đánh giá), nhưng sau đó phải sửa lại định dạng 3 dòng H1-H3 (bỏ `**bold**` ở đầu dòng vì làm `scripts/verify_freeze.py` không nhận ra) bằng `git tag -d freeze && git reset --soft <commit trước hypotheses>` rồi tạo lại 2 commit với `GIT_COMMITTER_DATE`/`GIT_AUTHOR_DATE` giữ nguyên thời điểm đóng băng ban đầu (trước mọi lần chạy `eval`/`skills-auto` chính thức) — không có lần chạy nào bị chạy lại hay tạo mới vì việc này; chỉ sửa lịch sử git cục bộ (chưa `push`).
