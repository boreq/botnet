from botnet.modules.builtin.fediverse import extract_urls
from botnet.modules.builtin.fediverse import extract_canonical_url


class TestExtractUrls:
    def test_extract_single_url(self):
        text = "Check this out: https://example.com/@user/123456"
        urls = extract_urls(text)
        assert urls == ["https://example.com/@user/123456"]

    def test_extract_cross_instance_url(self):
        text = "https://chaos.social/@robpike@hachyderm.io/116660384710304342"
        urls = extract_urls(text)
        assert urls == ["https://chaos.social/@robpike@hachyderm.io/116660384710304342"]

    def test_extract_users_statuses_url(self):
        text = "https://example.com/users/alice/statuses/12345"
        urls = extract_urls(text)
        assert urls == ["https://example.com/users/alice/statuses/12345"]

    def test_extract_notes_url(self):
        text = "https://example.com/notes/abc123xyz"
        urls = extract_urls(text)
        assert urls == ["https://example.com/notes/abc123xyz"]

    def test_extract_objects_url(self):
        text = "https://example.com/objects/uuid-123"
        urls = extract_urls(text)
        assert urls == ["https://example.com/objects/uuid-123"]

    def test_extract_multiple_urls(self):
        text = (
            "First: https://example.com/@user/123 and second: "
            "https://other.com/@admin/456"
        )
        urls = extract_urls(text)
        assert set(urls) == {
            "https://example.com/@user/123",
            "https://other.com/@admin/456",
        }

    def test_strip_trailing_punctuation(self):
        text = "Check https://example.com/@user/123."
        urls = extract_urls(text)
        assert urls == ["https://example.com/@user/123"]

    def test_strip_multiple_trailing_chars(self):
        text = "Look: https://example.com/@user/123!?."
        urls = extract_urls(text)
        assert urls == ["https://example.com/@user/123"]

    def test_no_urls(self):
        text = "This is just plain text without any URLs"
        urls = extract_urls(text)
        assert urls == []

    def test_non_fediverse_urls_ignored(self):
        text = "Check https://google.com and https://example.com/@user/123"
        urls = extract_urls(text)
        assert urls == ["https://example.com/@user/123"]

    def test_deduplication(self):
        text = (
            "https://example.com/@user/123 and "
            "https://example.com/@user/123 again"
        )
        urls = extract_urls(text)
        assert urls == ["https://example.com/@user/123"]


class TestExtractCanonicalUrl:
    def test_string_url(self):
        obj = {"url": "https://example.com/@user/123"}
        result = extract_canonical_url(obj)
        assert result == "https://example.com/@user/123"

    def test_array_of_strings(self):
        obj = {"url": ["https://example.com/@user/123", "https://other.com"]}
        result = extract_canonical_url(obj)
        assert result == "https://example.com/@user/123"

    def test_array_of_link_objects(self):
        obj = {
            "url": [
                {"type": "Link", "href": "https://example.com/@user/123"},
                {"type": "Link", "href": "https://other.com"},
            ]
        }
        result = extract_canonical_url(obj)
        assert result == "https://example.com/@user/123"

    def test_mixed_array(self):
        obj = {
            "url": [
                "https://example.com/@user/123",
                {"type": "Link", "href": "https://other.com"},
            ]
        }
        result = extract_canonical_url(obj)
        assert result == "https://example.com/@user/123"

    def test_no_url_field(self):
        obj = {"type": "Note", "content": "Hello"}
        result = extract_canonical_url(obj)
        assert result is None

    def test_empty_url_field(self):
        obj = {"url": ""}
        result = extract_canonical_url(obj)
        assert result is None

    def test_link_object_without_href(self):
        obj = {"url": [{"type": "Link"}]}
        result = extract_canonical_url(obj)
        assert result is None
