// site/js/pages/about.js - what Znanjograf is, where its content comes from, the
// licences, the known limits and the privacy promise. Every sentence is in strings.js;
// the only text written here is the names of licences and products, which must stay
// as they are in the Cyrillic mirror too.

import { esc, initCommon, t } from "../common.js";

const NAMES = { mit: "MIT", ccby: "CC BY 4.0", katex: "KaTeX" };
const LIMITS = ["about.limits.1", "about.limits.2", "about.limits.3", "about.limits.4", "about.limits.5", "about.limits.6"];

// Keys ending in Html hold simple markup from strings.js and go in unescaped.
const html = (key, params) => t(key, params);

function markup() {
  return `<div class="zg-wrap zg-narrow">
  <h1 class="zg-title" data-zg-focus>${esc(t("about.title"))}</h1>
  <p class="zg-lead">${esc(t("about.lead"))}</p>

  <section class="zg-section" aria-labelledby="zg-about-what">
    <h2 class="zg-subtitle" id="zg-about-what">${esc(t("about.what.title"))}</h2>
    <ul>
      <li>${html("about.what.graphHtml")}</li>
      <li>${html("about.what.bankHtml")}</li>
      <li>${html("about.what.diagHtml")}</li>
    </ul>
  </section>

  <section class="zg-section" aria-labelledby="zg-about-sources">
    <h2 class="zg-subtitle" id="zg-about-sources">${esc(t("about.sources.title"))}</h2>
    <p>${esc(t("about.sources.p1"))}</p>
    <p>${esc(t("about.sources.p2"))}</p>
    <p>${html("about.sources.repoHtml")}</p>
    <p class="zg-note zg-note-warn">${esc(t("about.notOfficial"))}</p>
  </section>

  <section class="zg-section" aria-labelledby="zg-about-licence">
    <h2 class="zg-subtitle" id="zg-about-licence">${esc(t("about.licence.title"))}</h2>
    <p>${html("about.licence.codeHtml", { mit: NAMES.mit })}</p>
    <p>${html("about.licence.dataHtml", { ccby: NAMES.ccby })}</p>
    <p>${html("about.licence.katexHtml", { katex: NAMES.katex, mit: NAMES.mit })}</p>
  </section>

  <section class="zg-section" aria-labelledby="zg-about-limits">
    <h2 class="zg-subtitle" id="zg-about-limits">${esc(t("about.limits.title"))}</h2>
    <ol>${LIMITS.map((key) => `<li>${esc(t(key))}</li>`).join("")}</ol>
  </section>

  <section class="zg-section" aria-labelledby="zg-about-privacy">
    <h2 class="zg-subtitle" id="zg-about-privacy">${esc(t("about.privacy.title"))}</h2>
    <p>${esc(t("about.privacy.p1"))}</p>
    <p>${esc(t("about.privacy.p2"))}</p>
    <p>${html("about.privacy.p3Html")}</p>
  </section>
</div>`;
}

function main() {
  if (!initCommon()) return;
  const root = document.getElementById("zg-main") || document.body;
  root.innerHTML = markup();
}

main();
