import re

with open('safemap.js', 'r') as f:
    content = f.read()

# Replace Emojis in SAFE_PLACES
emoji_map = {
    '👮': 'shield-check',
    '🏥': 'hospital',
    '💊': 'pill',
    '🚇': 'train-track',
    '🛡️': 'shield',
    '🚒': 'flame',
    '🏪': 'store',
    '🏛️': 'landmark',
    '🔦': 'flashlight',
    '📞': 'phone-call',
    '🏧': 'credit-card',
    '⛽': 'fuel'
}

for emoji, lucide_name in emoji_map.items():
    content = content.replace(f"icon: '{emoji}'", f"icon: '{lucide_name}'")

# Replace Danger icons
content = content.replace("createCustomIcon('⚠️', 'marker-danger')", "createCustomIcon('alert-triangle', 'marker-danger')")
content = content.replace("createCustomIcon('📍', 'marker-user')", "createCustomIcon('user', 'marker-user')")
content = content.replace("createCustomIcon('🏁', 'marker-destination')", "createCustomIcon('map-pin', 'marker-destination')")

# Update popup titles that had emojis hardcoded
content = content.replace("`⚠️ ${zone.name}", "`<i data-lucide=\"alert-triangle\"></i> ${zone.name}")
content = content.replace("`${place.icon} ${place.name}", "`<i data-lucide=\"${place.icon}\"></i> ${place.name}")
content = content.replace("'📍 Your Location'", "'<i data-lucide=\"user\"></i> Your Location'")

with open('safemap.js', 'w') as f:
    f.write(content)
