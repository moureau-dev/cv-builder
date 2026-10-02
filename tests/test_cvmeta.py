from cvmeta import as_meta, as_xmp, collect, meta_name, slugify

MARKDOWN = """# Jane Doe

[jane@example.com](mailto:jane@example.com) | [+1 555 010 0000](tel:+15550100000) | Berlin, Germany

[Linkedin](https://linkedin.com/in/jane) | [Github](https://github.com/jane) | [Website](https://jane.dev)

### About

Text that is not part of the contact block.
"""


def test_collect_name_and_links():
    name, links = collect(MARKDOWN)
    assert name == "Jane Doe"
    keys = dict(links)
    assert keys["linkedin"] == "https://linkedin.com/in/jane"
    assert keys["github"] == "https://github.com/jane"
    assert keys["email"] == "mailto:jane@example.com"
    assert keys["phone"] == "tel:+15550100000"


def test_collect_ignores_links_after_first_heading():
    _, links = collect(MARKDOWN + "\n[Repository](https://github.com/jane/repo)\n")
    assert "https://github.com/jane/repo" not in dict(links).values()


def test_meta_name_mapping():
    assert meta_name("Linkedin", "https://linkedin.com/in/x") == "linkedin"
    assert meta_name("Open Source", "https://github.com/org") == "opensource"
    assert meta_name("Moureau.dev", "https://moureau.dev") == "moureau"
    assert meta_name("", "mailto:a@b.c") == "email"


def test_slugify():
    assert slugify("Jane Doe") == "Jane-Doe"
    assert slugify("José Álvarez") == "Jose-Alvarez"


def test_as_meta():
    _, links = collect(MARKDOWN)
    markup = as_meta(links)
    assert '<meta name="github" content="https://github.com/jane" />' in markup


def test_as_xmp():
    name, links = collect(MARKDOWN)
    xmp = as_xmp(name, links)
    assert "<cv:name>Jane Doe</cv:name>" in xmp
    assert "<cv:github>https://github.com/jane</cv:github>" in xmp
