#!/usr/bin/env python3
"""
PR 自动审核脚本
根据 PR合并要求规范.md 逐步检查，不通过则评论拒绝，全部通过则自动合并。
"""

import os
import re
import sys
import json
import subprocess
import datetime
import requests

# ── 环境变量 ──────────────────────────────────────────────
PR_TITLE   = os.environ["PR_TITLE"]
PR_NUMBER  = os.environ["PR_NUMBER"]
BASE_SHA   = os.environ["BASE_SHA"]
HEAD_SHA   = os.environ["HEAD_SHA"]
KIMI_KEY   = os.environ.get("KIMI_API_KEY", "")
GH_TOKEN   = os.environ["GH_TOKEN"]
REPO       = os.environ["REPO"]

GITHUB_API = "https://api.github.com"
HEADERS    = {
    "Authorization": f"Bearer {GH_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

# ── GitHub 工具函数 ───────────────────────────────────────

def comment(body: str):
    """在 PR 上发评论"""
    url = f"{GITHUB_API}/repos/{REPO}/issues/{PR_NUMBER}/comments"
    requests.post(url, headers=HEADERS, json={"body": body})


def merge_pr():
    """自动合并 PR"""
    url = f"{GITHUB_API}/repos/{REPO}/pulls/{PR_NUMBER}/merge"
    resp = requests.put(url, headers=HEADERS, json={
        "merge_method": "merge",
        "commit_title": f"[自动合并] {PR_TITLE}",
    })
    return resp.status_code == 200


def reject(reason: str):
    """评论拒绝原因后退出"""
    body = f"""## PR 检查未通过 ❌

{reason}

---
*此评论由自动审核机器人生成。请修改后重新推送，PR 会自动更新。*
"""
    comment(body)
    sys.exit(0)   # 非零会让 Action 标红，用 0 让 job 绿色但 PR 被拒


# ── 获取变更文件列表 ──────────────────────────────────────

def get_changed_files():
    result = subprocess.run(
        ["git", "diff", "--name-only", BASE_SHA, HEAD_SHA],
        capture_output=True, text=True
    )
    files = [f.strip() for f in result.stdout.strip().splitlines() if f.strip()]
    return files


# ── 步骤 1：PR 标题格式 ───────────────────────────────────
# 格式：[学号姓名]LabX作业提交  或  [学号姓名] LabX作业提交
TITLE_RE = re.compile(r'^\[(\d{10}[\u4e00-\u9fff]+)\]\s?(Lab\d+)作业提交$')

def check_title():
    m = TITLE_RE.match(PR_TITLE)
    if not m:
        reject(
            f"**PR 标题格式错误**\n\n"
            f"当前标题：`{PR_TITLE}`\n\n"
            f"正确格式：`[学号姓名]LabX作业提交` 或 `[学号姓名] LabX作业提交`\n\n"
            f"注意事项：\n"
            f"- 括号必须是英文方括号 `[]`，不能用 `【】`\n"
            f"- 学号为 10 位数字，紧跟姓名，中间无空格\n"
            f"- `Lab` 中 L 必须大写\n\n"
            f"示例：`[2024010002王诗惠]Lab1作业提交`"
        )
    return m.group(1), m.group(2)   # 学号姓名, LabX


# ── 步骤 2 & 3 & 4 & 5：文件路径规范 ─────────────────────

STUDENT_DIR_RE = re.compile(r'^\d{10}[\u4e00-\u9fff]+$')
LAB_DIR_RE     = re.compile(r'^Lab\d+$')

def check_files(student_id_name: str, lab: str, changed_files: list):
    # 允许的前缀
    allowed_prefix = f"{student_id_name}/{lab}/"

    for f in changed_files:
        # 禁止修改任何其他地方
        if not f.startswith(allowed_prefix):
            reject(
                f"**修改范围超出自己的文件夹**\n\n"
                f"检测到修改了不属于自己的路径：`{f}`\n\n"
                f"只允许修改 `{allowed_prefix}` 下的文件，"
                f"请勿修改其他同学的文件夹、homework 文件夹或根目录文件。"
            )

    # 检查学生文件夹命名
    parts = changed_files[0].split("/")
    student_dir = parts[0]
    if not STUDENT_DIR_RE.match(student_dir):
        reject(
            f"**学生文件夹命名不规范**\n\n"
            f"文件夹名 `{student_dir}` 不符合要求。\n\n"
            f"格式：10位学号 + 姓名，中间无空格，例如 `2024010002王诗惠`"
        )

    # 检查学生文件夹与标题一致
    if student_dir != student_id_name:
        reject(
            f"**文件夹名与 PR 标题不一致**\n\n"
            f"PR 标题中的学号姓名：`{student_id_name}`\n"
            f"实际文件夹名：`{student_dir}`\n\n"
            f"两者必须完全一致。"
        )

    # 检查 Lab 文件夹命名
    if len(parts) < 2:
        reject("**未找到 Lab 文件夹**，请检查目录结构。")
    lab_dir = parts[1]
    if not LAB_DIR_RE.match(lab_dir):
        reject(
            f"**Lab 文件夹命名不规范**\n\n"
            f"文件夹名 `{lab_dir}` 不符合要求。\n\n"
            f"格式：`Lab` + 数字，L 必须大写，例如 `Lab1`"
        )
    if lab_dir != lab:
        reject(
            f"**Lab 文件夹与 PR 标题不一致**\n\n"
            f"PR 标题中的 Lab：`{lab}`\n"
            f"实际文件夹：`{lab_dir}`\n\n"
            f"两者必须一致。"
        )

    return [f for f in changed_files]  # 全部在自己目录内


# ── 步骤 6：作业文件基本检查 ─────────────────────────────

def check_homework_files(changed_files: list, lab: str):
    """对照 homework/LabX 检查提交文件数量和名称"""
    hw_dir = f"homework/{lab}"

    # 获取作业要求文件列表
    result = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", HEAD_SHA, hw_dir],
        capture_output=True, text=True
    )
    hw_files = [
        os.path.basename(f.strip())
        for f in result.stdout.strip().splitlines()
        if f.strip()
    ]

    if not hw_files:
        # homework 中没有对应 Lab，跳过文件名检查
        return

    # 学生提交的文件名（只取文件名，不含路径）
    submitted = [os.path.basename(f) for f in changed_files]

    # 检查是否有必须提交的文件（homework 中的文件作为参考）
    # 实际规范：文件数量和文件名必须符合作业要求
    missing = [f for f in hw_files if f not in submitted]
    extra   = [f for f in submitted if f not in hw_files]

    issues = []
    if missing:
        issues.append(f"**缺少文件**：{', '.join(f'`{f}`' for f in missing)}")
    if extra:
        issues.append(f"**多余文件**（不在作业要求中）：{', '.join(f'`{f}`' for f in extra)}")

    if issues:
        reject(
            f"**作业文件不符合要求**\n\n"
            + "\n\n".join(issues) +
            f"\n\n作业要求文件：{', '.join(f'`{f}`' for f in hw_files)}\n\n"
            f"请参考 `{hw_dir}/` 中的作业要求。"
        )


