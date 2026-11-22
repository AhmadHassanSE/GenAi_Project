/* The paper: renders an edition from the API (or the bundled sample), English, Urdu or Roman Urdu, regular or large print. */
document.addEventListener("DOMContentLoaded", async () => {
  const S = window.Subah;
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => [...(r || document).querySelectorAll(s)];
  const esc = S.esc;

  let profile = S.store.get();
  const LANGS = ["en", "ur", "ro"];
  let lang = LANGS.includes(profile.lang) ? profile.lang : "en";
  let large = !!profile.large;
  let edition = null;

  const T = {
    en: {
      edition: "Edition", city: (c) => c, noCity: "All of Pakistan", stories: (n) => `${n} stories`,
      summaryAI: "Summary written by AI from the linked reports only.",
      inWords: (o) => `In ${o}’s own words, from its report.`, listen: "Listen", stop: "Stop", listenStory: "Listen to this story",
      noUrduVoice: "This device has no Urdu voice, so the English text is read instead.", noSpeech: "This browser cannot read aloud.",
      why: "Why it is here", score: (p) => `${p.outlets} outlets` + (p.city ? `, +${p.city} your city` : "") + (p.topics ? `, +${p.topics} your topics` : ""),
      sources: (n) => `Sources (${n})`, from: "Headline from", read: "of", readLabel: (n) => `of ${n} read`, done: "All read",
      made: "How this paper was made", reader: "Your settings", change: "Change",
      topicsNone: "no topics chosen", endHead: "That’s the paper.", endBody: "Nothing else is waiting. The last page shows today’s top three again, with their sources.",
      endBtn: "Finish today’s paper", generate: "Generate today’s paper now", generating: "Generating…",
      picked: (n, of) => `You kept ${n} of today’s top ${of} stories. Loved ones come first; within each group the published formula sets the order.`, repick: "Pick again",
      offline: "The paper server isn’t running, so this is the bundled sample paper built from test feeds.",
      sample: "Sample paper built from the synthetic test feeds.",
      sourceLine: (ed) => ed.source === "live" ? "Built from live feeds" : ed.source === "snapshot" ? "Built from a saved snapshot of the feeds" : "Built from the synthetic test feeds",
      statFeeds: "feeds answered", statArticles: "reports read", statGrouped: "stories after grouping", statAI: "AI summaries", statFallback: "headline fallbacks", statCalls: "AI calls"
    },
    ur: {
      edition: "شمارہ", city: (c) => c, noCity: "پورا پاکستان", stories: (n) => `${S.toUrduDigits(n)} خبریں`,
      summaryAI: "خلاصہ مصنوعی ذہانت نے صرف منسلک رپورٹس سے لکھا ہے۔",
      inWords: (o) => `${o} کے اپنے الفاظ میں، اس کی رپورٹ سے۔`, listen: "سنیں", stop: "روکیں", listenStory: "یہ خبر سنیں",
      noUrduVoice: "اس آلے پر اردو آواز موجود نہیں، اس لیے انگریزی متن پڑھا جا رہا ہے۔", noSpeech: "یہ براؤزر پڑھ کر نہیں سنا سکتا۔",
      why: "یہ خبر یہاں کیوں ہے", score: (p) => `${S.toUrduDigits(p.outlets)} ادارے` + (p.city ? `، آپ کا شہر +${S.toUrduDigits(p.city)}` : "") + (p.topics ? `، آپ کے موضوعات +${S.toUrduDigits(p.topics)}` : ""),
      sources: (n) => `ذرائع (${S.toUrduDigits(n)})`, from: "سرخی بشکریہ", readLabel: (n) => `میں سے ${S.toUrduDigits(n)} پڑھی`, done: "سب پڑھ لیں",
      made: "یہ اخبار کیسے بنا", reader: "آپ کی ترتیبات", change: "تبدیل کریں",
      topicsNone: "کوئی موضوع منتخب نہیں", endHead: "بس، یہی تھا آج کا اخبار۔", endBody: "آگے کچھ انتظار نہیں کر رہا۔ آخری صفحے پر آج کی تین بڑی خبریں ذرائع کے ساتھ دوبارہ ہیں۔",
      endBtn: "آج کا اخبار مکمل کریں", generate: "آج کا اخبار ابھی بنائیں", generating: "بن رہا ہے…",
      picked: (n, of) => `آپ نے آج کی ${S.toUrduDigits(of)} بڑی خبروں میں سے ${S.toUrduDigits(n)} رکھیں۔ پسندیدہ خبریں پہلے ہیں؛ ہر گروپ میں ترتیب شائع شدہ فارمولے کے مطابق ہے۔`, repick: "دوبارہ منتخب کریں",
      offline: "اخبار کا سرور نہیں چل رہا، اس لیے یہ آزمائشی فیڈز سے بنا نمونہ اخبار ہے۔",
      sample: "آزمائشی فیڈز سے بنا نمونہ اخبار۔",
      sourceLine: (ed) => ed.source === "live" ? "تازہ فیڈز سے بنا" : ed.source === "snapshot" ? "فیڈز کے محفوظ شدہ نسخے سے بنا" : "آزمائشی فیڈز سے بنا",
      statFeeds: "فیڈز نے جواب دیا", statArticles: "رپورٹس پڑھی گئیں", statGrouped: "گروپ بندی کے بعد خبریں", statAI: "AI خلاصے", statFallback: "صرف سرخیاں", statCalls: "AI کالز"
    },
    /* Roman Urdu: Urdu in Latin letters. Story text comes from the AI's checked Roman Urdu; where there is none,
       the English text is shown and labelled as such. */
    ro: {
      edition: "Shumara", city: (c) => c, noCity: "Poora Pakistan", stories: (n) => `${n} khabrein`,
      summaryAI: "Khulasa AI ne sirf neeche di gayi reports se likha hai.",
      noRoman: "Is khabar ka Roman Urdu khulasa nahin bana, is liye English mein hai.",
      inWords: (o) => `${o} ke apne alfaaz mein, us ki report se.`, listen: "Sunein", stop: "Rokein", listenStory: "Yeh khabar sunein",
      noUrduVoice: "", noSpeech: "Yeh browser parh kar nahin suna sakta.",
      why: "Yeh khabar yahan kyun hai", score: (p) => `${p.outlets} idare` + (p.city ? `, aap ka shehar +${p.city}` : "") + (p.topics ? `, aap ke mauzoo +${p.topics}` : ""),
      sources: (n) => `Zaraye (${n})`, from: "Surkhi bashukriya", readLabel: (n) => `${n} mein se parhi`, done: "Sab parh liya",
      made: "Yeh akhbaar kaise bana", reader: "Aap ki settings", change: "Badlein",
      topicsNone: "koi mauzoo nahin chuna", endHead: "Bas, yahi tha aaj ka akhbaar.", endBody: "Aage kuch intezar nahin kar raha. Aakhri safhe par aaj ki teen bari khabrein zaraye ke saath dobara hain.",
      endBtn: "Aaj ka akhbaar mukammal karein", generate: "Aaj ka akhbaar abhi banayein", generating: "Ban raha hai…",
      picked: (n, of) => `Aap ne aaj ki ${of} bari khabron mein se ${n} rakhin. Pasandida khabrein pehle hain; har group mein tarteeb shaya shuda formula ke mutabiq hai.`, repick: "Dobara chunein",
      offline: "Akhbaar ka server nahin chal raha, is liye yeh test feeds se bana namoona akhbaar hai.",
      sample: "Test feeds se bana namoona akhbaar.",
      sourceLine: (ed) => ed.source === "live" ? "Taaza feeds se bana" : ed.source === "snapshot" ? "Feeds ki mehfooz copy se bana" : "Test feeds se bana",
      statFeeds: "feeds ne jawab diya", statArticles: "reports parhi gayin", statGrouped: "grouping ke baad khabrein", statAI: "AI khulase", statFallback: "sirf surkhiyan", statCalls: "AI calls"
    }
  };
  const htmlLang = (l) => (l === "ro" ? "ur-Latn" : l);
  /* the story's text in the reading language, or English when the AI wrote no Roman Urdu for it */
  const sumOf = (st, l) => (st.summary ? (st.summary[l] ? { lang: l, ...st.summary[l] } : { lang: "en", ...st.summary.en }) : null);
  const num = (n) => (lang === "ur" ? S.toUrduDigits(n) : String(n));
  let catalog = { topics: [], cities: [] };

  const paper = $("#paper");
  const note = $("#pp-note");

  /* ---------------------------------------------------------------- rendering */
  function sectionOf(st) {
    const t = st.topics && st.topics[0];
    return t ? (lang === "ur" ? t.ur : t.en) : (lang === "ur" ? "خبر" : "News");
  }
  function sourcesList(st, open) {
    const L = T[lang];
    const items = st.sources.map((s) => `
      <li class="pp-src${st.used_sources.includes(s.id) ? " is-used" : ""}">
        <span class="pp-src__meta"><b>${esc(s.outlet)}</b><span>${s.lang === "ur" ? "اردو" : "English"}</span><span>${esc(S.ago(s.published, lang))}</span></span>
        <a href="${esc(s.link)}" target="_blank" rel="noopener noreferrer"${s.lang === "ur" ? ' lang="ur" dir="rtl"' : ' lang="en" dir="ltr"'}>${esc(s.title)}</a>
      </li>`).join("");
    return `<details class="pp-sources"${open ? " open" : ""}><summary>${L.sources(st.sources.length)}</summary><ul>${items}</ul></details>`;
  }
  function body(st) {
    const L = T[lang];
    const sm = sumOf(st, lang);
    if (sm) {
      const other = sm.lang !== lang;
      return `<p class="pp-dek"${other ? ' lang="en"' : ""}>${esc(sm.text)}</p><p class="pp-ai">${L.summaryAI}${other && L.noRoman ? ` ${L.noRoman}` : ""}</p>`;
    }
    const b = briefOf(st);
    if (!b) return "";
    const ur = b.lang === "ur";
    return `<p class="pp-dek pp-dek--quote"${ur ? ' lang="ur" dir="rtl"' : ' lang="en" dir="ltr"'}>${esc(b.text)}</p>
      <p class="pp-ai">${L.inWords(`<a href="${esc(b.link)}" target="_blank" rel="noopener noreferrer">${esc(b.outlet)}</a>`)}</p>`;
  }
  function briefOf(st) {
    return st.brief ? (st.brief[lang] || st.brief.en || st.brief.ur) : null;
  }
  function storyHTML(st, lead, pos) {
    const L = T[lang];
    const head = S.headlineOf(st, lang);
    const headLang = !st.summary && /[؀-ۿ]/.test(head) ? "ur" : (st.summary ? sumOf(st, lang).lang : "en");
    const tag = lead ? "h2" : "h3";
    return `
      <article class="${lead ? "pp-lead" : "pp-story"}" id="${esc(st.id)}" data-i="${pos}" aria-labelledby="h-${esc(st.id)}">
        <div class="${lead ? "pp-lead__main" : "pp-story__main"}">
          <p class="pp-sec"><span>${esc(sectionOf(st))}</span><span class="pp-num">${num(pos + 1)}</span>${pickHTML(st)}</p>
          <${tag} class="pp-head" id="h-${esc(st.id)}"${headLang !== lang ? ` lang="${htmlLang(headLang)}" dir="${headLang === "ur" ? "rtl" : "ltr"}"` : ""}>${esc(head)}</${tag}>
          ${!st.summary ? `<p class="pp-from">${L.from} ${esc(st.headline_from[headLang === "ur" ? "ur" : "en"])}</p>` : ""}
          ${body(st)}
          <div class="pp-badge-row">${S.coverageHTML(st, lang)}</div>
          ${S.forYouHTML(st.for_you, lang)}
          <p class="pp-why"><span>${L.why}:</span> ${L.score(st.score_parts)}</p>
          <button class="pp-say" type="button" data-say="${pos}" aria-label="${esc(L.listenStory)}">${S.ICONS.speaker}<span>${esc(L.listen)}</span></button>
        </div>
        <div class="${lead ? "pp-lead__side" : "pp-story__side"}">${st.outlet_count > 1 ? S.constellationHTML(st, { big: lead, lang }) : ""}${sourcesList(st, false)}</div>
      </article>`;
  }
  function pickHTML(st) {
    const p = edition.picks && edition.picks[st.id];
    if (p !== "love") return "";
    return `<span class="pp-loved">${lang === "ur" ? "آپ کی پسندیدہ" : lang === "ro" ? "Aap ki pasandida" : "You loved this"}</span>`;
  }
  function cityName(id) {
    const c = catalog.cities.find((x) => x.id === id);
    return c ? (lang === "ur" ? c.ur : c.en) : null;
  }
  function topicName(id) {
    const t = catalog.topics.find((x) => x.id === id);
    return t ? (lang === "ur" ? t.ur : t.en) : id;
  }
  function madeHTML(ed) {
    const L = T[lang];
    const st = ed.stats, ai = ed.ai;
    const cells = [
      [st.feeds_ok, L.statFeeds], [st.articles, L.statArticles], [st.stories_grouped, L.statGrouped],
      [ai.summarised || 0, L.statAI], [ai.fallback || 0, L.statFallback], [ai.calls || 0, L.statCalls]
    ];
    const aiNote = ai.enabled ? "" : `<p class="pp-made__note">${esc(ai.note || "")}</p>`;
    return `
      <section class="pp-made" aria-labelledby="made-title">
        <h2 id="made-title">${L.made}</h2>
        <p class="pp-made__src">${L.sourceLine(ed)}. ${esc(S.dates[lang](new Date(ed.as_of)))}</p>
        <dl class="pp-made__stats">${cells.map(([v, k]) => `<div><dt>${k}</dt><dd class="tabular">${num(v)}</dd></div>`).join("")}</dl>
        <p class="pp-made__rank">${esc(ed.ranking[lang] || ed.ranking.en)}</p>
        ${aiNote}
        <a class="link-arrow" href="sources.html">${lang === "ur" ? "ہمارے ذرائع اور درجہ بندی" : lang === "ro" ? "Hamare zaraye aur ranking ka tareeqa" : "Our sources and how we rank"}</a>
      </section>`;
  }
  function render() {
    if (!edition) return;
    const L = T[lang];
    paper.setAttribute("lang", htmlLang(lang));
    paper.setAttribute("dir", lang === "ur" ? "rtl" : "ltr");
    paper.setAttribute("aria-busy", "false");
    const stories = S.pickedStories(edition);
    const city = cityName(edition.profile.city);
    const topics = (edition.profile.topics || []).map(topicName);
    document.title = `${S.paperTitle(profile.name, "en")}, today’s paper`;
    paper.innerHTML = `
      <header class="pp-mast">
        <div class="pp-mast__top"><span>${L.edition} ${esc(edition.edition_id.slice(0, 8))}</span><span>${esc(city || L.noCity)}</span><span>${lang === "ur" ? S.dates.hijriUr(new Date(edition.as_of)) : S.dates.hijriEn(new Date(edition.as_of))}</span></div>
        <h1 class="pp-title">${esc(S.paperTitle(profile.name, lang))}</h1>
        <p class="pp-title-alt" ${lang === "ur" ? 'lang="en" dir="ltr"' : 'lang="ur" dir="rtl"'}>${esc(S.paperTitle(profile.name, lang === "ur" ? "en" : "ur"))}</p>
        <div class="pp-mast__bar"><span>${S.dates[lang](new Date(edition.as_of))}</span><span>${L.stories(stories.length)}</span></div>
        <p class="pp-for"><span>${L.reader}:</span> <b>${esc(city || L.noCity)}</b><span>${esc(topics.length ? topics.join(lang === "ur" ? "، " : ", ") : L.topicsNone)}</span><a href="onboard.html">${L.change}</a></p>
      </header>
      ${edition.picks ? `<p class="pp-picks">${L.picked(stories.length, edition.stories.length)} <a href="onboard.html">${L.repick}</a></p>` : ""}
      ${stories.length ? storyHTML(stories[0], true, 0) : ""}
      <div class="pp-grid">${stories.slice(1).map((s, i) => storyHTML(s, false, i + 1)).join("")}</div>
      ${madeHTML(edition)}
      <footer class="pp-end">
        <div class="pp-end__rule"></div>
        <h2>${L.endHead}</h2>
        <p>${L.endBody}</p>
        <a class="btn btn--primary" href="end.html" data-magnetic="0.18"><span>${L.endBtn}</span><span class="btn__orb">${S.ICONS.arrow}</span></a>
      </footer>`;
    paper.style.setProperty("--scale", large ? 1.25 : 1);
    paper.classList.toggle("is-large", large);
    S.magnetic(paper);
    observeConstellations();
    stopSpeaking();
    $$(".pp-say", paper).forEach((b) => b.addEventListener("click", () => {
      const i = +b.dataset.say;
      if (speakingFrom === i) stopSpeaking(); else speakFrom(i, true);
    }));
    $("#pp-listen .pp-listen__label").textContent = T[lang].listen;
    $("#pp-generate .pp-generate__label").textContent = L.generate;
    dots.innerHTML = stories.map((s, i) => `<li><span class="sr-only">Story ${i + 1}</span></li>`).join("");
    read.clear();
    updateProgress();
    note.textContent = edition.sample ? (S.api.online === false ? L.offline : L.sample) : "";
  }

  /* draw each constellation as it scrolls into view */
  function observeConstellations() {
    const figs = $$(".cst", paper);
    if (S.reduceMotion || !("IntersectionObserver" in window)) { figs.forEach((f) => f.classList.add("is-drawn")); return; }
    const io = new IntersectionObserver((es) => es.forEach((e) => {
      if (e.isIntersecting) { e.target.classList.add("is-drawn"); io.unobserve(e.target); }
    }), { rootMargin: "0px 0px -10% 0px" });
    figs.forEach((f) => io.observe(f));
  }

  /* ---------------------------------------------------------------- read aloud (the browser's own voices) */
  const synth = window.speechSynthesis;
  let speakingFrom = -1;
  function pickVoice(l) {
    const voices = synth ? synth.getVoices() : [];
    const want = l === "ur" ? ["ur"] : ["en-PK", "en-IN", "en-GB", "en"];
    for (const w of want) {
      const v = voices.find((x) => (x.lang || "").toLowerCase().startsWith(w.toLowerCase()));
      if (v) return v;
    }
    return null;
  }
  function spoken(st, l) {
    const sm = sumOf(st, l);
    const head = sm ? sm.headline : (st.headline[l] || st.headline.en);
    const text = sm ? sm.text : ((st.brief && (st.brief[l] || st.brief.en)) || {}).text || "";
    return `${head}. ${text}`;
  }
  function stopSpeaking() {
    if (synth) synth.cancel();
    speakingFrom = -1;
    $$(".is-reading", paper).forEach((el) => el.classList.remove("is-reading"));
    $$(".pp-say", paper).forEach((b) => { b.classList.remove("is-on"); b.querySelector("span").textContent = T[lang].listen; });
    const tb = $("#pp-listen");
    if (tb) { tb.classList.remove("is-speaking"); tb.setAttribute("aria-pressed", "false"); $(".pp-listen__label", tb).textContent = T[lang].listen; }
  }
  function speakFrom(start, onlyOne) {
    if (!synth) { S.toast(T[lang].noSpeech); return; }
    stopSpeaking();
    const stories = S.pickedStories(edition);
    let l = lang;
    let voice = pickVoice(l);
    if (l === "ur" && !voice) { l = "en"; voice = pickVoice("en"); S.toast(T[lang].noUrduVoice); }
    speakingFrom = start;
    const tb = $("#pp-listen");
    tb.classList.add("is-speaking");
    tb.setAttribute("aria-pressed", "true");
    $(".pp-listen__label", tb).textContent = T[lang].stop;
    const list = onlyOne ? [start] : stories.map((_, i) => i).filter((i) => i >= start);
    list.forEach((i, k) => {
      const u = new SpeechSynthesisUtterance(spoken(stories[i], l));
      if (voice) { u.voice = voice; u.lang = voice.lang; } else u.lang = l === "ur" ? "ur-PK" : "en-GB";
      u.rate = 0.97;
      u.onstart = () => {
        $$("[data-i]", paper).forEach((el) => el.classList.toggle("is-reading", +el.dataset.i === i));
        $$(".pp-say", paper).forEach((b) => {
          const on = +b.dataset.say === i;
          b.classList.toggle("is-on", on);
          b.querySelector("span").textContent = on ? T[lang].stop : T[lang].listen;
        });
        const el = $(`[data-i="${i}"]`, paper);
        if (el && !onlyOne) el.scrollIntoView({ behavior: S.reduceMotion ? "auto" : "smooth", block: "center" });
      };
      if (k === list.length - 1) u.onend = () => { if (speakingFrom === start) stopSpeaking(); };
      synth.speak(u);
    });
  }
  if (synth) { synth.getVoices(); synth.onvoiceschanged = () => synth.getVoices(); }
  $("#pp-listen").addEventListener("click", () => {
    if ($("#pp-listen").classList.contains("is-speaking")) stopSpeaking(); else speakFrom(0, false);
  });
  window.addEventListener("pagehide", () => { if (synth) synth.cancel(); });

  /* ---------------------------------------------------------------- reading progress */
  const dots = $("#pp-dots");
  const ring = $("#pp-ring");
  const read = new Set();
  const bar = $(".read-progress span");
  let ticking = false;
  function updateProgress() {
    if (!edition) return;
    const n = S.pickedStories(edition).length;
    const vh = window.innerHeight;
    let current = -1;
    $$("[data-i]", paper).forEach((b) => {
      const r = b.getBoundingClientRect();
      const i = +b.dataset.i;
      if (r.bottom < vh * 0.55) read.add(i);
      if (current < 0 && r.bottom > 160) current = i;
    });
    $$("li", dots).forEach((li, i) => { li.classList.toggle("is-read", read.has(i)); li.classList.toggle("is-current", i === current && !read.has(i)); });
    const L = T[lang];
    $("#pp-read").textContent = read.size === n ? L.done : num(read.size);
    $("#pp-read-label").textContent = read.size === n ? "" : L.readLabel(n);
    ring.style.strokeDashoffset = String(100.53 * (1 - read.size / Math.max(1, n)));
    const d = document.documentElement;
    bar.style.setProperty("--p", Math.min(1, window.scrollY / Math.max(1, d.scrollHeight - vh)));
  }
  window.addEventListener("scroll", () => {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(() => { updateProgress(); ticking = false; });
  }, { passive: true });
  window.addEventListener("resize", updateProgress);

  /* ---------------------------------------------------------------- language and size */
  const langSeg = $("#pp-lang");
  const sizeSeg = $("#pp-size");
  const paintSegs = () => {
    $$("button", langSeg).forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.lang === lang)));
    $$("button", sizeSeg).forEach((b) => b.setAttribute("aria-pressed", String((b.dataset.large === "1") === large)));
  };
  paintSegs();
  langSeg.addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b || b.dataset.lang === lang) return;
    const go = () => { lang = b.dataset.lang; profile = S.store.set({ lang }); paintSegs(); render(); };
    if (document.startViewTransition && !S.reduceMotion) document.startViewTransition(go); else go();
  });
  sizeSeg.addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    large = b.dataset.large === "1";
    profile = S.store.set({ large });
    paintSegs();
    paper.style.setProperty("--scale", large ? 1.25 : 1);
    paper.classList.toggle("is-large", large);
    updateProgress();
  });

  /* ---------------------------------------------------------------- generate now */
  const genBtn = $("#pp-generate");
  genBtn.addEventListener("click", async () => {
    if (genBtn.disabled) return;
    genBtn.disabled = true;
    genBtn.classList.add("is-busy");
    $(".pp-generate__label", genBtn).textContent = T[lang].generating;
    paper.setAttribute("aria-busy", "true");
    const overlay = $("#live-overlay");
    const main = $("#paper-main");
    try {
      overlay.hidden = false;
      main.inert = true;
      const live = await S.Live.create($("#live-root"), { lang });
      const fresh = await S.api.generateStream(profile, null, null, live.onEvent);
      await live.replay(fresh);
      edition = fresh;
      S.api.online = true;
      render();
      window.scrollTo({ top: 0, behavior: S.reduceMotion ? "auto" : "smooth" });
      const ai = edition.ai;
      S.toast(ai.enabled
        ? `Paper ready: ${ai.summarised} AI summaries, ${ai.fallback} headline fallbacks, ${ai.calls} AI calls.`
        : `Paper ready with headlines and links only (${ai.note}).`);
    } catch (err) {
      S.toast(err.status ? `Could not generate: ${err.message}` : "The paper server isn’t running. Start it to generate a live paper.");
      paper.setAttribute("aria-busy", "false");
    } finally {
      $("#live-overlay").hidden = true;
      $("#paper-main").inert = false;
      genBtn.disabled = false;
      genBtn.classList.remove("is-busy");
      $(".pp-generate__label", genBtn).textContent = T[lang].generate;
    }
  });

  /* settings restored from the reader's account after this page loaded */
  document.addEventListener("subah:profile", (e) => {
    profile = e.detail;
    lang = LANGS.includes(profile.lang) ? profile.lang : "en";
    large = !!profile.large;
    paintSegs();
    render();
  });

  /* ---------------------------------------------------------------- load */
  await S.api.health();
  try { catalog = await S.api.catalog(); } catch (e) { /* names fall back to ids */ }
  try {
    edition = await S.api.edition();
  } catch (e) {
    paper.innerHTML = `<p class="pp-loading">Couldn’t load a paper. Start the server and use “Generate today’s paper now”.</p>`;
    return;
  }
  render();
  if (location.hash) {
    const el = document.querySelector(location.hash);
    if (el) setTimeout(() => el.scrollIntoView({ block: "start" }), 60);
  }
});
