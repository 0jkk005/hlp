import os
import zipfile

latex_dir = 'latex'
zip_path = os.path.join(latex_dir, 'IEEEtran_Submission_Package.zip')

# Remove existing zip if present
if os.path.exists(zip_path):
    os.remove(zip_path)

files_to_zip = [
    'bare_jrnl.tex',
    'references.bib',
    'IEEEtran.cls'
]

with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
    for f in files_to_zip:
        full_path = os.path.join(latex_dir, f)
        z.write(full_path, arcname=f)
        print(f"Added {f} ({os.path.getsize(full_path)} bytes)")

    figures_dir = os.path.join(latex_dir, 'figures')
    if os.path.exists(figures_dir):
        for fig in sorted(os.listdir(figures_dir)):
            fig_path = os.path.join(figures_dir, fig)
            if os.path.isfile(fig_path):
                arc_name = os.path.join('figures', fig)
                z.write(fig_path, arcname=arc_name)
                print(f"Added {arc_name} ({os.path.getsize(fig_path)} bytes)")

print(f"\nSuccessfully generated {zip_path} ({os.path.getsize(zip_path)} bytes)")
