import os
from urllib.parse import urljoin

JIRA_BASE_URL = os.getenv("JIRA_URL")

def execute(ctx):
    ctx.log("💬 STEP: POST_JIRA_COMMENT")

    jira = ctx.get("jira")           # ResilientSession
    issue_key = ctx.get("issue_key")
    comment = ctx.get("final_comment")

    if not jira or not issue_key or not comment:
        ctx.log(
            f"ℹ️ Missing jira {jira} / issue_key {issue_key} / final_comment {comment} → skipping"
        )
        return ctx

    try:
        # ✅ API v2 expects STRING body
        url = urljoin(
            JIRA_BASE_URL,
            f"/rest/api/2/issue/{issue_key}/comment"
        )

        payload = {
            "body": comment
        }

        resp = jira.post(url, json=payload)

        if resp.status_code not in (200, 201):
            ctx.log(f"❌ Jira API error {resp.status_code}: {resp.text}")
        else:
            ctx.log("✅ Jira PUBLIC comment posted successfully")

    except Exception as e:
        ctx.log(f"❌ Failed to post Jira comment → {e}")

    return ctx
