(() => {
  const nav = document.querySelector('.site-nav, body > nav');
  const navLinks = nav?.querySelector('.nav-links');

  if (navLinks) {
    navLinks.innerHTML = `
      <div class="desktop-menu-group">
        <button class="desktop-menu-trigger" type="button">Pacientes <svg viewBox="0 0 24 24"><path d="m6 9 6 6 6-6"/></svg></button>
        <div class="desktop-menu-panel">
          <a href="terapia.html"><strong>Terapia</strong><span>Atendimento clínico</span></a>
          <a href="ansiedade.html"><strong>Ansiedade</strong><span>Guia para pacientes</span></a>
          <a href="index.html#processo"><strong>Processo</strong><span>Como funciona</span></a>
          <a href="index.html#sobre"><strong>Sobre</strong><span>Conheça a psicóloga</span></a>
        </div>
      </div>
      <div class="desktop-menu-group">
        <button class="desktop-menu-trigger" type="button">Psicólogas <svg viewBox="0 0 24 24"><path d="m6 9 6 6 6-6"/></svg></button>
        <div class="desktop-menu-panel">
          <a href="supervisao.html"><strong>Supervisão</strong><span>Desenvolvimento clínico</span></a>
          <a href="psireal-tcc.html"><strong>PsiReal TCC</strong><span>Plataforma clínica</span></a>
          <a href="https://michellepsicologiareal-collab.github.io/biblioteca-psi-real/"><strong>Biblioteca</strong><span>Materiais e recursos</span></a>
        </div>
      </div>
      <div class="desktop-menu-group">
        <button class="desktop-menu-trigger" type="button">Empresas <svg viewBox="0 0 24 24"><path d="m6 9 6 6 6-6"/></svg></button>
        <div class="desktop-menu-panel">
          <a href="corporativo.html"><strong>Corporativo</strong><span>Palestras e soluções</span></a>
        </div>
      </div>
      <a href="index.html#faq">FAQ</a>
      <a class="nav-cta" href="https://wa.me/5511947388423" target="_blank" rel="noopener">Agendar</a>
    `;
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
    menu.setAttribute('aria-label', 'Menu móvel');
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
            <a href="index.html#terapia">Terapia <span>clínica</span></a>
            <a href="ansiedade.html">Ansiedade <span>guia</span></a>
            <a href="index.html#processo">Processo <span>como funciona</span></a>
            <a href="index.html#sobre">Sobre <span>quem atende</span></a>
          </div>
          <div class="mobile-menu-group">
            <strong>Para psicólogas</strong>
            <a href="supervisao.html">Supervisão <span>clínica</span></a>
            <a href="psireal-tcc.html">PsiReal TCC <span>plataforma</span></a>
            <a href="https://michellepsicologiareal-collab.github.io/biblioteca-psi-real/">Biblioteca <span>recursos</span></a>
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
