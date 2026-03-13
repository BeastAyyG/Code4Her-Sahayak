/* ===== SAHAYAK - Interactive Scripts ===== */

document.addEventListener('DOMContentLoaded', () => {

  // ===== PARTICLE BACKGROUND =====
  const canvas = document.getElementById('bg-canvas');
  const ctx = canvas.getContext('2d');
  let particles = [];
  let mouseX = 0, mouseY = 0;

  function resizeCanvas() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  }
  resizeCanvas();
  window.addEventListener('resize', resizeCanvas);

  class Particle {
    constructor() {
      this.reset();
    }
    reset() {
      this.x = Math.random() * canvas.width;
      this.y = Math.random() * canvas.height;
      this.size = Math.random() * 1.5 + 0.5;
      this.speedX = (Math.random() - 0.5) * 0.3;
      this.speedY = (Math.random() - 0.5) * 0.3;
      this.opacity = Math.random() * 0.4 + 0.1;
      this.hue = Math.random() > 0.5 ? 270 : 330; // purple or pink
    }
    update() {
      this.x += this.speedX;
      this.y += this.speedY;
      if (this.x < 0 || this.x > canvas.width) this.speedX *= -1;
      if (this.y < 0 || this.y > canvas.height) this.speedY *= -1;
    }
    draw() {
      ctx.beginPath();
      ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
      ctx.fillStyle = `'rgba(255, 255, 255, ' + (this.opacity * 0.2) + ')'`;
      ctx.fill();
    }
  }

  // Create particles
  const particleCount = Math.min(80, Math.floor(window.innerWidth / 15));
  for (let i = 0; i < particleCount; i++) {
    particles.push(new Particle());
  }

  function drawConnections() {
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x;
        const dy = particles[i].y - particles[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 120) {
          ctx.beginPath();
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);
          ctx.strokeStyle = `rgba(255, 255, 255, ${0.06 * (1 - dist / 120)})`;
          ctx.lineWidth = 0.5;
          ctx.stroke();
        }
      }
    }
  }

  function animateParticles() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    particles.forEach(p => {
      p.update();
      p.draw();
    });
    drawConnections();
    requestAnimationFrame(animateParticles);
  }
  animateParticles();

  // Track mouse for future interactive features
  document.addEventListener('mousemove', (e) => {
    mouseX = e.clientX;
    mouseY = e.clientY;
  });


  // ===== NAVBAR SCROLL =====
  const navbar = document.getElementById('navbar');
  window.addEventListener('scroll', () => {
    if (window.scrollY > 50) {
      navbar.classList.add('scrolled');
    } else {
      navbar.classList.remove('scrolled');
    }
  });


  // ===== MOBILE MENU TOGGLE =====
  const menuToggle = document.getElementById('menuToggle');
  const navMenu = document.getElementById('navMenu');

  menuToggle.addEventListener('click', () => {
    navMenu.classList.toggle('active');
  });

  // Close menu on link click
  navMenu.querySelectorAll('a').forEach(link => {
    link.addEventListener('click', () => {
      navMenu.classList.remove('active');
    });
  });


  // ===== SMOOTH SCROLL =====
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
      e.preventDefault();
      const target = document.querySelector(this.getAttribute('href'));
      if (target) {
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });


  // ===== ACTIVE NAV LINK UPDATE =====
  const sections = document.querySelectorAll('section[id]');
  const navLinks = navMenu.querySelectorAll('a');

  window.addEventListener('scroll', () => {
    let current = '';
    sections.forEach(section => {
      const sectionTop = section.offsetTop - 120;
      if (window.scrollY >= sectionTop) {
        current = section.getAttribute('id');
      }
    });
    navLinks.forEach(link => {
      link.classList.remove('active');
      if (link.getAttribute('href') === `#${current}`) {
        link.classList.add('active');
      }
    });
  });


  // ===== SCROLL REVEAL (CSS-based, no JS opacity side effects) =====
  const revealObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        revealObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

  document.querySelectorAll('.reveal').forEach(el => revealObserver.observe(el));


  // ===== ANIMATED COUNTERS =====
  const counterElements = document.querySelectorAll('[data-target]');
  let countersAnimated = new Set();

  const counterObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting && !countersAnimated.has(entry.target)) {
        countersAnimated.add(entry.target);
        animateCounter(entry.target);
      }
    });
  }, { threshold: 0.5 });

  counterElements.forEach(el => counterObserver.observe(el));

  function animateCounter(el) {
    const target = parseFloat(el.dataset.target);
    const suffix = el.dataset.suffix || '';
    const isDecimal = el.dataset.decimal === 'true';
    const duration = 2000;
    const startTime = performance.now();

    function update(currentTime) {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);

      // Ease out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = eased * target;

      if (isDecimal) {
        el.textContent = current.toFixed(1) + suffix;
      } else if (target >= 1000) {
        el.textContent = Math.floor(current).toLocaleString() + suffix;
      } else {
        el.textContent = Math.floor(current) + suffix;
      }

      if (progress < 1) {
        requestAnimationFrame(update);
      }
    }

    requestAnimationFrame(update);
  }


  // ===== SOS BUTTON =====
  const sosBtn = document.getElementById('sosBtn');
  sosBtn.addEventListener('click', () => {
    // Simulate SOS activation
    sosBtn.style.transform = 'scale(0.95)';
    setTimeout(() => { sosBtn.style.transform = ''; }, 150);

    // Show a simulated alert
    const alert = document.createElement('div');
    alert.style.cssText = `
      position: fixed;
      top: 80px;
      left: 50%;
      transform: translateX(-50%) translateY(-20px);
      background: rgba(220, 38, 38, 0.15);
      border: 1px solid rgba(220, 38, 38, 0.3);
      backdrop-filter: blur(16px);
      padding: 14px 28px;
      border-radius: 12px;
      color: #fca5a5;
      font-family: 'Inter', sans-serif;
      font-size: 0.9rem;
      font-weight: 500;
      z-index: 9999;
      opacity: 0;
      transition: all 0.4s ease-out;
    `;
    alert.textContent = 'SOS Activated - Contacts Alerted';
    document.body.appendChild(alert);

    requestAnimationFrame(() => {
      alert.style.opacity = '1';
      alert.style.transform = 'translateX(-50%) translateY(0)';
    });

    setTimeout(() => {
      alert.style.opacity = '0';
      alert.style.transform = 'translateX(-50%) translateY(-20px)';
      setTimeout(() => alert.remove(), 400);
    }, 3000);
  });


  // ===== MAP TOGGLE BUTTONS =====
  const mapBtns = document.querySelectorAll('.map-toggle button');
  mapBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      mapBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
    });
  });


  // ===== QUICK MESSAGE BUTTONS =====
  const quickMsgBtns = document.querySelectorAll('.quick-msg');
  quickMsgBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      btn.style.background = 'rgba(255, 255, 255, 0.25)';
      btn.style.transform = 'scale(0.95)';
      setTimeout(() => {
        btn.style.background = '';
        btn.style.transform = '';
      }, 300);
    });
  });


  // ===== FEATURE CARD GLOW ON HOVER =====
  document.querySelectorAll('.feature-card').forEach(card => {
    card.addEventListener('mousemove', (e) => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      card.style.background = `radial-gradient(circle at ${x}px ${y}px, rgba(255, 255, 255, 0.06), var(--bg-card-hover))`;
    });
    card.addEventListener('mouseleave', () => {
      card.style.background = '';
    });
  });

});
