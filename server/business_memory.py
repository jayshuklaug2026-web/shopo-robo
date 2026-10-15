"""
Shopo Robo — Business Memory Graph Engine
==========================================
Structured relational business memory representing connected store entities:
- Entities: Products, Suppliers, Sales, Purchases, Stores, Stock Adjustments, Approved Actions
- Memory Types:
  * verified_record: Direct factual record with exact source_table, source_id, and event_timestamp.
  * ai_derived_summary: Synthesized insight automatically invalidated when source tables change.
- Multi-lingual Natural Language Query Interface (English, Hindi, Hinglish).
- Strict multi-tenant isolation: Never mixes records across shopkeepers.
- Never fabricates missing supplier relationships or phantom transactions.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import json
import re

import database as db

# ────────────────────────────────────────────────────────────
# Memory Sync & Synthesis
# ────────────────────────────────────────────────────────────

def sync_verified_memories(user_id: str, store_id: Optional[str] = None) -> int:
    """
    Ingest verified facts directly from primary database tables into business_memories.
    Avoids duplicate entries by checking entity, key, and source_id.
    """
    now = datetime.now(timezone.utc).isoformat()
    synced_count = 0

    # 1. Product Memories
    products = db.get_products(user_id)
    for p in products:
        p_name = p.get("product_name") or p.get("name") or "Product"
        p_id = p.get("id")
        created_at = p.get("created_at") or now
        supplier = p.get("supplier_name") or p.get("supplier") or ""
        cost_p = float(p.get("purchase_price") or p.get("cost_price") or 0.0)
        sell_p = float(p.get("selling_price") or p.get("price") or 0.0)

        # Baseline product fact
        existing = db.get_business_memories(user_id, entity_type="product", entity_name=p_name, limit=5)
        fact_keys = {m["fact_key"] for m in existing}

        if "pricing_baseline" not in fact_keys:
            db.create_business_memory(
                user_id=user_id,
                entity_type="product",
                entity_name=p_name,
                fact_key="pricing_baseline",
                fact_value=f"Cost price ₹{cost_p:.2f}, Selling price ₹{sell_p:.2f} ({p.get('unit', 'unit')}).",
                fact_type="verified_record",
                confidence=1.0,
                source_table="inventory",
                source_id=p_id,
                event_timestamp=created_at,
                store_id=store_id
            )
            synced_count += 1

        if supplier and "primary_supplier" not in fact_keys:
            db.create_business_memory(
                user_id=user_id,
                entity_type="supplier",
                entity_name=supplier,
                fact_key="supplied_product",
                fact_value=f"Supplies {p_name} at recorded baseline ₹{cost_p:.2f}.",
                fact_type="verified_record",
                confidence=1.0,
                source_table="inventory",
                source_id=p_id,
                event_timestamp=created_at,
                store_id=store_id
            )
            synced_count += 1

    # 2. Product DNA Events (Historical adjustments, supplier changes)
    if hasattr(db, "get_product_dna_events"):
        dna_events = db.get_product_dna_events(user_id, limit=100)
        for ev in dna_events:
            p_id = ev.get("product_id")
            p_name = ev.get("product_name") or "Product"
            ev_type = ev.get("event_type")
            ev_ts = ev.get("created_at") or now

            existing = db.get_business_memories(user_id, entity_type="product", entity_name=p_name, limit=10)
            existing_sources = {m["source_id"] for m in existing}
            if ev.get("id") not in existing_sources:
                fact_desc = f"DNA Event: {ev_type.replace('_', ' ').title()} - {ev.get('notes', 'Stock update')}"
                db.create_business_memory(
                    user_id=user_id,
                    entity_type="product",
                    entity_name=p_name,
                    fact_key=f"dna_{ev_type}",
                    fact_value=fact_desc,
                    fact_type="verified_record",
                    confidence=1.0,
                    source_table="product_dna_events",
                    source_id=ev.get("id"),
                    event_timestamp=ev_ts,
                    store_id=store_id
                )
                synced_count += 1

    # 3. Supplier Negotiations
    if hasattr(db, "get_supplier_negotiations"):
        negs = db.get_supplier_negotiations(user_id, limit=50)
        for neg in negs:
            s_name = neg.get("supplier_name") or "Supplier"
            existing = db.get_business_memories(user_id, entity_type="supplier", entity_name=s_name, limit=10)
            existing_sources = {m["source_id"] for m in existing}
            if neg.get("id") not in existing_sources:
                db.create_business_memory(
                    user_id=user_id,
                    entity_type="supplier",
                    entity_name=s_name,
                    fact_key="negotiation_history",
                    fact_value=(
                        f"Negotiated for {neg.get('product_name')}: Quoted ₹{neg.get('quoted_price')}, "
                        f"Target ₹{neg.get('target_price')} ({neg.get('scenario')}). Status: {neg.get('status')}."
                    ),
                    fact_type="verified_record",
                    confidence=1.0,
                    source_table="supplier_negotiations",
                    source_id=neg.get("id"),
                    event_timestamp=neg.get("created_at") or now,
                    store_id=store_id
                )
                synced_count += 1

    # 4. Generate AI-derived summaries for star items and top suppliers
    sales = db.get_transactions(user_id, limit=200)
    if sales:
        db.invalidate_derived_memories(user_id)
        # Aggregate product sales volume
        prod_volume: Dict[str, float] = {}
        for s in sales:
            if s.get("product_name"):
                p_name = s.get("product_name")
                qty = float(s.get("quantity") or 1.0)
                prod_volume[p_name] = prod_volume.get(p_name, 0.0) + qty
            items = s.get("items") or []
            if isinstance(items, str):
                try:
                    items = json.loads(items)
                except Exception:
                    items = []
            for item in items:
                p_name = item.get("name") or item.get("product_name") or "Item"
                qty = float(item.get("quantity") or 1.0)
                prod_volume[p_name] = prod_volume.get(p_name, 0.0) + qty

        if prod_volume:
            top_seller = max(prod_volume.items(), key=lambda x: x[1])
            db.create_business_memory(
                user_id=user_id,
                entity_type="product",
                entity_name=top_seller[0],
                fact_key="derived_sales_velocity",
                fact_value=f"Highest historical volume item with {top_seller[1]:.0f} recorded units sold.",
                fact_type="ai_derived_summary",
                confidence=0.88,
                source_table="sales",
                source_id=None,
                event_timestamp=now,
                store_id=store_id
            )
            synced_count += 1

    return synced_count


# ────────────────────────────────────────────────────────────
# Graph Representation & Natural Language Query
# ────────────────────────────────────────────────────────────

def get_business_graph(user_id: str) -> Dict[str, Any]:
    """
    Constructs a node-edge graph representation of the business memory for visualization.
    """
    sync_verified_memories(user_id)
    memories = db.get_business_memories(user_id, only_valid=True, limit=100)

    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    node_ids = set()

    def add_node(nid: str, label: str, ntype: str):
        if nid not in node_ids:
            node_ids.add(nid)
            nodes.append({"id": nid, "label": label, "type": ntype})

    # Add core user store node
    add_node("store_root", "Shopo Robo Store", "store")

    for m in memories:
        ent_type = m["entity_type"]
        ent_name = m["entity_name"]
        ent_id = f"{ent_type}:{ent_name.lower().replace(' ', '_')}"

        add_node(ent_id, ent_name, ent_type)
        edges.append({
            "source": "store_root",
            "target": ent_id,
            "relation": m["fact_key"],
            "fact": m["fact_value"],
            "fact_type": m["fact_type"],
            "timestamp": m["event_timestamp"]
        })

    return {
        "nodes_count": len(nodes),
        "edges_count": len(edges),
        "nodes": nodes,
        "edges": edges,
        "memories": memories
    }


def query_business_memory(user_id: str, query_text: str) -> Dict[str, Any]:
    """
    Answers natural language queries in Hindi, Hinglish, or English using verified memory records.
    Never invents missing facts; returns explicit "No record found" when uncertain.
    """
    sync_verified_memories(user_id)
    matched = db.query_business_memories(user_id, query_text, limit=10)

    is_hindi = bool(re.search(r'[\u0900-\u097F]', query_text))
    is_hinglish = any(w in query_text.lower() for w in ["kab", "kitna", "kya", "dukaan", "maal", "bhav", "khareeda"])

    if not matched:
        if is_hindi:
            msg = f"क्षमा करें, '{query_text}' के संबंध में स्टोर रिकॉर्ड में कोई सत्यापित स्मृति या तथ्य नहीं मिला।"
        elif is_hinglish:
            msg = f"Sorry, '{query_text}' ke baare mein koi verified business record nahi mila."
        else:
            msg = f"No verified business records found matching query: '{query_text}'."

        return {
            "query": query_text,
            "found": False,
            "answer": msg,
            "evidence": [],
            "source_records_count": 0
        }

    # Group evidence
    evidence = []
    for m in matched:
        evidence.append({
            "entity": f"{m['entity_name']} ({m['entity_type']})",
            "fact": m["fact_value"],
            "source": f"{m['source_table']} (ID: {m.get('source_id') or 'Aggregated'})",
            "timestamp": m["event_timestamp"],
            "type": m["fact_type"],
            "confidence": m["confidence"]
        })

    # Compose response
    top = matched[0]
    if is_hindi:
        answer = f"**{top['entity_name']}** ({top['entity_type']}) के संबंध में:\n{top['fact_value']}\n(स्रोत: {top['source_table']} • समय: {top['event_timestamp'][:10]})"
    elif is_hinglish:
        answer = f"**{top['entity_name']}** ke baare mein record:\n{top['fact_value']}\n(Source: {top['source_table']}, Date: {top['event_timestamp'][:10]})"
    else:
        answer = f"Regarding **{top['entity_name']}** ({top['entity_type']}):\n{top['fact_value']}\n(Source: {top['source_table']}, Recorded: {top['event_timestamp'][:10]})"

    return {
        "query": query_text,
        "found": True,
        "answer": answer,
        "primary_entity": top["entity_name"],
        "evidence": evidence,
        "source_records_count": len(matched)
    }
