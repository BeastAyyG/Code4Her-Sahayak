import os
import re

CSS_FILE = "styles.css"
INDEX_FILE = "index.html"
SIGNUP_FILE = "signup.html"
SAFEMAP_FILE = "safemap.html"
JS_FILE = "script.js"

def update_css():
    with open(CSS_FILE, "r") as f:
        css = f.read()

    # Redesign variables
    replacements = {
        r"--bg-primary:\s*#07070e;": "--bg-primary: #050505;",
        r"--bg-secondary:\s*#0c0c18;": "--bg-secondary: #0A0A0B;",
        r"--bg-card:\s*rgba\(255, 255, 255, 0.03\);": "--bg-card: #0F0F11;",
        r"--bg-card-hover:\s*rgba\(255, 255, 255, 0.06\);": "--bg-card-hover: #18181B;",
        r"--border-subtle:\s*rgba\(255, 255, 255, 0.06\);": "--border-subtle: #27272A;",
        r"--border-glow:\s*rgba\(168, 85, 247, 0.3\);": "--border-glow: rgba(255, 255, 255, 0.1);",
        r"--text-primary:\s*#f0f0f5;": "--text-primary: #EDEDED;",
        r"--text-secondary:\s*rgba\(240, 240, 245, 0.6\);": "--text-secondary: #A1A1AA;",
        r"--accent-primary:\s*#a855f7;": "--accent-primary: #FFFFFF;",
        r"--gradient-hero:\s*linear-gradient[^;]+;": "--gradient-hero: linear-gradient(135deg, #FFFFFF 0%, #A1A1AA 100%);",
        
        # Rethink buttons
        r"\.btn-primary\s*\{[^}]+\}": ".btn-primary {\n  background: #EDEDED;\n  color: #050505;\n  font-weight: 500;\n  box-shadow: 0 4px 14px rgba(0,0,0,0.4);\n}",
        r"\.btn-primary:hover\s*\{[^}]+\}": ".btn-primary:hover {\n  background: #FFFFFF;\n  transform: translateY(-1px);\n}",
        r"\.btn-secondary\s*\{[^}]+\}": ".btn-secondary {\n  background: transparent;\n  color: #EDEDED;\n  border: 1px solid #3F3F46;\n}",
        r"\.btn-sos\s*\{[^}]+\}": ".btn-sos {\n  background: #E11D48;\n  color: white;\n  box-shadow: 0 4px 14px rgba(225, 29, 72, 0.4);\n  animation: none;\n}",
        r"\.btn-sos:hover\s*\{[^}]+\}": ".btn-sos:hover {\n  background: #BE123C;\n  transform: translateY(-1px);\n}",
        
        # Remove glow and bouncy animations typical of AI
        r"animation:\s*sos-pulse[^;]+;": "",
        r"animation:\s*pulse-dot[^;]+;": "",
        r"box-shadow: 0 30px 80px rgba\(0, 0, 0, 0.5\), 0 0 80px rgba\(168, 85, 247, 0.1\);": "box-shadow: 0 10px 40px rgba(0,0,0,0.8), 0 0 0 1px rgba(255,255,255,0.05);",
        r"background:\s*rgba\(168, 85, 247, 0.12\)[^;]*;": "background: #18181A;",
        r"background:\s*rgba\(236, 72, 153, 0.12\)[^;]*;": "background: #18181A;",
        r"background:\s*rgba\(34, 211, 238, 0.12\)[^;]*;": "background: #18181A;",
        r"background:\s*rgba\(34, 197, 94, 0.12\)[^;]*;": "background: #18181A;",
        r"box-shadow:\s*0 0 20px rgba\([^)]+\);": "border: 1px solid #27272A;",
        
        # Clean up chat bubbles
        r"\.chat-msg\.incoming\s*\{[^}]+\}": ".chat-msg.incoming {\n  background: #18181B;\n  border: 1px solid #27272A;\n  border-bottom-left-radius: 4px;\n  align-self: flex-start;\n  color: #EDEDED;\n}",
        r"\.chat-msg\.outgoing\s*\{[^}]+\}": ".chat-msg.outgoing {\n  background: #E11D48;\n  border-bottom-right-radius: 4px;\n  align-self: flex-end;\n  color: white;\n}",
    }

    for pattern, replacement in replacements.items():
        css = re.sub(pattern, replacement, css)

    with open(CSS_FILE, "w") as f:
        f.write(css)


