(() => {
  "use strict";

  const escapeHtml = (value) => String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");

  const inline = (value) => {
    let s = escapeHtml(value);
    s = s.replace(/`([^`]+)`/g, "<code>$1</code>");
    s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    s = s.replace(/__([^_]+)__/g, "<strong>$1</strong>");
    return s;
  };

  const splitCells = (line) =>
    line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map(x => x.trim());

  const isSeparator = (line) => {
    const cells = splitCells(line);
    return cells.length > 1 && cells.every(c => /^:?-{3,}:?$/.test(c));
  };

  const render = (raw) => {
    const lines = String(raw || "").replace(/\r\n?/g, "\n").split("\n");
    const out = [];
    let i = 0;

    while (i < lines.length) {
      const t = lines[i].trim();

      if (!t) {
        i += 1;
        continue;
      }

      if (t.startsWith("|") && i + 1 < lines.length && isSeparator(lines[i + 1])) {
        const headers = splitCells(lines[i]);
        i += 2;
        const rows = [];
        while (i < lines.length && lines[i].trim().startsWith("|")) {
          rows.push(splitCells(lines[i]));
          i += 1;
        }

        let html = '<div class="analysis-table-wrap"><table class="analysis-table"><thead><tr>';
        html += headers.map(h => `<th>${inline(h)}</th>`).join("");
        html += "</tr></thead><tbody>";
        for (const row of rows) {
          html += "<tr>";
          for (let c = 0; c < headers.length; c += 1) {
            html += `<td>${inline(row[c] || "")}</td>`;
          }
          html += "</tr>";
        }
        html += "</tbody></table></div>";
        out.push(html);
        continue;
      }

      const heading = t.match(/^(#{1,4})\s+(.+)$/);
      if (heading) {
        const level = Math.min(heading[1].length + 2, 5);
        out.push(`<h${level}>${inline(heading[2])}</h${level}>`);
        i += 1;
        continue;
      }

      if (/^[-*]\s+/.test(t)) {
        const items = [];
        while (i < lines.length && /^[-*]\s+/.test(lines[i].trim())) {
          items.push(lines[i].trim().replace(/^[-*]\s+/, ""));
          i += 1;
        }
        out.push("<ul>" + items.map(x => `<li>${inline(x)}</li>`).join("") + "</ul>");
        continue;
      }

      const para = [t];
      i += 1;
      while (
        i < lines.length &&
        lines[i].trim() &&
        !lines[i].trim().startsWith("|") &&
        !/^#{1,4}\s+/.test(lines[i].trim()) &&
        !/^[-*]\s+/.test(lines[i].trim())
      ) {
        para.push(lines[i].trim());
        i += 1;
      }
      out.push(`<p>${inline(para.join(" "))}</p>`);
    }

    return out.join("\n");
  };

  document.querySelectorAll("[data-analysis-markdown]").forEach((node) => {
    const raw = node.textContent || "";
    node.innerHTML = render(raw);
  });
})();
