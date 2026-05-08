"""Demo client: spawn the MCP server as a subprocess, list tools, exercise each.

Mirrors what an LLM-agent client (Claude Desktop, the MCP inspector, a custom
agent) does when wiring up to the server. Useful as a smoke test and as a
template for the alert-triage and IR copilot agents.
"""
from __future__ import annotations

import asyncio
import json
import sys

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def _call(session: ClientSession, name: str, args: dict) -> dict:
    result = await session.call_tool(name, args)
    content = result.content[0].text if result.content else "{}"
    return json.loads(content)


async def main() -> None:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_security_tooling.server"],
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools_resp = await session.list_tools()
            print("Tools available:")
            for t in tools_resp.tools:
                desc = (t.description or "").splitlines()[0] if t.description else "(no description)"
                print(f"  - {t.name}: {desc}")
            print()

            # search_events: 3 sample queries
            print("== search_events ==")
            for query, limit in (("", 3), ("mitre_technique=T1059.001", 5),
                                  ("host=finance03 severity=high", 5)):
                print(f"-> search_events(query={query!r}, limit={limit})")
                parsed = await _call(session, "search_events",
                                     {"query": query, "limit": limit})
                print(f"   matched={parsed['matched']}, returned={len(parsed['events'])}")
                for ev in parsed["events"]:
                    print(f"   - {ev['id']} {ev['timestamp']} {ev['host']:<14} "
                          f"sev={ev.get('severity', '?')}")
            print()

            # search_alerts
            print("== search_alerts ==")
            for query in ("host=finance03", "verdict=needs_investigation"):
                print(f"-> search_alerts(query={query!r})")
                parsed = await _call(session, "search_alerts",
                                     {"query": query, "limit": 5})
                print(f"   matched={parsed['matched']}")
                for a in parsed["alerts"]:
                    print(f"   - {a['alert_id']} {a['name']} (verdict={a['verdict']})")
            print()

            # get_alert: known + unknown
            print("== get_alert ==")
            for aid in ("HIST-002", "HIST-9999-not-real"):
                parsed = await _call(session, "get_alert", {"alert_id": aid})
                if parsed.get("found", True):
                    print(f"   {aid}: {parsed.get('name', '?')} "
                          f"(severity={parsed.get('severity', '?')})")
                else:
                    print(f"   {aid}: not found")
            print()

            # list_hosts
            print("== list_hosts ==")
            for query in ("criticality=critical", "department=finance"):
                print(f"-> list_hosts(query={query!r})")
                parsed = await _call(session, "list_hosts",
                                     {"query": query, "limit": 5})
                print(f"   matched={parsed['matched']}")
                for h in parsed["hosts"]:
                    print(f"   - {h['hostname']:<16} {h['ip']:<16} "
                          f"crit={h['criticality']}, owner={h['owner']}")
            print()

            # enrich_indicator: known malicious + unknown
            print("== enrich_indicator ==")
            for ind in ("malicious.example.invalid", "198.51.100.7", "8.8.8.8"):
                parsed = await _call(session, "enrich_indicator", {"indicator": ind})
                print(f"   {ind}: known={parsed['known']}, "
                      f"rep={parsed['reputation']}, tags={parsed.get('tags', [])}")


if __name__ == "__main__":
    asyncio.run(main())
