/* ===== ANTIGRAVITY & DESIGN SPELLS ===== */
/* Pure CSS animations + GSAP only for hover micro-interactions */
/* NO scroll-based opacity changes - content always visible */

document.addEventListener('DOMContentLoaded', () => {

    if (typeof gsap === 'undefined') return;

    // ─── Reduced motion guard ────────────────────────────────────────────────
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    // ─── 1. MAGNETIC BUTTON SPELL 🧲 ────────────────────────────────────────
    // Purely hover-based pull - no opacity changes, no visible-state changes
    document.querySelectorAll('.btn, .btn-social, .logo-icon').forEach(el => {
        el.addEventListener('mousemove', e => {
            const r = el.getBoundingClientRect();
            const x = (e.clientX - r.left - r.width / 2) * 0.25;
            const y = (e.clientY - r.top - r.height / 2) * 0.25;
            gsap.to(el, { x, y, rotation: x * 0.04, ease: 'power2.out', duration: 0.25, overwrite: true });
        });
        el.addEventListener('mouseleave', () => {
            gsap.to(el, { x: 0, y: 0, rotation: 0, ease: 'elastic.out(1, 0.4)', duration: 0.9, overwrite: true });
        });
    });

    // ─── 2. 3D CARD TILT 🌌 ─────────────────────────────────────────────────
    // Applied to visual elements only - no opacity side effects
    document.querySelectorAll(
        '.feature-card, .hero-phone, .step-card, .signup-form-wrapper, .ai-chat-mockup, .map-mockup, .stat-card, .phone-frame'
    ).forEach(el => {
        el.style.willChange = 'transform';
        el.addEventListener('mousemove', e => {
            const r = el.getBoundingClientRect();
            const x = (e.clientX - r.left) / r.width - 0.5;
            const y = (e.clientY - r.top) / r.height - 0.5;
            gsap.to(el, {
                rotationY: x * 10, rotationX: -y * 10,
                transformPerspective: 1000,
                ease: 'power1.out', duration: 0.35, overwrite: true
            });
        });
        el.addEventListener('mouseleave', () => {
            gsap.to(el, {
                rotationY: 0, rotationX: 0,
                ease: 'power3.out', duration: 0.6, overwrite: true
            });
        });
    });

    // ─── 3. QUICK MESSAGE BUTTON CLICK FEEDBACK ──────────────────────────────
    document.querySelectorAll('.quick-msg').forEach(btn => {
        btn.addEventListener('click', () => {
            gsap.timeline()
                .to(btn, { scale: 0.94, duration: 0.1 })
                .to(btn, { scale: 1, ease: 'elastic.out(1, 0.3)', duration: 0.5 });
        });
    });

    // ─── 4. SOS BUTTON CLICK FEEDBACK ────────────────────────────────────────
    const sosBtn = document.querySelector('.btn-sos');
    if (sosBtn) {
        sosBtn.addEventListener('mousedown', () => {
            gsap.to(sosBtn, { scale: 0.92, duration: 0.1 });
        });
        sosBtn.addEventListener('mouseup', () => {
            gsap.to(sosBtn, { scale: 1, ease: 'elastic.out(1, 0.3)', duration: 0.6 });
        });
    }

    // ─── 5. NAVBAR LETTER SPACING EFFECT ────────────────────────────────────
    const logo = document.querySelector('.navbar-logo');
    if (logo) {
        logo.addEventListener('mouseenter', () => {
            gsap.to(logo, { letterSpacing: '0.04em', duration: 0.35, ease: 'power2.out' });
        });
        logo.addEventListener('mouseleave', () => {
            gsap.to(logo, { letterSpacing: '-0.02em', duration: 0.35, ease: 'power2.inOut' });
        });
    }

    // ─── 6. FEATURE CARD BORDER GLOW ON HOVER ───────────────────────────────
    document.querySelectorAll('.feature-card').forEach(card => {
        card.addEventListener('mousemove', e => {
            const r = card.getBoundingClientRect();
            const x = e.clientX - r.left;
            const y = e.clientY - r.top;
            card.style.background = `radial-gradient(circle at ${x}px ${y}px, #1a1a1d 0%, #0F0F11 60%)`;
        });
        card.addEventListener('mouseleave', () => {
            card.style.background = '';
        });
    });

});
