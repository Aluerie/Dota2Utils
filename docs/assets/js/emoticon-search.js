// Card grids, search box and click-to-copy for the Dota 2 emoticons page (docs/ListEmoticons/index.md).
// The page itself is plain Markdown tables (so it also reads fine on GitHub); this script reads the emoticons
// from them and turns every table into a grid of cards that fits any screen width.
(() => {
  "use strict";

  const input = document.getElementById("emoticon-search");
  const results = document.getElementById("emoticon-results");
  const status = document.getElementById("emoticon-status");
  if (!input || !results || !status) return;

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

  async function copy(emoticon) {
    try {
      await navigator.clipboard.writeText(emoticon.chr);
    } catch {
      // Older browsers / insecure context: fall back to a hidden textarea;
      const area = document.createElement("textarea");
      area.value = emoticon.chr;
      area.style.position = "fixed";
      area.style.opacity = "0";
      document.body.append(area);
      area.select();
      document.execCommand("copy");
      area.remove();
    }
    showToast(`Copied ${emoticon.alias} - paste it into Dota 2`);
  }

  function card(emoticon) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "emoticon-card";
    button.title = `${emoticon.category}: click to copy ${emoticon.alias}`;

    const img = document.createElement("img");
    img.src = emoticon.src;
    img.alt = emoticon.alias;
    img.loading = "lazy";
    img.width = 64;
    img.height = 64;

    const label = document.createElement("code");
    label.textContent = emoticon.alias;

    button.append(img, label);
    button.addEventListener("click", () => copy(emoticon));
    return button;
  }

  function grid(items) {
    const container = document.createElement("div");
    container.className = "emoticon-grid";
    container.append(...items.map(card));
    return container;
  }

  // Each table row holds three emoticons as (preview, chr, alias) cell triples, under a category heading.
  const emoticons = [];
  for (const table of document.querySelectorAll("#content table")) {
    let heading = table.previousElementSibling;
    while (heading && heading.tagName !== "H2") heading = heading.previousElementSibling;
    const category = heading ? heading.textContent.trim() : "";

    const found = [];
    for (const row of table.querySelectorAll("tbody tr")) {
      const cells = row.querySelectorAll("td");
      for (let i = 0; i + 2 < cells.length; i += 3) {
        const img = cells[i].querySelector("img");
        const chr = cells[i + 1].textContent.trim();
        const alias = cells[i + 2].textContent.trim();
        if (!img || !chr || !alias) continue;
        found.push({
          src: img.getAttribute("src"),
          chr,
          alias,
          name: alias.replace(/:/g, "").toLowerCase(),
          category,
        });
      }
    }
    // Only emoticon tables become grids (the "Last Updated" stats table has no emoticons);
    if (found.length) {
      table.replaceWith(grid(found));
      emoticons.push(...found);
    }
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
    if (found.length) results.append(grid(found));
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
