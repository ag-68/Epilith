from data.filing_text import exhibit_documents, filing_html_to_text

WORKIVA_STYLE = """<?xml version='1.0' encoding='ASCII'?>
<html xmlns:ix="http://www.xbrl.org/2013/inlineXBRL"><head><title>nvda-20260125</title></head><body>
<div style="display:none"><ix:header><ix:hidden>nvda-20260125 0001045810 false</ix:hidden></ix:header></div>
<div><span style="font-weight:700">Item 1. Business</span></div>
<div><span>Our Company</span></div>
<div><span>NVIDIA pioneered accelerated computing.</span><span> It is now an AI infrastructure company.</span></div>
<div><span style="font-weight:700">Item 1A. Risk Factors</span></div>
<div><span>Management&#8217;s view &amp; ours.</span></div>
</body></html>"""


def test_block_elements_become_lines_and_hidden_header_is_dropped():
    text = filing_html_to_text(WORKIVA_STYLE)
    lines = text.splitlines()
    assert lines[0] == "Item 1. Business"
    assert lines[1] == "Our Company"
    assert lines[2] == "NVIDIA pioneered accelerated computing. It is now an AI infrastructure company."
    assert lines[3] == "Item 1A. Risk Factors"
    assert lines[4] == "Management’s view & ours."
    assert "0001045810" not in text


def test_exhibit_documents_reads_the_index_table():
    html = """<table>
    <tr><th>Seq</th><th>Description</th><th>Document</th><th>Type</th><th>Size</th></tr>
    <tr><td>1</td><td>8-K</td><td><a href="/Archives/x/nvda-8k.htm">nvda-8k.htm</a></td><td>8-K</td><td>1</td></tr>
    <tr><td>2</td><td>EX-99.1</td><td><a href="/Archives/x/q2fy27pr.htm">q2fy27pr.htm</a></td><td>EX-99.1</td><td>2</td></tr>
    <tr><td>3</td><td>GRAPHIC</td><td><a href="/Archives/x/logo.jpg">logo.jpg</a></td><td>GRAPHIC</td><td>3</td></tr>
    </table>"""
    assert exhibit_documents(html) == [("nvda-8k.htm", "8-K"), ("q2fy27pr.htm", "EX-99.1"), ("logo.jpg", "GRAPHIC")]
