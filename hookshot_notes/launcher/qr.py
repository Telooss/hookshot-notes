import qrcode
import qrcode.image.svg


def svg(url: str) -> str:
    return qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage, border=2).to_string(encoding="unicode")
