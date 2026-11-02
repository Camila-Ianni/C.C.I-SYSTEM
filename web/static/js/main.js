/**
 * C.C.I. SYSTEM — Interactive Client-side Script
 * Autora: Camila Carolina Ianni
 */

document.addEventListener('DOMContentLoaded', () => {
  // 1. Filtrado de juegos por categoría
  const filterBtns = document.querySelectorAll('.filter-btn');
  const gameCards = document.querySelectorAll('.game-card');

  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const selectedCat = btn.dataset.cat.toUpperCase();

      gameCards.forEach(card => {
        const cardCats = (card.dataset.categories || '').toUpperCase().split(' ');
        if (selectedCat === 'TODOS' || cardCats.includes(selectedCat)) {
          card.style.display = 'flex';
          card.style.animation = 'fadeIn 0.3s ease';
        } else {
          card.style.display = 'none';
        }
      });
    });
  });

  // 2. Modal interactivo de ficha de juego
  const modal = document.getElementById('gameModal');
  const modalClose = document.getElementById('modalClose');
  const modalImg = document.getElementById('modalImg');
  const modalTitle = document.getElementById('modalTitle');
  const modalYear = document.getElementById('modalYear');
  const modalGenre = document.getElementById('modalGenre');
  const modalPlayers = document.getElementById('modalPlayers');
  const modalDev = document.getElementById('modalDev');
  const modalDesc = document.getElementById('modalDesc');

  function openModal(card) {
    const title = card.dataset.title;
    const genre = card.dataset.genre;
    const dev = card.dataset.dev;
    const year = card.dataset.year;
    const players = card.dataset.players;
    const desc = card.dataset.desc;
    const imgSrc = card.querySelector('img').src;

    modalTitle.textContent = title;
    modalGenre.textContent = genre;
    modalDev.textContent = `Desarrollador: ${dev}`;
    modalYear.textContent = year;
    modalPlayers.textContent = `${players} Jugador(es)`;
    modalDesc.textContent = desc;
    modalImg.src = imgSrc;
    modalImg.alt = title;

    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
  }

  function closeModal() {
    modal.style.display = 'none';
    document.body.style.overflow = '';
  }

  gameCards.forEach(card => {
    card.addEventListener('click', () => openModal(card));
  });

  if (modalClose) {
    modalClose.addEventListener('click', closeModal);
  }

  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        closeModal();
      }
    });
  }

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && modal && modal.style.display === 'flex') {
      closeModal();
    }
  });

  // 3. Highlight enlace activo al scrollear
  const sections = document.querySelectorAll('section[id]');
  const navLinks = document.querySelectorAll('.nav-link');

  window.addEventListener('scroll', () => {
    const scrollY = window.pageYOffset;
    sections.forEach(current => {
      const sectionHeight = current.offsetHeight;
      const sectionTop = current.offsetTop - 120;
      const sectionId = current.getAttribute('id');

      if (scrollY > sectionTop && scrollY <= sectionTop + sectionHeight) {
        navLinks.forEach(link => {
          link.classList.remove('active');
          if (link.getAttribute('href') === `#${sectionId}`) {
            link.classList.add('active');
          }
        });
      }
    });
  });
});
