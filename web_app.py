# """
# web_app.py — Minimal Flask WSGI wrapper for PythonAnywhere

# This provides a simple HTML upload form and returns a ZIP of generated
# thumbnails using the existing `thumbnail.create_thumbnail` function.

# Deploy this file to PythonAnywhere and point the web app WSGI entry to
# `web_app.app`.
# """

# import io
# import zipfile
# import tempfile
# from pathlib import Path
# from flask import Flask, request, send_file, render_template_string
# from PIL import Image

# # Import the core thumbnail function from thumbnail.py
# import sys
# sys.path.insert(0, str(Path(__file__).parent))
# from thumbnail import create_thumbnail

# app = Flask(__name__)

# INDEX_HTML = """
# <!doctype html>
# <title>WebP Thumbnail Creator</title>
# <h1>Upload images to create thumbnails</h1>
# <form method=post enctype=multipart/form-data action="/generate">
#   <label>Choose images (multiple allowed):</label><br>
#   <input type=file name=files multiple accept="image/*"><br><br>

#   <label>Max width (px):</label>
#   <input type=number name=width value=150 min=50 max=500><br><br>

#   <label>Quality (1-100):</label>
#   <input type=number name=quality value=1 min=1 max=100><br><br>

#   <label>Max size (KB, 0 to disable):</label>
#   <input type=number step=0.1 name=max_size_kb value=1.0 min=0><br><br>

#   <input type=submit value="Generate Thumbnails">
# </form>
# """

# @app.route('/')
# def index():
#     return render_template_string(INDEX_HTML)


# @app.route('/generate', methods=['POST'])
# def generate():
#     files = request.files.getlist('files') or []
#     width = int(request.form.get('width', 150))
#     quality = int(request.form.get('quality', 1))
#     try:
#         max_size_kb = float(request.form.get('max_size_kb', 1.0))
#     except Exception:
#         max_size_kb = 1.0

#     if not files:
#         return "No files uploaded", 400

#     # Create a zip in memory
#     zip_buffer = io.BytesIO()
#     with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
#         for uploaded in files:
#             # Save uploaded file to a temp file so thumbnail.create_thumbnail can read it
#             with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded.filename).suffix) as in_tmp:
#                 in_tmp.write(uploaded.read())
#                 in_tmp_path = Path(in_tmp.name)

#             # Prepare output temp path
#             with tempfile.NamedTemporaryFile(delete=False, suffix='.webp') as out_tmp:
#                 out_tmp_path = Path(out_tmp.name)

#             # Call the existing create_thumbnail function
#             result = create_thumbnail(
#                 input_path=in_tmp_path,
#                 output_path=out_tmp_path,
#                 width=width,
#                 height=None,
#                 quality=quality,
#                 max_size_kb=max_size_kb if max_size_kb > 0 else None,
#                 verbose=False,
#             )

#             if result.get('success'):
#                 # Read output bytes and add to zip
#                 with open(result['output_path'], 'rb') as f:
#                     data = f.read()
#                 arcname = Path(uploaded.filename).stem + '-thumbnail.webp'
#                 zf.writestr(arcname, data)

#     zip_buffer.seek(0)
#     return send_file(
#         zip_buffer,
#         mimetype='application/zip',
#         as_attachment=True,
#         download_name='thumbnails.zip',
#     )


# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=5000)
