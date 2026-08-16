function escapeHtml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function renderInline(s) {
  const codes = [];
  s = s.replace(/`([^`]+)`/g, (m, c) => { codes.push(c); return "\u0001" + (codes.length - 1) + "\u0001"; });
  s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  s = s.replace(/(^|[^*])\*([^*\s][^*]*?)\*(?!\*)/g, "$1<em>$2</em>");
  s = s.replace(/(^|[^\w])_([^_\s][^_]*?)_(?![\w])/g, "$1<em>$2</em>");
  s = s.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  s = s.replace(/\u0001(\d+)\u0001/g, (m, i) => "<code>" + codes[+i] + "</code>");
  return s;
}

const BLOCK_START = /^(#{1,6}\s|>|```|\s*[-*+]\s|\s*\d+\.\s|\s*\|)/;

function renderTableRow(line, tag) {
  const cells = line.trim().replace(/^\||\|$/g, "").split("|");
  return "<tr>" + cells.map((c) => "<" + tag + ">" + renderInline(escapeHtml(c.trim())) + "</" + tag + ">").join("") + "</tr>";
}

function renderMarkdown(src) {
  const lines = src.split("\n");
  let html = "", i = 0, listType = null;
  const closeList = () => { if (listType) { html += "</" + listType + ">"; listType = null; } };
  while (i < lines.length) {
    const line = lines[i];
    if (/^```/.test(line)) {
      closeList(); i++;
      let code = "";
      while (i < lines.length && !/^```/.test(lines[i])) { code += lines[i] + "\n"; i++; }
      i++;
      html += "<pre><code>" + escapeHtml(code.replace(/\n$/, "")) + "</code></pre>";
      continue;
    }
    const h = line.match(/^(#{1,6})\s+(.*)$/);
    if (h) { closeList(); const lvl = h[1].length; html += "<h" + lvl + ">" + renderInline(escapeHtml(h[2])) + "</h" + lvl + ">"; i++; continue; }
    if (/^\s*(---|\*\*\*|___)\s*$/.test(line)) { closeList(); html += "<hr>"; i++; continue; }
    if (/^>\s?/.test(line)) {
      closeList(); let quote = "";
      while (i < lines.length && /^>\s?/.test(lines[i])) { quote += lines[i].replace(/^>\s?/, "") + "\n"; i++; }
      html += "<blockquote>" + renderMarkdown(quote.trim()) + "</blockquote>";
      continue;
    }
    if (/^\s*\|/.test(line) && /\|/.test(line.slice(1))) {
      closeList();
      const rows = [];
      while (i < lines.length && /^\s*\|/.test(lines[i])) { rows.push(lines[i]); i++; }
      const isSep = (r) => /^[\s|:-]+$/.test(r);
      let head = "", bodyRows = rows;
      if (rows.length >= 2 && isSep(rows[1])) { head = "<thead>" + renderTableRow(rows[0], "th") + "</thead>"; bodyRows = rows.slice(2); }
      const body = bodyRows.filter((r) => !isSep(r)).map((r) => renderTableRow(r, "td")).join("");
      html += "<table>" + head + "<tbody>" + body + "</tbody></table>";
      continue;
    }
    const ul = line.match(/^\s*[-*+]\s+(.*)$/);
    if (ul) { if (listType !== "ul") { closeList(); html += "<ul>"; listType = "ul"; } html += "<li>" + renderInline(escapeHtml(ul[1])) + "</li>"; i++; continue; }
    const ol = line.match(/^\s*\d+\.\s+(.*)$/);
    if (ol) { if (listType !== "ol") { closeList(); html += "<ol>"; listType = "ol"; } html += "<li>" + renderInline(escapeHtml(ol[1])) + "</li>"; i++; continue; }
    if (/^\s*$/.test(line)) { closeList(); i++; continue; }
    closeList();
    let para = line; i++;
    while (i < lines.length && !/^\s*$/.test(lines[i]) && !BLOCK_START.test(lines[i]) && !/^\s*(---|\*\*\*|___)\s*$/.test(lines[i])) {
      para += "\n" + lines[i]; i++;
    }
    html += "<p>" + renderInline(escapeHtml(para)).replace(/\n/g, "<br>") + "</p>";
  }
  closeList();
  return html;
}
