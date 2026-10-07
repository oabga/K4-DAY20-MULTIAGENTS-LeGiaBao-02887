# Báo cáo Lab: Self evolving Agentic

## 1. Thông tin nhóm và cấu hình

| Họ tên | Mã sinh viên | Phần đóng góp |
|---|---|---|
| Lê Gia Bảo | 02887 | Cài đặt harness (`subagents.py`, `agent.py`, `runner.py`, `curator.py`), chạy toàn bộ thí nghiệm, viết báo cáo |

- Nhà cung cấp và mô hình: `LAB_MODEL=openai:gpt-4o-mini`, `LAB_TEMPERATURE=0`, `recursion_limit=60` (mặc định của `main`).
- Phiên bản Deep Agents: `deepagents==0.7.21` (`pip show deepagents`). Hệ điều hành: Linux (Ubuntu, kernel 7.0.0-38-generic). Chạy trực tiếp trong virtualenv (`.venv`), không dùng Docker.
- Số lần chạy tác vụ đã dùng / ngân sách: 3 (baseline/learn, bao gồm 2 lần chạy lại `data-learn` do chạm `recursion_limit`) + 3 (subagents/learn) + 2 lần gọi curator (1 lần bị xóa vì sinh skill có hại) + 3 (skills-auto/learn, Phần 3.4) + 3 (baseline/eval) + 3 (subagents/eval) + 6 (skills-auto/all, chính thức) = 23 lần chạy tác tử thật + 2 lần gọi curator, dùng model giá rẻ `gpt-4o-mini` để giữ ngân sách thấp.
- Commit của tag `freeze`: điền sau khi tạo tag (xem lệnh ở Phụ lục).

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

> Dán nội dung `report/table.md` và kết quả `python scripts/check_breakdown.py`. Nêu các lần chạy có `error` hoặc `skills_modified = true` (nếu có) và cách xử lý.

```text
(dán bảng ở đây)
```

## 8. Phân tích

> Trả lời từng câu bằng số liệu từ mục 7 và bằng chứng từ vết. Kết quả âm hoặc không có khác biệt vẫn hợp lệ nếu được phân tích tốt.

1. So với `baseline`, điều kiện nào cải thiện điểm tác vụ **học**? Điều kiện nào cải thiện điểm tác vụ **đánh giá**? Có điều kiện nào cải thiện tác vụ học nhưng không cải thiện tác vụ đánh giá? Nếu có, đó là dấu hiệu gì?
2. Tách điểm thành check kỹ thuật và check quy ước (`rule_`). Skill do curator sinh giúp nhóm check nào? Check quy ước **mới** của tác vụ đánh giá có được skill giúp không, và vì sao?
3. Dựa vào vết và `skills_read`, giải thích một check mà skill giúp đạt và một check mà skill không giúp (skill chưa được đọc, đọc nhưng không làm theo, skill thiếu hoặc sai).
4. Chi phí: so sánh số token trung bình giữa các điều kiện. Điều kiện nào có hiệu quả tốt nhất theo điểm trên mỗi token? Đa tác tử có đáng chi phí trong thí nghiệm này không?
5. Có dấu hiệu rò rỉ dữ liệu hoặc quá khớp nào trong skill sinh ra không? Nhóm đã phòng tránh như thế nào?
6. Nhiễu: so sánh điểm tác vụ học của cùng bộ skill ở Phần 3.4 (đã sao lưu) và sau đóng băng. Chênh lệch bao nhiêu? Nó cho biết điều gì về độ tin cậy của các chênh lệch trong bảng ở mục 7?

## 9. Hạn chế và tính hợp lệ

> Nêu ít nhất 3 hạn chế và ảnh hưởng của từng hạn chế đến kết luận (ví dụ: chỉ 3 tác vụ mỗi vai trò, mỗi cấu hình chạy một lần, nhiễu của mô hình, tác vụ do giảng viên thiết kế sẵn quy ước, chỉ một mô hình).

1.
2.
3.

## 10. Kết luận

> Tối đa 5 câu. Chỉ khẳng định điều số liệu hỗ trợ. Nêu một đề xuất cải tiến tiếp theo.

## Phụ lục

- Lệnh đã chạy (theo thứ tự):
- Thử thách mở rộng (nếu có): hướng chọn, kết quả, nhận xét.
- Ghi chú khác:
