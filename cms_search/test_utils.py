from cms_search.utils import strip_tags


class TestStripTags:

    def test_removes_html_tags(self):
        result = strip_tags('<p>Hello <strong>World</strong></p>')
        assert 'Hello' in result
        assert 'World' in result
        assert '<p>' not in result
        assert '<strong>' not in result

    def test_handles_empty_attributes(self):
        # Previously triggered ValueError in lxml: <div {}> from template rendering
        result = strip_tags('<div {}>some text</div>')
        assert 'some text' in result

    def test_preserves_plain_text(self):
        result = strip_tags('Just plain text')
        assert 'Just plain text' in result

    def test_non_string_passthrough_none(self):
        assert strip_tags(None) is None

    def test_non_string_passthrough_int(self):
        assert strip_tags(123) == 123

    def test_removes_script_tags(self):
        result = strip_tags('<p>Hello</p><script>alert("xss")</script><p>World</p>')
        assert 'Hello' in result
        assert 'World' in result
        assert 'alert' not in result

    def test_removes_style_content(self):
        html = '<style>.container { color: red; }</style><p>Visible text</p>'
        result = strip_tags(html)
        assert 'Visible text' in result
        assert 'color' not in result
        assert 'container' not in result

    def test_empty_string(self):
        assert strip_tags('') == ''

    def test_collapses_whitespace(self):
        result = strip_tags('<p>Hello</p>   <p>World</p>')
        assert 'Hello' in result
        assert 'World' in result
        # No excessive whitespace
        assert '   ' not in result

    def test_nested_html(self):
        html = '<div><ul><li>Item 1</li><li>Item 2</li></ul></div>'
        result = strip_tags(html)
        assert 'Item 1' in result
        assert 'Item 2' in result

    def test_html_with_urls_preserved(self):
        html = '<a href="https://example.com">Visit https://example.com/page</a>'
        result = strip_tags(html)
        assert 'example.com/page' in result

    def test_preserves_urls_in_text(self):
        html = '<p>Mehr unter https://www.zukunft-personal.com/path/page.html</p>'
        result = strip_tags(html)
        assert 'zukunft-personal.com/path/page.html' in result

    def test_preserves_email_in_text(self):
        html = '<p>Kontakt: info@zukunft-personal.com</p>'
        result = strip_tags(html)
        assert 'info@zukunft-personal.com' in result

    # --- Link preservation tests ---

    def test_link_single(self):
        html = '<p>Gehe zum <a href="https://zp.de/dashboard">Aussteller Portal</a></p>'
        result = strip_tags(html)
        assert 'Aussteller Portal' in result
        assert 'https://zp.de/dashboard' in result

    def test_link_multiple_in_one_text(self):
        html = (
            '<p>Besuche <a href="https://a.de">Seite A</a>, '
            '<a href="https://b.de">Seite B</a> und '
            '<a href="https://c.de/path">Seite C</a>.</p>'
        )
        result = strip_tags(html)
        assert 'Seite A' in result
        assert 'https://a.de' in result
        assert 'Seite B' in result
        assert 'https://b.de' in result
        assert 'Seite C' in result
        assert 'https://c.de/path' in result

    def test_link_self_referencing(self):
        html = '<a href="https://example.com">https://example.com</a>'
        result = strip_tags(html)
        assert 'https://example.com' in result

    def test_link_with_nested_html(self):
        html = '<a href="https://zp.de"><strong>Portal</strong> öffnen</a>'
        result = strip_tags(html)
        assert 'Portal' in result
        assert 'https://zp.de' in result

    def test_link_with_single_quotes(self):
        html = "<a href='https://zp.de/page'>Link</a>"
        result = strip_tags(html)
        assert 'https://zp.de/page' in result
        assert 'Link' in result

    def test_link_with_extra_attributes(self):
        html = '<a class="btn" href="https://zp.de" target="_blank" rel="noopener">Click</a>'
        result = strip_tags(html)
        assert 'https://zp.de' in result
        assert 'Click' in result

    def test_link_href_with_query_and_fragment(self):
        html = '<a href="https://zp.de/search?q=hr&lang=de#results">Suche</a>'
        result = strip_tags(html)
        assert 'https://zp.de/search?q=hr&lang=de#results' in result

    def test_link_multiline(self):
        html = '<a\n  href="https://zp.de/dashboard"\n  class="btn"\n>Dashboard</a>'
        result = strip_tags(html)
        assert 'https://zp.de/dashboard' in result
        assert 'Dashboard' in result

    def test_link_adjacent(self):
        html = '<a href="https://a.de">A</a><a href="https://b.de">B</a>'
        result = strip_tags(html)
        assert 'https://a.de' in result
        assert 'https://b.de' in result
        assert 'A' in result
        assert 'B' in result

    def test_link_empty_href(self):
        html = '<a href="">Text</a>'
        result = strip_tags(html)
        assert 'Text' in result

    def test_link_in_list(self):
        html = '''<ol>
            <li>Gehe zum <a href="https://zp.de/login">Login</a></li>
            <li>Klicke auf <a href="https://zp.de/profile">Profil</a></li>
            <li>Fülle das <a href="https://zp.de/form">Formular</a> aus</li>
        </ol>'''
        result = strip_tags(html)
        assert 'https://zp.de/login' in result
        assert 'https://zp.de/profile' in result
        assert 'https://zp.de/form' in result
        assert 'Login' in result
        assert 'Profil' in result
        assert 'Formular' in result

    def test_link_with_no_href(self):
        html = '<a name="anchor">Anchor text</a>'
        result = strip_tags(html)
        assert 'Anchor text' in result

    def test_mixed_links_and_plain_text(self):
        html = (
            '<p>Schritt 1: Öffne <a href="https://zp.de">ZP</a>. '
            'Schritt 2: Warte. '
            'Schritt 3: Klicke <a href="https://zp.de/go">hier</a>.</p>'
        )
        result = strip_tags(html)
        assert 'Schritt 1' in result
        assert 'Schritt 2: Warte' in result
        assert 'Schritt 3' in result
        assert 'https://zp.de' in result
        assert 'https://zp.de/go' in result
