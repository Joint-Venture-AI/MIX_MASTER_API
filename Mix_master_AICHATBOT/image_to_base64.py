import argparse
import base64
import io

from PIL import Image


def image_to_base64(image_path, resize=True, max_size=1024, output_file=None):
    """
    Convert an image to base64 encoding

    Args:
        image_path (str): Path to the image file
        resize (bool): Whether to resize the image if it's too large
        max_size (int): Maximum dimension (width or height) for resizing
        output_file (str): Optional file to save the base64 string to

    Returns:
        str: Base64 encoded image string
    """
    try:
        # Open and optionally resize the image
        img = Image.open(image_path)

        if resize and max(img.size) > max_size:
            ratio = max_size / max(img.size)
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            print(f"Resizing image from {img.size} to {new_size}")
            img = img.resize(new_size, Image.LANCZOS)

        # Convert to JPEG and encode
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        img_bytes = buffer.getvalue()

        # Encode to base64
        base64_str = base64.b64encode(img_bytes).decode("utf-8")

        # Add data URL prefix
        data_url = f"data:image/jpeg;base64,{base64_str}"

        # Save to file if requested
        if output_file:
            with open(output_file, "w") as f:
                f.write(data_url)
            print(f"Base64 string saved to {output_file}")

        # Print stats
        print(f"Original image size: {len(img_bytes):,} bytes")
        print(f"Base64 string length: {len(data_url):,} characters")

        return data_url

    except Exception as e:
        print(f"Error: {str(e)}")
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert an image to base64 for API testing"
    )
    parser.add_argument("image", help="Path to the image file")
    parser.add_argument("--output", "-o", help="Output file to save the base64 string")
    parser.add_argument(
        "--no-resize", action="store_true", help="Do not resize the image"
    )
    parser.add_argument(
        "--max-size", type=int, default=1024, help="Maximum dimension for resizing"
    )

    args = parser.parse_args()

    base64_str = image_to_base64(
        args.image,
        resize=not args.no_resize,
        max_size=args.max_size,
        output_file=args.output,
    )

    if base64_str:
        print("\nBase64 string (first 100 chars):")
        print(base64_str[:100] + "...")
        print("\nUse this string in the 'image' field of your API request")

        if not args.output:
            print("\nTip: Use the --output option to save the full string to a file")
