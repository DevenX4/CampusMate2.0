"""OKF knowledge layer: the derived graph must reproduce the dataset's knowledge exactly, and
every fact must carry the right trust label."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.db import get_db
from app.knowledge.graph import EDGE_QUERIES, READINGS, all_edges
from app.knowledge.okf import build_items, render_markdown, write_items
from app.knowledge.validate import compare_edges, compare_items
from app.main import app
from app.services.knowledge import entity_item


def test_every_predicate_has_both_readings():
    assert set(EDGE_QUERIES) == set(READINGS)


def test_derived_graph_reproduces_the_dataset_relationships(seeded_session):
    report = compare_edges(all_edges(seeded_session), get_settings().data_dir / "structured" / "relationships.json")
    assert (report["generated"], report["fixture"]) == (1202, 1202)
    assert report["missing"] == [] and report["extra"] == []
    assert report["source_type_mismatches"] == []
    # Known, documented difference: the coordinator edges cite the faculty record instead of
    # the programmes document (same synthetic trust level).
    assert report["citation_differences"] == {"COORDINATED_BY": 2}


def test_legacy_course_cites_its_earliest_catalog_listing(seeded_session):
    # Listed in 2017-18 (p.112), 2018-19 (p.89) and 2019-20 (p.62): the citation must not
    # depend on the order PostgreSQL happens to return rows in.
    [edge] = [e for e in all_edges(seeded_session) if (e.subject_id, e.predicate) == ("COURSE-2IT503", "BELONGS_TO")]
    assert (edge.source_type, edge.source_document_id, edge.source_page) == (
        "derived_official", "DOC-OFFICIAL-CATALOG-001", 112)


def test_items_match_the_dataset_okf_entities(seeded_session):
    report = compare_items(build_items(seeded_session),
                           get_settings().data_dir / "knowledge" / "OKF_style" / "index.json")
    assert report["missing"] == [] and report["extra"] == [] and report["generated"] == 297


def test_mixed_record_labels_each_attribute(seeded_session):
    item = entity_item(seeded_session, "COURSE-2CEIT602")
    assert item["source_type"] == "official"
    assert item["attribute_source_types"] == {"department_id": "synthetic", "synthetic_description": "synthetic"}
    taught_by = {t["id"]: t["source_type"] for t in item["relationships"]["taught_by"]}
    assert taught_by == {"FAC-IT-002": "synthetic", "FAC-IT-004": "synthetic"}
    assert item["relationships"]["offered_in"] == [{"id": "SEM-BTECH-IT-06", "source_type": "official"}]
    markdown = render_markdown(item)
    assert "- [synthetic] **synthetic_description**" in markdown
    assert "- [official] **course_name**: ARTIFICIAL INTELLIGENCE" in markdown


def test_synthetic_entities_carry_a_disclaimer(seeded_session):
    assert "NOT a Ganpat University fact" in render_markdown(entity_item(seeded_session, "FAC-IT-002"))


def test_generation_writes_files_and_regeneration_replaces_them(seeded_session, tmp_path):
    out = tmp_path / "knowledge"
    assert write_items(seeded_session, out)["items"] == 297
    (out / "stray.txt").write_text("left over", encoding="utf-8")
    write_items(seeded_session, out)
    assert not (out / "stray.txt").exists()  # the folder is rebuilt, not patched
    assert (out / "course" / "COURSE-2CEIT602.md").is_file()
    assert sum(1 for _ in (out / "relationships.jsonl").open(encoding="utf-8")) == 1202


@pytest.fixture
def client(seeded_session):
    app.dependency_overrides[get_db] = lambda: seeded_session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_entity_api_is_public_and_names_related_entities(client):
    body = client.get("/api/v1/knowledge/entities/COURSE-2CEIT602").json()
    names = {t["id"]: t["title"] for t in body["relationships"]["taught_by"]}
    assert names["FAC-IT-002"] == "Dr. Arjun Tensorkar"
    assert body["provenance"]["page"] == 15


def test_okf_endpoint_and_unknown_entity(client):
    response = client.get("/api/v1/knowledge/entities/LAB-IT-002/okf")
    assert response.status_code == 200 and response.headers["content-type"].startswith("text/markdown")
    assert response.text.startswith("---\nid: LAB-IT-002")
    assert client.get("/api/v1/knowledge/entities/COURSE-NOPE").status_code == 404
