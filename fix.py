import os

files = ["index.html", "signup.html", "safemap.html"]

for f in files:
    if os.path.exists(f):
        with open(f, "r") as file:
            content = file.read()
        
        # Revert 'in'
        content = content.replace('<i data-lucide="linkedin"></i>', 'in')
        content = content.replace('<i data-lucide="linkedin">', 'in') # My script did replace("in", '<i data-lucide="linkedin">') which produces something missing </i> as well, wait, my script did: "in": '<i data-lucide="linkedin"></i>' 
        # Actually my script mapped: '"in": \'<i data-lucide="linkedin"></i>\''
        content = content.replace('<i data-lucide="linkedin"></i>', 'in')
        
        # Revert any remaining messed up linkedin
        content = content.replace('<i data-lucide="linkedin">', 'in') 

        # Now precisely target the footer link for linkedin
        # <a href="#" class="footer-social" aria-label="LinkedIn">in</a>
        content = content.replace(
            '<a href="#" class="footer-social" aria-label="LinkedIn">in</a>',
            '<a href="#" class="footer-social" aria-label="LinkedIn"><i data-lucide="linkedin"></i></a>'
        )

        with open(f, "w") as file:
            file.write(content)
print("Fix applied")
