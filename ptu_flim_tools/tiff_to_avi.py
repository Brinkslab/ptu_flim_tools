import pathlib

import numpy as np
import tifffile


def _save_video_skvideo(data, output_dir, name):
    path = output_dir.joinpath(f"video_{name}.avi")
    skvideo.io.vwrite(path, data)  # skvideo defaults are not lossless!
    return path


def _save_video_cv2(data, output_dir, name):
    path = output_dir.joinpath(f"video_{name}.avi")
    fourcc = cv2.VideoWriter.fourcc("F", "F", "V", "1")  # lossless compression
    writer = cv2.VideoWriter(str(path), fourcc, 1, data.shape[1:], False)
    for frame in data:
        writer.write(frame)

    return path


try:
    import cv2
except ImportError:
    try:
        import skvideo.io
    except ImportError:
        raise RuntimeError(
            "a video writing library is required, either python-opencv or "
            "scikit-video needs to be installed"
        ) from None
    else:
        _save_video = _save_video_skvideo
else:
    _save_video = _save_video_cv2


def tiff_to_avi(tiff_path):
    path = pathlib.Path(tiff_path)
    with tifffile.TiffFile(path) as fp:
        array = fp.asarray()

    if len(array.shape) != 3:
        raise ValueError(
            f"tiff file at {tiff_path} does not contain a stack of 2d images, "
            f"it instead has shape {array.shape}"
        )

    top = array.max()
    scale = 0
    if top:
        scale = 0xFF / top
        array = np.multiply(array, scale).astype(np.uint8)

    return _save_video(array, path.parent, path.stem), scale, len(array)


def _main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("tiff_file")
    args = parser.parse_args()

    path, scale, frames = tiff_to_avi(args.tiff_file)
    size = round(path.stat().st_size / 10**6, 2)
    print(
        f"wrote to {path}, contrast scaled {scale} times, "
        f"{frames} frames, {size} mb"
    )


if __name__ == "__main__":
    _main()
