"""
EXIF metadata analyzer.

Extracts technical metadata from images (camera info, GPS, etc.).
"""

from pathlib import Path
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

from ingest_core.analyzers.base import BaseAnalyzer, AnalyzerResult


class EXIFAnalyzer(BaseAnalyzer):
    """
    Extract EXIF metadata from images.

    Extracts:
    - Image dimensions and color mode
    - Camera make/model
    - Exposure settings (aperture, shutter, ISO)
    - GPS coordinates
    - Date taken
    """

    name = "exif"
    supported_types = ["image"]

    async def analyze(self, file_path: Path, asset_type: str, **kwargs) -> AnalyzerResult:
        """Extract EXIF metadata from image."""
        try:
            with Image.open(file_path) as img:
                # Basic image info
                data = {
                    "width": img.width,
                    "height": img.height,
                    "aspect_ratio": round(img.width / img.height, 3),
                    "color_mode": img.mode,
                    "format": img.format,
                    "has_alpha": img.mode in ("RGBA", "LA", "PA"),
                    "is_landscape": img.width > img.height,
                    "is_portrait": img.height > img.width,
                    "is_square": img.width == img.height,
                }

                # Extract EXIF data
                exif_data = img._getexif()
                if exif_data:
                    parsed_exif = self._parse_exif(exif_data)
                    data.update(parsed_exif)

                return AnalyzerResult(
                    analyzer_name=self.name,
                    success=True,
                    data=data,
                )

        except Exception as e:
            return AnalyzerResult(
                analyzer_name=self.name,
                success=False,
                error=str(e),
            )

    def _parse_exif(self, exif_data: dict) -> dict:
        """Parse EXIF data into readable format."""
        parsed = {}

        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)

            if tag == "Make":
                parsed["camera_make"] = str(value).strip()
            elif tag == "Model":
                parsed["camera_model"] = str(value).strip()
            elif tag == "FocalLength":
                parsed["focal_length"] = float(value) if value else None
            elif tag == "FNumber":
                parsed["aperture"] = float(value) if value else None
            elif tag == "ISOSpeedRatings":
                parsed["iso"] = int(value) if value else None
            elif tag == "ExposureTime":
                parsed["shutter_speed"] = str(value)
            elif tag == "DateTimeOriginal":
                parsed["date_taken"] = str(value)
            elif tag == "GPSInfo":
                gps = self._parse_gps(value)
                if gps:
                    parsed.update(gps)

        return parsed

    def _parse_gps(self, gps_info: dict) -> dict | None:
        """Parse GPS coordinates from EXIF."""
        try:
            def convert_to_degrees(value):
                d, m, s = value
                return float(d) + float(m) / 60 + float(s) / 3600

            lat = gps_info.get(2)  # GPSLatitude
            lat_ref = gps_info.get(1)  # GPSLatitudeRef
            lon = gps_info.get(4)  # GPSLongitude
            lon_ref = gps_info.get(3)  # GPSLongitudeRef

            if lat and lon:
                latitude = convert_to_degrees(lat)
                longitude = convert_to_degrees(lon)

                if lat_ref == "S":
                    latitude = -latitude
                if lon_ref == "W":
                    longitude = -longitude

                return {
                    "gps_latitude": round(latitude, 6),
                    "gps_longitude": round(longitude, 6),
                }
        except Exception:
            pass

        return None