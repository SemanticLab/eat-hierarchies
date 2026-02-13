#!/usr/bin/env python3
"""
Enrich hierarchy.json instance entries with additional Wikibase properties:
  - used in (P194)
  - IEEE Term (P206)
  - skos:exactMatch (P54)
  - thumbnail URL (P3)

Reads hierarchy.json, queries the SPARQL endpoint in batches,
and writes enriched_hierarchy.json.
"""

import json
import os
import sys
import urllib.parse
import urllib.request
import time

SPARQL_ENDPOINT = "https://query.semlab.io/proxy/wdqs/bigdata/namespace/wdq/sparql"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")
INPUT_FILE = os.path.join(DATA_DIR, "hierarchy.json")
OUTPUT_FILE = os.path.join(DATA_DIR, "enriched_hierarchy.json")
BATCH_SIZE = 40

HEADERS = {
    "Accept": "application/sparql-results+json",
    "User-Agent": "Mozilla/5.0 (HierarchyBuilder/1.0)",
}


def sparql_query(query: str) -> dict:
    """Execute a SPARQL query and return parsed JSON results."""
    encoded = urllib.parse.urlencode({"query": query})
    url = f"{SPARQL_ENDPOINT}?{encoded}"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def extract_qid(uri: str) -> str:
    """Extract Q-ID from a Wikibase entity URI."""
    return uri.rsplit("/", 1)[-1]


def collect_all_ids(node: dict) -> set:
    """Recursively collect all Q-IDs (instances and subclasses) from the hierarchy."""
    ids = set()
    ids.add(node["id"])
    for inst in node.get("instances", []):
        ids |= collect_all_ids(inst)
    for sc in node.get("subclasses", []):
        ids |= collect_all_ids(sc)
    return ids


def fetch_enrichments(qids: list[str]) -> dict:
    """
    Query P194, P206, P54, P3 for a batch of Q-IDs.
    Returns a dict: qid -> {used_in: [...], ieee_term: [...], exact_match: [...], thumbnail: [...]}
    """
    values = " ".join(f"wd:{q}" for q in qids)
    query = f"""SELECT ?item ?desc ?usedIn ?usedInLabel ?ieee ?exact ?thumb WHERE {{
      VALUES ?item {{ {values} }}
      OPTIONAL {{ ?item schema:description ?desc . FILTER(LANG(?desc) = "en") }}
      OPTIONAL {{ ?item wdt:P194 ?usedIn . }}
      OPTIONAL {{ ?item wdt:P206 ?ieee . }}
      OPTIONAL {{ ?item wdt:P54 ?exact . }}
      OPTIONAL {{ ?item wdt:P3 ?thumb . }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}"""

    data = sparql_query(query)
    result = {}

    for b in data["results"]["bindings"]:
        qid = extract_qid(b["item"]["value"])
        if qid not in result:
            result[qid] = {
                "description": None,
                "used_in": [],
                "ieee_term": [],
                "exact_match": [],
                "thumbnail": [],
            }
        rec = result[qid]

        if "desc" in b and rec["description"] is None:
            rec["description"] = b["desc"]["value"]

        if "usedIn" in b:
            entry = {
                "id": extract_qid(b["usedIn"]["value"]),
                "label": b.get("usedInLabel", {}).get("value", ""),
            }
            if entry not in rec["used_in"]:
                rec["used_in"].append(entry)

        if "ieee" in b:
            val = b["ieee"]["value"]
            if val not in rec["ieee_term"]:
                rec["ieee_term"].append(val)

        if "exact" in b:
            val = b["exact"]["value"]
            if val not in rec["exact_match"]:
                rec["exact_match"].append(val)

        if "thumb" in b:
            val = b["thumb"]["value"]
            if val not in rec["thumbnail"]:
                rec["thumbnail"].append(val)

    return result


def apply_enrichments(node: dict, enrichments: dict):
    """Recursively apply enrichment data to all entries in the hierarchy."""
    qid = node["id"]
    if qid in enrichments:
        for key, values in enrichments[qid].items():
            if values:
                node[key] = values
    for inst in node.get("instances", []):
        apply_enrichments(inst, enrichments)
    for sc in node.get("subclasses", []):
        apply_enrichments(sc, enrichments)


def main():
    print(f"Loading {INPUT_FILE}...", file=sys.stderr)
    with open(INPUT_FILE) as f:
        hierarchy = json.load(f)

    # Collect all unique instance Q-IDs
    all_ids = set()
    for root in hierarchy["hierarchy"]:
        all_ids |= collect_all_ids(root)

    print(f"Found {len(all_ids)} unique items to enrich", file=sys.stderr)

    # Fetch enrichments in batches
    all_enrichments = {}
    id_list = sorted(all_ids)
    for i in range(0, len(id_list), BATCH_SIZE):
        batch = id_list[i : i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (len(id_list) + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"  Batch {batch_num}/{total_batches} ({len(batch)} items)...", file=sys.stderr)
        enrichments = fetch_enrichments(batch)
        all_enrichments.update(enrichments)
        if i + BATCH_SIZE < len(id_list):
            time.sleep(0.5)

    enriched_count = sum(1 for v in all_enrichments.values()
                         if any(v[k] for k in v))
    print(f"Got enrichment data for {enriched_count}/{len(all_ids)} items", file=sys.stderr)

    # Apply to hierarchy
    for root in hierarchy["hierarchy"]:
        apply_enrichments(root, all_enrichments)

    # Write output
    with open(OUTPUT_FILE, "w") as f:
        json.dump(hierarchy, f, indent=2, ensure_ascii=False)

    print(f"Written to {OUTPUT_FILE}", file=sys.stderr)


if __name__ == "__main__":
    main()
