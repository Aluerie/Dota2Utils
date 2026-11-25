// Search box and click-to-copy for the Dota 2 emoticons page (docs/ListEmoticons/index.md).
// Reads the emoticons from the page's Markdown tables, so the page itself stays plain Markdown.
(() => {
  "use strict";

  const input = document.getElementById("emoticon-search");
  const results = document.getElementById("emoticon-results");
  const status = document.getElementById("emoticon-status");
  if (!input || !results || !status) return;

  // Each table row holds three emoticons as (preview, chr, alias) cell triples, under a category heading.
  const emoticons = [];
  for (const table of document.querySelectorAll("#content table")) {
    let heading = table.previousElementSibling;
    while (heading && heading.tagName !== "H2") heading = heading.previousElementSibling;
    const category = heading ? heading.textContent.trim() : "";

    for (const row of table.querySelectorAll("tbody tr")) {
      const cells = row.querySelectorAll("td");
      for (let i = 0; i + 2 < cells.length; i += 3) {
        const img = cells[i].querySelector("img");
        const chr = cells[i + 1].textContent.trim();
        const alias = cells[i + 2].textContent.trim();
        if (!img || !chr || !alias) continue;

        emoticons.push({
          src: img.getAttribute("src"),
          chr,
          alias,
          name: alias.replace(/:/g, "").toLowerCase(),
          category,
        });
        // Click-to-copy also works in the full tables;
        const chrCell = cells[i + 1];
        chrCell.classList.add("emoticon-copy");
        chrCell.title = `Click to copy ${alias}`;
        chrCell.addEventListener("click", () => copy(chr, alias));
      }
    }
  }

  let toastTimer;
  const toast = document.createElement("div");
  toast.className = "emoticon-toast";
  toast.setAttribute("role", "status");
  toast.hidden = true;
  document.body.append(toast);

  function showToast(text) {
    toast.textContent = text;
    toast.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => (toast.hidden = true), 1600);
  }

  async function copy(chr, alias) {
    try {
      await navigator.clipboard.writeText(chr);
    } catch {
      // Older browsers / insecure context: fall back to a hidden textarea;
      const area = document.createElement("textarea");
      area.value = chr;
      area.style.position = "fixed";
      area.style.opacity = "0";
      document.body.append(area);
      area.select();
      document.execCommand("copy");
      area.remove();
    }
    showToast(`Copied ${alias} - paste it into Dota 2`);
  }

  function rank(emoticon, query) {
    if (emoticon.name === query) return 0;
    if (emoticon.name.startsWith(query)) return 1;
    if (emoticon.name.includes(query)) return 2;
    if (emoticon.category.toLowerCase().includes(query)) return 3;
    return -1;
  }

  function render() {
    const query = input.value.trim().toLowerCase().replace(/:/g, "");
    const url = new URL(window.location.href);
    if (query) url.searchParams.set("q", query);
    else url.searchParams.delete("q");
    history.replaceState(null, "", url);

    results.replaceChildren();
    if (!query) {
      status.textContent = `${emoticons.length} emoticons. Type to search, click one to copy it.`;
      return;
    }

    const found = emoticons
      .map((emoticon) => ({ emoticon, score: rank(emoticon, query) }))
      .filter(({ score }) => score >= 0)
      .sort((a, b) => a.score - b.score || a.emoticon.name.localeCompare(b.emoticon.name))
      .map(({ emoticon }) => emoticon);

    status.textContent = found.length
      ? `${found.length} of ${emoticons.length} emoticons match "${query}". Click one to copy it.`
      : `No emoticons match "${query}".`;

    for (const emoticon of found) {
      const card = document.createElement("button");
      card.type = "button";
      card.className = "emoticon-card";
      card.title = `${emoticon.category}: click to copy ${emoticon.alias}`;

      const img = document.createElement("img");
      img.src = emoticon.src;
      img.alt = emoticon.alias;
      img.loading = "lazy";
      img.width = 48;
      img.height = 48;

      const label = document.createElement("code");
      label.textContent = emoticon.alias;

      card.append(img, label);
      card.addEventListener("click", () => copy(emoticon.chr, emoticon.alias));
      results.append(card);
    }
  }

  input.addEventListener("input", render);
  input.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      input.value = "";
      render();
    }
  });
  // "/" jumps to the search box, like on GitHub;
  document.addEventListener("keydown", (event) => {
    const typing = ["INPUT", "TEXTAREA"].includes(document.activeElement?.tagName);
    if (event.key === "/" && !typing) {
      event.preventDefault();
      input.focus();
    }
  });

  input.value = new URL(window.location.href).searchParams.get("q") ?? "";
  render();
})();
