#!/usr/bin/env python3
"""
thumbnail.py — Web-optimized WebP Thumbnail Creator
====================================================
A command-line tool to resize, compress, and export images as WebP thumbnails.

Features:
  - Single image processing or batch folder processing
  - Configurable width, height, quality
  - Auto aspect-ratio preservation
  - Optional --max-size loop to shrink until under a target file size
  - Summary: original size vs. output size vs. % reduction

Dependencies:
  pip install Pillow

Author: You :)
"""

import argparse
import os
import sys
import io
from pathlib import Path
from PIL import Image, UnidentifiedImageError  # type: ignore[import-untyped]  # pyrefly: ignore[missing-import]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Supported input image extensions (case-insensitive)
SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tiff"}

# Default folders (relative to where thumbnail.py lives)
# Drop images into `input/` and results go to `output/`
SCRIPT_DIR         = Path(__file__).parent.resolve()
DEFAULT_INPUT_DIR  = SCRIPT_DIR / "input"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "output"


# ANSI color codes for prettier terminal output
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def human_size(num_bytes: int) -> str:
    """Convert bytes to a human-readable KB string."""
    kb = num_bytes / 1024
    return f"{num_bytes} bytes ({kb:.2f} KB)"


def is_image_file(path: Path) -> bool:
    """Return True if the file extension is a supported image format."""
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def compute_dimensions(original_w: int, original_h: int,
                       target_w: int, target_h: int | None) -> tuple[int, int]:
    """
    Compute the final (width, height) for resizing.

    - If only target_w is given → preserve aspect ratio.
    - If both target_w and target_h are given → use exact dimensions (caller
      will crop/pad as needed via thumbnail() or resize()).
    """
    if target_h is None:
        # Auto-calculate height from aspect ratio
        ratio = target_w / original_w
        new_h = max(1, int(original_h * ratio))
        return target_w, new_h
    else:
        return target_w, target_h


def resize_image(img: Image.Image, width: int, height: int | None) -> Image.Image:
    """
    Resize the image to fit within the given dimensions, maintaining aspect ratio.

    - If height is None → fit within a (width × width) bounding box.
      Both width AND height will be ≤ width. Works for landscape AND portrait.
      Example: width=150 → landscape 1672×941 becomes 150×84
                          → portrait  941×1672 becomes 84×150  ✓
    - If height is given → resize to exact dimensions (may distort aspect ratio).
    """
    if height is None:
        # Fit within a square bounding box: max(width, height) ≤ width
        # PIL's thumbnail() handles both orientations correctly
        img_copy = img.copy()
        img_copy.thumbnail((width, width), Image.LANCZOS)
        return img_copy
    else:
        # Force exact dimensions (user explicitly set --height)
        return img.resize((width, height), Image.LANCZOS)


def convert_to_rgb(img: Image.Image) -> Image.Image:
    """
    Convert image to RGB mode if necessary.
    WebP supports RGBA but not palette/P mode directly.
    We keep RGBA (transparency) and convert everything else to RGB.
    """
    if img.mode in ("RGB", "RGBA"):
        return img
    elif img.mode == "P":
        # Palette mode — convert via RGBA to preserve any transparency
        img = img.convert("RGBA")
    if img.mode == "RGBA":
        return img
    return img.convert("RGB")


def save_webp(img: Image.Image, output_path: Path, quality: int) -> int:
    """
    Save image as WebP with the given quality.
    Returns the final file size in bytes.
    """
    img.save(str(output_path), format="WEBP", quality=quality, method=6)
    return output_path.stat().st_size


def save_webp_to_bytes(img: Image.Image, quality: int) -> int:
    """
    Save image to an in-memory buffer (for size estimation without writing disk).
    Returns the byte size of the resulting WebP.
    """
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=quality, method=6)
    return buf.tell()


# ---------------------------------------------------------------------------
# Core thumbnail-creation logic
# ---------------------------------------------------------------------------

