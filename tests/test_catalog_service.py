from app.services.catalog_service import CatalogService


class TestCatalogService:
    def test_get_categorized_tools_returns_tuple(self, settings):
        svc = CatalogService(settings)
        result = svc.get_categorized_tools()
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_categorized_tools_has_categories(self, settings):
        svc = CatalogService(settings)
        categories, _ = svc.get_categorized_tools()
        assert len(categories) >= 5
        expected = [
            "AI & Crypto",
            "Image Processing",
            "Calculators",
            "Developer & SEO",
            "Business & Operations",
            "Productivity & Utilities",
        ]
        for cat in expected:
            assert cat in categories, f"Missing category: {cat}"

    def test_all_tools_have_names_urls_descs(self, settings):
        svc = CatalogService(settings)
        categories, _ = svc.get_categorized_tools()
        for cat_name, tools in categories.items():
            for tool in tools:
                assert "name" in tool, f"Tool in {cat_name} missing name"
                assert "url" in tool, f"Tool {tool.get('name')} missing url"
                assert "desc" in tool, f"Tool {tool.get('name')} missing desc"
                assert tool["url"].startswith("/tool/")

    def test_tools_are_sorted(self, settings):
        svc = CatalogService(settings)
        categories, _ = svc.get_categorized_tools()
        for cat_name, tools in categories.items():
            names = [t["name"] for t in tools]
            assert names == sorted(names), f"Tools in {cat_name} not sorted"

    def test_get_valid_tools_returns_list(self, settings):
        svc = CatalogService(settings)
        tools = svc.get_valid_tools()
        assert isinstance(tools, list)
        assert len(tools) >= 10
        assert "qr-generator" in tools
        assert "crypto-price-prediction" in tools

    def test_valid_tools_no_duplicates(self, settings):
        svc = CatalogService(settings)
        tools = svc.get_valid_tools()
        assert len(tools) == len(set(tools))

    def test_get_categorized_tools_all_accounted_for(self, settings):
        svc = CatalogService(settings)
        valid = set(svc.get_valid_tools())
        categories, _ = svc.get_categorized_tools()
        categorized = set()
        for tools in categories.values():
            for t in tools:
                slug = t["url"].replace("/tool/", "")
                categorized.add(slug)
        assert categorized == valid, "Mismatch between valid tools and categorized tools"

    def test_get_valid_tools_missing_some(self, settings):
        svc = CatalogService(settings)
        tools = svc.get_valid_tools()
        important = ["qr-generator", "invoice-generator", "calculator"]
        for t in important:
            assert t in tools, f"Missing important tool: {t}"

    def test_caching_works(self, settings):
        svc = CatalogService(settings)
        result1, _ = svc.get_categorized_tools()
        result2, _ = svc.get_categorized_tools()
        assert result1 is result2, "Cache should return the same object"
