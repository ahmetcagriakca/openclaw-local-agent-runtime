"""Tests for B-114 Knowledge/connector input layer."""
import pytest

from services.knowledge_store import KnowledgeEntry, KnowledgeStore


@pytest.fixture
def store(tmp_path):
    path = str(tmp_path / "knowledge.json")
    return KnowledgeStore(store_path=path)


class TestKnowledgeEntry:
    def test_entry_defaults(self):
        entry = KnowledgeEntry(entry_id="e1", name="test", connector_type="text", content="hello")
        assert entry.entry_id == "e1"
        assert entry.content_hash != ""
        assert entry.size_bytes == 5
        assert entry.enabled is True

    def test_entry_hash_deterministic(self):
        e1 = KnowledgeEntry(entry_id="a", name="a", connector_type="text", content="same")
        e2 = KnowledgeEntry(entry_id="b", name="b", connector_type="text", content="same")
        assert e1.content_hash == e2.content_hash

    def test_entry_hash_differs(self):
        e1 = KnowledgeEntry(entry_id="a", name="a", connector_type="text", content="one")
        e2 = KnowledgeEntry(entry_id="b", name="b", connector_type="text", content="two")
        assert e1.content_hash != e2.content_hash


class TestKnowledgeStoreAdd:
    def test_add_text(self, store):
        entry = store.add("doc1", "text", "hello world")
        assert entry.name == "doc1"
        assert entry.connector_type == "text"
        assert entry.content == "hello world"
        assert store.count == 1

    def test_add_file(self, store):
        entry = store.add("readme", "file", "# README\ncontent here")
        assert entry.connector_type == "file"

    def test_add_url(self, store):
        entry = store.add("api-ref", "url", "https://example.com/api")
        assert entry.connector_type == "url"

    def test_add_invalid_type(self, store):
        with pytest.raises(ValueError, match="Invalid connector_type"):
            store.add("bad", "invalid", "content")

    def test_add_with_tags(self, store):
        entry = store.add("tagged", "text", "content", tags=["api", "docs"])
        assert entry.tags == ["api", "docs"]

    def test_add_with_metadata(self, store):
        entry = store.add("meta", "text", "content", metadata={"source": "manual"})
        assert entry.metadata == {"source": "manual"}


class TestKnowledgeStoreGet:
    def test_get_existing(self, store):
        added = store.add("doc", "text", "content")
        found = store.get(added.entry_id)
        assert found is not None
        assert found.name == "doc"

    def test_get_missing(self, store):
        assert store.get("nonexistent") is None


class TestKnowledgeStoreUpdate:
    def test_update_name(self, store):
        added = store.add("old", "text", "content")
        updated = store.update(added.entry_id, name="new")
        assert updated.name == "new"

    def test_update_content(self, store):
        added = store.add("doc", "text", "old content")
        old_hash = added.content_hash
        updated = store.update(added.entry_id, content="new content")
        assert updated.content == "new content"
        assert updated.content_hash != old_hash

    def test_update_tags(self, store):
        added = store.add("doc", "text", "content")
        updated = store.update(added.entry_id, tags=["new-tag"])
        assert updated.tags == ["new-tag"]

    def test_update_enabled(self, store):
        added = store.add("doc", "text", "content")
        updated = store.update(added.entry_id, enabled=False)
        assert updated.enabled is False

    def test_update_missing(self, store):
        assert store.update("nonexistent", name="x") is None


class TestKnowledgeStoreDelete:
    def test_delete_existing(self, store):
        added = store.add("doc", "text", "content")
        assert store.delete(added.entry_id) is True
        assert store.count == 0

    def test_delete_missing(self, store):
        assert store.delete("nonexistent") is False


class TestKnowledgeStoreList:
    def test_list_all(self, store):
        store.add("a", "text", "aa")
        store.add("b", "file", "bb")
        entries, total = store.list()
        assert total == 2

    def test_list_by_type(self, store):
        store.add("a", "text", "aa")
        store.add("b", "file", "bb")
        entries, total = store.list(connector_type="text")
        assert total == 1
        assert entries[0]["connector_type"] == "text"

    def test_list_by_tag(self, store):
        store.add("a", "text", "aa", tags=["api"])
        store.add("b", "text", "bb", tags=["docs"])
        entries, total = store.list(tag="api")
        assert total == 1

    def test_list_search(self, store):
        store.add("api docs", "text", "hello")
        store.add("guide", "text", "world")
        entries, total = store.list(search="api")
        assert total == 1

    def test_list_enabled_only(self, store):
        added = store.add("a", "text", "aa")
        store.add("b", "text", "bb")
        store.update(added.entry_id, enabled=False)
        entries, total = store.list(enabled_only=True)
        assert total == 1

    def test_list_pagination(self, store):
        for i in range(5):
            store.add(f"doc-{i}", "text", f"content-{i}")
        entries, total = store.list(limit=2, offset=0)
        assert len(entries) == 2
        assert total == 5


class TestKnowledgeStoreSearch:
    def test_search_by_tags(self, store):
        store.add("a", "text", "aa", tags=["api", "docs"])
        store.add("b", "text", "bb", tags=["guide"])
        store.add("c", "text", "cc", tags=["api"])
        results = store.search_by_tags(["api"])
        assert len(results) == 2

    def test_search_no_match(self, store):
        store.add("a", "text", "aa", tags=["docs"])
        results = store.search_by_tags(["nonexistent"])
        assert len(results) == 0


class TestKnowledgeStoreMission:
    def test_get_for_mission_by_ids(self, store):
        e1 = store.add("a", "text", "aa")
        store.add("b", "text", "bb")
        results = store.get_for_mission(entry_ids=[e1.entry_id])
        assert len(results) == 1
        assert results[0]["entry_id"] == e1.entry_id

    def test_get_for_mission_by_tags(self, store):
        store.add("a", "text", "aa", tags=["security"])
        store.add("b", "text", "bb", tags=["api"])
        results = store.get_for_mission(mission_tags=["security"])
        assert len(results) == 1

    def test_get_for_mission_combined(self, store):
        e1 = store.add("a", "text", "aa", tags=["security"])
        store.add("b", "text", "bb", tags=["api"])
        results = store.get_for_mission(mission_tags=["api"], entry_ids=[e1.entry_id])
        assert len(results) == 2

    def test_get_for_mission_disabled_excluded(self, store):
        e1 = store.add("a", "text", "aa", tags=["security"])
        store.update(e1.entry_id, enabled=False)
        results = store.get_for_mission(mission_tags=["security"])
        assert len(results) == 0


class TestKnowledgeStorePersistence:
    def test_persistence_round_trip(self, tmp_path):
        path = str(tmp_path / "knowledge.json")
        store1 = KnowledgeStore(store_path=path)
        store1.add("persisted", "text", "hello")
        assert store1.count == 1

        store2 = KnowledgeStore(store_path=path)
        assert store2.count == 1
        entries, _ = store2.list()
        assert entries[0]["name"] == "persisted"

    def test_empty_store(self, tmp_path):
        path = str(tmp_path / "nonexistent.json")
        store = KnowledgeStore(store_path=path)
        assert store.count == 0


class TestKnowledgeStoreStats:
    def test_stats(self, store):
        store.add("a", "text", "hello")
        store.add("b", "file", "world!")
        stats = store.stats()
        assert stats["total_entries"] == 2
        assert stats["enabled"] == 2
        assert stats["by_connector_type"]["text"] == 1
        assert stats["by_connector_type"]["file"] == 1
        assert stats["total_bytes"] > 0
