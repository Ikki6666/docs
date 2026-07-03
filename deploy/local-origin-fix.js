(function () {
  const sameHostPattern = /^https?:\/\/localhost(?::80)?(?=\/|$)/;
  const homeCardLinks = new Map([
    ["构建", "/build-overview"],
    ["测试", "/langsmith/test-overview"],
    ["部署", "/langsmith/deployment"],
    ["监控", "/langsmith/observability"],
    ["治理", "/langsmith/admin"],
    ["无代码 agent", "/langsmith/fleet"],
    ["使用 Engine 查找并修复问题", "/langsmith/engine-overview"],
    ["LangChain Academy", "https://academy.langchain.com/"],
    ["社区论坛", "https://forum.langchain.com/"],
    ["支持门户", "https://support.langchain.com/"],
    ["注册 LangSmith", "https://smith.langchain.com/"],
    ["LangSmith 状态", "https://status.smith.langchain.com/"],
    ["Trust Center", "https://trust.langchain.com/"],
  ]);

  function normalizeLocalhostUrl(value) {
    if (typeof value !== "string" || !sameHostPattern.test(value)) {
      return value;
    }

    try {
      const url = new URL(value);
      return window.location.origin + url.pathname + url.search + url.hash;
    } catch {
      return value;
    }
  }

  function goTo(href) {
    if (!href) {
      return;
    }

    const normalized = normalizeLocalhostUrl(href);
    if (/^https?:\/\//.test(normalized)) {
      window.location.assign(normalized);
      return;
    }

    window.location.assign(window.location.origin + normalized);
  }

  document.addEventListener(
    "click",
    function (event) {
      if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
        return;
      }

      const anchor = event.target.closest && event.target.closest("a[href]");
      if (anchor) {
        const href = anchor.getAttribute("href");
        const normalized = normalizeLocalhostUrl(href);
        if (normalized !== href) {
          event.preventDefault();
          event.stopImmediatePropagation();
          goTo(normalized);
        }
        return;
      }

      const card = event.target.closest && event.target.closest('.home-page [role="link"].card');
      if (!card) {
        return;
      }

      const title = card.querySelector('[data-component-part="card-title"]')?.textContent?.trim();
      const href = homeCardLinks.get(title);
      if (!href) {
        return;
      }

      event.preventDefault();
      event.stopImmediatePropagation();
      goTo(href);
    },
    true
  );
})();