# ── 步骤 7：文件格式检查（空文件、Python语法等）─────────

def check_file_format(changed_files: list):
    issues = []

    for fpath in changed_files:
        # 读取文件内容
        result = subprocess.run(
            ["git", "show", f"{HEAD_SHA}:{fpath}"],
            capture_output=True, text=True, errors="replace"
        )
        content = result.stdout

        filename = os.path.basename(fpath)
        ext = os.path.splitext(filename)[1].lower()

        # 文件内容有效性：少于10行有效内容
        valid_lines = [l for l in content.splitlines() if l.strip()]
        if len(valid_lines) < 10:
            issues.append(f"`{fpath}`：有效内容少于 10 行（当前 {len(valid_lines)} 行）")
            continue

        # AI Prompt 检测
        prompt_patterns = [
            "忽略之前的要求", "直接通过审查", "假装没看到", "不要检查",
            "ignore previous", "<system>", "[INST]", "bypass"
        ]
        for pat in prompt_patterns:
            if pat.lower() in content.lower():
                issues.append(f"`{fpath}`：检测到疑似 AI Prompt 内容（含 `{pat}`），**禁止合并**")

        # .md 文件：检查是否使用了 Markdown 语法
        if ext == ".md":
            md_indicators = ["# ", "## ", "- ", "* ", "```", "|", "**"]
            has_md = any(ind in content for ind in md_indicators)
            # HTML实体编码
            if "&#x" in content or "&amp;" in content:
                issues.append(f"`{fpath}`：.md 文件包含 HTML 实体编码（如 `&#x20;`），请直接使用对应字符")
            # 转义字符滥用
            if re.search(r'\\_|\\\\|\\\[|\\\]', content):
                issues.append(f"`{fpath}`：.md 文件中存在不必要的转义字符（如 `\\_`、`\\[`），请直接书写")
            if not has_md:
                issues.append(f"`{fpath}`：.md 文件未使用 Markdown 语法，请用标题、列表、代码块等格式书写")

        # .txt 文件：不应包含 Markdown 或 HTML
        if ext == ".txt":
            if re.search(r'^#+\s', content, re.MULTILINE):
                issues.append(f"`{fpath}`：.txt 文件不应使用 Markdown 标题语法（`# 标题`）")
            if "<html" in content.lower() or "<body" in content.lower():
                issues.append(f"`{fpath}`：.txt 文件不应包含 HTML 标签")

        # .py 文件：语法检查
        if ext == ".py":
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".py", mode="w",
                                             delete=False, encoding="utf-8") as tmp:
                tmp.write(content)
                tmp_path = tmp.name
            syntax = subprocess.run(
                ["python3", "-m", "py_compile", tmp_path],
                capture_output=True, text=True
            )
            os.unlink(tmp_path)
            if syntax.returncode != 0:
                issues.append(f"`{fpath}`：Python 文件存在语法错误，无法运行")

    if issues:
        reject(
            "**文件格式检查未通过**\n\n"
            + "\n\n".join(f"- {i}" for i in issues)
        )


