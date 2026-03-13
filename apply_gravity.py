import os
import re

html_files = ["index.html", "signup.html", "safemap.html"]

gsap_scripts = """
    <!-- GSAP for Smooth Motion & Motion Magic -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/gsap.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/ScrollTrigger.min.js"></script>
    <script src="gravity.js"></script>
</body>
"""

for f in html_files:
    if os.path.exists(f):
        with open(f, "r") as file:
            content = file.read()
        
        # Add GSAP and gravity.js before </body> if not already there
        if "gravity.js" not in content and "</body>" in content:
            content = content.replace("</body>", gsap_scripts)
            
        with open(f, "w") as file:
            file.write(content)

# Update script.js to remove IntersectionObserver for .reveal mapping (we will do it via GSAP)
if os.path.exists("script.js"):
    with open("script.js", "r") as file:
        script_js = file.read()
    
    script_js = re.sub(r"// ===== SCROLL REVEAL =====.*?(?=(// ===== |\Z))", "", script_js, flags=re.DOTALL | re.MULTILINE)
    
    with open("script.js", "w") as file:
        file.write(script_js)

# Update styles.css to clean up static animations and prep 3D classes
if os.path.exists("styles.css"):
    with open("styles.css", "r") as file:
        styles = file.read()
    
    # Remove static fadeInUp implementations
    styles = re.sub(r"animation:\s*fadeInUp[^;]+;", "", styles)
    styles = re.sub(r"transform:\s*translateY\([^)]+\);", "/* handled by GSAP */", styles)
    
    # Add prep classes for 3D
    prep_styles = """
/* Gravity 3D Utilities */
.hero-phone, .feature-card, .step-card {
    will-change: transform;
    transform-style: preserve-3d;
}
.btn {
    will-change: transform;
}
"""
    if "Gravity 3D Utilities" not in styles:
        styles += prep_styles
        
    with open("styles.css", "w") as file:
        file.write(styles)

# Create gravity.js
gravity_js = """
/* ===== ANTIGRAVITY & DESIGN SPELLS ===== */
/* Powered by GSAP */

document.addEventListener('DOMContentLoaded', () => {
    
    // 1. MAGENTIC BUTTON SPELL 🧲
    // Gives buttons a subtle physics-based pull when the user hovers over them
    const magneticElements = document.querySelectorAll('.btn, .logo-icon, .btn-social');
    
    magneticElements.forEach(el => {
        el.addEventListener('mousemove', (e) => {
            const rect = el.getBoundingClientRect();
            // Calculate cursor position relative to the center of the button
            const x = e.clientX - rect.left - rect.width / 2;
            const y = e.clientY - rect.top - rect.height / 2;
            
            // Move the button slightly towards the cursor
            gsap.to(el, {
                x: x * 0.3,
                y: y * 0.3,
                rotation: x * 0.05,
                ease: 'power2.out',
                duration: 0.3
            });
        });
        
        el.addEventListener('mouseleave', () => {
            // Spring back into place
            gsap.to(el, {
                x: 0,
                y: 0,
                rotation: 0,
                ease: 'elastic.out(1, 0.3)',
                duration: 1
            });
        });
    });

    // 2. 3D TILT EFFECT 🌌 (Antigravity spatial design)
    // Applied to feature cards and the hero phone to give them depth (parallax effect on mousemove)
    const tiltElements = document.querySelectorAll('.feature-card, .hero-phone, .step-card, .signup-form-wrapper');
    
    tiltElements.forEach(el => {
        el.addEventListener('mousemove', (e) => {
            const rect = el.getBoundingClientRect();
            // Get position normalized from -1 to 1
            const x = (e.clientX - rect.left) / rect.width - 0.5;
            const y = (e.clientY - rect.top) / rect.height - 0.5;
            
            // Gentle spatial rotation on X and Y axes
            gsap.to(el, {
                rotationY: x * 15,
                rotationX: -y * 15,
                transformPerspective: 1000,
                ease: 'power1.out',
                duration: 0.4
            });
        });
        
        el.addEventListener('mouseleave', () => {
            gsap.to(el, {
                rotationY: 0,
                rotationX: 0,
                ease: 'power3.out',
                duration: 0.6
            });
        });
    });

    // 3. BUTTERY SCROLL REVEALS 🌬️
    gsap.registerPlugin(ScrollTrigger);

    // Fade in text elements sequentially
    const revealTitles = document.querySelectorAll('.section-label, .section-title, .section-description, .brand-title');
    revealTitles.forEach(el => {
        gsap.fromTo(el, 
            { y: 30, opacity: 0 },
            {
                y: 0, 
                opacity: 1,
                duration: 1,
                ease: 'power3.out',
                scrollTrigger: {
                    trigger: el,
                    start: 'top 85%',
                    toggleActions: 'play none none none'
                }
            }
        );
    });

    // Staggered grid reveals for cards (domino effect)
    const grids = document.querySelectorAll('.features-grid, .steps-container, .stats-grid, .brand-features');
    grids.forEach(grid => {
        const cards = grid.children;
        gsap.fromTo(cards, 
            { y: 50, opacity: 0, rotationX: 10 },
            {
                y: 0, 
                opacity: 1,
                rotationX: 0,
                stagger: 0.1,
                duration: 0.8,
                ease: 'power2.out',
                scrollTrigger: {
                    trigger: grid,
                    start: 'top 80%',
                    toggleActions: 'play none none none'
                }
            }
        );
    });

    // Specific Hero Animations
    const tl = gsap.timeline();
    tl.from('.hero-badge, .navbar-logo', { y: -20, opacity: 0, duration: 0.6, ease: 'power2.out' })
      .from('.hero-title', { y: 30, opacity: 0, duration: 0.8, ease: 'power3.out' }, '-=0.2')
      .from('.hero-subtitle', { y: 20, opacity: 0, duration: 0.6, ease: 'power2.out' }, '-=0.4')
      .from('.hero-actions .btn', { y: 20, opacity: 0, duration: 0.5, stagger: 0.1, ease: 'back.out(1.7, 0.3)' }, '-=0.2')
      .from('.hero-stats .hero-stat', { opacity: 0, y: 15, duration: 0.5, stagger: 0.1 }, '-=0.3')
      .from('.hero-phone', { y: 50, opacity: 0, rotationY: -15, duration: 1, ease: 'power3.out' }, '-=1');
      
    // Floating cards parallax on scroll
    gsap.to('.floating-card', {
        yPercent: -30,
        ease: 'none',
        scrollTrigger: {
            trigger: '.hero',
            start: 'top top',
            end: 'bottom top',
            scrub: true
        }
    });

});
"""

with open("gravity.js", "w") as f:
    f.write(gravity_js)

print("Gravity injected across all pages.")
