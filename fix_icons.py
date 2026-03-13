import re

with open('safemap.js', 'r') as f:
    content = f.read()

# Add a call to lucide.createIcons() at the end of generating zones
if 'lucide.createIcons();' not in content:
    content = content.replace('dangerLayerGroup.addLayer(marker);\n    });\n  }', 'dangerLayerGroup.addLayer(marker);\n    });\n    if (typeof lucide !== \'undefined\') lucide.createIcons();\n  }')
    content = content.replace('safeLayerGroup.addLayer(marker);\n    });\n  }', 'safeLayerGroup.addLayer(marker);\n    });\n    if (typeof lucide !== \'undefined\') lucide.createIcons();\n  }')
    
    content = content.replace('addTo(map);\n          userMarker.bindPopup', 'addTo(map);\n          userMarker.bindPopup')
    content = content.replace('updateDangerList();\n  }', 'updateDangerList();\n    if (typeof lucide !== \'undefined\') lucide.createIcons();\n  }')
    content = content.replace('updateSafeList();\n  }', 'updateSafeList();\n    if (typeof lucide !== \'undefined\') lucide.createIcons();\n  }')

# Also fix the initial marker creation to trigger lucide.createIcons()
content = content.replace('\n          }\n          map.setView([lat, lon], 15);\n', '\n          }\n          if (typeof lucide !== \'undefined\') lucide.createIcons();\n          map.setView([lat, lon], 15);\n')
content = content.replace('\n          }\n        }\n\n        container.classList.remove(\'active\');\n', '\n          }\n          if (typeof lucide !== \'undefined\') lucide.createIcons();\n        }\n\n        container.classList.remove(\'active\');\n')


with open('safemap.js', 'w') as f:
    f.write(content)