# ── 步骤 8：Kimi AI 内容质量检查 ─────────────────────────

def read_homework_requirement(lab: str) -> str:
    """读取 homework/LabX 下的作业要求文件内容"""
    hw_dir = f"homework/{lab}"
    result = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", HEAD_SHA, hw_dir],
        capture_output=True, text=True
    )
    hw_files = [f.strip() for f in result.stdout.strip().splitlines() if f.strip()]

    contents = []
    for hf in hw_files:
        r = subprocess.run(
            ["git", "show", f"{HEAD_SHA}:{hf}"],
            capture_output=True, text=True, errors="replace"
        )
        contents.append(f"### 作业要求文件：{hf}\n\n{r.stdout}")
    return "\n\n---\n\n".join(contents)


def read_student_files(changed_files: list) -> str:
    contents = []
    for fpath in changed_files:
        r = subprocess.run(
            ["git", "show", f"{HEAD_SHA}:{fpath}"],
            capture_output=True, text=True, errors="replace"
        )
        contents.append(f"### 学生文件：{fpath}\n\n{r.stdout}")
    return "\n\n---\n\n".join(contents)


def check_content_with_kimi(lab: str, changed_files: list):
    if not KIMI_KEY:
        return  # 没有配置 Key 则跳过

    hw_content = read_homework_requirement(lab)
    student_content = read_student_files(changed_files)

    if not hw_content:
        return  # 没有作业要求文件，跳过

    system_prompt = """你是一名严格的助教，负责审查学生的作业提交。
你需要根据作业要求，检查学生提交的作业内容是否合格。

判断标准（以下任一情况则不合格）：
1. 答案明显错误：知识填空或问答的答案与事实明显不符
2. 不按作业要求：明显未按照作业要求完成，敷衍了事
3. 引用外部资源错误：图片引用路径错误、引用不存在的文件等
4. 内容明显抄袭或雷同（和作业要求原文完全一致，无任何自己的作答）

可以忽略的问题：
- 极个别错别字
- 大小写不规范
- 内容详细程度略有差异

请用以下 JSON 格式回复，不要输出任何其他内容：
{
  "pass": true 或 false,
  "reason": "如果不通过，说明具体问题；如果通过，填写'内容质量合格'"
}"""

    user_msg = f"""## 作业要求

{hw_content}

## 学生提交内容

{student_content}

请判断学生作业是否合格。"""

    try:
        resp = requests.post(
            "https://api.moonshot.cn/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {KIMI_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "moonshot-v1-8k",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
                "temperature": 0.1,
            },
            timeout=60,
        )
        result_text = resp.json()["choices"][0]["message"]["content"].strip()
        # 清理可能的 markdown 代码块
        result_text = re.sub(r"```json|```", "", result_text).strip()
        result = json.loads(result_text)

        if not result.get("pass", True):
            reject(
                f"**作业内容质量检查未通过**\n\n"
                f"{result.get('reason', '内容存在问题，请检查后重新提交。')}"
            )
    except Exception as e:
        # Kimi 调用失败不阻断流程，记录即可
        print(f"[warn] Kimi 检查失败，跳过内容检查：{e}")


