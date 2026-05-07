"""Demo client: spawn the MCP server as a subprocess, list tools, call search_events.

Mirrors what an LLM-agent client (Claude Desktop, the MCP inspector, a custom
agent) does when wiring up to the server. Useful as a smoke test and as a
template for the alert-triage agent in the next project.
"""
from __future__ import annotations

import asyncio
import json
import sys

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


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

            queries = (
                ("", 3),
                ("mitre_technique=T1059.001", 5),
                ("host=finance03 severity=high", 5),
            )
            for query, limit in queries:
                print(f"-> search_events(query={query!r}, limit={limit})")
                result = await session.call_tool(
                    "search_events",
                    {"query": query, "limit": limit},
                )
                content = result.content[0].text if result.content else "{}"
                parsed = json.loads(content)
                print(f"   matched={parsed['matched']}, returned={len(parsed['events'])}")
                for ev in parsed["events"]:
                    print(
                        f"   - {ev['id']} {ev['timestamp']} "
                        f"{ev['host']:<14} {ev.get('process.name', '?'):<18} "
                        f"sev={ev.get('severity', '?')}"
                    )
                print()


if __name__ == "__main__":
    asyncio.run(main())
