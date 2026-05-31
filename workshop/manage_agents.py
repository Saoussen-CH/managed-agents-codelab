"""Utilities for listing, inspecting, and deleting saved managed agents."""
import sys
from google import genai

client = genai.Client()


def list_agents() -> None:
    agents = client.agents.list()
    items = agents.agents or []
    if not items:
        print("No saved agents found.")
        return
    for a in items:
        print(f"{a.id}: {a.description or '(no description)'}")


def get_agent(agent_id: str) -> None:
    agent = client.agents.get(id=agent_id)
    print(agent)


def delete_agent(agent_id: str) -> None:
    client.agents.delete(id=agent_id)
    print(f"Deleted: {agent_id}")


USAGE = """\
Usage:
  uv run manage_agents.py list
  uv run manage_agents.py get <agent_id>
  uv run manage_agents.py delete <agent_id>
"""

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] == "list":
        list_agents()
    elif args[0] == "get" and len(args) == 2:
        get_agent(args[1])
    elif args[0] == "delete" and len(args) == 2:
        delete_agent(args[1])
    else:
        print(USAGE)
        sys.exit(1)
