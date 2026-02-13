#!/usr/bin/env python3
"""
Query a Wikibase SPARQL endpoint and build a hierarchy of items
based on subclass_of (P55), superclass_of (P199), and instance_of (P1) relationships.

Outputs a nested JSON hierarchy.
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
OUTPUT_FILE = os.path.join(DATA_DIR, "hierarchy.json")

# Seed Q-IDs to start exploration from
SEED_QIDS = [
    "Q29605",  # uniquely engineered device
    "Q29600",  # theatrical prop
    "Q29606",  # audio device
    "Q29607",  # visual projection or display device
    "Q20619",  # musical instrument
    "Q29604",  # signal processing component
    "Q29603",  # communication device
    "Q29584",  # sensor
    "Q24355",  # home appliance
    "Q29614",  # imaging device
    "Q23229",  # material
    "Q29599",  # device
    "Q24401",  # paper
    "Q24230",  # wood product
    "Q29608",  # wood product (alternate)
    "Q29609",  # plastic/foam material
    "Q24231",  # metal
    "Q29610",  # textile material
    "Q29601",  # theatrical scenery component
    "Q29602",  # phenomenon
    "Q29611",  # auditory phenomenon
    "Q29612",  # light phenomenon
    "Q29613",  # biological signal or activity
    "Q27168",  # object
]

# Manual override: Q-IDs to remove from the final hierarchy.
# Any item listed here (and all its children) will be pruned from the output.
EXCLUDE_QIDS = [
    "Q19053",  # place
    "Q19048",  # agent
    "Q19071",  # event
    "Q26150",  # work
    "Q28932",
    "Q19069",
    
]

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


def query_relationships(qids: list[str]) -> tuple[dict, list, list, list]:
    """
    Query P55 (subclass_of), P199 (superclass_of), and P1 (instance_of)
    for a batch of Q-IDs. Returns labels dict and relationship lists.
    """
    values = " ".join(f"wd:{q}" for q in qids)
    query = f"""SELECT ?item ?itemLabel ?p55value ?p55valueLabel
                       ?p199value ?p199valueLabel ?p1value ?p1valueLabel WHERE {{
      VALUES ?item {{ {values} }}
      OPTIONAL {{ ?item wdt:P55 ?p55value . }}
      OPTIONAL {{ ?item wdt:P199 ?p199value . }}
      OPTIONAL {{ ?item wdt:P1 ?p1value . }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}"""

    data = sparql_query(query)
    labels = {}
    subclass_of = []   # (child, parent)
    superclass_of = []  # (parent, child)
    instance_of = []    # (instance, class)

    for b in data["results"]["bindings"]:
        item_id = extract_qid(b["item"]["value"])
        item_label = b.get("itemLabel", {}).get("value", item_id)
        labels[item_id] = item_label

        if "p55value" in b:
            parent_id = extract_qid(b["p55value"]["value"])
            parent_label = b.get("p55valueLabel", {}).get("value", parent_id)
            labels[parent_id] = parent_label
            subclass_of.append((item_id, parent_id))

        if "p199value" in b:
            child_id = extract_qid(b["p199value"]["value"])
            child_label = b.get("p199valueLabel", {}).get("value", child_id)
            labels[child_id] = child_label
            superclass_of.append((item_id, child_id))

        if "p1value" in b:
            class_id = extract_qid(b["p1value"]["value"])
            class_label = b.get("p1valueLabel", {}).get("value", class_id)
            labels[class_id] = class_label
            instance_of.append((item_id, class_id))

    return labels, subclass_of, superclass_of, instance_of


def query_instances_of(class_qids: list[str]) -> tuple[dict, list]:
    """Query all items that are instances (P1) of the given class Q-IDs."""
    values = " ".join(f"wd:{q}" for q in class_qids)
    query = f"""SELECT ?item ?itemLabel ?class ?classLabel WHERE {{
      VALUES ?class {{ {values} }}
      ?item wdt:P1 ?class .
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}"""

    data = sparql_query(query)
    labels = {}
    instance_of = []

    for b in data["results"]["bindings"]:
        item_id = extract_qid(b["item"]["value"])
        item_label = b.get("itemLabel", {}).get("value", item_id)
        class_id = extract_qid(b["class"]["value"])
        class_label = b.get("classLabel", {}).get("value", class_id)
        labels[item_id] = item_label
        labels[class_id] = class_label
        instance_of.append((item_id, class_id))

    return labels, instance_of


def query_subclasses_of(parent_qids: list[str]) -> tuple[dict, list]:
    """Query all items that are subclasses (P55) of the given Q-IDs."""
    values = " ".join(f"wd:{q}" for q in parent_qids)
    query = f"""SELECT ?item ?itemLabel ?parent ?parentLabel WHERE {{
      VALUES ?parent {{ {values} }}
      ?item wdt:P55 ?parent .
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}"""

    data = sparql_query(query)
    labels = {}
    subclass_of = []

    for b in data["results"]["bindings"]:
        item_id = extract_qid(b["item"]["value"])
        item_label = b.get("itemLabel", {}).get("value", item_id)
        parent_id = extract_qid(b["parent"]["value"])
        parent_label = b.get("parentLabel", {}).get("value", parent_id)
        labels[item_id] = item_label
        labels[parent_id] = parent_label
        subclass_of.append((item_id, parent_id))

    return labels, subclass_of


def build_hierarchy():
    """Main function: query the endpoint and build the hierarchy."""
    all_labels = {}
    all_subclass_of = set()   # (child, parent) - class hierarchy
    all_instance_of = set()   # (instance, class) - instance membership

    print("Step 1: Querying seed items for P55/P199/P1 relationships...", file=sys.stderr)
    labels, subclass_rels, superclass_rels, instance_rels = query_relationships(SEED_QIDS)
    all_labels.update(labels)

    for child, parent in subclass_rels:
        all_subclass_of.add((child, parent))
    for parent, child in superclass_rels:
        all_subclass_of.add((child, parent))
    for inst, cls in instance_rels:
        all_instance_of.add((inst, cls))

    # Discover new Q-IDs from relationships
    discovered = set()
    for child, parent in all_subclass_of:
        discovered.add(child)
        discovered.add(parent)
    for inst, cls in all_instance_of:
        discovered.add(inst)
        discovered.add(cls)

    new_qids = discovered - set(SEED_QIDS)
    if new_qids:
        print(f"Step 2: Discovered {len(new_qids)} additional items, querying...", file=sys.stderr)
        new_list = list(new_qids)
        # Query in batches of 50
        for i in range(0, len(new_list), 50):
            batch = new_list[i:i + 50]
            labels2, sub2, super2, inst2 = query_relationships(batch)
            all_labels.update(labels2)
            for child, parent in sub2:
                all_subclass_of.add((child, parent))
            for parent, child in super2:
                all_subclass_of.add((child, parent))
            for inst, cls in inst2:
                all_instance_of.add((inst, cls))
            time.sleep(0.5)

    # Now query instances OF all known class items (reverse direction)
    all_known = set()
    for child, parent in all_subclass_of:
        all_known.add(child)
        all_known.add(parent)
    all_known.update(SEED_QIDS)

    print(f"Step 3: Querying instances of {len(all_known)} class items...", file=sys.stderr)
    known_list = list(all_known)
    for i in range(0, len(known_list), 50):
        batch = known_list[i:i + 50]
        labels3, inst3 = query_instances_of(batch)
        all_labels.update(labels3)
        for inst, cls in inst3:
            all_instance_of.add((inst, cls))
        time.sleep(0.5)

    # Query subclasses of all known items (reverse direction of P55)
    print(f"Step 4: Querying subclasses of all known items...", file=sys.stderr)
    for i in range(0, len(known_list), 50):
        batch = known_list[i:i + 50]
        labels4, sub4 = query_subclasses_of(batch)
        all_labels.update(labels4)
        for child, parent in sub4:
            all_subclass_of.add((child, parent))
        time.sleep(0.5)

    print(f"\nTotal items: {len(all_labels)}", file=sys.stderr)
    print(f"Subclass relationships: {len(all_subclass_of)}", file=sys.stderr)
    print(f"Instance relationships: {len(all_instance_of)}", file=sys.stderr)

    # Build hierarchy structure
    # Identify which items are "classes" (have subclasses or instances under them)
    classes_with_children = set()
    for child, parent in all_subclass_of:
        classes_with_children.add(parent)
    for inst, cls in all_instance_of:
        classes_with_children.add(cls)

    # Build parent->children maps
    subclass_children = {}  # parent -> [child classes]
    for child, parent in all_subclass_of:
        subclass_children.setdefault(parent, set()).add(child)

    instance_children = {}  # class -> [instances]
    for inst, cls in all_instance_of:
        instance_children.setdefault(cls, set()).add(inst)

    # Find items with parents (subclass_of)
    items_with_parents = set()
    for child, parent in all_subclass_of:
        items_with_parents.add(child)

    # Items that are instances of something
    items_that_are_instances = set()
    for inst, cls in all_instance_of:
        items_that_are_instances.add(inst)

    # Find root items: classes that have no subclass_of parent
    all_class_items = set()
    for child, parent in all_subclass_of:
        all_class_items.add(child)
        all_class_items.add(parent)
    # Also include seed items and any item that has instances under it
    all_class_items.update(SEED_QIDS)
    all_class_items.update(classes_with_children)

    root_classes = all_class_items - items_with_parents
    # Keep roots that are meaningful: they have subclasses or instances under them
    # These are items with no subclass_of parent that serve as hierarchy roots
    root_classes = {r for r in root_classes
                    if r in classes_with_children or r in subclass_children}
    # Also include seed items that have no subclass_of parent but have instances
    for seed in SEED_QIDS:
        if seed not in items_with_parents and seed in classes_with_children:
            root_classes.add(seed)
    # Items to exclude from the hierarchy entirely (too broad / not domain-relevant)
    # Q19054 "thing" and its non-seed descendants are excluded
    # Their seed-item children get promoted to top-level roots
    excluded_items = {"Q19063", "Q27377", "Q19054", "Q27168"}
    root_classes -= excluded_items

    # Remove excluded items from the subclass tree so their children float up
    for excluded in excluded_items:
        # Find children of excluded item and detach them
        children = subclass_children.pop(excluded, set())
        for child in children:
            all_subclass_of.discard((child, excluded))
        # Rebuild items_with_parents
    items_with_parents = set()
    for child, parent in all_subclass_of:
        items_with_parents.add(child)

    # Recalculate roots after removing excluded items
    all_class_items = set()
    for child, parent in all_subclass_of:
        all_class_items.add(child)
        all_class_items.add(parent)
    all_class_items.update(SEED_QIDS)
    all_class_items.update(classes_with_children)

    root_classes = all_class_items - items_with_parents
    root_classes = {r for r in root_classes
                    if r in classes_with_children or r in subclass_children}
    for seed in SEED_QIDS:
        if seed not in items_with_parents and seed in classes_with_children:
            root_classes.add(seed)
    root_classes -= excluded_items

    # Remove items that are instances of a DOMAIN class AND already appear
    # under their parent in the tree (avoid duplicate root entries)
    meta_classes = {"Q19063", "Q27377"}
    for r in list(root_classes):
        if r not in items_that_are_instances:
            continue
        parent_classes = {cls for inst, cls in all_instance_of if inst == r}
        domain_parents = parent_classes - meta_classes - excluded_items
        # If it's an instance of a domain class that IS in the tree, skip as root
        # (it will appear as an instance under that class)
        if domain_parents and r not in subclass_children:
            # Check if any domain parent is itself in the tree
            parents_in_tree = domain_parents & (all_class_items - excluded_items)
            if parents_in_tree:
                root_classes.discard(r)

    print(f"Root classes: {[(r, all_labels.get(r, r)) for r in sorted(root_classes)]}", file=sys.stderr)

    def build_node(qid: str, visited: set = None) -> dict:
        """Recursively build a hierarchy node."""
        if visited is None:
            visited = set()
        if qid in visited:
            return {"id": qid, "label": all_labels.get(qid, qid), "note": "circular reference"}
        visited = visited | {qid}

        node = {
            "id": qid,
            "label": all_labels.get(qid, qid),
        }

        # Add subclass children
        sub_children = sorted(subclass_children.get(qid, set()))
        if sub_children:
            node["subclasses"] = [build_node(c, visited) for c in sub_children]

        # Add instance children
        inst_children = sorted(instance_children.get(qid, set()))
        if inst_children:
            node["instances"] = []
            for ic in inst_children:
                inst_node = {"id": ic, "label": all_labels.get(ic, ic)}
                # Check if instance also has instances under it (some items are both)
                ic_instances = sorted(instance_children.get(ic, set()))
                if ic_instances:
                    inst_node["instances"] = [
                        {"id": iic, "label": all_labels.get(iic, iic)}
                        for iic in ic_instances
                    ]
                # Check if instance has subclasses
                ic_subclasses = sorted(subclass_children.get(ic, set()))
                if ic_subclasses:
                    inst_node["subclasses"] = [build_node(sc, visited) for sc in ic_subclasses]
                node["instances"].append(inst_node)

        return node

    # Build the full hierarchy from roots
    exclude_set = set(EXCLUDE_QIDS)
    root_list = [r for r in sorted(root_classes, key=lambda x: all_labels.get(x, x))
                 if r not in exclude_set]

    def prune(node):
        """Remove any node whose id is in EXCLUDE_QIDS (drops all its children too)."""
        if "subclasses" in node:
            node["subclasses"] = [prune(c) for c in node["subclasses"]
                                  if c["id"] not in exclude_set]
            if not node["subclasses"]:
                del node["subclasses"]
        if "instances" in node:
            node["instances"] = [prune(c) for c in node["instances"]
                                 if c["id"] not in exclude_set]
            if not node["instances"]:
                del node["instances"]
        return node

    hierarchy = {
        "hierarchy": [prune(build_node(r)) for r in root_list],
        "metadata": {
            "endpoint": SPARQL_ENDPOINT,
            "seed_items": len(SEED_QIDS),
            "total_items_discovered": len(all_labels),
            "subclass_relationships": len(all_subclass_of),
            "instance_relationships": len(all_instance_of),
            "manually_excluded": [{"id": q, "label": all_labels.get(q, q)} for q in EXCLUDE_QIDS],
            "properties_used": {
                "P1": "instance of",
                "P55": "subclass of",
                "P199": "superclass of",
            },
        },
    }

    return hierarchy


if __name__ == "__main__":
    hierarchy = build_hierarchy()
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(hierarchy, f, indent=2, ensure_ascii=False)
    print(f"Written to {OUTPUT_FILE}", file=sys.stderr)