def replace_html(file_path):
    if not os.path.exists(file_path):
        return

    with open(file_path, "r") as f:
        html = f.read()

    # Add Lucide and remove emojis
    emoji_map = {
        "🛡️": '<i data-lucide="shield"></i>',
        "🚨": '<i data-lucide="siren"></i>',
        "▶": '<i data-lucide="play"></i>',
        "📍": '<i data-lucide="map-pin"></i>',
        "✅": '<i data-lucide="check-circle"></i>',
        "🏛️": '<i data-lucide="building"></i>',
        "🏥": '<i data-lucide="hospital"></i>',
        "👮": '<i data-lucide="badge-check"></i>',
        "🎓": '<i data-lucide="graduation-cap"></i>',
        "💜": '<i data-lucide="heart"></i>',
        "🤖": '<i data-lucide="bot"></i>',
        "💬": '<i data-lucide="message-square"></i>',
        "👨‍👩‍👧": '<i data-lucide="users"></i>',
        "🧠": '<i data-lucide="activity"></i>',
        "🗣️": '<i data-lucide="mic"></i>',
        "⚡": '<i data-lucide="zap"></i>',
        "🗺️": '<i data-lucide="map"></i>',
        "💡": '<i data-lucide="lightbulb"></i>',
        "👥": '<i data-lucide="users"></i>',
        "⚠️": '<i data-lucide="alert-triangle"></i>',
        "🏠": '<i data-lucide="home"></i>',
        "📱": '<i data-lucide="smartphone"></i>',
        "📖": '<i data-lucide="book-open"></i>',
        "𝕏": '<i data-lucide="twitter"></i>',
        "📷": '<i data-lucide="instagram"></i>',
        "in": '<i data-lucide="linkedin"></i>',
        "⌨": '<i data-lucide="github"></i>',
        "➤": '<i data-lucide="send"></i>',
        "👁️": '<i data-lucide="eye"></i>'
    }

    for emoji, icon in emoji_map.items():
        html = html.replace(emoji, icon)

    # Inject lucide CSS styling for icons to match sizes
    if "<head>" in html and "lucide.min.js" not in html:
        lucide_script = '''
  <script src="https://unpkg.com/lucide@latest"></script>
  <style>
    i[data-lucide] { width: 1.2em; height: 1.2em; display: inline-block; vertical-align: middle; }
    .btn i[data-lucide], .btn-sos i[data-lucide] { width: 1em; height: 1em; margin-right: 6px; }
    .feature-icon i[data-lucide] { width: 1.5em; height: 1.5em; stroke-width: 1.5; color: #EDEDED; }
    .logo-icon i[data-lucide] { width: 20px; height: 20px; color: #FFF; }
  </style>
'''
        html = html.replace('</head>', lucide_script + '\n</head>')

    # Init Lucide
    if "</body>" in html and "lucide.createIcons()" not in html:
        init_script = '''
  <script>
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
  </script>
'''
        html = html.replace('</body>', init_script + '\n</body>')

    # Remove ai glow
    html = html.replace('<div class="hero-glow"></div>', '')

    with open(file_path, "w") as f:
        f.write(html)

def update_js():
    if not os.path.exists(JS_FILE): return
    with open(JS_FILE, "r") as f:
        js = f.read()

    # Disable particles lines, set stroke to gray
    js = js.replace("hsla(${this.hue}, 70%, 70%, ${this.opacity})", "'rgba(255, 255, 255, ' + (this.opacity * 0.2) + ')'")
    js = js.replace("rgba(168, 85, 247,", "rgba(255, 255, 255,")

    # Update create icons hook if dynamically adding stuff
    # Handle the SOS alert specifically where it injects emojis
    js = js.replace("'🚨 SOS Activated — Emergency contacts alerted!'", "'SOS Activated - Contacts Alerted'")

    with open(JS_FILE, "w") as f:
        f.write(js)

if __name__ == "__main__":
    update_css()
    for file in [INDEX_FILE, SIGNUP_FILE, SAFEMAP_FILE]:
        replace_html(file)
    update_js()
    print("Redesign complete.")
