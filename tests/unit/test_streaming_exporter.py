import os
import zipfile
from pathlib import Path

from photo_cleaner.exporter import StreamingExporter


def _make_dummy_files(base: Path, sizes_mb):
    files = []
    base.mkdir(parents=True, exist_ok=True)
    for idx, size_mb in enumerate(sizes_mb):
        path = base / f"dummy_{idx + 1}.bin"
        path.write_bytes(os.urandom(int(size_mb * 1024 * 1024)))
        files.append(path)
    return files


def test_streaming_exporter_writes_zip(tmp_path):
    source_dir = tmp_path / "src"
    output_dir = tmp_path / "out"
    files = _make_dummy_files(source_dir, [0.25, 0.5, 0.75])

    exporter = StreamingExporter(output_dir)
    progress = []

    success, failure, errors, archive_path, cancelled = exporter.export_files_streaming(
        files,
        progress_callback=lambda current, total, name: progress.append((current, total, name)),
    )

    assert success == 3
    assert failure == 0
    assert errors == []
    assert cancelled is False
    assert archive_path.exists()
    with zipfile.ZipFile(archive_path, "r") as zf:
        names = zf.namelist()
        assert sorted(names) == [f"dummy_{i}.bin" for i in range(1, 4)]
        for name in names:
            with zf.open(name) as zf_file:
                assert len(zf_file.read()) > 0

    assert progress[-1][0] == 3
    assert progress[-1][1] == 3


def test_streaming_exporter_can_cancel_mid_run(tmp_path):
    source_dir = tmp_path / "src"
    output_dir = tmp_path / "out"
    files = _make_dummy_files(source_dir, [0.25, 0.25, 0.25])

    exporter = StreamingExporter(output_dir)

    def progress_callback(current, total, name):
        if current == 1:
            exporter.request_cancel()

    success, failure, errors, archive_path, cancelled = exporter.export_files_streaming(
        files,
        progress_callback=progress_callback,
    )

    assert cancelled is True
    assert success == 1
    assert failure == 0
    assert errors == []
    with zipfile.ZipFile(archive_path, "r") as zf:
        names = zf.namelist()
        assert names == ["dummy_1.bin"]