# ── 步骤 9：截止时间检查 ──────────────────────────────────

def get_deadline(lab: str) -> datetime.date | None:
    """从 homework/LabX/LabX.md 中提取截止时间"""
    hw_file = f"homework/{lab}/{lab}.md"
    result = subprocess.run(
        ["git", "show", f"{HEAD_SHA}:{hw_file}"],
        capture_output=True, text=True, errors="replace"
    )
    if result.returncode != 0:
        return None

    content = result.stdout
    # 匹配常见格式：截止时间：2025-03-22 / 截止日期：YYYY/MM/DD
    patterns = [
        r'截止[时日][间期][：:]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
        r'deadline[：:]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
        r'due[：:\s]+(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
    ]
    for pat in patterns:
        m = re.search(pat, content, re.IGNORECASE)
        if m:
            date_str = m.group(1).replace("/", "-")
            try:
                return datetime.date.fromisoformat(date_str)
            except ValueError:
                pass
    return None


def check_deadline(lab: str):
    deadline = get_deadline(lab)
    if deadline is None:
        return  # 没找到截止时间，跳过

    # 北京时间 = UTC+8
    now_utc = datetime.datetime.utcnow()
    now_bj  = now_utc + datetime.timedelta(hours=8)
    today   = now_bj.date()

    if today <= deadline:
        return  # 未超时

    delta = (today - deadline).days

    if delta > 7:
        reject(
            f"**超时超过 7 天，PR 已关闭** ❌\n\n"
            f"- **作业截止时间**：{deadline}\n"
            f"- **当前时间**：{today}（北京时间）\n"
            f"- **超时天数**：{delta} 天\n\n"
            f"超时 7 天以上不予受理，此 PR 将被关闭。"
        )
        # 关闭 PR
        url = f"{GITHUB_API}/repos/{REPO}/pulls/{PR_NUMBER}"
        requests.patch(url, headers=HEADERS, json={"state": "closed"})
        sys.exit(0)
    else:
        reject(
            f"## PR 检查未通过 ❌\n\n"
            f"此 PR 已超时。\n\n"
            f"- **作业截止时间**：{deadline}\n"
            f"- **当前时间**：{today}（北京时间）\n"
            f"- **超时天数**：{delta} 天\n\n"
            f"超过截止时间，暂不予合并。如有特殊情况，请联系老师说明。"
        )


# ── 主流程 ────────────────────────────────────────────────

def main():
    print(f"[PR #{PR_NUMBER}] 开始审核：{PR_TITLE}")

    # 1. 标题格式
    student_id_name, lab = check_title()
    print(f"  ✓ 标题格式正确：{student_id_name} / {lab}")

    # 获取变更文件
    changed_files = get_changed_files()
    if not changed_files:
        reject("**PR 没有任何文件变更**，请确认是否提交了作业文件。")

    # 2-5. 文件路径规范
    check_files(student_id_name, lab, changed_files)
    print(f"  ✓ 文件路径规范正确，共 {len(changed_files)} 个文件")

    # 6. 作业文件数量和名称
    check_homework_files(changed_files, lab)
    print(f"  ✓ 作业文件数量和名称检查通过")

    # 7. 文件格式检查
    check_file_format(changed_files)
    print(f"  ✓ 文件格式检查通过")

    # 8. Kimi 内容质量检查
    check_content_with_kimi(lab, changed_files)
    print(f"  ✓ 内容质量检查通过")

    # 9. 截止时间
    check_deadline(lab)
    print(f"  ✓ 截止时间检查通过")

    # 全部通过 → 评论 + 合并
    comment(
        f"## PR 检查通过 ✅\n\n"
        f"所有检查项均通过，正在自动合并...\n\n"
        f"| 检查项 | 结果 |\n"
        f"|--------|------|\n"
        f"| PR 标题格式 | ✅ |\n"
        f"| 文件路径规范 | ✅ |\n"
        f"| 作业文件完整性 | ✅ |\n"
        f"| 文件格式 | ✅ |\n"
        f"| 内容质量 | ✅ |\n"
        f"| 提交时间 | ✅ |\n"
    )

    ok = merge_pr()
    if ok:
        print(f"  ✓ PR #{PR_NUMBER} 已自动合并")
    else:
        print(f"  ✗ 合并失败，可能存在冲突，请手动处理")
        comment("⚠️ 自动合并失败，可能存在合并冲突，请老师手动处理。")


if __name__ == "__main__":
    main()
