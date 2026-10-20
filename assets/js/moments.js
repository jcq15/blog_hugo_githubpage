(() => {
  "use strict";
  // No JavaScript: complete text and ordinary image links remain available.
  let lightbox;
  let currentImages = [];
  let currentIndex = 0;
  let returnFocus;
  function showImage(index) {
    currentIndex = (index + currentImages.length) % currentImages.length;
    const item = currentImages[currentIndex];
    const image = lightbox.querySelector("img");
    image.src = item.href;
    image.alt = item.querySelector("img").alt || "片刻配图";
    lightbox.querySelector("[data-image-count]").textContent =
      `${currentIndex + 1} / ${currentImages.length}`;
    lightbox.querySelector("nav").hidden = currentImages.length < 2;
  }
  function openImage(event, links, index) {
    if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey ||
        typeof HTMLDialogElement === "undefined") return;
    event.preventDefault();
    if (!lightbox) {
      lightbox = document.createElement("dialog");
      lightbox.className = "moment-lightbox";
      lightbox.setAttribute("aria-label", "查看完整配图");
      lightbox.innerHTML = '<div class="moment-lightbox-bar"><span data-image-count aria-live="polite"></span><button type="button" data-close autofocus>关闭</button></div><img class="moment-lightbox-image" alt=""><nav class="moment-lightbox-nav" aria-label="切换配图"><button type="button" data-prev>上一张</button><button type="button" data-next>下一张</button></nav>';
      document.body.append(lightbox);
      lightbox.querySelector("[data-close]").addEventListener("click", () => lightbox.close());
      lightbox.querySelector("[data-prev]").addEventListener("click", () => showImage(currentIndex - 1));
      lightbox.querySelector("[data-next]").addEventListener("click", () => showImage(currentIndex + 1));
      lightbox.addEventListener("click", e => {
        if (e.target !== lightbox) return;
        const r = lightbox.getBoundingClientRect();
        if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) lightbox.close();
      });
      lightbox.addEventListener("keydown", e => {
        if (e.key === "ArrowLeft") { e.preventDefault(); showImage(currentIndex - 1); }
        if (e.key === "ArrowRight") { e.preventDefault(); showImage(currentIndex + 1); }
      });
      lightbox.addEventListener("close", () => {
        document.documentElement.style.overflow = "";
        returnFocus?.focus({ preventScroll: true });
      });
    }
    currentImages = links;
    returnFocus = event.currentTarget;
    showImage(index);
    document.documentElement.style.overflow = "hidden";
    lightbox.showModal();
  }

  document.querySelectorAll("[data-moment]").forEach((moment, index) => {
    const text = moment.querySelector("[data-moment-text]");
    const photos = [];
    // Only move standalone photos; keep inline emoji and mixed text intact.
    [...text.querySelectorAll("img:not(.closed-social-emoji)")].forEach(img => {
      const paragraph = img.closest("p");
      if (!paragraph || paragraph.textContent.trim() ||
          paragraph.querySelector(".closed-social-emoji") ||
          paragraph.querySelector("video,audio,iframe,code")) return;
      const originalLink = img.closest("a");
      if (originalLink && originalLink.querySelectorAll("img").length !== 1) return;
      const link = originalLink || document.createElement("a");
      link.href = img.src;
      link.setAttribute("aria-label", `查看配图 ${photos.length + 1}`);
      if (!originalLink) link.append(img);
      photos.push(link);
      link.remove();
      if (!paragraph.querySelector("img") && !paragraph.textContent.trim()) paragraph.remove();
    });
    if (photos.length) {
      const gallery = document.createElement("div");
      gallery.className = "moment-gallery";
      gallery.dataset.count = String(photos.length);
      gallery.setAttribute("aria-label", "片刻配图");
      photos.forEach((link, imageIndex) => {
        gallery.append(link);
        link.addEventListener("click", e => openImage(e, photos, imageIndex));
      });
      moment.append(gallery);
    }
    const lines = Number(moment.dataset.collapseLines);
    if (!(lines > 0)) return;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "moment-toggle";
    button.hidden = true;
    text.id = `moment-text-${index}`;
    button.setAttribute("aria-controls", text.id);
    button.setAttribute("aria-expanded", "false");
    button.textContent = "全文";
    text.after(button);
    let expanded = false;
    const savedTabIndexes = new Map();
    function restoreFocusTargets() {
      savedTabIndexes.forEach((value, node) => {
        if (value === null) node.removeAttribute("tabindex");
        else node.setAttribute("tabindex", value);
      });
      savedTabIndexes.clear();
    }
    function update() {
      restoreFocusTargets();
      const limit = parseFloat(getComputedStyle(text).lineHeight) * lines;
      text.style.setProperty("--moment-fold-height", `${limit}px`);
      const tooLong = text.scrollHeight > limit + 2;
      const collapsed = tooLong && !expanded;
      text.classList.toggle("is-collapsed", collapsed);
      button.hidden = !tooLong;
      button.textContent = expanded ? "收起" : "全文";
      button.setAttribute("aria-expanded", String(expanded));
      if (collapsed) {
        const bottom = text.getBoundingClientRect().bottom;
        text.querySelectorAll("a,button,input,select,textarea,[tabindex]").forEach(node => {
          if (node.getBoundingClientRect().bottom > bottom) {
            savedTabIndexes.set(node, node.getAttribute("tabindex"));
            node.setAttribute("tabindex", "-1");
          }
        });
      }
    }
    button.addEventListener("click", () => {
      expanded = !expanded;
      update();
      if (!expanded && button.getBoundingClientRect().top < 0) {
        moment.scrollIntoView({ block: "start" });
      }
    });
    update();
    // Recompute after fonts, inline images and responsive width changes.
    if ("ResizeObserver" in window) {
      let width;
      new ResizeObserver(entries => {
        const next = entries[0].contentRect.width;
        if (width !== next) { width = next; update(); }
      }).observe(moment);
    } else window.addEventListener("resize", update);
    text.querySelectorAll("img").forEach(img => img.addEventListener("load", update));
    document.fonts?.ready.then(update);
  });
})();
