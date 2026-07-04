from __future__ import annotations

import urllib.request
from datetime import date
from pathlib import Path


BASE_URL = "https://clients.stott.marketing"
OUT = Path("firebase-static/public/punch-club/index.html")


def fetch(path: str) -> str:
    with urllib.request.urlopen(f"{BASE_URL}{path}", timeout=30) as response:
        body = response.read().decode("utf-8")
    if not body.lower().lstrip().startswith("<!doctype"):
        body = "<!doctype html>\n" + body
    return body


def replace_once(content: str, old: str, new: str) -> str:
    if old not in content:
        raise RuntimeError(f"Expected Punch Club content not found: {old[:90]}")
    return content.replace(old, new, 1)


def replace_optional(content: str, old: str, new: str) -> str:
    return content.replace(old, new, 1) if old in content else content


def inject_public_updates(content: str) -> str:
    if "clientPublicUpdates" in content:
        return content

    styles = """
      .posted-updates {
        display: grid;
        gap: 12px;
      }
      .posted-update {
        padding: 15px 0;
        border-top: 1px solid var(--line, #dce3ea);
      }
      .posted-update:first-child { border-top: 0; padding-top: 0; }
      .posted-update p { margin: 0; line-height: 1.6; }
      .dynamic-takeaways {
        display: grid;
        gap: 10px;
        margin: 0;
        padding: 0;
        list-style: none;
      }
      .dynamic-takeaways li {
        display: grid;
        grid-template-columns: 22px 1fr;
        gap: 10px;
        align-items: start;
        padding: 10px 0;
        border-top: 1px solid var(--line, #dce3ea);
      }
      .dynamic-takeaways .box {
        width: 17px;
        height: 17px;
        margin-top: 3px;
        border: 2px solid #95a8b3;
        border-radius: 4px;
        background: #fff;
      }
"""
    section = """
        <section id="posted-updates-section" class="card wide-card" hidden>
          <h2>Current Updates</h2>
          <div id="posted-updates" class="posted-updates"></div>
          <ul id="dynamic-takeaways" class="dynamic-takeaways"></ul>
        </section>
"""
    script = """
    <script type="module">
      import { initializeApp } from "https://www.gstatic.com/firebasejs/12.6.0/firebase-app.js";
      import {
        collection,
        getDocs,
        getFirestore,
        orderBy,
        query
      } from "https://www.gstatic.com/firebasejs/12.6.0/firebase-firestore.js";

      const firebaseConfig = {
        apiKey: "AIzaSyDRpeu3P6qrbHQ69PsPjOdUZw0slbxTbsA",
        authDomain: "clients.stott.marketing",
        projectId: "stott-mktg-client-update-data",
        storageBucket: "stott-mktg-client-update-data.firebasestorage.app",
        messagingSenderId: "446049206946",
        appId: "1:446049206946:web:bab80b19302e5d03a58dfb",
        measurementId: "G-PFDY1X5S54"
      };

      const app = initializeApp(firebaseConfig);
      const db = getFirestore(app);

      function addPostedUpdate(text) {
        const section = document.querySelector("#posted-updates-section");
        const list = document.querySelector("#posted-updates");
        const article = document.createElement("article");
        article.className = "posted-update";
        const paragraph = document.createElement("p");
        paragraph.textContent = text || "";
        article.append(paragraph);
        list.append(article);
        section.hidden = false;
      }

      function addMeetingTakeaway(text, completed) {
        const section = document.querySelector("#posted-updates-section");
        const list = document.querySelector("#dynamic-takeaways");
        const item = document.createElement("li");
        const box = document.createElement("span");
        box.className = "box";
        box.setAttribute("aria-hidden", "true");
        const label = document.createElement("span");
        label.textContent = text || "";
        if (completed) label.style.textDecoration = "line-through";
        item.append(box, label);
        list.append(item);
        section.hidden = false;
      }

      async function loadPostedUpdates() {
        try {
          const snapshot = await getDocs(query(
            collection(db, "clientPublicUpdates", "punch-club", "items"),
            orderBy("posted_at", "asc")
          ));
          snapshot.forEach((documentSnapshot) => {
            const entry = documentSnapshot.data();
            if (!entry.text) return;
            if (entry.entry_type === "meeting_takeaway") {
              addMeetingTakeaway(entry.text, Boolean(entry.completed));
            } else {
              addPostedUpdate(entry.text);
            }
          });
        } catch (error) {
          console.error("Could not load posted client updates", error);
        }
      }

      loadPostedUpdates();
    </script>
"""
    content = replace_once(content, "</style>", styles + "\n    </style>")
    content = replace_once(content, "      </main>", section + "\n      </main>")
    content = replace_once(content, "  </body>", script + "\n  </body>")
    return content


def enhance_punch_club(content: str) -> str:
    published = date.today().strftime("%B %-d, %Y")
    if "data-refresh-action" not in content:
        button_css = """
      .topbar-actions {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 10px;
        flex-wrap: wrap;
      }

      .update-data-button {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-height: 38px;
        padding: 8px 14px;
        border: 1px solid #1d3557;
        border-radius: 8px;
        background: #1d3557;
        color: #fff;
        font-size: 12px;
        font-weight: 850;
        letter-spacing: .03em;
        text-decoration: none;
        text-transform: uppercase;
        box-shadow: 0 8px 18px rgba(29, 53, 87, .18);
      }

      .update-data-button:hover {
        background: #12243d;
      }
"""
        content = replace_once(content, "</style>", button_css + "\n    </style>")
        content = replace_once(
            content,
            '<span class="pill"><span class="dot" aria-hidden="true"></span> Private client update</span>',
            """<div class="topbar-actions">
          <a class="update-data-button" data-refresh-action href="https://github.com/stott-marketing/client-update-portal/actions/workflows/deploy-firebase-hosting.yml" target="_blank" rel="noreferrer" title="Open the secure server-side refresh and deploy workflow">UPDATE DATA</a>
          <span class="pill"><span class="dot" aria-hidden="true"></span> Private client update</span>
        </div>""",
        )

    content = replace_optional(
        content,
        "May activity, June progress, reporting rollout, and account actions\n              across active Punch Club marketing work. Prepared by Stott Marketing\n              with updates through June 22, 2026.",
        "Performance reporting, rollout status, and account actions across active Punch Club marketing work. "
        f"Published {published}; source data dates vary by connected account.",
    )
    content = replace_optional(
        content,
        '<span class="pill">Updated June 23, 2026</span>',
        '<span class="pill">Source notes from June 23, 2026</span>',
    )
    return content


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    content = enhance_punch_club(inject_public_updates(fetch("/punch-club")))
    OUT.write_text(content, encoding="utf-8")
    print(f"Wrote Punch Club report to {OUT}")


if __name__ == "__main__":
    main()
