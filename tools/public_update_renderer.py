from __future__ import annotations


def public_update_css(*, text_color: str = "#3f4c56", line_color: str = "var(--line, #dce3ea)") -> str:
    return f"""
      .posted-updates {{
        display: grid;
        gap: 12px;
      }}
      .posted-update {{
        padding: 15px 0;
        border-top: 1px solid {line_color};
      }}
      .posted-update:first-child {{ border-top: 0; padding-top: 0; }}
      .posted-update p {{
        margin: 0;
        color: {text_color};
        line-height: 1.6;
      }}
      .posted-update ul,
      .posted-update ol {{
        margin: 0;
        padding-left: 22px;
        color: {text_color};
        line-height: 1.55;
      }}
      .posted-update li + li {{
        margin-top: 4px;
      }}
      .posted-update a {{
        color: #1d5f9f;
        overflow-wrap: anywhere;
      }}
      .dynamic-takeaways {{
        display: grid;
        gap: 10px;
        margin: 0;
        padding: 0;
        list-style: none;
      }}
      .dynamic-takeaways li {{
        display: grid;
        grid-template-columns: 22px 1fr;
        gap: 10px;
        align-items: start;
        padding: 10px 0;
        border-top: 1px solid {line_color};
      }}
      .dynamic-takeaways .box {{
        width: 17px;
        height: 17px;
        margin-top: 3px;
        border: 2px solid #95a8b3;
        border-radius: 4px;
        background: #fff;
      }}
"""


def public_update_js_helpers() -> str:
    return """
      function appendTextWithLinks(parent, text) {
        const pattern = /(https?:\\/\\/[^\\s]+)/g;
        String(text || "").split(pattern).forEach((part) => {
          if (!part) return;
          if (part.startsWith("http://") || part.startsWith("https://")) {
            const link = document.createElement("a");
            link.href = part;
            link.textContent = part;
            link.rel = "noreferrer";
            link.target = "_blank";
            parent.append(link);
          } else {
            parent.append(document.createTextNode(part));
          }
        });
      }

      function renderFormattedUpdate(container, text) {
        const lines = String(text || "").split(/\\n+/).map((line) => line.trim()).filter(Boolean);
        let list = null;

        lines.forEach((line) => {
          const numbered = line.match(/^\\d+\\.\\s+(.+)/);
          const bulleted = line.match(/^[-*]\\s+(.+)/);
          if (numbered || bulleted) {
            if (!list || list.tagName !== (numbered ? "OL" : "UL")) {
              list = document.createElement(numbered ? "ol" : "ul");
              container.append(list);
            }
            const item = document.createElement("li");
            appendTextWithLinks(item, numbered ? numbered[1] : bulleted[1]);
            list.append(item);
            return;
          }

          list = null;
          const paragraph = document.createElement("p");
          appendTextWithLinks(paragraph, line);
          container.append(paragraph);
        });
      }
"""


def add_posted_update_js(*, show_section_call: str) -> str:
    return f"""
      function addPostedUpdate(text) {{
        const list = document.querySelector("#posted-updates");
        const article = document.createElement("article");
        article.className = "posted-update";
        renderFormattedUpdate(article, text);
        list.append(article);
        {show_section_call}
      }}
"""
