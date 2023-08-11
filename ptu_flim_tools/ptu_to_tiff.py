"""convert a ptu file to three tiff files
"""
import logging
import pathlib

import numpy as np
import tifffile

from .third_party.readPTU_FLIM.readPTU_FLIM import PTUreader


def _get_lifetime_image(data):
    work_data = data[:, :, 0, :]
    size = len(data[0, 0, 0])
    bin_range = np.reshape(np.linspace(0, size, size), (1, 1, size))
    mult = np.sum(work_data * bin_range, axis=2)
    summed = np.sum(work_data, axis=2)
    not_zero = summed != 0  # avoid dividing by zero
    return np.divide(mult, summed, out=np.zeros(summed.shape), where=not_zero)


def _write_tiff(name, data, output_dir, stem, comment=None):
    logging.info(f"writing {name} as compressed tiff")
    tif_path = output_dir / f"{name}_{stem}.tif"
    tifffile.imwrite(
        tif_path,
        data,
        photometric="minisblack",
        compression="zlib",
        compressionargs={"level": 8},
        predictor=True,
        description=comment,
    )
    size = round(tif_path.stat().st_size / 10**6, 2)
    logging.info(f"created {tif_path}, {size} mb")


def ptu_to_tiff(ptu_path, output_dir=None):
    """convert a ptu file to three tiff files

    ptu_path: location of file to read
    output_dir: where to write the tiff files to, defaults to the same
        directory as ptu_file

    will write a tiff file named stack.tif, containing each frame; a tiff
    file named sum.tif, containing the total intensity value per pixel; and a
    tiff file named lifetime.tif, containing the calculated lifetime images; to
    the output_dir
    """
    path = pathlib.Path(ptu_path)
    if output_dir is None:
        output_dir = path.parent
    else:
        output_dir = pathlib.Path(output_dir)

    ptu_file = PTUreader(str(path))
    comment = f"""sync = {[*ptu_file.sync]}
tcspc = {[*ptu_file.tcspc]}
channel = {[*ptu_file.channel]}
special = {[*ptu_file.special]}
"""
    # NOTE: getting data stack destroys info in object
    stack, cumulative = ptu_file.get_flim_data_stack()
    del ptu_file

    logging.info("converting to 8bit")
    if np.max(stack) > 0xFF or np.max(cumulative) > 0xFF:
        raise RuntimeError("data can't be converted to 8 bit")

    stack = stack.astype(np.uint8)
    cumulative = cumulative.astype(np.uint8)
    lifetime = _get_lifetime_image(stack)

    view = stack[:, :, 0]
    data = np.moveaxis(view, 2, 0)
    size = round(data.size / 10**6, 2)
    logging.info(f"stack shape {data.shape}, {size} mb, {data.dtype}")

    _write_tiff("stack", data, output_dir, path.stem, comment)
    _write_tiff("sum", cumulative, output_dir, path.stem)
    _write_tiff("lifetime", lifetime, output_dir, path.stem)


def _main():
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s:%(levelname)s:%(name)s:%(message)s",
    )

    parser = argparse.ArgumentParser()
    parser.add_argument("ptu_path")
    parser.add_argument("output_dir", nargs="?")
    args = parser.parse_args()

    ptu_to_tiff(args.ptu_path, args.output_dir)


if __name__ == "__main__":
    _main()
