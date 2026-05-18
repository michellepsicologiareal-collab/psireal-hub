(() => {
  const nav = document.querySelector('.site-nav, body > nav');
  const navLinks = nav?.querySelector('.nav-links');

  if (navLinks) {
    navLinks.innerHTML = `
      <a class="nav-cta" href="https://wa.me/5511947388423" target="_blank" rel="noopener">Agendar</a>
    `;
  }

  if (nav && !document.querySelector('[data-desktop-sidebar]')) {
    document.body.classList.add('has-desktop-sidebar');
    const sidebar = document.createElement('aside');
    sidebar.className = 'desktop-sidebar';
    sidebar.setAttribute('data-desktop-sidebar', '');
    sidebar.setAttribute('aria-label', 'Navegacao principal');
    sidebar.innerHTML = `
      <div class="desktop-sidebar-group">
        <strong>Para pacientes</strong>
        <a href="terapia.html"><span>Terapia</span><small>Atendimento clinico</small></a>
        <a href="ansiedade.html"><span>Ansiedade</span><small>Guia para pacientes</small></a>
        <a href="index.html#processo"><span>Processo</span><small>Como funciona</small></a>
        <a href="index.html#sobre"><span>Sobre</span><small>Conheca a psicologa</small></a>
      </div>
      <div class="desktop-sidebar-group">
        <strong>Para psis</strong>
        <a href="supervisao.html"><span>Supervisao</span><small>Desenvolvimento clinico</small></a>
        <a href="psireal-tcc.html"><span>PsiReal TCC</span><small>Plataforma clinica</small></a>
        <a href="biblioteca-tcc/index.html"><span>Biblioteca TCC</span><small>Materiais e recursos</small></a>
      </div>
      <div class="desktop-sidebar-group">
        <strong>Para empresas</strong>
        <a href="corporativo.html"><span>Corporativo</span><small>Palestras e solucoes</small></a>
      </div>
      <a class="desktop-sidebar-link" href="index.html#faq">FAQ</a>
    `;
    document.body.appendChild(sidebar);
  }

  if (nav && !document.querySelector('[data-mobile-menu]')) {
    const button = document.createElement('button');
    button.className = 'mobile-menu-toggle';
    button.type = 'button';
    button.setAttribute('aria-label', 'Abrir menu');
    button.setAttribute('aria-expanded', 'false');
    button.setAttribute('data-mobile-menu-open', '');
    button.innerHTML = '<svg viewBox="0 0 24 24"><path d="M4 7h16M4 12h16M4 17h16"/></svg>';
    nav.appendChild(button);

    const menu = document.createElement('aside');
    menu.className = 'mobile-menu';
    menu.setAttribute('data-mobile-menu', '');
    menu.setAttribute('aria-label', 'Menu movel');
    menu.innerHTML = `
      <button class="mobile-menu-backdrop" type="button" aria-label="Fechar menu" data-mobile-menu-close></button>
      <div class="mobile-menu-panel">
        <div class="mobile-menu-head">
          <span class="mobile-menu-kicker">Navegar</span>
          <button class="mobile-menu-close" type="button" aria-label="Fechar menu" data-mobile-menu-close>
            <svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6 6 18"/></svg>
          </button>
        </div>
        <div class="mobile-menu-groups">
          <div class="mobile-menu-group">
            <strong>Para pacientes</strong>
            <a href="index.html#terapia">Terapia <span>clinica</span></a>
            <a href="ansiedade.html">Ansiedade <span>guia</span></a>
            <a href="index.html#processo">Processo <span>como funciona</span></a>
            <a href="index.html#sobre">Sobre <span>quem atende</span></a>
          </div>
          <div class="mobile-menu-group">
            <strong>Para psis</strong>
            <a href="supervisao.html">Supervisao <span>clinica</span></a>
            <a href="psireal-tcc.html">PsiReal TCC <span>plataforma</span></a>
            <a href="biblioteca-tcc/index.html">Biblioteca TCC <span>recursos</span></a>
          </div>
          <div class="mobile-menu-group">
            <strong>Para empresas</strong>
            <a href="corporativo.html">Corporativo <span>palestras</span></a>
          </div>
        </div>
        <a class="mobile-menu-cta" href="https://wa.me/5511947388423" target="_blank" rel="noopener">Agendar conversa</a>
      </div>
    `;
    document.body.appendChild(menu);
  }

  const menu = document.querySelector('[data-mobile-menu]');
  const openButton = document.querySelector('[data-mobile-menu-open]');
  const closeButtons = document.querySelectorAll('[data-mobile-menu-close]');

  if (!menu || !openButton) return;

  const setOpen = (isOpen) => {
    menu.classList.toggle('is-open', isOpen);
    document.body.style.overflow = isOpen ? 'hidden' : '';
    openButton.setAttribute('aria-expanded', String(isOpen));
  };

  openButton.addEventListener('click', () => setOpen(true));
  closeButtons.forEach((button) => button.addEventListener('click', () => setOpen(false)));
  menu.querySelectorAll('a').forEach((link) => link.addEventListener('click', () => setOpen(false)));
  window.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') setOpen(false);
  });
})();
