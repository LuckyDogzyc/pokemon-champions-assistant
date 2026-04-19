import base64

from app.services import roi_capture


def _make_ppm_preview_data_url(width=4, height=3):
    header = f'P6\n{width} {height}\n255\n'.encode('ascii')
    pixels = bytearray()
    for y in range(height):
        for x in range(width):
            pixels.extend(((x * 20) % 256, (y * 40) % 256, ((x + y) * 60) % 256))
    return 'data:image/x-portable-pixmap;base64,' + base64.b64encode(header + bytes(pixels)).decode('ascii')


class _StubEncoded:
    def tobytes(self):
        return b'jpeg-crop'


class _StubImage:
    shape = (3, 4, 3)

    def __getitem__(self, key):
        return self


class _StubCv2:
    IMWRITE_JPEG_QUALITY = 1

    @staticmethod
    def imdecode(buffer, flags):
        return _StubImage()

    @staticmethod
    def imencode(ext, image, params=None):
        assert ext == '.jpg'
        return True, _StubEncoded()


def test_crop_preview_image_data_url_falls_back_to_cv2_when_ffmpeg_missing(monkeypatch):
    monkeypatch.setattr(roi_capture.shutil, 'which', lambda name: None)
    monkeypatch.setattr(roi_capture, 'cv2', _StubCv2, raising=False)

    cropped = roi_capture.crop_preview_image_data_url(
        _make_ppm_preview_data_url(),
        {'left': 1, 'top': 1, 'width': 2, 'height': 2},
    )

    assert cropped == 'data:image/jpeg;base64,anBlZy1jcm9w'
