"""
app.py — Gradio Web UI for the WebP Thumbnail Creator
=======================================================
This is a SEPARATE file from thumbnail.py.
It imports the core logic from thumbnail.py and wraps it
in a beautiful browser-based drag-and-drop interface.

Run:
    python3 app.py

Then open:  http://localhost:7860
Share on local network:  http://<your-ip>:7860
"""

import io
import os
import sys
import gradio as gr  # type: ignore[import-untyped]  # pyrefly: ignore[missing-import]
from pathlib import Path
from PIL import Image  # type: ignore[import-untyped]  # pyrefly: ignore[missing-import]

# ---------------------------------------------------------------------------
# Import core logic from thumbnail.py (no changes to thumbnail.py at all)
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent))
from thumbnail import create_thumbnail  # type: ignore[import-untyped]  # pyrefly: ignore[missing-import]

# ---------------------------------------------------------------------------
# Gradio processing function
# ---------------------------------------------------------------------------

def process_images(
    files,           # list of uploaded file paths from Gradio
    width: int,
    quality: int,
    max_size_kb: float,
):
    """
    Called by Gradio when the user clicks Generate.
    Processes each uploaded image ENTIRELY IN MEMORY — no disk storage needed.
    Returns:
      - A gallery of thumbnail previews
      - A summary text
      - A list of output file paths for download
    """
    if not files:
        return [], "⚠️ No images uploaded. Please upload at least one image.", []

    gallery_images = []   # PIL images for preview
    output_paths   = []   # temp file paths for download
    summary_lines  = ["### 📊 Results\n"]

    # Use system temp dir for ephemeral output (no persistent storage)
    import tempfile
    temp_dir = Path(tempfile.mkdtemp())

    for file_path in files:
        input_path  = Path(file_path)
        output_path = temp_dir / f"{input_path.stem}-thumbnail.webp"

        result = create_thumbnail(
            input_path  = input_path,
            output_path = output_path,
            width       = width,
            height      = None,           # always auto aspect ratio
            quality     = quality,
            max_size_kb = max_size_kb if max_size_kb > 0 else None,
            verbose     = False,
        )

        if result["success"]:
            # Load thumbnail as PIL image for gallery preview
            thumb_img = Image.open(str(result["output_path"]))
            gallery_images.append(thumb_img)
            output_paths.append(str(result["output_path"]))

            orig_kb   = result["original_bytes"] / 1024
            out_kb    = result["output_bytes"]   / 1024
            reduction = (
                ((result["original_bytes"] - result["output_bytes"]) / result["original_bytes"]) * 100
                if result["original_bytes"] > 0 else 0
            )

            summary_lines.append(
                f"✅ **{input_path.name}**  \n"
                f"&nbsp;&nbsp;&nbsp;`{result['final_width']}×{result['final_height']} px` | "
                f"`{result['output_bytes']} bytes ({out_kb:.2f} KB)` | "
                f"**{reduction:.1f}% smaller**"
            )
        else:
            summary_lines.append(f"❌ **{input_path.name}** — {result['error']}")

    summary = "\n\n".join(summary_lines)
    return gallery_images, summary, output_paths


# ---------------------------------------------------------------------------
# Build Gradio UI
# ---------------------------------------------------------------------------

def build_ui():
    with gr.Blocks(
        title="🖼️ WebP Thumbnail Creator",
    ) as demo:

        # ── Header ────────────────────────────────────────────────────────
        gr.HTML("""
        <div style="text-align:center; padding: 20px 0 10px 0;">
            <h1 style="font-size:2rem; font-weight:700; margin:0;">
                🖼️ WebP Thumbnail Creator
            </h1>
            <p style="color:#6b7280; margin-top:6px; font-size:1rem;">
                Drag &amp; drop images → get under 150×150 px, under 1 KB thumbnails instantly
            </p>
        </div>
        """)

        # ── Main layout ───────────────────────────────────────────────────
        with gr.Row():

            # Left column — inputs
            with gr.Column(scale=1):
                gr.Markdown("### 📤 Upload Images")
                upload = gr.File(
                    label="Drop images here (PNG, JPG, WEBP, BMP…)",
                    file_types=["image"],
                    file_count="multiple",
                    height=200,
                )

                gr.Markdown("### ⚙️ Settings")
                with gr.Row():
                    width_slider = gr.Slider(
                        minimum=50, maximum=500, value=150, step=10,
                        label="Max Width (px)",
                    )
                    quality_slider = gr.Slider(
                        minimum=1, maximum=100, value=1, step=1,
                        label="Quality (1=smallest)",
                    )

                max_size_input = gr.Number(
                    value=1.0,
                    label="Max File Size (KB) — set 0 to disable",
                    minimum=0,
                    precision=1,
                )

                generate_btn = gr.Button(
                    "⚡ Generate Thumbnails",
                    variant="primary",
                    size="lg",
                )

            # Right column — outputs
            with gr.Column(scale=1):
                gr.Markdown("### 📥 Thumbnail Previews")
                gallery = gr.Gallery(
                    label="Generated Thumbnails",
                    columns=3,
                    height=250,
                    object_fit="contain",
                )
                summary_md = gr.Markdown("_Results will appear here after generating..._")

                gr.Markdown("### 💾 Download")
                download_files = gr.File(
                    label="Download Thumbnails",
                    file_count="multiple",
                    interactive=False,
                )

        # ── Info footer ───────────────────────────────────────────────────
        gr.Markdown("""
        ---
        **💡 Tips:**
        - All thumbnails are also saved to the `output/` folder automatically
        - Default: max **150×150 px** + max **1 KB** file size
        - Aspect ratio is always preserved

        <div style="text-align:center; margin-top:12px; font-size:0.82rem; color:#6b7280;">
            Built with ❤️ by <strong>Dinanath Mishra</strong>
        </div>
        """)

        # ── Wire up button ────────────────────────────────────────────────
        generate_btn.click(
            fn       = process_images,
            inputs   = [upload, width_slider, quality_slider, max_size_input],
            outputs  = [gallery, summary_md, download_files],
        )

    return demo


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 50)
    print("  🖼️  WebP Thumbnail Creator — Web UI")
    print("=" * 50)
    print()

    demo = build_ui()
    port = int(os.environ.get("PORT", 7860))

    demo.launch(
        server_name = "0.0.0.0",
        server_port = port,
        share       = False,
        inbrowser   = False,
        show_error  = True,
        theme       = gr.themes.Soft(
            primary_hue   = "violet",
            secondary_hue = "indigo",
            neutral_hue   = "slate",
        ),
    )
