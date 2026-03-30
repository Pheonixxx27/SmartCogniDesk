#!/usr/bin/env python3
"""
Test Script: Check JIRA Issue Connection
Purpose: Verify JIRA connectivity and fetch issue details without running the full bot
Usage: python test_jira_issue.py [ISSUE_KEY]
Example: python test_jira_issue.py LOGFTC-42101
"""

import os
import sys
from jira import JIRA
from dotenv import load_dotenv
import json

load_dotenv()

JIRA_URL = os.getenv("JIRA_URL")
JIRA_TOKEN = os.getenv("JIRA_TOKEN")
JIRA_USERNAME = os.getenv("JIRA_USERNAME")

def test_connection():
    """Test basic JIRA connection"""
    print("🔍 Testing JIRA connection...")
    try:
        jira = JIRA(
            server=JIRA_URL,
            basic_auth=(JIRA_USERNAME, JIRA_TOKEN)
        )
        print("✅ Successfully connected to JIRA")
        return jira
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return None

def fetch_issue(jira, issue_key):
    """Fetch and display issue details"""
    print(f"\n🔍 Fetching issue: {issue_key}...")
    
    try:
        fields = [
            "key",
            "status",
            "summary",
            "description",
            "customfield_34303",  # Tier 2
            "customfield_19765",  # Data Detail
            "attachment",
            "created",
            "updated",
        ]
        
        issue = jira.issue(issue_key, fields=fields)
        
        print(f"\n✅ Issue Found!")
        print(f"   Key: {issue.key}")
        print(f"   Status: {issue.fields.status}")
        print(f"   Summary: {issue.fields.summary}")
        print(f"   Created: {issue.fields.created}")
        print(f"   Updated: {issue.fields.updated}")
        
        # Description
        if issue.fields.description:
            desc = issue.fields.description[:200]
            print(f"   Description: {desc}...")
        else:
            print(f"   Description: (empty)")
        
        # Tier 2
        tier2 = issue.raw["fields"].get("customfield_34303")
        if tier2:
            if isinstance(tier2, list) and tier2:
                tier2 = tier2[0]
            if isinstance(tier2, dict):
                tier2_val = tier2.get("value") or tier2.get("name")
            else:
                tier2_val = tier2
            print(f"   Tier 2 (customfield_34303): {tier2_val}")
        else:
            print(f"   Tier 2 (customfield_34303): (empty)")
        
        # Data Detail
        detail = issue.raw["fields"].get("customfield_19765")
        if detail:
            detail_str = str(detail)[:200]
            print(f"   Data Detail (customfield_19765): {detail_str}")
        else:
            print(f"   Data Detail (customfield_19765): (empty)")
        
        # Attachments
        attachments = issue.raw["fields"].get("attachment", [])
        print(f"   Attachments: {len(attachments)} file(s)")
        for att in attachments:
            print(f"      - {att.get('filename')} ({att.get('size')} bytes)")
        
        return issue
    
    except Exception as e:
        print(f"❌ Error fetching issue: {e}")
        return None

def list_queue():
    """List all tickets in queue"""
    print("\n🔍 Fetching JIRA queue...")
    
    try:
        jira = JIRA(
            server=JIRA_URL,
            basic_auth=(JIRA_USERNAME, JIRA_TOKEN)
        )
        
        JQL = """
        project = LOGFTC
        AND status NOT IN (CANCELED, REJECTED, CLOSED, COMPLETED, RESOLVED)
        AND "Resolution Group" = "ITSM - LOOR-FOO"
        """
        
        fields = [
            "key",
            "status",
            "summary",
            "customfield_34303",  # Tier 2
        ]
        
        issues = jira.search_issues(JQL, fields=fields, maxResults=20)
        
        print(f"\n✅ Found {len(issues)} ticket(s) in queue:\n")
        
        for issue in issues:
            tier2 = issue.raw["fields"].get("customfield_34303")
            if tier2:
                if isinstance(tier2, list) and tier2:
                    tier2 = tier2[0]
                if isinstance(tier2, dict):
                    tier2_val = tier2.get("value") or tier2.get("name")
                else:
                    tier2_val = tier2
            else:
                tier2_val = "(empty)"
            
            print(f"   {issue.key:15} | Status: {str(issue.fields.status):15} | Tier2: {tier2_val:20} | {issue.fields.summary[:40]}")
        
    except Exception as e:
        print(f"❌ Error fetching queue: {e}")

def main():
    """Main function"""
    print("=" * 80)
    print("JIRA Issue Checker - Test Script")
    print("=" * 80)
    
    # Verify credentials
    if not JIRA_URL or not JIRA_TOKEN or not JIRA_USERNAME:
        print("❌ Missing JIRA credentials in .env file")
        print("   Required: JIRA_URL, JIRA_USERNAME, JIRA_TOKEN")
        return
    
    print(f"   JIRA_URL: {JIRA_URL}")
    print(f"   JIRA_USERNAME: {JIRA_USERNAME}")
    print()
    
    # Test connection
    jira = test_connection()
    if not jira:
        return
    
    # If issue key provided as argument
    if len(sys.argv) > 1:
        issue_key = sys.argv[1].upper()
        fetch_issue(jira, issue_key)
    else:
        # Otherwise show queue
        list_queue()
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
