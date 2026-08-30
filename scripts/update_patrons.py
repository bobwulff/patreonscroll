#!/usr/bin/env python3
"""
Pulls the current active patron list from the Patreon API (v2) and writes
it out as patrons.csv in the same "Name,Tier" shape as a manual Patreon
export, so index.html doesn't need to change at all.

Required environment variables (set these as GitHub Actions secrets):
  PATREON_CLIENT_ID       - from your Patreon API client
  PATREON_CLIENT_SECRET   - from your Patreon API client
  PATREON_REFRESH_TOKEN   - your creator's refresh token

Optional:
  PATREON_CAMPAIGN_ID     - only needed if your Patreon account runs more
                            than one campaign; otherwise the script finds
                            your one campaign automatically.
"""

import csv
import os
import sys
import requests

TOKEN_URL = "https://www.patreon.com/api/oauth2/token"
API_BASE = "https://www.patreon.com/api/oauth2/v2"


def get_access_token():
    client_id = os.environ["PATREON_CLIENT_ID"]
    client_secret = os.environ["PATREON_CLIENT_SECRET"]
    refresh_token = os.environ["PATREON_REFRESH_TOKEN"]

    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=30,
    )
    if not resp.ok:
        # Patreon includes a specific reason (invalid_client, invalid_grant,
        # etc.) in the response body that requests' default error message
        # doesn't show. Print it so failures are actually diagnosable.
        print(f"::error::Patreon token refresh failed ({resp.status_code}): {resp.text}", file=sys.stderr)
    resp.raise_for_status()
    data = resp.json()

    new_refresh_token = data.get("refresh_token")
    if new_refresh_token and new_refresh_token != refresh_token:
        # Patreon can rotate refresh tokens on use. If that happens, the
        # secret stored in GitHub is now stale and the *next* run will fail
        # unless it's updated. We can't silently fix the secret from here
        # without extra setup (see README), so surface it loudly instead of
        # failing mysteriously in a future run.
        print(
            "::warning::Patreon issued a new refresh_token. Update the "
            "PATREON_REFRESH_TOKEN GitHub secret to the value printed "
            "below (only visible in this log to you as the repo owner) "
            "or future runs will start failing.",
            file=sys.stderr,
        )
        print(f"NEW_REFRESH_TOKEN={new_refresh_token}", file=sys.stderr)

    return data["access_token"]


def get_campaign_id(access_token):
    forced = os.environ.get("PATREON_CAMPAIGN_ID")
    if forced:
        return forced

    resp = requests.get(
        f"{API_BASE}/campaigns",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()["data"]
    if not data:
        raise RuntimeError("No campaigns found for this creator token.")
    if len(data) > 1:
        ids = ", ".join(c["id"] for c in data)
        raise RuntimeError(
            f"Multiple campaigns found ({ids}). Set PATREON_CAMPAIGN_ID "
            "to the one you want."
        )
    return data[0]["id"]


def get_active_members(access_token, campaign_id):
    """Yields (name, tier_title) for every currently active patron."""
    url = f"{API_BASE}/campaigns/{campaign_id}/members"
    params = {
        "include": "currently_entitled_tiers,user",
        "fields[member]": "full_name,patron_status",
        "fields[tier]": "title",
        "fields[user]": "full_name",
        "page[count]": 200,
    }

    while url:
        resp = requests.get(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
            params=params,
            timeout=30,
        )
        resp.raise_for_status()
        payload = resp.json()

        # Build a quick lookup of included tier resources by id -> title
        tiers_by_id = {
            item["id"]: item["attributes"].get("title", "")
            for item in payload.get("included", [])
            if item["type"] == "tier"
        }

        for member in payload.get("data", []):
            attrs = member["attributes"]
            if attrs.get("patron_status") != "active_patron":
                continue

            name = attrs.get("full_name", "").strip()
            if not name:
                continue

            tier_refs = (
                member.get("relationships", {})
                .get("currently_entitled_tiers", {})
                .get("data", [])
            )
            for ref in tier_refs:
                tier_title = tiers_by_id.get(ref["id"])
                if tier_title:
                    yield name, tier_title

        # Follow pagination if there's another page
        url = payload.get("links", {}).get("next")
        params = None  # the "next" link already has query params baked in


def main():
    access_token = get_access_token()
    campaign_id = get_campaign_id(access_token)
    members = list(get_active_members(access_token, campaign_id))

    out_path = os.path.join(os.path.dirname(__file__), "..", "patrons.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "Tier"])
        writer.writerows(members)

    print(f"Wrote {len(members)} active patron rows to {out_path}")


if __name__ == "__main__":
    main()
