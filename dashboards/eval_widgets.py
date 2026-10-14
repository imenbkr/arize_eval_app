"""Configure the per-model eval widgets on an Arize AX dashboard (GraphQL API).

Arize charts reference attributes by internal dimension ids, which the API
cannot look up for custom span attributes. So this script starts from a bar
chart created once in the UI (attribute `attributes.metadata.model`, one filter
on the eval label), reads its dimension ids, and rewrites it as a stacked,
normalised pass/fail chart per model:

    python dashboards/eval_widgets.py --dashboard "RAG Eval - LLM Overview (rag-eval-experiments)"
"""
import argparse

from arize_dashboard import gql, space_items

# widget title -> (eval label attribute, passing value, failing value)
EVAL_WIDGETS = {
    "Hallucination by model": ("hallucination", "factual", "hallucinated"),
    "Correctness by model": ("correctness", "correct", "incorrect"),
}
PASS_COLOR, FAIL_COLOR = "#4C9A6A", "#D1495B"


def widgets(dashboard_id):
    data = gql("""query($id: ID!) { node(id: $id) { ... on Dashboard {
        barChartWidgets(first: 20) { edges { node { id title gridPosition
          plots { modelEnvironmentName dimensionCategory model { id }
            dimension { id name dataType category }
            filters { filterType operator dimension { id name dataType category } } } } } } } } }""",
        {"id": dashboard_id})
    return {e["node"]["title"]: e["node"] for e in data["node"]["barChartWidgets"]["edges"]}


def value_ids(model_id, dim):
    data = gql("""query($id: ID!, $dim: DimensionInput) { node(id: $id) { ... on Model {
        dimensionValues(first: 20, dimension: $dim, modelEnvironmentName: tracing, filterType: spanProperty) {
          edges { node { id value } } } } } }""",
        {"id": model_id, "dim": dim})
    return {e["node"]["value"]: e["node"]["id"] for e in data["node"]["dimensionValues"]["edges"]}


def dim_input(d):
    return {"id": d["id"], "name": d["name"], "dataType": d["dataType"], "category": "spanProperty"}


def plot(base, label_dim, value, value_id, title, position, color):
    return {
        "title": title,
        "position": position,
        "modelId": base["model"]["id"],
        "modelVersionIds": [],
        "modelEnvironmentName": "tracing",
        "dimensionCategory": "spanProperty",
        "dimension": dim_input(base["dimension"]),
        "colors": [color],
        "filters": [{
            "filterType": "spanProperty",
            "operator": "equals",
            "dimension": dim_input(label_dim),
            "dimensionValues": [{"id": value_id, "value": value}],
        }],
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dashboard", default="RAG Eval - LLM Overview (rag-eval-experiments)")
    args = p.parse_args()

    _, dashboards = space_items()
    dashboard_id = dashboards[args.dashboard]
    existing = widgets(dashboard_id)
    for title, (label, ok, bad) in EVAL_WIDGETS.items():
        if title not in existing:
            print(f"Skipped '{title}': create it once in the UI first (see module docstring)")
            continue
        w = existing[title]
        base = w["plots"][0]
        label_dim = base["filters"][0]["dimension"]
        assert label_dim["name"] == f"attributes.metadata.{label}", label_dim["name"]
        ids = value_ids(base["model"]["id"], dim_input(label_dim))
        gql("""mutation($input: UpdateBarChartWidgetMutationInput!) {
            updateBarChartWidget(input: $input) { clientMutationId } }""",
            {"input": {"id": w["id"], "dashboardId": dashboard_id, "updateData": {
                "title": title,
                "creationStatus": "published",
                "gridPosition": w["gridPosition"],
                "xAxisLabel": "model",
                "yAxisLabel": "share of eval cases",
                "isStacked": True,
                "isNormalized": True,
                "showLegend": True,
                "timeRangeKey": "7d",
                "plots": [
                    plot(base, label_dim, ok, ids[ok], ok, 0, PASS_COLOR),
                    plot(base, label_dim, bad, ids[bad], bad, 1, FAIL_COLOR),
                ],
            }}})
        print(f"Updated '{title}': {ok} / {bad}, stacked and normalised by model")


if __name__ == "__main__":
    main()
