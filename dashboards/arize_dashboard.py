"""Dashboards as code for Arize AX (GraphQL API).

Creates an LLM-overview dashboard from Arize's generativeLlmModelV2 template
for a tracing project, unless a dashboard with the same name already exists.

    python dashboards/arize_dashboard.py --project arize-eval-demo
    python dashboards/arize_dashboard.py --project rag-eval-experiments --delete

Needs ARIZE_SPACE_ID and ARIZE_API_KEY (from .env or the environment).
"""
import argparse
import json
import os
import urllib.request

from dotenv import load_dotenv

load_dotenv()
API = "https://app.arize.com/graphql"
SPACE = os.environ["ARIZE_SPACE_ID"]


def gql(query, variables=None):
    req = urllib.request.Request(
        API,
        data=json.dumps({"query": query, "variables": variables or {}}).encode(),
        headers={"x-api-key": os.environ["ARIZE_API_KEY"], "Content-Type": "application/json"},
    )
    try:
        body = json.load(urllib.request.urlopen(req, timeout=60))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode()[:800]}") from None
    if body.get("errors"):
        raise RuntimeError(body["errors"])
    return body["data"]


def space_items():
    data = gql("""query($id: ID!) { node(id: $id) { ... on Space {
        models(first: 50) { edges { node { id name } } }
        dashboards(first: 50) { edges { node { id name } } } } } }""", {"id": SPACE})["node"]
    models = {e["node"]["name"]: e["node"]["id"] for e in data["models"]["edges"]}
    dashboards = {e["node"]["name"]: e["node"]["id"] for e in data["dashboards"]["edges"]}
    return models, dashboards


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--project", default=os.environ.get("ARIZE_PROJECT", "rag-eval-experiments"))
    p.add_argument("--name", default=None)
    p.add_argument("--delete", action="store_true", help="delete the dashboard instead")
    args = p.parse_args()
    name = args.name or f"RAG Eval - LLM Overview ({args.project})"

    models, dashboards = space_items()
    if args.delete:
        if name not in dashboards:
            print(f"Nothing to delete: '{name}' not found")
            return
        gql("""mutation($input: UpdateDashboardStatusMutationInput!) {
            updateDashboardStatus(input: $input) { clientMutationId } }""",
            {"input": {"dashboardId": dashboards[name], "status": "deleted"}})
        print(f"Deleted '{name}'")
        return
    if name in dashboards:
        print(f"Already exists: '{name}' ({dashboards[name]})")
        return
    if args.project not in models:
        raise SystemExit(f"Project '{args.project}' not found in the space; send traces to it first.")
    d = gql("""mutation($input: CreateDashboardFromTemplateMutationInput!) {
        createDashboardFromTemplate(input: $input) { dashboard { id name } } }""",
        {"input": {"name": name, "modelId": models[args.project],
                   "modelEnvironmentName": "tracing", "template": "generativeLlmModelV2"}})
    print(f"Created '{name}' ({d['createDashboardFromTemplate']['dashboard']['id']})")


if __name__ == "__main__":
    main()
