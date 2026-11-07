// Small, dependency-free behaviour layer that replaces the HubSpot theme JavaScript.
const $$ = <T extends Element = HTMLElement>(sel: string, root: ParentNode = document) => Array.from(root.querySelectorAll<T>(sel) as NodeListOf<any>) as T[];

/* ---------- header: mobile menu + dropdowns ---------- */
const burger = document.querySelector<HTMLButtonElement>('[data-burger]');
burger?.addEventListener('click', () => {
  const open = document.body.classList.toggle('nav-open');
  burger.setAttribute('aria-expanded', String(open));
  burger.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
});
$$('.nav__toggle').forEach((btn) => {
  btn.addEventListener('click', (e) => {
    e.preventDefault();
    const li = btn.closest('.nav__item')!;
    const open = li.classList.toggle('is-open');
    btn.setAttribute('aria-expanded', String(open));
  });
});
$$('.nav__link--label').forEach((el) => {
  el.addEventListener('click', () => (el.parentElement?.querySelector('.nav__toggle') as HTMLElement | null)?.click());
  el.addEventListener('keydown', (e) => { if ((e as KeyboardEvent).key === 'Enter') (el as HTMLElement).click(); });
});
document.querySelector('[data-back-to-top]')?.addEventListener('click', (e) => { e.preventDefault(); window.scrollTo({ top: 0, behavior: 'smooth' }); });

/* ---------- accordions ---------- */
$$('.hp-accordion').forEach((acc) => {
  const title = acc.querySelector<HTMLElement>('.hp-accordion__title');
  if (!title) return;
  title.setAttribute('role', 'button');
  title.setAttribute('aria-expanded', 'false');
  acc.removeAttribute('tabindex');
  title.tabIndex = 0;
  const toggle = () => {
    const open = acc.classList.toggle('is-open');
    title.setAttribute('aria-expanded', String(open));
  };
  title.addEventListener('click', toggle);
  title.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); } });
});

/* ---------- tabs ---------- */
$$('.hp-tabs').forEach((tabs) => {
  const tabEls = $$('.hp-tabs__tab', tabs);
  const panels = $$(':scope > .hp-tabs__body > .hp-tabs__content', tabs);
  const select = tabs.querySelector<HTMLSelectElement>('.hp-tabs__dropdown select');
  const show = (i: number) => {
    tabEls.forEach((t, j) => { t.classList.toggle('hp-tabs__tab--active', i === j); t.setAttribute('aria-selected', String(i === j)); });
    panels.forEach((p, j) => p.classList.toggle('is-active', i === j));
    if (select) select.selectedIndex = i;
  };
  tabEls.forEach((t, i) => {
    t.setAttribute('role', 'tab');
    t.tabIndex = 0;
    t.addEventListener('click', () => show(i));
    t.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); show(i); } });
  });
  select?.addEventListener('change', () => show(select.selectedIndex));
  show(Math.max(0, tabEls.findIndex((t) => t.classList.contains('hp-tabs__tab--active'))));
});

/* ---------- "show more" collapsed galleries ---------- */
$$('.hp-show-more__button').forEach((btn) => {
  btn.addEventListener('click', (e) => {
    e.preventDefault();
    const sec = btn.closest('[class*="hp-sec"]') || btn.parentElement!;
    $$('.hp-show-more__target--collapsed', sec).forEach((t) => t.classList.remove('hp-show-more__target--collapsed'));
    $$('.hp-show-more__container--collapsed', sec).forEach((t) => t.classList.remove('hp-show-more__container--collapsed'));
    btn.remove();
  });
});

/* ---------- carousels (testimonials, client logos, image sliders) ---------- */
$$('.hp-swiper, .swiper, .splide').forEach((root) => {
  if (root.parentElement?.closest('.hp-swiper, .swiper, .splide')) return;
  const track = root.querySelector<HTMLElement>(':scope > .swiper-wrapper, .swiper-wrapper, .splide__list');
  if (!track) return;
  track.classList.add('hp-scroller');
  // slides per view, from the editor settings
  const holder = root.closest<HTMLElement>('[data-nr-elements]');
  let per = Number(holder?.dataset.nrElements || 0);
  try { per = per || JSON.parse(track.dataset.sliderSettings || '{}').slider_nr_items || 0; } catch { /* ignore */ }
  if (per) track.style.setProperty('--per-view', String(per));
  if (track.querySelector(':scope > .hp-image-box')) track.classList.add('hp-scroller--boxes');
  const host = root.parentElement || root;
  const step = (dir: number) => track.scrollBy({ left: dir * track.clientWidth * 0.9, behavior: 'smooth' });
  $$('.swiper-button-prev, .splide__arrow--prev', host).forEach((b) => { b.setAttribute('role', 'button'); b.setAttribute('aria-label', 'Previous'); b.tabIndex = 0; b.addEventListener('click', () => step(-1)); });
  $$('.swiper-button-next, .splide__arrow--next', host).forEach((b) => { b.setAttribute('role', 'button'); b.setAttribute('aria-label', 'Next'); b.tabIndex = 0; b.addEventListener('click', () => step(1)); });
});

/* ---------- timeline: two staggered columns (odd items left, even items right) ---------- */
$$('.hp-timeline').forEach((tl) => {
  const items = $$(':scope > .hp-timeline-item', tl);
  if (items.length < 2 || window.matchMedia('(max-width: 767px)').matches) return;
  const cols = [document.createElement('ul'), document.createElement('ul')];
  cols.forEach((c) => c.classList.add('hp-timeline__col'));
  items.forEach((it, i) => cols[i % 2].appendChild(it));
  tl.replaceChildren(...cols);
  tl.classList.add('is-split');
});

