import os
import re

CSS_FILE = "styles.css"
SIGNUP_CSS = "signup.css"
SAFEMAP_CSS = "safemap.css"

def refine_css(file_path):
    if not os.path.exists(file_path):
        return

    with open(file_path, "r") as f:
        css = f.read()

    # Font change
    css = re.sub(
        r"@import url\('https://fonts.googleapis.com/css2\?family=Inter[^\)]+'\);",
        "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');",
        css
    )
    
    # Body font
    css = re.sub(
        r"font-family:\s*'Inter',\s*-apple-system,\s*BlinkMacSystemFont,\s*sans-serif;",
        "font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;",
        css
    )
    
    # Generic AI colors left over
    css = css.replace("rgba(168, 85, 247, 0.1)", "rgba(255, 255, 255, 0.04)")
    css = css.replace("rgba(168, 85, 247, 0.2)", "rgba(255, 255, 255, 0.1)")
    css = css.replace("rgba(168, 85, 247, 0.15)", "rgba(255, 255, 255, 0.06)")
    css = css.replace("rgba(168, 85, 247, 0.08)", "rgba(255, 255, 255, 0.03)")
    css = css.replace("rgba(168, 85, 247, 0.06)", "rgba(255, 255, 255, 0.02)")
    css = css.replace("rgba(236, 72, 153, 0.05)", "rgba(255, 255, 255, 0.02)")
    css = css.replace("rgba(236, 72, 153, 0.06)", "rgba(255, 255, 255, 0.02)")
    css = css.replace("var(--accent-secondary)", "#A1A1AA")
    
    # Glass effect change - make it solid instead of blurred for premium feel
    css = re.sub(
        r"--glass-bg:\s*rgba\(255, 255, 255, 0.03\);",
        "--glass-bg: #18181A;",
        css
    )
    css = re.sub(
        r"--glass-border:\s*rgba\(255, 255, 255, 0.08\);",
        "--glass-border: #27272A;",
        css
    )
    
    # Adjust titles for impeccable tyopgraphy
    css = re.sub(
        r"(\.section-title\s*\{[^}]+)letter-spacing:\s*-0\.03em;",
        r"\1letter-spacing: -0.04em;",
        css
    )
    css = re.sub(
        r"(\.hero-title\s*\{[^}]+)letter-spacing:\s*-0\.04em;",
        r"\1letter-spacing: -0.05em;",
        css
    )
    
    # Feature icons - crisp
    css = css.replace("rgba(236, 72, 153, 0.12)", "var(--bg-card)")
    css = css.replace("rgba(34, 211, 238, 0.12)", "var(--bg-card)")
    css = css.replace("rgba(34, 197, 94, 0.12)", "var(--bg-card)")
    
    with open(file_path, "w") as f:
        f.write(css)

for file in [CSS_FILE, SIGNUP_CSS, SAFEMAP_CSS]:
    refine_css(file)
print("Typography and colors refined.")
