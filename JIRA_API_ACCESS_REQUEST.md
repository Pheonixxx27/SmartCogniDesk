# JIRA API Access Request - SupportTicketResolver Bot

## Overview
The SupportTicketResolver project is an automated bot system that processes JIRA tickets using AI/LLM analysis. It requires programmatic access to the JIRA API to function.

## Current Status
- ❌ **BLOCKED** - HTTP 403 Forbidden with `CAPTCHA_CHALLENGE` header
- ℹ️ **Previous Status** - Working fine 1 month ago
- 📅 **Issue Date** - March 29, 2026

## Technical Requirements

### Authentication Method
- **Type:** Basic Authentication with API Token
- **Email:** `vishant.singh@falabella.cl`
- **Token Name:** `vishant_ai_token` (or similar)
- **JIRA URL:** `https://jira.falabella.tech`

### API Endpoints Used
```
- GET /rest/api/2/serverInfo (test connection)
- GET /rest/api/2/issue/{TICKET_KEY} (fetch ticket details)
- POST /rest/api/2/issue/{TICKET_KEY}/comment (post comments)
- GET /rest/api/2/search (JQL queries)
- POST /rest/api/2/issue/{TICKET_KEY}/transitions (change status)
```

### Project Details
- **Project Key:** LOGFTC
- **Statuses Accessed:** OPEN, IN_PROGRESS, etc.
- **Fields Required:** description, customfield_34303, customfield_19765, attachment
- **Update Operations:** Adding comments, transitioning issues

## The Problem

```
Error Response:
Status Code: 403
x-authentication-denied-reason: CAPTCHA_CHALLENGE
Response: "Basic Authentication Failure - AUTHENTICATION_DENIED"
```

**Why This Matters:**
- The API call is being blocked regardless of token validity
- This is a **server-side security policy** affecting all programmatic access
- Manual browser logins work fine, but API clients are blocked
- CAPTCHA challenges require human interaction (impossible for automation)

## Solutions Requested

### Option 1: Disable CAPTCHA for API Access (Recommended)
- Allow Basic Auth with valid API tokens to bypass CAPTCHA
- Most compatible with automation tools

### Option 2: IP Whitelisting
- Whitelist the IP address(es) from which the bot runs
- Current IP: (run `curl ifconfig.me` to check)

### Option 3: Service Account
- Create a dedicated service account for automation
- Better for production use cases
- Separates human user access from automated access

## Impact Without Fix
- ❌ Automated ticket processing cannot run
- ❌ AI-driven ticket analysis disabled
- ❌ SLA management automation blocked
- ❌ Reporting and dashboard updates halted

## Timeline
- ✅ Was working: March 2026 (1 month ago)
- ❌ Started failing: March 29, 2026
- Request: Enable programmatic access immediately

## Contact Information
- **User:** Vishant Singh
- **Email:** vishant.singh@falabella.cl
- **System:** SupportTicketResolver (AI-powered JIRA automation bot)
- **Urgency:** HIGH - Blocking automation pipeline

---

**Please enable one of the three solutions above to restore API access.**

Thank you!