/* ---------- before/after image comparison ---------- */
$$('.hp-img-comp-slider').forEach((wrap) => {
  const after = wrap.querySelector<HTMLElement>('.hp-img-comp__after-img-wrapper');
  const handle = wrap.querySelector<HTMLElement>('.hp-img-comp-slider__resizer');
  if (!after || !handle) return;
  const set = (pct: number) => {
    pct = Math.min(100, Math.max(0, pct));
    after.style.clipPath = `inset(0 0 0 ${pct}%)`;
    handle.style.left = pct + '%';
    handle.setAttribute('aria-valuenow', String(Math.round(pct)));
  };
  handle.setAttribute('role', 'slider');
  handle.setAttribute('aria-label', 'Before and after comparison');
  handle.setAttribute('aria-valuemin', '0');
  handle.setAttribute('aria-valuemax', '100');
  handle.tabIndex = 0;
  let drag = false;
  const move = (x: number) => { const r = wrap.getBoundingClientRect(); set(((x - r.left) / r.width) * 100); };
  wrap.addEventListener('pointerdown', (e) => { drag = true; wrap.setPointerCapture(e.pointerId); move(e.clientX); });
  wrap.addEventListener('pointermove', (e) => drag && move(e.clientX));
  wrap.addEventListener('pointerup', () => (drag = false));
  handle.addEventListener('keydown', (e) => {
    const cur = parseFloat(handle.style.left) || 50;
    if (e.key === 'ArrowLeft') set(cur - 5);
    if (e.key === 'ArrowRight') set(cur + 5);
  });
  set(50);
});

/* ---------- lightbox (images + videos) ---------- */
const dialog = document.querySelector<HTMLDialogElement>('.hp-lightbox-dialog');
const body = dialog?.querySelector<HTMLElement>('.hp-lightbox-dialog__body');
const close = () => { dialog?.close(); if (body) body.innerHTML = ''; };
dialog?.querySelector('.hp-lightbox-dialog__close')?.addEventListener('click', close);
dialog?.addEventListener('click', (e) => { if (e.target === dialog) close(); });
dialog?.addEventListener('close', () => { if (body) body.innerHTML = ''; });
$$('.hp-lightbox').forEach((el) => {
  const url = el.getAttribute('data-lightbox-href');
  const type = el.getAttribute('data-lightbox-type');
  const inline = el.querySelector<HTMLElement>('.lighbox-content');
  if (!url && !inline) return;
  el.style.cursor = 'zoom-in';
  if (el.tagName !== 'A' && el.tagName !== 'BUTTON') { el.setAttribute('role', 'button'); el.tabIndex = 0; }
  const open = (e: Event) => {
    if ((e.target as HTMLElement).closest('a[href]:not([href="#"])') && (e.target as HTMLElement).closest('a') !== el) return;
    e.preventDefault();
    if (!dialog || !body) return;
    if (inline) body.innerHTML = inline.innerHTML;
    else if (type === 'video') body.innerHTML = `<div class="hp-lightbox-dialog__video"><iframe src="${url}${url!.includes('?') ? '&' : '?'}autoplay=1" allow="autoplay; fullscreen; picture-in-picture" allowfullscreen title="Video"></iframe></div>`;
    else {
      const img = document.createElement('img');
      img.src = url!;
      img.alt = el.querySelector('img')?.alt || '';
      body.replaceChildren(img);
    }
    body.querySelector('video')?.play().catch(() => {});
    dialog.showModal();
  };
  el.addEventListener('click', open);
  el.addEventListener('keydown', (e) => { if ((e as KeyboardEvent).key === 'Enter') open(e); });
});

/* ---------- lead forms ---------- */
$$<HTMLFormElement>('[data-lead-form]').forEach((form) => {
  const page = form.querySelector<HTMLInputElement>('[data-page-url]');
  if (page) page.value = location.href;
  const status = form.querySelector<HTMLElement>('.lead-form__status')!;
  if (new URLSearchParams(location.search).get('submitted') === '1') {
    status.textContent = 'Thanks for submitting the contact us form. A representative will be in touch within 1-business day';
  }
  form.addEventListener('submit', async (e) => {
    const group = form.querySelector('[data-require-one]');
    if (group && !group.querySelector('input:checked')) {
      e.preventDefault();
      status.textContent = 'Please choose at least one service.';
      return;
    }
    e.preventDefault();
    const btn = form.querySelector<HTMLButtonElement>('button[type="submit"]')!;
    btn.disabled = true;
    status.textContent = 'Sending…';
    try {
      const res = await fetch(form.action, { method: 'POST', body: new FormData(form), headers: { Accept: 'application/json' } });
      const json = await res.json().catch(() => ({}));
      if (res.ok && json.ok) {
        window.dataLayer?.push({ event: 'form_submission', form_type: (form.elements.namedItem('form') as HTMLInputElement).value });
        if (json.redirect && !json.redirect.includes('submitted=1')) { location.href = json.redirect; return; }
        form.reset();
        status.textContent = json.message || 'Thanks! We will be in touch shortly.';
      } else {
        status.textContent = json.message || 'Sorry, something went wrong. Please call (519)-997-2434.';
      }
    } catch {
      status.textContent = 'Sorry, something went wrong. Please call (519)-997-2434.';
    }
    btn.disabled = false;
  });
});

declare global { interface Window { dataLayer?: unknown[] } }
export {};
