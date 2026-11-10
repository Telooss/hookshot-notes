IMAGE_W, IMAGE_H = 2000, 1440


def project(x: float, z: float, cam: dict) -> tuple[float, float]:
    """World (x, z) to map-image pixels. `cam` = {"x", "z", "height"} from MapCaptureInfo;
    `height` is the capture's horizontal extent in world units (checked on dungeon floors and field exits)."""
    s = IMAGE_W / cam["height"]
    return IMAGE_W / 2 + (x - cam["x"]) * s, IMAGE_H / 2 + (z - cam["z"]) * s