def create_thumbnail(
    input_path: Path,
    output_path: Path,
    width: int,
    height: int | None,
    quality: int,
    max_size_kb: float | None,
    verbose: bool = True,
) -> dict:
    """
    Process a single image: resize → compress → save as WebP.

    Returns a dict with keys:
        input_path, output_path, original_bytes, output_bytes,
        final_quality, final_width, final_height, success, error
    """
    result = {
        "input_path":    input_path,
        "output_path":   output_path,
        "original_bytes": 0,
        "output_bytes":   0,
        "final_quality":  quality,
        "final_width":    width,
        "final_height":   height,
        "success":        False,
        "error":          None,
    }

    # ── 1. Validate input ──────────────────────────────────────────────────
    if not input_path.exists():
        result["error"] = f"File not found: {input_path}"
        return result

    if not is_image_file(input_path):
        result["error"] = f"Unsupported file format: {input_path.suffix}"
        return result

    result["original_bytes"] = input_path.stat().st_size

    # ── 2. Open image ──────────────────────────────────────────────────────
    try:
        img = Image.open(str(input_path))
        img.load()  # force decode — catches corrupt images early
    except UnidentifiedImageError:
        result["error"] = f"Cannot identify image file (corrupt or unsupported): {input_path}"
        return result
    except Exception as e:
        result["error"] = f"Error opening image: {e}"
        return result

    # ── 3. Convert mode ────────────────────────────────────────────────────
    img = convert_to_rgb(img)

    # ── 4. Resize ──────────────────────────────────────────────────────────
    img = resize_image(img, width, height)
    result["final_width"], result["final_height"] = img.size

    # ── 5. Ensure output directory exists ──────────────────────────────────
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # ── 6. Handle --max-size loop ──────────────────────────────────────────
    if max_size_kb is not None and max_size_kb > 0:
        max_bytes = max_size_kb * 1024
        current_quality = quality
        current_img = img
        iteration = 0
        max_iterations = 50  # safety cap to avoid infinite loops

        if verbose:
            print(f"  {CYAN}→ Targeting max size: {max_size_kb} KB{RESET}")

        while iteration < max_iterations:
            estimated = save_webp_to_bytes(current_img, current_quality)

            if verbose:
                print(f"    Attempt {iteration+1}: quality={current_quality}, "
                      f"size={estimated/1024:.2f} KB ({estimated} bytes)")

            if estimated <= max_bytes:
                # We're under the limit — save for real
                final_bytes = save_webp(current_img, output_path, current_quality)
                result["output_bytes"]  = final_bytes
                result["final_quality"] = current_quality
                result["final_width"], result["final_height"] = current_img.size
                result["success"] = True
                if verbose:
                    print(f"  {GREEN}✓ Target achieved at quality={current_quality}{RESET}")
                return result

            # Still too big — try reducing quality first, then dimensions
            if current_quality > 1:
                # Drop quality by 5 (or to minimum 1)
                current_quality = max(1, current_quality - 5)
            else:
                # Quality already at minimum — shrink dimensions by 10%
                cw, ch = current_img.size
                new_cw = max(1, int(cw * 0.9))
                new_ch = max(1, int(ch * 0.9))
                if new_cw == cw and new_ch == ch:
                    # Can't shrink further
                    break
                current_img = img.resize((new_cw, new_ch), Image.LANCZOS)
                if verbose:
                    print(f"    Resizing to {new_cw}×{new_ch} (quality at minimum)")

            iteration += 1

        # Fell through the loop — save best effort anyway
        if verbose:
            print(f"  {YELLOW}⚠ Could not reach {max_size_kb} KB target — saving best effort.{RESET}")
        final_bytes = save_webp(current_img, output_path, current_quality)
        result["output_bytes"]  = final_bytes
        result["final_quality"] = current_quality
        result["final_width"], result["final_height"] = current_img.size
        result["success"] = True
        return result

    # ── 7. Normal save (no max-size loop) ──────────────────────────────────
    try:
        final_bytes = save_webp(img, output_path, quality)
        result["output_bytes"]  = final_bytes
        result["success"] = True
    except Exception as e:
        result["error"] = f"Error saving image: {e}"

    return result


