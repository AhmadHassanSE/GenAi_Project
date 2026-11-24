/* The last page: today's top three again, with sources, then close the paper. */
document.addEventListener("DOMContentLoaded", async () => {
  const S = window.Subah;
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => [...(r || document).querySelectorAll(s)];
  const profile = S.store.get();
  let lang = ["ur", "ro"].includes(profile.lang) ? profile.lang : "en";
  let edition = null;
  try { edition = await S.api.edition(); } catch (e) { /* page still works without stories */ }

  const T = {
    en: {
      back: "Back to today’s paper", lede: "You’re done for today. Nothing else is waiting.",
      rememberTitle: "Today’s top three, once more", nextTitle: "Your next paper prints in",
      nextNote: "Tomorrow at 7:00 am, Lahore time. Until then, the news can wait.", close: "Close the paper",
      gift: "Make one for someone you love", seeYou: "See you at seven.", home: "Back to the front page",
      stats: (ed) => [[S.pickedStories(ed).length, "stories in today’s paper"], [ed.stats.outlets_read, "outlets read overnight"], [0, "feeds to scroll"]],
      sources: (n) => `Sources (${n})`, none: "Generate a paper first to see its top three here.",
      takeTitle: "Three things to remember", quizTitle: "A quick quiz", quizLede: "Three questions from today’s paper. Every answer is in a story above.",
      right: "Right.", wrong: (a) => `Not quite. The answer is ${a}.`, score: (n, of) => `You got ${n} of ${of}.`, readIt: "Read the story",
      madeBy: (src) => src === "ai" ? "Written by AI from the checked summaries, then checked against the sources." : "Built from the paper’s own outlet counts."
    },
    ur: {
      back: "آج کے اخبار پر واپس", lede: "آج کے لیے بس۔ آگے کچھ انتظار نہیں کر رہا۔",
      rememberTitle: "آج کی تین بڑی خبریں، ایک بار پھر", nextTitle: "آپ کا اگلا اخبار چھپنے میں",
      nextNote: "کل صبح سات بجے، لاہور کے وقت کے مطابق۔ تب تک خبریں انتظار کر سکتی ہیں۔", close: "اخبار بند کریں",
      gift: "کسی پیارے کے لیے بنائیں", seeYou: "سات بجے ملتے ہیں۔", home: "پہلے صفحے پر واپس",
      stats: (ed) => [[S.pickedStories(ed).length, "خبریں آج کے اخبار میں"], [ed.stats.outlets_read, "ادارے رات بھر پڑھے گئے"], [0, "فیڈ اسکرول کرنے کو"]],
      sources: (n) => `ذرائع (${S.toUrduDigits(n)})`, none: "یہاں تین بڑی خبریں دیکھنے کے لیے پہلے اخبار بنائیں۔",
      takeTitle: "یاد رکھنے کی تین باتیں", quizTitle: "ایک مختصر کوئز", quizLede: "آج کے اخبار سے تین سوال۔ ہر جواب اوپر کسی خبر میں ہے۔",
      right: "درست۔", wrong: (a) => `صحیح جواب: ${a}`, score: (n, of) => `آپ کے ${S.toUrduDigits(of)} میں سے ${S.toUrduDigits(n)} جواب درست ہیں۔`, readIt: "خبر پڑھیں",
      madeBy: (src) => src === "ai" ? "مصنوعی ذہانت نے جانچے ہوئے خلاصوں سے لکھا، پھر ذرائع سے ملایا گیا۔" : "اخبار میں دی گئی اداروں کی تعداد سے بنایا گیا۔"
    },
    ro: {
      back: "Aaj ke akhbaar par wapas", lede: "Aaj ke liye bas. Aage kuch intezar nahin kar raha.",
      rememberTitle: "Aaj ki teen bari khabrein, ek baar phir", nextTitle: "Aap ka agla akhbaar chhapne mein",
      nextNote: "Kal subah saat baje, Lahore ke waqt ke mutabiq. Tab tak khabrein intezar kar sakti hain.", close: "Akhbaar band karein",
      gift: "Kisi pyare ke liye banayein", seeYou: "Saat baje milte hain.", home: "Pehle safhe par wapas",
      stats: (ed) => [[S.pickedStories(ed).length, "khabrein aaj ke akhbaar mein"], [ed.stats.outlets_read, "idare raat bhar parhe gaye"], [0, "feeds scroll karne ko"]],
      sources: (n) => `Zaraye (${n})`, none: "Yahan teen bari khabrein dekhne ke liye pehle akhbaar banayein.",
      takeTitle: "Yaad rakhne ki teen baatein", quizTitle: "Ek mukhtasar quiz", quizLede: "Aaj ke akhbaar se teen sawal. Har jawab upar kisi khabar mein hai.",
      right: "Durust.", wrong: (a) => `Sahi jawab: ${a}`, score: (n, of) => `Aap ke ${of} mein se ${n} jawab durust hain.`, readIt: "Khabar parhein",
      madeBy: (src) => src === "ai" ? "AI ne jaanche hue khulason se likha, phir zaraye se milaya gaya." : "Akhbaar mein di gayi idaron ki tadaad se banaya gaya."
    }
  };
  const num = (n) => (lang === "ur" ? S.toUrduDigits(n) : String(n));

  function renderTop() {
    const L = T[lang];
    const list = $("#remember-list");
    const mine = edition ? S.pickedStories(edition) : [];
    if (!mine.length) { list.innerHTML = `<li>${L.none}</li>`; return; }
    list.innerHTML = mine.slice(0, 3).map((st, i) => {
      const head = S.headlineOf(st, lang);
      const headUr = /[؀-ۿ]/.test(head);
      const headEn = lang === "ro" && !headUr && !(st.summary && st.summary.ro);
      return `<li class="is-flip top3" style="--i:${i}"${lang === "ur" ? ' lang="ur" dir="rtl"' : lang === "ro" ? ' lang="ur-Latn"' : ""}>
        <p class="top3__head"${headUr ? ' lang="ur" dir="rtl"' : headEn ? ' lang="en"' : ""}>${S.esc(head)}</p>
        ${S.coverageHTML(st, lang, { dots: false })}
        <details class="top3__src"><summary>${L.sources(st.sources.length)}</summary><ul>${st.sources.map((s) =>
          `<li><b>${S.esc(s.outlet)}</b> <a href="${S.esc(s.link)}" target="_blank" rel="noopener noreferrer"${s.lang === "ur" ? ' lang="ur" dir="rtl"' : ""}>${S.esc(s.title)}</a></li>`).join("")}</ul></details>
      </li>`;
    }).join("");
  }
  function renderStats() {
    const box = $("#bas-stats");
    if (!edition) { box.innerHTML = ""; return; }
    box.innerHTML = T[lang].stats(edition).map(([v, k]) => `<div role="listitem"><b class="tabular">${num(v)}</b><span${lang === "ur" ? ' lang="ur"' : ""}>${k}</span></div>`).join("");
  }
  /* takeaways and quiz: from edition.closing, checked on the server; English where a language is missing */
  const inLang = (obj) => (obj && (obj[lang] || obj.en)) || "";
  const isUr = (t) => /[؀-ۿ]/.test(t);
  const dirAttr = (t) => (isUr(t) ? ' lang="ur" dir="rtl"' : lang === "ur" ? ' lang="en" dir="ltr"' : "");
  let answers = {};
  function renderClosing() {
    const L = T[lang];
    const end = edition && edition.closing;
    const takes = (end && end.takeaways) || [];
    $("#takeaways").hidden = !takes.length;
    $("#take-list").innerHTML = takes.map((t) => `<li${dirAttr(inLang(t))}>${S.esc(inLang(t))}</li>`).join("");
    const quiz = (end && end.quiz) || [];
    $("#quiz").hidden = !quiz.length;
    $("#quiz-list").innerHTML = quiz.map((q, i) => {
      const opts = (q.options[lang] || q.options.en);
      const question = inLang(q.question);
      const picked = answers[i];
      return `<li class="quiz__q" data-q="${i}">
        <p class="quiz__ask"${dirAttr(question)}>${S.esc(question)}</p>
        <div class="quiz__opts" role="group" aria-label="${S.esc(question)}">${opts.map((o, k) => {
          const state = picked == null ? "" : k === q.answer ? " is-right" : k === picked ? " is-wrong" : "";
          return `<button type="button" class="quiz__opt${state}" data-k="${k}"${picked != null ? " disabled" : ""}${dirAttr(o)}>${S.esc(o)}</button>`;
        }).join("")}</div>
        <p class="quiz__fb" aria-live="polite">${picked == null ? "" : (picked === q.answer ? L.right : S.esc(L.wrong(opts[q.answer])))}
          ${picked == null ? "" : `<a href="paper.html#${S.esc(q.story)}">${L.readIt}</a>`}</p>
        <p class="quiz__src">${L.madeBy(q.source)}</p>
      </li>`;
    }).join("");
    const done = Object.keys(answers).length;
    $("#quiz-score").textContent = quiz.length && done === quiz.length
      ? L.score(quiz.filter((q, i) => answers[i] === q.answer).length, quiz.length) : "";
  }
  $("#quiz-list").addEventListener("click", (e) => {
    const b = e.target.closest(".quiz__opt");
    if (!b || b.disabled) return;
    answers[+b.closest(".quiz__q").dataset.q] = +b.dataset.k;
    renderClosing();
  });

  let cd = 0;
  function apply() {
    const L = T[lang];
    $$("[data-t]").forEach((el) => {
      const k = el.dataset.t;
      if (typeof L[k] !== "string") return;
      el.textContent = L[k];
      el.classList.toggle("is-ur", lang === "ur");
      if (lang === "ur") { el.setAttribute("lang", "ur"); el.setAttribute("dir", "rtl"); }
      else if (lang === "ro") { el.setAttribute("lang", "ur-Latn"); el.removeAttribute("dir"); }
      else { el.removeAttribute("lang"); el.removeAttribute("dir"); }
    });
    $$("#end-lang button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.lang === lang)));
    renderTop();
    renderStats();
    renderClosing();
    clearInterval(cd);
    cd = S.countdown($("#end-countdown"), { urdu: lang === "ur" });
  }
  $("#end-lang").addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b || b.dataset.lang === lang) return;
    lang = b.dataset.lang;
    S.store.set({ lang });
    apply();
  });

  /* close the paper */
  const closing = $("#closing");
  const closeBtn = $("#close-paper");
  const main = $("#end-main");
  closeBtn.addEventListener("click", () => {
    closing.hidden = false;
    requestAnimationFrame(() => closing.classList.add("is-open"));
    main.inert = true;
    document.body.style.overflow = "hidden";
    setTimeout(() => $("#closing-home").focus(), S.reduceMotion ? 0 : 700);
  });
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape" || closing.hidden) return;
    closing.classList.remove("is-open");
    closing.hidden = true;
    main.inert = false;
    document.body.style.overflow = "";
    closeBtn.focus();
  });

  apply();
});