# ---------------------------------------------------------------------------
# Summary printing
# ---------------------------------------------------------------------------

def print_result_summary(result: dict):
    """Print a formatted summary for a single processed image."""
    input_path  = result["input_path"]
    output_path = result["output_path"]

    if not result["success"]:
        print(f"  {RED}✗ FAILED: {result['error']}{RESET}")
        return

    orig  = result["original_bytes"]
    final = result["output_bytes"]

    if orig > 0:
        reduction = ((orig - final) / orig) * 100
    else:
        reduction = 0.0

    print(f"  {BOLD}Input : {RESET}{input_path.name}  ({human_size(orig)})")
    print(f"  {BOLD}Output: {RESET}{output_path.name}  ({human_size(final)})")
    print(f"  {BOLD}Dims  : {RESET}{result['final_width']}×{result['final_height']} px  "
          f"| Quality: {result['final_quality']}")
    if reduction > 0:
        print(f"  {GREEN}{BOLD}Saved : {reduction:.1f}% reduction{RESET}")
    else:
        print(f"  {YELLOW}Note  : Output is larger than input (very small original){RESET}")


def print_batch_summary(results: list[dict]):
    """Print an aggregate summary for batch processing."""
    total       = len(results)
    succeeded   = [r for r in results if r["success"]]
    failed      = [r for r in results if not r["success"]]
    total_orig  = sum(r["original_bytes"] for r in succeeded)
    total_final = sum(r["output_bytes"]   for r in succeeded)

    print()
    print(f"{BOLD}{'─'*55}{RESET}")
    print(f"{BOLD}  BATCH SUMMARY{RESET}")
    print(f"{'─'*55}")
    print(f"  Processed : {total} file(s)")
    print(f"  {GREEN}Succeeded : {len(succeeded)}{RESET}")
    if failed:
        print(f"  {RED}Failed    : {len(failed)}{RESET}")
        for r in failed:
            print(f"    • {r['input_path'].name}: {r['error']}")
    if total_orig > 0:
        overall_reduction = ((total_orig - total_final) / total_orig) * 100
        print(f"  Total input size  : {human_size(total_orig)}")
        print(f"  Total output size : {human_size(total_final)}")
        print(f"  {GREEN}{BOLD}Overall reduction : {overall_reduction:.1f}%{RESET}")
    print(f"{'─'*55}")


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="thumbnail.py",
        description=(
            "Create web-optimized WebP thumbnails from common image formats.\n"
            "Supports single-file and batch (folder) processing.\n\n"
            "DEFAULT MODE (no arguments):\n"
            "  Drop images into the `input/` folder next to this script,\n"
            "  then just run:  python3 thumbnail.py\n"
            "  Results are saved to the `output/` folder automatically."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 thumbnail.py                          # auto: input/ → output/
  python3 thumbnail.py -i banner.png -w 120 -q 1
  python3 thumbnail.py -i banner.png --max-size 1
  python3 thumbnail.py --input-dir ./originals --output-dir ./thumbnails -w 150
        """,
    )

    # ── Input / output ─────────────────────────────────────────────────────
    # NOTE: required=False — if neither is given, we use the default input/ folder
    input_group = parser.add_mutually_exclusive_group(required=False)
    input_group.add_argument(
        "-i", "--input",
        type=Path,
        metavar="FILE",
        help="Path to a single source image (PNG, JPG, JPEG, WEBP, …)",
    )
    input_group.add_argument(
        "--input-dir",
        type=Path,
        metavar="DIR",
        help="Path to a folder of images to process in batch mode",
    )

    parser.add_argument(
        "-o", "--output",
        type=Path,
        metavar="FILE",
        default=None,
        help=(
            "Output filename for single-file mode "
            "(default: <original-name>-thumbnail.webp)"
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        metavar="DIR",
        default=None,
        help="Output folder for batch mode (default: same as --input-dir)",
    )

    # ── Resize options ─────────────────────────────────────────────────────
    parser.add_argument(
        "-w", "--width",
        type=int,
        default=150,
        metavar="PX",
        help="Target width in pixels (default: 150)",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=None,
        metavar="PX",
        help=(
            "Target height in pixels. If omitted, auto-calculated from "
            "aspect ratio. If given, image is resized to exact dimensions."
        ),
    )

    # ── Quality / size options ─────────────────────────────────────────────
    parser.add_argument(
        "-q", "--quality",
        type=int,
        default=1,
        choices=range(1, 101),
        metavar="1-100",
        help="WebP compression quality 1–100 (default: 1 for smallest files)",
    )
    parser.add_argument(
        "--max-size",
        type=float,
        default=1.0,
        metavar="KB",
        help=(
            "Target maximum output file size in KB (default: 1.0). "
            "Quality and dimensions are automatically reduced until under this limit. "
            "Set to 0 to disable."
        ),
    )

    # ── Misc ───────────────────────────────────────────────────────────────
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress detailed per-attempt output (only show summary)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-process all images even if a thumbnail already exists in output/",
    )

    return parser


# ---------------------------------------------------------------------------
# Default output path helper
# ---------------------------------------------------------------------------

def default_output_path(input_path: Path, output_dir: Path | None = None) -> Path:
    """
    Build a default output path: <stem>-thumbnail.webp
    Placed in output_dir if given, else same directory as input.
    """
    stem = input_path.stem
    filename = f"{stem}-thumbnail.webp"
    if output_dir:
        return output_dir / filename
    return input_path.parent / filename


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = build_parser()
    args = parser.parse_args()

    verbose = not args.quiet

    # ── DEFAULT MODE: no -i and no --input-dir → use input/ → output/ ───────
    if not args.input and not args.input_dir:
        # Auto-create the default folders if they don't exist yet
        DEFAULT_INPUT_DIR.mkdir(parents=True, exist_ok=True)
        DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        print(f"{BOLD}Default mode: reading from  → {DEFAULT_INPUT_DIR}{RESET}")
        print(f"{BOLD}             saving  to    → {DEFAULT_OUTPUT_DIR}{RESET}")
        print()

        all_files   = sorted(DEFAULT_INPUT_DIR.iterdir())
        image_files = [f for f in all_files if f.is_file() and is_image_file(f)]
        skipped     = [f for f in all_files if f.is_file() and not is_image_file(f)]

        if not image_files:
            print(f"{YELLOW}⚠  No images found in '{DEFAULT_INPUT_DIR}'.{RESET}")
            print(f"{CYAN}   Just drop your PNG/JPG/WEBP files into the `input/` folder and run again!{RESET}")
            sys.exit(0)

        if skipped:
            print(f"{YELLOW}  Skipping {len(skipped)} non-image file(s): "
                  f"{', '.join(f.name for f in skipped)}{RESET}")

        print(f"{BOLD}Found {len(image_files)} image(s) to process...{RESET}\n")

        results  = []
        skipped_already = []  # images whose thumbnails already exist
        for idx, img_path in enumerate(image_files, 1):
            out_path = default_output_path(img_path, DEFAULT_OUTPUT_DIR)

            # ── Skip if thumbnail already exists (unless --force) ──────────
            if out_path.exists() and not args.force:
                print(f"{YELLOW}[{idx}/{len(image_files)}] Skipping (already done): {img_path.name}{RESET}")
                skipped_already.append(img_path)
                continue

            print(f"{CYAN}[{idx}/{len(image_files)}] Processing: {img_path.name}{RESET}")
            result = create_thumbnail(
                input_path  = img_path,
                output_path = out_path,
                width       = args.width,
                height      = args.height,
                quality     = args.quality,
                max_size_kb = args.max_size,
                verbose     = verbose,
            )
            print_result_summary(result)
            print()
            results.append(result)

        if skipped_already:
            print(f"{YELLOW}  ↩ {len(skipped_already)} image(s) skipped (thumbnail already exists). Use --force to re-process.{RESET}\n")

        if results:
            print_batch_summary(results)
        elif not skipped_already:
            print(f"{YELLOW}⚠ Nothing to process.{RESET}")
        return

    # ── BATCH MODE ──────────────────────────────────────────────────────────
    if args.input_dir:
        input_dir = args.input_dir

        if not input_dir.exists() or not input_dir.is_dir():
            print(f"{RED}✗ Error: --input-dir '{input_dir}' does not exist or is not a folder.{RESET}")
            sys.exit(1)

        output_dir = args.output_dir if args.output_dir else input_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        # Collect all image files in the directory (non-recursive)
        all_files   = sorted(input_dir.iterdir())
        image_files = [f for f in all_files if f.is_file() and is_image_file(f)]
        skipped     = [f for f in all_files if f.is_file() and not is_image_file(f)]

        if not image_files:
            print(f"{YELLOW}⚠ No supported image files found in '{input_dir}'.{RESET}")
            sys.exit(0)

        print(f"{BOLD}Batch mode: {len(image_files)} image(s) found in '{input_dir}'{RESET}")
        if skipped:
            print(f"{YELLOW}  Skipping {len(skipped)} non-image file(s): "
                  f"{', '.join(f.name for f in skipped)}{RESET}")
        print()

        results = []
        skipped_already = []  # images whose thumbnails already exist
        for idx, img_path in enumerate(image_files, 1):
            out_path = default_output_path(img_path, output_dir)

            # ── Skip if thumbnail already exists (unless --force) ──────────
            if out_path.exists() and not args.force:
                print(f"{YELLOW}[{idx}/{len(image_files)}] Skipping (already done): {img_path.name}{RESET}")
                skipped_already.append(img_path)
                continue

            print(f"{CYAN}[{idx}/{len(image_files)}] Processing: {img_path.name}{RESET}")

            result = create_thumbnail(
                input_path  = img_path,
                output_path = out_path,
                width       = args.width,
                height      = args.height,
                quality     = args.quality,
                max_size_kb = args.max_size,
                verbose     = verbose,
            )
            print_result_summary(result)
            print()
            results.append(result)

        if skipped_already:
            print(f"{YELLOW}  ↩ {len(skipped_already)} image(s) skipped (thumbnail already exists). Use --force to re-process.{RESET}\n")

        if results:
            print_batch_summary(results)
        elif not skipped_already:
            print(f"{YELLOW}⚠ Nothing to process.{RESET}")

    # ── SINGLE FILE MODE ────────────────────────────────────────────────────
    else:
        input_path = args.input

        # Determine output path
        if args.output:
            output_path = args.output
            # Ensure the output has a .webp extension
            if output_path.suffix.lower() != ".webp":
                output_path = output_path.with_suffix(".webp")
        else:
            output_path = default_output_path(input_path)

        print(f"{BOLD}Processing: {input_path.name}{RESET}")
        print()

        result = create_thumbnail(
            input_path  = input_path,
            output_path = output_path,
            width       = args.width,
            height      = args.height,
            quality     = args.quality,
            max_size_kb = args.max_size,
            verbose     = verbose,
        )

        if not result["success"]:
            print(f"{RED}✗ Error: {result['error']}{RESET}")
            sys.exit(1)

        print_result_summary(result)
        print()
        print(f"{GREEN}✓ Saved to: {output_path.resolve()}{RESET}")


if __name__ == "__main__":
    main()
